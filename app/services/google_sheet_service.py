import json
import random
import time
from datetime import datetime
from typing import Dict, Any, List

from flask import current_app
from tenacity import retry, stop_after_attempt, wait_exponential

from app.models import Task, TaskLog, TaskResult, db
from app.services.google_sheet_client import GoogleSheet
from app.utils.db_stock_api import StockAPIClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleSheetService:
    """Google Sheet服务"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.google_sheet = None
        self.api_client = StockAPIClient()

    def execute_task(self, task_id: str, event_queue=None, app=None):
        """执行Google Sheet任务"""
        try:
            # 统一使用应用上下文
            context_app = app or current_app
            with context_app.app_context():
                task = Task.query.get(task_id)
                if not task:
                    self._push_log(task_id, 'error', f'任务 {task_id} 不存在', event_queue)
                    return False

                # 解析配置
                config_data = json.loads(task.config) if isinstance(task.config, str) else task.config

                # 推送任务开始日志
                self._push_log(task_id, 'info', '开始执行Google Sheet任务', event_queue)

                # 初始化Google Sheet连接
                self._init_google_sheet(config_data)

                # 获取参数列表
                parameters = config_data.get('parameters', [])
                if not parameters:
                    error_msg = f"任务 {task_id} 没有参数配置"
                    logger.error(error_msg)
                    self._push_log(task_id, 'error', error_msg, event_queue)
                    return False
                name = task.name
                sheet_code = config_data.get('sheet_name', "")

                # 默认参数值
                multiplier_value = 4
                danbian_value = 0.85
                xiancang_value = 0.24
                zhishu_value = 0.88
                smoothing_value = 0.08
                bordering_value = 0.38

                # 获取股票参数
                stock_param = self.get_single_stock_template_param(name)

                if stock_param is not None and stock_param != "error":
                    multiplier_index = 0 if stock_param.get('multiplier_index', 0) == 0 else stock_param.get(
                        'multiplier_index', 0) + 1
                    success_count, failed_count = self.get_bdl(task, task_id, event_queue, app, name, parameters,
                                                               config_data, multiplier_index)
                elif stock_param != "error":
                    cell_updates = {
                        "B6": multiplier_value,
                        "B7": danbian_value,
                        "B9": xiancang_value,
                        "B10": zhishu_value,
                        "B11": smoothing_value,
                        "B12": bordering_value
                    }
                    # 批量更新单元格
                    if self.google_sheet:
                        self.google_sheet.update_jumped_cells(cell_updates)
                        logger.info(f"参数已写入到表格: {cell_updates}")
                    else:
                        logger.error("Google Sheet连接未建立")
                        return False, {}
                    time.sleep(random.randint(20, 30))
                    success_count, failed_count = self.get_bdl(task, task_id, event_queue, app, name, parameters,
                                                               config_data)
                else:
                    logger.error("获取股票参数失败")

                # success_count, failed_count = self.get_bdl(task, task_id, event_queue, app, parameters, config_data)

                # 推送任务完成信息
                completion_msg = f'任务执行完成！成功: {success_count}, 失败: {failed_count}'
                self._push_log(task_id, 'info', completion_msg, event_queue)

                return True

        except Exception as e:
            error_msg = f"执行Google Sheet任务失败: {task_id}, 错误: {str(e)}"
            logger.error(error_msg)
            self._push_log(task_id, 'error', error_msg, event_queue)
            return False

    def get_bdl(self, task, task_id, event_queue, app, name, parameters, config_data, index_z=0):
        # 计算总参数组合数（不生成实际组合，避免内存问题）
        total_combinations = 1
        for param_list in parameters:
            total_combinations *= len(param_list)

        # 更新任务总步数
        task.total_steps = total_combinations
        db.session.commit()

        # 推送参数组合信息
        self._push_log(task_id, 'info', f'将执行 {total_combinations} 个参数组合', event_queue)

        # 执行参数组合
        success_count = 0
        failed_count = 0

        for i in range(index_z, total_combinations):
            # 按需计算参数组合，避免内存问题
            combination = self._get_parameter_combination_by_index(parameters, i)
            # 检查任务是否被取消
            task = Task.query.get(task_id)  # 重新获取任务状态
            if not task or task.status == 'cancelled':
                self._push_log(task_id, 'warning', f'任务 {task_id} 已被取消', event_queue)
                return False

            # 推送执行进度
            progress_msg = f'正在执行第 {i + 1}/{total_combinations} 个参数组合'
            self._push_log(task_id, 'info', progress_msg, event_queue)

            # 更新当前步数
            task.current_step = i + 1
            db.session.commit()

            # 执行单个参数组合
            try:
                success, result = self._execute_parameter_combination(
                    task_id, i, combination, config_data, event_queue
                )

                if success:
                    success_count += 1
                    self._push_log(task_id, 'info', f'第 {i + 1} 个参数组合执行成功，{result}', event_queue)
                else:
                    self._push_log(task_id, 'warning', f'第 {i + 1} 个参数组合执行失败', event_queue)
                    break

                param_load = {
                    "stock_no": name,
                    "multiplier": result['B6'],
                    "danbian": result['B7'],
                    "xiancang": result['B9'],
                    "zhishu": result['B10'],
                    "smoothing": result['B11'],
                    "bordering": result['B12'],
                    "multiplier_index": i,
                    "danbian_index": 0,
                    "xiancang_index": 0,
                    "zhishu_index": 0,
                    "smoothing_index": 0,
                    "bordering_index": 0,
                    "return_rate": result['I15'],
                    "annualized_rate": result['I16'],
                    "maxdd": result['I17'],
                    "index_rate": result['I18'],
                    "index_annualized_rate": result['I19'],
                    "max_index_dd": result['I20'],
                    "fee_total": result['I21'],
                    "fee_annualized": result['I22'],
                    "year_rate": result['I23']
                }
                # 保存结果到数据库
                self._save_task_result(task_id, i, combination, result, success, app)
                # 推送结果，到生产数据库
                self.send_stock_template_param_data(param_load)

            except Exception as e:
                failed_count += 1
                error_msg = f'第 {i + 1} 个参数组合执行出错: {str(e)}'
                logger.error(error_msg)
                self._push_log(task_id, 'error', error_msg, event_queue)

        return success_count, failed_count

    @retry(
        stop=stop_after_attempt(3),  # 最多尝试3次
        wait=wait_exponential(multiplier=1, min=4, max=10),  # 指数退避：4s, 6s, 10s...
        reraise=True  # 重试耗尽后重新抛出原始异常
    )
    def send_stock_template_param_data(self, payload: Dict) -> int:
        """
        发送股票模板参数数据

        Args:
            payload: 参数数据字典

        Returns:
            返回的ID或0
        """
        return self.api_client.insert_stock_template_param(payload)

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

    def _execute_parameter_combination(self, task_id: str, index: int, combination: List, config_data: Dict[str, Any],
                                       event_queue=None) -> tuple:
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
            results = {}

            # 定时检查是否完成（最多检查60次，每次间隔1分钟）
            for attempt in range(60):
                time.sleep(random.randint(20, 30))  # 等待1分钟
                logger.info(f"第 {attempt + 1} 次检查执行状态...")

                # 检查所有位置是否都有产出
                all_completed = True
                for key, position in check_positions.items():
                    try:
                        if self.google_sheet:
                            value = self.google_sheet.get_cell(position)
                            if value in ['#DIV/0!', ''] or 'target' in str(value):
                                results[key] = value
                                all_completed = False
                                break
                    except Exception as e:
                        logger.error(f"检查位置 {position} 时出错: {str(e)}")
                        all_completed = False
                        break

                if all_completed:
                    logger.info("所有参数执行完成，获取结果...")
                    # 获取结果
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

    def _wait_for_confirmation(self, task_id: str, combination: List, result: Dict, event_queue, app=None) -> bool:
        """等待前端确认"""
        if not event_queue:
            return True

        try:
            logger.info(f"发送第一次执行结果到前端，等待确认...")

            # 发送确认请求到前端
            event_queue.put({
                "type": "first_execution_complete",
                "data": {
                    "params": combination,
                    "results": result
                }
            })

            logger.info(f"已发送确认请求，等待前端响应...")

            # 等待确认事件 - 需要过滤掉自己发送的事件
            while True:
                event = event_queue.get(timeout=300)  # 5分钟超时
                logger.info(f"收到事件: {event}")

                # 如果是自己发送的事件，跳过
                if event.get("type") == "first_execution_complete":
                    logger.info("跳过自己发送的事件，继续等待确认...")
                    continue

                # 如果是确认事件
                if event.get("type") == "confirmation":
                    if event.get("data", {}).get("confirmed"):
                        logger.info("收到前端确认，继续执行")
                        return True
                    else:
                        logger.info("收到前端拒绝确认，停止执行")
                        return False

                # 其他事件也跳过
                logger.info(f"跳过非确认事件: {event.get('type')}")

        except Exception as e:
            logger.error(f"等待确认时出错: {str(e)}")
            return False

    def _push_log(self, task_id: str, level: str, message: str, event_queue=None):
        """推送日志到前端和数据库"""
        try:
            # 记录到系统日志
            if level == 'error':
                logger.error(f"任务 {task_id}: {message}")
            elif level == 'warning':
                logger.warning(f"任务 {task_id}: {message}")
            else:
                logger.info(f"任务 {task_id}: {message}")

            # 保存到数据库
            with current_app.app_context():
                log = TaskLog(
                    task_id=task_id,
                    level=level,
                    message=message
                )
                db.session.add(log)
                db.session.commit()

            # 推送到前端（如果SSE连接存在）
            if event_queue:
                try:
                    event_queue.put({
                        "type": "log_update",
                        "data": {
                            "level": level,
                            "message": message,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    })
                except Exception as e:
                    logger.warning(f"推送日志到前端失败: {str(e)}")

        except Exception as e:
            logger.error(f"推送日志失败: {str(e)}")

    def _save_task_result(self, task_id: str, step_index: int, parameters: List, result: Dict, success: bool, app=None):
        """保存任务结果到数据库"""
        try:
            if app:
                # 在后台线程中使用传递的应用实例
                with app.app_context():
                    task_result = TaskResult(
                        task_id=task_id,
                        step_index=step_index,
                        parameters=json.dumps(parameters),
                        result=json.dumps(result),
                        success=success
                    )
                    db.session.add(task_result)
                    db.session.commit()
            else:
                # 在主线程中使用当前应用上下文
                from flask import current_app
                with current_app.app_context():
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

    def _get_parameter_combination_by_index(self, parameters: List[List], index: int) -> List:
        """
        根据索引按需计算参数组合，避免内存问题
        
        Args:
            parameters: 参数列表的列表
            index: 组合索引
            
        Returns:
            参数组合列表
        """
        combination = []
        remaining_index = index

        # 从最后一个参数开始计算
        for param_list in reversed(parameters):
            param_index = remaining_index % len(param_list)
            combination.insert(0, param_list[param_index])
            remaining_index = remaining_index // len(param_list)

        return combination
