import os
import json
import time
import threading
import itertools
import queue
from datetime import datetime
from googlesheet import GoogleSheet
from logger import TextLogger

class GoogleSheetTaskExecutor:
    """Google Sheet任务执行器"""
    
    def __init__(self, task_id, tasks_dict, task_events_dict, config):
        self.task_id = task_id
        self.tasks = tasks_dict
        self.task_events = task_events_dict
        self.config = config
        self.google_sheet = None
        
    def add_log(self, message):
        """添加日志消息"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        
        # 如果有任务ID，也添加到任务日志中
        if self.task_id and self.task_id in self.tasks:
            self.tasks[self.task_id]['logs'].append(log_entry)
        
        TextLogger.info(message)
    
    def execute_parameter_group(self, params, is_first=False):
        """执行一组参数"""
        try:
            # 写入参数到Google Sheet
            self.add_log(f"开始执行参数组: {params}")
            
            # 获取参数位置配置
            param_positions = self.config.get('parameter_positions', {})
            
            # 准备要更新的单元格
            cell_updates = {}
            for i, (key, position) in enumerate(param_positions.items()):
                if i < len(params):
                    cell_updates[position] = params[i]
            
            # 批量更新单元格
            if self.google_sheet:
                self.google_sheet.update_jumped_cells(cell_updates)
                self.add_log(f"参数已写入到表格: {cell_updates}")
            else:
                self.add_log("Google Sheet连接未建立")
                return False, {}
            
            # 等待执行完成，检查指定位置
            check_positions = self.config.get('check_positions', {})
            result_positions = self.config.get('result_positions', {})
            
            # 定时检查是否完成（最多检查60次，每次间隔1分钟）
            for attempt in range(60):
                time.sleep(60)  # 等待1分钟
                self.add_log(f"第 {attempt + 1} 次检查执行状态...")
                
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
                        self.add_log(f"检查位置 {position} 时出错: {str(e)}")
                        all_completed = False
                        break
                
                if all_completed:
                    self.add_log("所有参数执行完成，获取结果...")
                    # 获取结果
                    results = {}
                    for key, position in result_positions.items():
                        try:
                            if self.google_sheet:
                                value = self.google_sheet.get_cell(position)
                                results[key] = value
                        except Exception as e:
                            self.add_log(f"获取结果位置 {position} 时出错: {str(e)}")
                            results[key] = "获取失败"
                    
                    self.add_log(f"执行结果: {results}")
                    
                    # 如果是第一次执行，发送确认请求到前端
                    if is_first:
                        self.add_log("第一次执行完成，等待前端确认...")
                        # 通过SSE发送确认请求
                        if self.task_id in self.task_events:
                            self.task_events[self.task_id].put({
                                "type": "first_execution_complete",
                                "data": {
                                    "params": params,
                                    "results": results
                                }
                            })
                        # 等待前端确认
                        return self.wait_for_confirmation(), results
                    
                    return True, results
            
            self.add_log("执行超时，未在规定时间内完成")
            return False, {}
            
        except Exception as e:
            self.add_log(f"执行参数组时出错: {str(e)}")
            return False, {}
    
    def wait_for_confirmation(self):
        """等待前端确认"""
        if self.task_id in self.task_events:
            try:
                # 等待确认事件
                event = self.task_events[self.task_id].get(timeout=300)  # 5分钟超时
                if event.get("type") == "confirmation" and event.get("data", {}).get("confirmed"):
                    self.add_log("收到前端确认，继续执行")
                    return True
                else:
                    self.add_log("未收到确认或确认被拒绝，停止执行")
                    return False
            except:
                self.add_log("等待确认超时，停止执行")
                return False
        return False
    
    def execute(self):
        """执行任务"""
        try:
            task = self.tasks.get(self.task_id, {})
            if not task:
                self.add_log(f"任务 {self.task_id} 不存在")
                return
                
            param_lists = task.get('parameters', [])
            task_config = task.get('config', {})
            task['status'] = 'running'
            task['start_time'] = datetime.now().isoformat()
            self.add_log(f"开始执行任务 {self.task_id}")
            
            # 初始化任务事件队列
            self.task_events[self.task_id] = queue.Queue()
            
            # 获取Google Sheet配置
            spreadsheet_id = task_config.get('spreadsheet_id') or self.config.get('spreadsheet_id', '')
            sheet_name = task_config.get('sheet_name') or self.config.get('sheet_name', 'data')
            token_type = task_config.get('token_type') or 'file'
            token_file = task_config.get('token_file') or self.config.get('token_file', 'data/token.json')
            token_json = task_config.get('token_json')
            proxy_url = task_config.get('proxy_url') or self.config.get('proxy_url', None)
            
            # 如果是JSON字符串认证方式，创建临时token文件
            if token_type == 'json' and token_json:
                try:
                    token_data = json.loads(token_json)
                    temp_token_file = f"data/temp_token_{self.task_id}.json"
                    with open(temp_token_file, 'w', encoding='utf-8') as f:
                        json.dump(token_data, f, ensure_ascii=False, indent=2)
                    token_file = temp_token_file
                except Exception as e:
                    self.add_log(f"解析Token JSON失败: {str(e)}")
                    task['status'] = 'error'
                    task['error_message'] = f'解析Token JSON失败: {str(e)}'
                    return
            
            if not spreadsheet_id:
                task['status'] = 'error'
                task['error_message'] = '请先配置电子表格ID'
                self.add_log(f"任务 {self.task_id} 执行失败: 请先配置电子表格ID")
                return
            
            self.google_sheet = GoogleSheet(spreadsheet_id, sheet_name, token_file, proxy_url)
            self.add_log(f"Google Sheet连接成功")
            
            # 生成参数组合
            combinations = list(itertools.product(*param_lists))
            task['total_combinations'] = len(combinations)
            self.add_log(f"生成了 {len(combinations)} 个参数组合")
            
            # 依次执行每个组合
            results = []
            start_index = task.get('current_combination_index', 0)
            for i in range(start_index, len(combinations)):
                if task.get('status') == 'cancelled':
                    self.add_log(f"任务 {self.task_id} 已被取消")
                    return
                    
                param_combination = combinations[i]
                is_first = (i == 0)  # 标记是否为第一次执行
                self.add_log(f"执行第 {i+1}/{len(combinations)} 个参数组合")
                
                success, result = self.execute_parameter_group(param_combination, is_first)
                results.append({
                    "combination": param_combination,
                    "success": success,
                    "result": result
                })
                
                # 更新任务进度
                self.tasks[self.task_id]['current_combination_index'] = i + 1
                self.tasks[self.task_id]['results'] = results
                
                # 保存任务状态到文件
                self.save_task_status()
                
                # 如果执行失败且是第一次执行，停止任务
                if not success and is_first:
                    self.add_log("第一次执行失败，停止任务")
                    task['status'] = 'error'
                    task['error_message'] = '第一次执行失败'
                    break
                
                # 如果第一次执行后未获得确认，停止任务
                if is_first and not success:
                    self.add_log("第一次执行未获得确认，停止任务")
                    task['status'] = 'cancelled'
                    task['error_message'] = '第一次执行未获得确认'
                    break
            
            task['status'] = 'completed'
            task['end_time'] = datetime.now().isoformat()
            self.add_log(f"任务 {self.task_id} 执行完成")
            
            # 删除临时token文件
            if token_type == 'json' and token_json and 'temp_token_' in token_file:
                try:
                    os.remove(token_file)
                except Exception as e:
                    self.add_log(f"删除临时token文件失败: {str(e)}")
            
        except Exception as e:
            if self.task_id in self.tasks:
                self.tasks[self.task_id]['status'] = 'error'
                self.tasks[self.task_id]['error_message'] = str(e)
            self.add_log(f"任务 {self.task_id} 执行出错: {str(e)}")
            
            # 删除临时token文件
            if self.task_id in self.tasks:
                task_config = self.tasks[self.task_id].get('config', {})
                token_type = task_config.get('token_type') or 'file'
                token_file = task_config.get('token_file') or self.config.get('token_file', 'data/token.json')
                if token_type == 'json' and 'temp_token_' in token_file:
                    try:
                        os.remove(token_file)
                    except Exception as e:
                        self.add_log(f"删除临时token文件失败: {str(e)}")
        finally:
            self.save_task_status()
            # 清理任务事件队列
            if self.task_id in self.task_events:
                del self.task_events[self.task_id]
    
    def save_task_status(self):
        """保存任务状态到文件"""
        try:
            # 只保存必要的任务信息
            tasks_to_save = {}
            for task_id, task in self.tasks.items():
                tasks_to_save[task_id] = {
                    'status': task['status'],
                    'parameters': task['parameters'] if task['status'] in ['pending', 'running'] else [],
                    'config': task['config'],
                    'start_time': task['start_time'],
                    'end_time': task['end_time'],
                    'current_combination_index': task['current_combination_index'],
                    'total_combinations': task['total_combinations'],
                    'error_message': task['error_message']
                }
            
            with open('data/tasks.json', 'w', encoding='utf-8') as f:
                json.dump(tasks_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            TextLogger.error(f"保存任务状态失败: {str(e)}")