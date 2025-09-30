import uuid
import threading
import queue
import json
# 获取当前应用实例，传递给后台线程
from flask import current_app
from datetime import datetime
from typing import Dict, Any, Optional
from app.models import Task, TaskLog, TaskResult, db
from app.services.google_sheet_service import GoogleSheetService
from app.utils.logger import get_logger
from app.utils.database import transaction_required, safe_delete, safe_update, safe_create

logger = get_logger(__name__)

class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.running_tasks: Dict[str, threading.Thread] = {}
        self.task_events: Dict[str, queue.Queue] = {}
        self.max_concurrent_tasks = 5
    
    @transaction_required
    def create_task(self, name: str, description: str, task_type: str, config: Dict[str, Any]) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())
        
        # 确保配置被正确序列化
        config_str = json.dumps(config) if isinstance(config, dict) else str(config)
        
        task = safe_create(
            Task,
            id=task_id,
            name=name,
            description=description,
            task_type=task_type,
            config=config_str,
            status='pending'
        )
        
        logger.info(f"创建任务: {task_id} - {name}")
        return task_id
    
    def start_task(self, task_id: str) -> bool:
        """启动任务"""
        if len(self.running_tasks) >= self.max_concurrent_tasks:
            logger.warning(f"任务队列已满，无法启动任务: {task_id}")
            return False
        
        task = Task.query.get(task_id)
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return False
        
        if task.status != 'pending':
            logger.warning(f"任务状态不是pending，无法启动: {task_id}")
            return False
        
        # 创建事件队列
        self.task_events[task_id] = queue.Queue()
        

        app = current_app._get_current_object()
        
        # 根据任务类型启动相应的执行器
        if task.task_type == 'google_sheet':
            thread = threading.Thread(target=self._execute_google_sheet_task, args=(task_id, app))
        else:
            logger.error(f"不支持的任务类型: {task.task_type}")
            return False
        
        thread.daemon = True
        self.running_tasks[task_id] = thread
        thread.start()
        
        logger.info(f"启动任务: {task_id}")
        return True
    
    @transaction_required
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = Task.query.get(task_id)
        if not task:
            return False
        
        if task.status in ['completed', 'cancelled', 'error']:
            return False
        
        # 使用safe_update更新任务状态
        safe_update(task, commit=False, status='cancelled', end_time=datetime.now())
        
        # 清理资源
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]
        if task_id in self.task_events:
            del self.task_events[task_id]
        
        self._add_task_log(task_id, 'info', f'任务已取消')
        logger.info(f"取消任务: {task_id}")
        return True
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = Task.query.get(task_id)
        if not task:
            return None
        
        return task.to_dict()
    
    def get_all_tasks(self) -> list:
        """获取所有任务"""
        tasks = Task.query.order_by(Task.created_at.desc()).all()
        return [task.to_dict() for task in tasks]
    
    def check_local_task_status(self, task_id: str) -> Dict[str, Any]:
        """检查本地任务状态，识别可能挂死的任务"""
        task = Task.query.get(task_id)
        if not task:
            return {"status": "not_found", "message": "任务不存在"}
        
        # 检查数据库状态
        db_status = task.status
        
        # 检查内存中是否还有运行的线程
        memory_running = task_id in self.running_tasks
        
        # 获取最新的任务结果和日志
        latest_result = TaskResult.query.filter_by(task_id=task_id).order_by(TaskResult.timestamp.desc()).first()
        latest_log = TaskLog.query.filter_by(task_id=task_id).order_by(TaskLog.timestamp.desc()).first()
        
        # 判断任务状态
        status_check = {
            "task_id": task_id,
            "db_status": db_status,
            "memory_running": memory_running,
            "current_step": task.current_step,
            "total_steps": task.total_steps,
            "latest_result_time": latest_result.timestamp.isoformat() if latest_result else None,
            "latest_log_time": latest_log.timestamp.isoformat() if latest_log else None,
            "can_restart": False,
            "restart_reason": None
        }
        
        # 识别可能需要重启的情况
        if db_status == 'running' and not memory_running:
            status_check["can_restart"] = True
            status_check["restart_reason"] = "任务在数据库中显示为运行状态，但内存中没有对应的线程"
        elif db_status == 'running' and memory_running:
            # 检查是否长时间没有更新（超过10分钟）
            import datetime
            now = datetime.datetime.now()
            if latest_log:
                time_diff = now - latest_log.timestamp
                if time_diff.total_seconds() > 600:  # 10分钟
                    status_check["can_restart"] = True
                    status_check["restart_reason"] = f"任务超过10分钟没有日志更新，可能已挂死"
            else:
                status_check["restart_reason"] = "任务正在正常运行"
        else:
            # 为非运行状态提供状态描述
            if db_status == 'pending':
                status_check["restart_reason"] = "任务处于待执行状态"
            elif db_status == 'completed':
                status_check["restart_reason"] = "任务已完成"
            elif db_status == 'error':
                status_check["restart_reason"] = "任务执行出错"
            elif db_status == 'cancelled':
                status_check["restart_reason"] = "任务已被取消"
            else:
                status_check["restart_reason"] = f"任务状态: {db_status}"
        
        return status_check
    
    def restart_task(self, task_id: str, resume_from_checkpoint: bool = True) -> Dict[str, Any]:
        """重启任务"""
        try:
            task = Task.query.get(task_id)
            if not task:
                return {"status": "error", "message": "任务不存在"}
            
            # 检查任务状态
            status_check = self.check_local_task_status(task_id)
            
            # 检查是否可以重启（放宽条件，允许pending、completed、error、cancelled状态的任务重启）
            if task.status == 'running':
                # 如果任务正在运行，检查是否真的在运行
                if not status_check.get("can_restart", False):
                    return {"status": "error", "message": "任务正在运行中，无法重启"}
            elif task.status not in ['pending', 'completed', 'error', 'cancelled']:
                return {"status": "error", "message": f"任务状态 '{task.status}' 不允许重启"}
            
            # 停止现有任务（如果在运行）
            if task_id in self.running_tasks:
                try:
                    self.cancel_task(task_id)
                    logger.info(f"已停止原有任务线程: {task_id}")
                except Exception as e:
                    logger.warning(f"停止原有任务线程失败: {str(e)}")
            
            # 清理任务状态
            if task_id in self.task_events:
                del self.task_events[task_id]
            
            # 根据断点恢复设置，决定从哪里开始
            if resume_from_checkpoint:
                # 从断点继续，保持current_step
                restart_step = task.current_step
                self._add_task_log(task_id, 'info', f'从断点重启任务，从第 {restart_step} 步继续')
            else:
                # 从头开始
                restart_step = 0
                task.current_step = 0
                self._add_task_log(task_id, 'info', '重新开始任务，从第 1 步开始')
            
            # 重置任务状态
            safe_update(task, commit=False, status='pending', error_message=None, end_time=None)
            
            # 重新启动任务
            success = self.start_task(task_id)
            
            if success:
                # 确定重启原因
                restart_reason = status_check.get("restart_reason")
                if not restart_reason:
                    if task.status == 'pending':
                        restart_reason = "用户手动重启待执行任务"
                    elif task.status == 'completed':
                        restart_reason = "用户手动重启已完成任务"
                    elif task.status == 'error':
                        restart_reason = "用户手动重启错误任务"
                    elif task.status == 'cancelled':
                        restart_reason = "用户手动重启已取消任务"
                    else:
                        restart_reason = "用户手动重启"
                
                self._add_task_log(task_id, 'info', f'任务重启成功，原因: {restart_reason}')
                return {
                    "status": "success", 
                    "message": "任务重启成功",
                    "restart_from_step": restart_step,
                    "restart_reason": restart_reason
                }
            else:
                return {"status": "error", "message": "任务重启失败"}
                
        except Exception as e:
            logger.error(f"重启任务失败: {task_id}, 错误: {str(e)}")
            return {"status": "error", "message": f"重启任务失败: {str(e)}"}
    
    def create_restart_task(self, original_task_id: str) -> str:
        """基于原任务创建新的重启任务"""
        try:
            original_task = Task.query.get(original_task_id)
            if not original_task:
                raise ValueError("原任务不存在")
            
            # 创建新的任务ID
            new_task_id = str(uuid.uuid4())
            
            # 复制原任务配置
            original_config = json.loads(original_task.config) if isinstance(original_task.config, str) else original_task.config
            
            # 创建新任务，名称添加重启标识
            new_task = Task(
                id=new_task_id,
                name=f"{original_task.name} (重启)",
                description=f"基于任务 {original_task_id} 重启",
                task_type=original_task.task_type,
                config=json.dumps(original_config),
                status='pending'
            )
            
            db.session.add(new_task)
            db.session.commit()
            
            logger.info(f"创建重启任务: {new_task_id} (基于 {original_task_id})")
            return new_task_id
            
        except Exception as e:
            logger.error(f"创建重启任务失败: {str(e)}")
            raise
    
    def get_task_logs(self, task_id: str) -> list:
        """获取任务日志"""
        logs = TaskLog.query.filter_by(task_id=task_id).order_by(TaskLog.timestamp.asc()).all()
        return [log.to_dict() for log in logs]
    
    def get_task_results(self, task_id: str) -> list:
        """获取任务结果"""
        results = TaskResult.query.filter_by(task_id=task_id).order_by(TaskResult.step_index.asc()).all()
        return [result.to_dict() for result in results]
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务及其相关数据"""
        try:
            with current_app.app_context():
                # 检查任务是否存在
                task = Task.query.get(task_id)
                if not task:
                    logger.warning(f"任务不存在: {task_id}")
                    return False
                
                # 如果任务正在运行，先取消任务
                if task.status == 'running':
                    # 直接更新状态，避免嵌套事务
                    task.status = 'cancelled'
                    task.end_time = datetime.now()
                
                # 删除任务结果
                TaskResult.query.filter_by(task_id=task_id).delete()
                
                # 删除任务日志
                TaskLog.query.filter_by(task_id=task_id).delete()
                
                # 删除任务本身
                db.session.delete(task)
                
                # 提交事务
                db.session.commit()
                
                # 清理内存中的任务事件队列
                if task_id in self.task_events:
                    del self.task_events[task_id]
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]
                
                logger.info(f"任务删除成功: {task_id}")
                return True
                
        except Exception as e:
            logger.error(f"删除任务失败: {task_id}, 错误: {str(e)}")
            db.session.rollback()
            return False
    
    def _execute_google_sheet_task(self, task_id: str, app):
        """执行Google Sheet任务"""
        try:
            # 使用传递的应用实例创建应用上下文
            with app.app_context():
                task = Task.query.get(task_id)
                if not task:
                    return
                
                # 更新任务状态
                task.status = 'running'
                task.start_time = datetime.now()
                db.session.commit()
                
                self._add_task_log(task_id, 'info', '开始执行Google Sheet任务', app)
                
                # 创建Google Sheet服务
                config = task.config
                service = GoogleSheetService(config,task_id, self.task_events.get(task_id), app)
                
                # 执行任务
                success = service.execute_task()
                
                # 检查任务当前状态（可能在执行过程中被取消）
                task = Task.query.get(task_id)
                if task and task.status == 'cancelled':
                    # 任务已被取消，保持cancelled状态
                    task.end_time = datetime.now()
                    db.session.commit()
                    self._add_task_log(task_id, 'info', f'任务执行完成，状态: cancelled（任务被取消）', app)
                else:
                    # 根据执行结果更新状态
                    task.status = 'completed' if success else 'error'
                    task.end_time = datetime.now()
                    db.session.commit()
                    self._add_task_log(task_id, 'info', f'任务执行完成，状态: {task.status}', app)
            
        except Exception as e:
            logger.error(f"执行任务失败: {task_id}, 错误: {str(e)}")
            
            # 更新任务状态为错误
            try:
                with app.app_context():
                    task = Task.query.get(task_id)
                    if task:
                        task.status = 'error'
                        task.error_message = str(e)
                        task.end_time = datetime.now()
                        db.session.commit()
            except:
                pass
            
            self._add_task_log(task_id, 'error', f'任务执行失败: {str(e)}', app)
        
        finally:
            # 清理资源
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            if task_id in self.task_events:
                del self.task_events[task_id]
    
    def _add_task_log(self, task_id: str, level: str, message: str, app=None):
        """添加任务日志"""
        try:
            if app:
                # 在后台线程中使用传递的应用实例
                with app.app_context():
                    log = TaskLog(
                        task_id=task_id,
                        level=level,
                        message=message
                    )
                    db.session.add(log)
                    db.session.commit()
            else:
                # 在主线程中使用当前应用上下文
                from flask import current_app
                with current_app.app_context():
                    log = TaskLog(
                        task_id=task_id,
                        level=level,
                        message=message
                    )
                    db.session.add(log)
                    db.session.commit()
        except Exception as e:
            logger.error(f"添加任务日志失败: {str(e)}")
    

# 全局任务管理器实例
task_manager = TaskManager()
