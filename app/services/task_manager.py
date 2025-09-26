import uuid
import threading
import queue
from datetime import datetime
from typing import Dict, Any, Optional
from app.models import Task, TaskLog, TaskResult, db
from app.services.google_sheet_service import GoogleSheetService
from app.utils.logger import get_logger

logger = get_logger(__name__)

class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.running_tasks: Dict[str, threading.Thread] = {}
        self.task_events: Dict[str, queue.Queue] = {}
        self.max_concurrent_tasks = 5
    
    def create_task(self, name: str, description: str, task_type: str, config: Dict[str, Any]) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())
        
        task = Task(
            id=task_id,
            name=name,
            description=description,
            task_type=task_type,
            config=config,
            status='pending'
        )
        
        db.session.add(task)
        db.session.commit()
        
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
        
        # 根据任务类型启动相应的执行器
        if task.task_type == 'google_sheet':
            thread = threading.Thread(target=self._execute_google_sheet_task, args=(task_id,))
        else:
            logger.error(f"不支持的任务类型: {task.task_type}")
            return False
        
        thread.daemon = True
        self.running_tasks[task_id] = thread
        thread.start()
        
        logger.info(f"启动任务: {task_id}")
        return True
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = Task.query.get(task_id)
        if not task:
            return False
        
        if task.status in ['completed', 'cancelled', 'error']:
            return False
        
        task.status = 'cancelled'
        task.end_time = datetime.utcnow()
        db.session.commit()
        
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
    
    def get_task_logs(self, task_id: str) -> list:
        """获取任务日志"""
        logs = TaskLog.query.filter_by(task_id=task_id).order_by(TaskLog.timestamp.asc()).all()
        return [log.to_dict() for log in logs]
    
    def get_task_results(self, task_id: str) -> list:
        """获取任务结果"""
        results = TaskResult.query.filter_by(task_id=task_id).order_by(TaskResult.step_index.asc()).all()
        return [result.to_dict() for result in results]
    
    def _execute_google_sheet_task(self, task_id: str):
        """执行Google Sheet任务"""
        try:
            task = Task.query.get(task_id)
            if not task:
                return
            
            # 更新任务状态
            task.status = 'running'
            task.start_time = datetime.utcnow()
            db.session.commit()
            
            self._add_task_log(task_id, 'info', '开始执行Google Sheet任务')
            
            # 创建Google Sheet服务
            config = task.config
            service = GoogleSheetService(config)
            
            # 执行任务
            success = service.execute_task(task_id, self.task_events.get(task_id))
            
            # 更新任务状态
            task.status = 'completed' if success else 'error'
            task.end_time = datetime.utcnow()
            db.session.commit()
            
            self._add_task_log(task_id, 'info', f'任务执行完成，状态: {task.status}')
            
        except Exception as e:
            logger.error(f"执行任务失败: {task_id}, 错误: {str(e)}")
            
            # 更新任务状态为错误
            task = Task.query.get(task_id)
            if task:
                task.status = 'error'
                task.error_message = str(e)
                task.end_time = datetime.utcnow()
                db.session.commit()
            
            self._add_task_log(task_id, 'error', f'任务执行失败: {str(e)}')
        
        finally:
            # 清理资源
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            if task_id in self.task_events:
                del self.task_events[task_id]
    
    def _add_task_log(self, task_id: str, level: str, message: str):
        """添加任务日志"""
        try:
            log = TaskLog(
                task_id=task_id,
                level=level,
                message=message
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            logger.error(f"添加任务日志失败: {str(e)}")
    
    def _add_task_result(self, task_id: str, step_index: int, parameters: Dict, result: Dict, success: bool, error_message: str = None):
        """添加任务结果"""
        try:
            task_result = TaskResult(
                task_id=task_id,
                step_index=step_index,
                parameters=parameters,
                result=result,
                success=success,
                error_message=error_message
            )
            db.session.add(task_result)
            db.session.commit()
        except Exception as e:
            logger.error(f"添加任务结果失败: {str(e)}")

# 全局任务管理器实例
task_manager = TaskManager()
