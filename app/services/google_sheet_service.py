import json
import time
import itertools
from typing import Dict, Any, Optional, List
from app.models import Task, TaskLog, TaskResult, db
from app.utils.logger import get_logger
from app.services.google_sheet_client import GoogleSheet

logger = get_logger(__name__)

class GoogleSheetService:
    """Google Sheet服务"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.google_sheet = None
    
    def execute_task(self, task_id: str, event_queue=None) -> bool:
        """执行Google Sheet任务"""
        try:
            task = Task.query.get(task_id)
            if not task:
                return False
            
            # 解析配置
            config_data = json.loads(task.config) if isinstance(task.config, str) else task.config
            
            # 初始化Google Sheet连接
            self._init_google_sheet(config_data)
            
            # 获取参数列表
            parameters = config_data.get('parameters', [])
            if not parameters:
                logger.error(f"任务 {task_id} 没有参数配置")
                return False
            
            # 生成参数组合
            combinations = list(itertools.product(*parameters))
            total_combinations = len(combinations)
            
            # 更新任务总步数
            task.total_steps = total_combinations
            db.session.commit()
            
            logger.info(f"任务 {task_id} 生成了 {total_combinations} 个参数组合")
            
            # 执行参数组合
            results = []
            for i, combination in enumerate(combinations):
                if task.status == 'cancelled':
                    logger.info(f"任务 {task_id} 已被取消")
                    return False
                
                # 更新当前步数
                task.current_step = i + 1
                db.session.commit()
                
                # 执行单个参数组合
                success, result = self._execute_parameter_combination(
                    task_id, i, combination, config_data, event_queue
                )
                
                results.append({
                    'combination': combination,
                    'success': success,
                    'result': result
                })
                
                # 保存结果到数据库
                self._save_task_result(task_id, i, combination, result, success)
                
                # 如果是第一次执行，等待确认
                if i == 0 and event_queue:
                    if not self._wait_for_confirmation(task_id, combination, result, event_queue):
                        logger.info(f"任务 {task_id} 第一次执行未获得确认，停止执行")
                        return False
            
            logger.info(f"任务 {task_id} 执行完成")
            return True
            
        except Exception as e:
            logger.error(f"执行Google Sheet任务失败: {task_id}, 错误: {str(e)}")
            return False
    
    def _init_google_sheet(self, config_data: Dict[str, Any]):
        """初始化Google Sheet连接"""
        try:
            spreadsheet_id = config_data.get('spreadsheet_id')
            sheet_name = config_data.get('sheet_name', 'data')
            token_file = config_data.get('token_file', 'data/token.json')
            proxy_url = config_data.get('proxy_url')
            
            if not spreadsheet_id:
                raise ValueError("缺少spreadsheet_id配置")
            
            self.google_sheet = GoogleSheet(spreadsheet_id, sheet_name, token_file, proxy_url)
            logger.info(f"Google Sheet连接成功: {spreadsheet_id}")
            
        except Exception as e:
            logger.error(f"初始化Google Sheet连接失败: {str(e)}")
            raise
    
    def _execute_parameter_combination(self, task_id: str, index: int, combination: List, config_data: Dict[str, Any], event_queue=None) -> tuple:
        """执行单个参数组合"""
        try:
            logger.info(f"执行第 {index + 1} 个参数组合: {combination}")
            
            # 获取参数位置配置
            param_positions = config_data.get('parameter_positions', {})
            
            # 准备要更新的单元格
            cell_updates = {}
            for i, (key, position) in enumerate(param_positions.items()):
                if i < len(combination):
                    cell_updates[position] = combination[i]
            
            # 批量更新单元格
            if self.google_sheet:
                self.google_sheet.update_jumped_cells(cell_updates)
                logger.info(f"参数已写入到表格: {cell_updates}")
            else:
                logger.error("Google Sheet连接未建立")
                return False, {}
            
            # 等待执行完成，检查指定位置
            check_positions = config_data.get('check_positions', {})
            result_positions = config_data.get('result_positions', {})
            
            # 定时检查是否完成（最多检查60次，每次间隔1分钟）
            for attempt in range(60):
                time.sleep(60)  # 等待1分钟
                logger.info(f"第 {attempt + 1} 次检查执行状态...")
                
                # 检查所有位置是否都有产出
                all_completed = True
                for key, position in check_positions.items():
                    try:
                        if self.google_sheet:
                            value = self.google_sheet.get_cell(position)
                            if value in ['#DIV/0!', ''] or 'target' in str(value):
                                all_completed = False
                                break
                    except Exception as e:
                        logger.error(f"检查位置 {position} 时出错: {str(e)}")
                        all_completed = False
                        break
                
                if all_completed:
                    logger.info("所有参数执行完成，获取结果...")
                    # 获取结果
                    results = {}
                    for key, position in result_positions.items():
                        try:
                            if self.google_sheet:
                                value = self.google_sheet.get_cell(position)
                                results[key] = value
                        except Exception as e:
                            logger.error(f"获取结果位置 {position} 时出错: {str(e)}")
                            results[key] = "获取失败"
                    
                    logger.info(f"执行结果: {results}")
                    return True, results
            
            logger.warning("执行超时，未在规定时间内完成")
            return False, {}
            
        except Exception as e:
            logger.error(f"执行参数组合时出错: {str(e)}")
            return False, {}
    
    def _wait_for_confirmation(self, task_id: str, combination: List, result: Dict, event_queue) -> bool:
        """等待前端确认"""
        if not event_queue:
            return True
        
        try:
            # 发送确认请求到前端
            event_queue.put({
                "type": "first_execution_complete",
                "data": {
                    "params": combination,
                    "results": result
                }
            })
            
            # 等待确认事件
            event = event_queue.get(timeout=300)  # 5分钟超时
            if event.get("type") == "confirmation" and event.get("data", {}).get("confirmed"):
                logger.info("收到前端确认，继续执行")
                return True
            else:
                logger.info("未收到确认或确认被拒绝，停止执行")
                return False
                
        except Exception as e:
            logger.error(f"等待确认时出错: {str(e)}")
            return False
    
    def _save_task_result(self, task_id: str, step_index: int, parameters: List, result: Dict, success: bool):
        """保存任务结果到数据库"""
        try:
            task_result = TaskResult(
                task_id=task_id,
                step_index=step_index,
                parameters=json.dumps(parameters),
                result=json.dumps(result),
                success=success
            )
            db.session.add(task_result)
            db.session.commit()
        except Exception as e:
            logger.error(f"保存任务结果失败: {str(e)}")
