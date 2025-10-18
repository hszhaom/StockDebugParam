import json
import random
import time
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional,Tuple

from flask import current_app
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_result

from app.exceptions.checkForErrors import checkForErrors
from app.models import Task, TaskLog, TaskResult, db
from app.services.config_manager import get_config_manager
from app.services.google_sheet_client import GoogleSheet
from app.utils.db_retry import safe_db_operation, db_retry_manager
from app.utils.db_stock_api import StockAPIClient
from app.utils.logger import get_logger
from app.utils.result_validator import validate_result_dict, validate_google_sheet_result, is_valid_result_value

logger = get_logger(__name__)


class GoogleSheetService:
    """Google Sheet服务"""

    def __init__(self, config: Dict[str, Any], task_id: str, event_queue=None, app=None):
        self.config = config
        self.google_sheet:Optional[GoogleSheet] = None
        self.api_client = StockAPIClient()
        # 保存参数到实例变量
        self.task_id = task_id
        self.event_queue = event_queue
        self.app = app
        # 创建任务专用日志记录器 - 不使用TaskLogger的前缀功能，我们自己控制格式
        self.task_logger = get_logger(f"{__name__}.{task_id}")

    def error_dd(self,error_msg):
        error_msg = self.app.notifier.error_google_task_templates(
            f"{self.task_id} -- {self.task.name}",
            error_msg,
            f"{current_app.config.get('BASE_URL')}/google-sheet/detail?task_id={self.task_id}")
        self.app.notifier.send_message(error_msg)

    def task_ok_to_dd(self,result):
        error_msg = self.app.notifier.google_task_ok_templates(
            f"{self.task_id} -- {self.task.name}",
            result,
            f"{current_app.config.get('BASE_URL')}/google-sheet/detail?task_id={self.task_id}"
                                                               )
        self.app.notifier.send_message(error_msg)


    def execute_task(self):
        """执行Google Sheet任务"""
        try:
            
            # 统一使用应用上下文
            context_app = self.app or current_app
            with context_app.app_context():
                task = Task.query.get(self.task_id)
                self.task = task
                if not task:
                    self._log_error(f'任务 {self.task_id} 不存在')
                    return 'error'

                # 检查任务是否已被取消
                if task.status == 'cancelled':
                    self._log_info(f'任务 {self.task_id} 已被取消，停止执行')
                    return 'cancelled'

                # 解析配置
                if isinstance(task.config, str):
                    try:
                        config_data = json.loads(task.config)
                    except json.JSONDecodeError as e:
                        self._log_error(f"配置解析失败: {str(e)}")
                        return 'error'
                else:
                    config_data = task.config or {}

                config_manager = get_config_manager()
                config_data = {**config_manager.get_google_sheet_config(), **config_data}
                
                # 推送任务开始日志
                self._log_info('开始执行Google Sheet任务')

                # 初始化Google Sheet连接
                self._init_google_sheet(config_data)

                # 获取参数列表
                parameters = config_data.get('parameters', [])
                if not parameters:
                    self._log_error("没有参数配置")
                    return 'error'
                
                name = task.name
                sheet_name = config_data.get('sheet_name', "")

                # 检查任务是否已被取消
                if task.status == 'cancelled':
                    self._log_info(f'任务 {self.task_id} 已被取消，停止执行')
                    return 'cancelled'

                stock_param = self.get_single_stock_template_param(name)

                if stock_param is not None and stock_param != "error":
                    multiplier_index = 0 if stock_param.get('multiplier_index', 0) == 0 else stock_param.get(
                        'multiplier_index', 0) + 1
                    self._log_info(f"开始执行参数批量处理，multiplier_index: {multiplier_index}")
                    success_count, failed_count, task_status = self.get_bdl(task, name, parameters, config_data, multiplier_index)
                elif stock_param != "error":
                    self._log_info("开始执行参数批量处理（默认参数模式）")
                    success_count, failed_count, task_status = self.get_bdl(task, name, parameters, config_data)
                else:
                    self._log_error("获取股票参数失败")
                    return 'error'

                # 根据任务状态决定返回结果
                if task_status == 'cancelled':
                    # 任务被取消，保持cancelled状态
                    self._log_info(f'任务已取消，成功执行: {success_count}, 失败: {failed_count}')
                    # 推送任务取消通知
                    self.task_ok_to_dd(f'任务已取消！成功执行: {success_count}, 失败: {failed_count}')
                    return 'cancelled'
                elif task_status == 'error':
                    # 任务执行出错
                    # 推送错误通知
                    error_details = f'任务执行出错！成功: {success_count}, 失败: {failed_count}'
                    if task.error:
                        error_details += f', 错误信息: {str(task.error)}'
                    self.error_dd(error_details)
                    return 'error'
                else:
                    if stock_param is not None and stock_param != "error":
                        final_status = 'completed' if success_count > 0 else 'error'
                        if final_status == 'completed':
                            # 推送成功完成通知
                            self.task_ok_to_dd(f'任务成功完成！成功执行: {success_count}, 失败: {failed_count}')
                        else:
                            # 推送失败通知
                            self.error_dd(f'任务执行失败！成功: {success_count}, 失败: {failed_count}')
                        return final_status

                if success_count == 0 and failed_count == 0:
                    self._log_error('任务执行失败')
                    # 推送无结果失败通知
                    self.error_dd('任务执行失败！没有成功或失败的参数组合')
                    return 'error'
                
                # 推送任务完成通知
                self.task_ok_to_dd(f'任务执行完成！成功: {success_count}, 失败: {failed_count}')
                # 推送任务完成信息
                completion_msg = f'任务执行完成！成功: {success_count}, 失败: {failed_count}'
                self._log_info(completion_msg)

                return 'completed'

        except Exception as e:
            # 检查是否是任务被取消导致的异常
            try:
                task = Task.query.get(self.task_id)
                if task and task.status == 'cancelled':
                    self._log_info(f'任务已被取消: {str(e)}')
                    return 'cancelled'
            except:
                pass
            
            # 其他异常情况
            error_msg = f"执行Google Sheet任务失败: {self.task_id}, 错误: {str(e)}"
            self._log_error(error_msg)
            self.error_dd(error_msg)
            return 'error'

    def get_bdl(self, task, name, parameters, config_data, index_z=0):
        """执行批量数据处理"""
        try:
            # 计算总参数组合数（不生成实际组合，避免内存问题）
            total_combinations = 1
            for param_list in parameters:
                total_combinations *= len(param_list)

            # 更新任务总步数
            task.total_steps = total_combinations
            db_retry_manager.commit_with_retry(db.session)

            # 推送参数组合信息
            self._log_info(f'将执行 {total_combinations} 个参数组合')

            # 执行参数组合
            success_count = 0
            failed_count = 0
            if index_z > total_combinations:
                self._log_warning(f'任务数据库内条数:{index_z} > 参数组合条数:{total_combinations}，跳过执行,好像执行过的')
                return 0, 0


            # 检查是否从断点恢复
            start_index = max(index_z, task.current_step - 1) if task.current_step >= 1 else index_z
            self._log_info(f"任务将从第 {start_index + 1} 个参数组合开始执行")
            success_count = start_index # 成功执行计数器，从断点除重新来

            for i in range(start_index, total_combinations):
                self._log_step(i + 1, total_combinations, f"开始执行参数组合")
                
                # 按需计算参数组合，避免内存问题
                combination = self._get_parameter_combination_by_index(parameters, i)
                
                # 原子性检查任务是否被取消
                # SQLite不支持FOR UPDATE，使用简单查询
                def check_task_status():
                    return db.session.execute(
                        text("SELECT status FROM tasks WHERE id = :task_id"),
                        {"task_id": self.task_id}
                    ).fetchone()
                
                result = safe_db_operation(check_task_status)
                
                if not result or result.status == 'cancelled':
                    self._log_warning("任务已被取消，停止执行")
                    return success_count, failed_count, 'cancelled'

                # 推送执行进度
                progress_msg = f'正在执行第 {i + 1}/{total_combinations} 个参数组合 {combination}'
                self._log_info(progress_msg)

                # 更新当前步数
                task.current_step = i + 1
                db_retry_manager.commit_with_retry(db.session)

                # 执行单个参数组合
                try:
                    success, result = self._execute_parameter_combination(combination, config_data)

                    if success:
                        success_count += 1
                        self._log_info(f'第 {i + 1} 个参数组合执行成功，{result}')
                    else:
                        self._log_warning(f'第 {i + 1} 个参数组合执行失败')
                        failed_count += 1
                        return success_count, failed_count, 'error'

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
                    self._save_task_result(i, combination, result, success)
                    # # 推送结果，到生产数据库
                    self.send_stock_template_param_data(param_load, lambda level, msg: self._log(level, msg))

                except checkForErrors as e:
                    self._log_error(str(e))
                    task.error = e
                    return success_count, failed_count, 'error'
                except Exception as e:
                    failed_count += 1
                    # 检查是否是任务被取消
                    task.error = e
                    try:
                        task_check = Task.query.get(self.task_id)
                        if task_check and task_check.status == 'cancelled':
                            self._log_info(f'第 {i + 1} 个参数组合执行中断（任务被取消）: {str(e)}')
                            break  # 退出循环
                    except:
                        pass

                    error_msg = f'第 {i + 1} 个参数组合执行出错: {str(e)}'
                    self._log_error(error_msg)
                    return success_count, failed_count, 'error'

                self._log_info(f"第 {i + 1} 个参数组合执行完成，成功: {success_count}, 失败: {failed_count}")

            self._log_info(f"批量数据处理完成，总成功: {success_count}, 总失败: {failed_count}")
            return success_count, failed_count, 'completed'
            
        except Exception as e:
            # 检查是否是任务被取消导致的异常
            try:
                task_check = Task.query.get(self.task_id)
                if task_check and task_check.status == 'cancelled':
                    self._log_info(f'批量数据处理中断（任务被取消）: {str(e)}')
                    return success_count, failed_count, 'cancelled'
            except:
                pass
            
            error_msg = f"批量数据处理失败: {traceback.format_exc()}"
            self._log_error(error_msg)
            return 0, 1, 'error'

    @retry(
        stop=stop_after_attempt(3),  # 最多尝试3次
        wait=wait_exponential(multiplier=1, min=4, max=10),  # 指数退避：4s, 6s, 10s...
        reraise=True  # 重试耗尽后重新抛出原始异常
    )
    def send_stock_template_param_data(self, payload: Dict,log) -> int:
        """
        发送股票模板参数数据

        Args:
            payload: 参数数据字典

        Returns:
            返回的ID或0
        """
        try:
            self._log_api("发送股票模板参数数据", f"payload: {payload}")
            result = self.api_client.insert_stock_template_param(payload)
            self._log_api("发送股票模板参数数据成功", f"ID: {result}")
            return result
        except Exception as e:
            self._log_api_error("发送股票模板参数数据", str(e))
            log('error',f"发送股票模板参数数据失败: {str(e)}")
            raise e

    @retry(
        stop=stop_after_attempt(3),  # 最多尝试3次
        wait=wait_exponential(multiplier=1, min=4, max=10),  # 指数退避：4s, 6s, 10s...
        reraise=True  # 重试耗尽后重新抛出原始异常
    )
    def get_single_stock_template_param(self, stock_no: str) -> Optional[Dict]:
        """
        获取单个股票模板参数
        
        Args:
            stock_no: 股票编号
            
        Returns:
            股票参数字典或None
        """
        try:
            self._log_api("获取股票模板参数", f"stock_no: {stock_no}")
            result = self.api_client.get_single_stock_template_param(stock_no)
            self._log_api("获取股票模板参数成功", f"返回结果: {type(result)}")
            return result
        except Exception as e:
            self._log_api_error("获取股票模板参数", str(e))
            raise
    

    def _init_google_sheet(self, config_data: Dict[str, Any]):
        """初始化Google Sheet连接"""
        try:
            self._log_info("开始初始化Google Sheet连接")
            
            spreadsheet_id = config_data.get('spreadsheet_id')
            sheet_name = config_data.get('sheet_name', 'data')
            token_file = config_data.get('token_file', 'data/token.json')
            proxy_url = config_data.get('proxy_url', None)

            if not spreadsheet_id:
                error_msg = "缺少spreadsheet_id配置"
                self._log_error(error_msg)
                raise ValueError(error_msg)

            self._log_info(f"连接参数 - Spreadsheet ID: {spreadsheet_id}, Sheet: {sheet_name}, Token: {token_file}")
            if proxy_url:
                self._log_info(f"使用代理: {proxy_url}")

            self.google_sheet = GoogleSheet(spreadsheet_id, sheet_name, token_file, proxy_url)
            if not self.google_sheet.worksheet:
                raise Exception("请先选择工作表")

            self._log_info("Google Sheet连接初始化成功")
        except Exception as e:
            error_msg = f"初始化Google Sheet连接失败: {str(e)}"
            self._log_error(error_msg)
            raise
            
    @staticmethod
    def get_worksheets(spreadsheet_id: str, token_file: str = "data/token.json", proxy_url: str = None) -> List[str]:
        """
        获取指定电子表格中的所有工作表名称
        
        Args:
            spreadsheet_id: 电子表格ID
            token_file: 认证文件路径
            proxy_url: 代理URL
            
        Returns:
            工作表名称列表
        """
        try:
            # 使用上下文管理器确保连接被正确关闭
            with GoogleSheet(spreadsheet_id, None, token_file, proxy_url) as google_sheet:
                # 获取所有工作表名称
                worksheets = google_sheet.get_all_worksheets()
                if not worksheets:
                    raise ValueError("未找到任何工作表")
                return worksheets
        except Exception as e:
            logger.error(f"获取工作表列表失败: {str(e)}")
            raise


    @retry(
        stop=stop_after_attempt(3),  # 最多尝试3次
        wait=wait_exponential(multiplier=1, min=4, max=10),  # 指数退避：4s, 6s, 10s...
        reraise=True,  # 重试耗尽后重新抛出原始异常
        retry=retry_if_result(lambda result: result[0] is False)
    )
    @validate_result_dict(none_values=(None, '', ' ', '#N/A', '#DIV/0!', '#ERROR!', '#VALUE!', '#REF!', '#NAME?', '#NUM!'))
    def _execute_parameter_combination(self, combination: List, config_data: Dict[str, Any]) -> tuple[bool, Dict[str, Any]]:
        """执行单个参数组合"""
        try:
            # 获取参数位置配置
            param_positions = config_data.get('parameter_positions', [])
            # 等待执行完成，检查指定位置
            check_positions = config_data.get('check_positions', [])
            result_positions = config_data.get('result_positions', [])

            results = {}
            cell_updates = {}

            def _update_cell(num=0):
                # 准备要更新的单元格
                for i, position in enumerate(param_positions):
                    cell_updates[position] = combination[i]
                    results[position] = combination[i]

                self._log_info(f"向Google Sheet写入参数: {cell_updates}")
                self.google_sheet.update_jumped_cells(cell_updates)
                if num <= 0:
                    return None
                # 随机选择一个键
                random_key = random.choice(list(cell_updates.keys()))
                self._log_info(f"防止模型卡顿，在随机位置写入：{random_key},当前是第{num + 1}轮检查")
                # 使用选中的键和对应的值更新单元格
                self.google_sheet.update_cell(random_key, cell_updates[random_key])
                return None

            def check_result(_position, _value=None):
                if not _value or not is_valid_result_value(_value):
                    self._log_info(f"结果位置 {_position} 值为空或无效，跳过重新检查")
                    raise Exception(f"结果位置 {_position} 值为空或无效，跳过重新检查")

                if str(_value).strip().startswith(("#", "#N/A")):
                    _error_msg = f"获取结果位置 {_position} 时出错: {str(_value)}"
                    raise checkForErrors(f"检查报错，出现#|#N/A 这种异常错误，联系用户检查 {_error_msg}")

                if '%' in _value:
                    _value = float(_value.replace('%', '').replace(',', '')) / 100
                if isinstance(_value, str):
                    _value = float(_value.replace(',', ''))

                results[_position] = round(_value, 5)

            def _validate_check_values(check_values: Dict[str, Any]) -> bool:
                """验证检查位置的值是否有效"""
                if not check_values:
                    return False
                
                for position, value in check_values.items():
                    if not value or value in ['#DIV/0!', '', '#N/A', '#ERROR!', '#VALUE!']:
                        return False
                    if 'target' in str(value).lower():
                        return False
                    
                    # 检查是否与输入参数匹配
                    input_key = f"B{position[1:]}"  # 将 I6 -> B6
                    if input_key in results:
                        try:
                            check_val = float(value.replace('%', '')) / 100 if '%' in value else float(value)
                            input_val = float(results[input_key])
                            if round(check_val) != round(input_val):
                                return False
                        except (ValueError, TypeError):
                            return False
                
                return True

            def _validate_result_values(result_values: Dict[str, Any]) -> Tuple[bool, List[str]]:
                """验证结果值是否完整有效"""
                if not result_values:
                    return False, ["结果字典为空"]
                
                missing_positions = []
                invalid_positions = []
                
                for position in result_positions:
                    if position not in result_values:
                        missing_positions.append(position)
                        continue
                    
                    value = result_values[position]
                    if not is_valid_result_value(value):
                        invalid_positions.append(f"{position}({value})")
                
                error_msgs = []
                if missing_positions:
                    error_msgs.append(f"缺少位置: {missing_positions}")
                if invalid_positions:
                    error_msgs.append(f"无效值: {invalid_positions}")
                
                return len(error_msgs) == 0, error_msgs


            sleep_num = 5

            def get_sell_sleep(min_sleep: int, max_sleep: int) -> int:
                nonlocal sleep_num
                if sleep_num <= 0:
                    sleep_num = 5
                _ = min(min_sleep + sleep_num * 5, max_sleep)  # 最多60秒
                sleep_num -= 1
                return int(_)

            # 写入参数到Google Sheet
            _update_cell()

            is_exit = 0
            max_error_num = 3

            # 定时检查是否完成（最多检查60次，20-30秒）
            for attempt in range(60):
                # 从配置获取执行延迟时间
                config_manager = get_config_manager()
                delay_min = int(config_manager.get_config('execution_delay_min', 20))
                delay_max = int(config_manager.get_config('execution_delay_max', 30))
                _ = get_sell_sleep(delay_min, delay_max)
                self._log_info(f"第 {attempt + 1} 次检查执行状态... delay {_} 秒")
                time.sleep(_)

                
                # 定期刷新参数，防止模型卡顿
                if attempt % 10 == 0 or attempt in [3, 5, 8]:
                    _update_cell(attempt)

                # 检查所有位置是否都有产出
                all_completed = True
                
                # 1. 检查检查位置的值
                if self.google_sheet and check_positions:
                    try:
                        check_values = self.google_sheet.get_cells_batch(check_positions)
                        self._log_info(f"获取到检查位置的值: {check_values}")
                        
                        if not _validate_check_values(check_values):
                            all_completed = False
                            self._log_info(f"检查位置验证失败，继续等待...")
                            continue
                            
                    except Exception as e:
                        error_msg = f"批量检查位置时出错: {str(e)}"
                        self._log_error(error_msg)
                        all_completed = False
                        continue

                # 2. 如果检查通过，获取结果
                if all_completed and self.google_sheet and result_positions:
                    try:
                        result_values = self.google_sheet.get_cells_batch(result_positions)
                        self._log_info(f"获取到参数执行结果: {result_values}")
                        
                        # 验证结果完整性
                        is_valid, error_msgs = _validate_result_values(result_values)
                        if not is_valid:
                            self._log_warning(f"结果验证失败: {error_msgs}，继续等待...")
                            all_completed = False
                            continue
                        
                        # 所有结果都有效，处理结果
                        for position in result_positions:
                            value = result_values.get(position, "")
                            check_result(position, value)
                        
                        # 使用专门的Google Sheet结果验证
                        is_valid_gs, gs_error_msg = validate_google_sheet_result(results)
                        if not is_valid_gs:
                            self._log_warning(f"Google Sheet结果验证失败: {gs_error_msg}")
                            return False, {}
                        
                        self._log_info(f"参数组合执行成功，结果: {results}")
                        return True, results

                    except checkForErrors as e:
                        raise e
                    except Exception as e:
                        error_msg = f"批量获取结果时出错: {str(e)}"
                        self._log_error(error_msg)
                        if is_exit <= max_error_num:
                            self._log_error(error_msg)
                            continue
                        # 回退到逐个获取
                        fallback_success = True
                        for position in result_positions:
                            try:
                                value = self.google_sheet.get_cell(position)
                                check_result(position, value)
                            except Exception as cell_error:
                                error_msg = f"获取结果位置 {position} 时出错: {str(cell_error)}"
                                self._log_error(error_msg)
                                fallback_success = False
                                break
                        
                        if fallback_success:
                            # 验证回退模式的结果
                            is_valid_gs, gs_error_msg = validate_google_sheet_result(results)
                            if is_valid_gs:
                                return True, results
                            else:
                                self._log_warning(f"回退模式结果验证失败: {gs_error_msg}")
                                return False, {}

            self._log_warning("执行超时，未在规定时间内完成")
            return False, {}

        except Exception as e:
            error_msg = f"执行参数组合时出错: {traceback.format_exc()}"
            self._log_error(error_msg)
            raise e

    def _log(self, level: str, message: str, log_type: str = 'general', **kwargs):
        """
        统一的日志记录接口 - 完整版，包含前端推送和数据库保存
        
        Args:
            level: 日志级别 ('info', 'warning', 'error')
            message: 日志消息
            log_type: 日志类型 ('general', 'step', 'progress', 'api', 'api_error')
            **kwargs: 额外参数，用于特定类型的日志
        """
        try:
            # 根据日志类型格式化消息
            formatted_message = self._format_log_message(message, log_type, **kwargs)
            
            # 添加简洁的任务ID前缀
            prefixed_message = f"[Task-{self.task_id[:8]}] {formatted_message}"
            
            # 1. 记录到系统日志（现在已经不会重复了）
            if level == 'error':
                self.task_logger.error(prefixed_message)
            elif level == 'warning':
                self.task_logger.warning(prefixed_message)
            else:
                self.task_logger.info(prefixed_message)
            
            # 2. 保存到数据库（TaskLog）
            self._save_to_database(level, formatted_message)
            
            # 3. 推送到前端（SSE）
            self._push_to_frontend(level, formatted_message)
            
        except Exception as e:
            # 记录日志系统本身的错误，但不引起循环
            pass
    
    def _format_log_message(self, message: str, log_type: str, **kwargs) -> str:
        """格式化日志消息"""
        if log_type == 'step':
            step = kwargs.get('step', 0)
            total = kwargs.get('total', 0)
            return f"[Step {step}/{total}] {message}"
        elif log_type == 'progress':
            percentage = kwargs.get('percentage', 0)
            return f"[Progress {percentage:.1f}%] {message}"
        elif log_type == 'api':
            action = kwargs.get('action', '')
            details = kwargs.get('details', '')
            base_msg = f"[API] {action}"
            return f"{base_msg} - {details}" if details else base_msg
        elif log_type == 'api_error':
            action = kwargs.get('action', '')
            error = kwargs.get('error', '')
            return f"[API_ERROR] {action} - {error}"
        else:
            return message
    
    def _save_to_database(self, level: str, message: str):
        """保存日志到数据库，包含重试逻辑"""
        def save_log_operation():
            log = TaskLog(
                task_id=self.task_id,
                level=level,
                message=message
            )
            db.session.add(log)
            db.session.commit()
        
        try:
            if self.app:
                with self.app.app_context():
                    safe_db_operation(save_log_operation)
            else:
                with current_app.app_context():
                    safe_db_operation(save_log_operation)
        except Exception as e:
            # 数据库保存失败时静默处理，不影响主流程
            pass
    
    def _push_to_frontend(self, level: str, message: str):
        """推送日志到前端"""
        try:
            if self.event_queue:
                self.event_queue.put({
                    "type": "log_update",
                    "data": {
                        "level": level,
                        "message": message,
                        "timestamp": datetime.now().isoformat()
                    }
                })
        except Exception as e:
            # 前端推送失败时静默处理，不影响主流程
            pass
    
    # 便捷的日志方法
    def _log_info(self, message: str, log_type: str = 'general', **kwargs):
        """记录info级别日志"""
        self._log('info', message, log_type, **kwargs)
    
    def _log_warning(self, message: str, log_type: str = 'general', **kwargs):
        """记录warning级别日志"""
        self._log('warning', message, log_type, **kwargs)
    
    def _log_error(self, message: str, log_type: str = 'general', **kwargs):
        """记录error级别日志"""
        self._log('error', message, log_type, **kwargs)
    
    def _log_step(self, step: int, total: int, message: str):
        """记录步骤日志"""
        self._log('info', message, 'step', step=step, total=total)
    
    def _log_progress(self, percentage: float, message: str):
        """记录进度日志"""
        self._log('info', message, 'progress', percentage=percentage)
    
    def _log_api(self, action: str, details: str = ''):
        """记录API调用日志"""
        self._log('info', '', 'api', action=action, details=details)
    
    def _log_api_error(self, action: str, error: str):
        """记录API错误日志"""
        self._log('error', '', 'api_error', action=action, error=error)

    def _save_task_result(self, step_index: int, parameters: List, result: Dict, success: bool):
        """保存任务结果到数据库，包含重试逻辑"""
        def save_result_operation():
            task_result = TaskResult(
                task_id=self.task_id,
                step_index=step_index,
                parameters=json.dumps(parameters),
                result=json.dumps(result),
                success=success
            )
            db.session.add(task_result)
            db.session.commit()
        
        try:
            if self.app:
                # 在后台线程中使用传递的应用实例
                with self.app.app_context():
                    safe_db_operation(save_result_operation)
            else:
                # 在主线程中使用当前应用上下文
                from flask import current_app
                with current_app.app_context():
                    safe_db_operation(save_result_operation)
        except Exception as e:
            error_msg = f"保存任务结果失败: {str(e)}"
            self._log_error(error_msg)
            # 注意：这里不能使用_push_log，因为可能导致循环调用

    def _get_parameter_combination_by_index(self, parameters: List[List], index: int) -> List:
        """
        根据索引按需计算参数组合，避免内存问题
        
        Args:
            parameters: 参数列表的列表
            index: 组合索引
            
        Returns:
            参数组合列表
        """
        try:
            logger.debug(f"计算第 {index} 个参数组合")
            combination = []
            remaining_index = index

            # 从最后一个参数开始计算
            for param_list in reversed(parameters):
                param_index = remaining_index % len(param_list)
                combination.insert(0, param_list[param_index])
                remaining_index = remaining_index // len(param_list)

            return combination
        except Exception as e:
            self._log_error(f"计算参数组合失败，索引: {index}, 错误: {str(e)}")
            raise
