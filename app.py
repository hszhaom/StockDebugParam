import os
import json
import time
import threading
import itertools
import uuid
import queue
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from googlesheet import GoogleSheet
from logger import TextLogger
from tasks.google_sheet_task import GoogleSheetTaskExecutor

app = Flask(__name__, template_folder='templates', static_folder='static')

# 全局变量
log_messages = []
execution_lock = threading.Lock()
first_execution = True
config = {}
tasks = {}  # 存储所有任务的状态
task_events = {}  # 存储任务事件，用于SSE通信

# 加载配置
def load_config():
    global config
    try:
        with open('config/config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        TextLogger.info("配置加载成功")
    except Exception as e:
        TextLogger.error(f"加载配置失败: {str(e)}")
        config = {}

# 保存配置
def save_config():
    try:
        with open('config/config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        TextLogger.info("配置保存成功")
    except Exception as e:
        TextLogger.error(f"保存配置失败: {str(e)}")

# 初始化配置
load_config()

def add_log(message, task_id=None):
    """添加日志消息"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    log_messages.append(log_entry)
    
    # 如果有任务ID，也添加到任务日志中
    if task_id and task_id in tasks:
        tasks[task_id]['logs'].append(log_entry)
    
    TextLogger.info(message)

def clear_logs():
    """清空日志"""
    global log_messages
    log_messages = []

def get_logs():
    """获取所有日志"""
    return log_messages

def execute_task_background(task_id):
    """后台执行任务"""
    global tasks, task_events, config
    
    try:
        # 创建任务执行器
        executor = GoogleSheetTaskExecutor(task_id, tasks, task_events, config)
        # 执行任务
        executor.execute()
    except Exception as e:
        if task_id in tasks:
            tasks[task_id]['status'] = 'error'
            tasks[task_id]['error_message'] = str(e)
        add_log(f"任务 {task_id} 执行出错: {str(e)}", task_id)

def save_task_status():
    """保存任务状态到文件"""
    try:
        # 只保存必要的任务信息
        tasks_to_save = {}
        for task_id, task in tasks.items():
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

def load_task_status():
    """从文件加载任务状态"""
    global tasks
    try:
        if os.path.exists('data/tasks.json'):
            # 检查文件是否为空
            if os.path.getsize('data/tasks.json') == 0:
                with open('data/tasks.json', 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                return
                
            with open('data/tasks.json', 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    tasks_data = {}
                else:
                    tasks_data = json.loads(content)
                
                # 恢复任务状态
                for task_id, task_data in tasks_data.items():
                    tasks[task_id] = {
                        'status': task_data['status'],
                        'parameters': task_data['parameters'],
                        'config': task_data.get('config', {}),
                        'start_time': task_data['start_time'],
                        'end_time': task_data['end_time'],
                        'current_combination_index': task_data['current_combination_index'],
                        'total_combinations': task_data['total_combinations'],
                        'error_message': task_data['error_message'],
                        'logs': [],
                        'results': []
                    }
            TextLogger.info("任务状态加载成功")
    except Exception as e:
        TextLogger.error(f"加载任务状态失败: {str(e)}")
        # 如果加载失败，创建一个空的任务文件
        try:
            with open('data/tasks.json', 'w', encoding='utf-8') as f:
                json.dump({}, f)
        except Exception as e2:
            TextLogger.error(f"创建任务状态文件失败: {str(e2)}")

# 初始化加载任务状态
load_task_status()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create')
def create_task_page():
    return render_template('create.html')

@app.route('/detail')
def task_detail_page():
    return render_template('detail.html')

@app.route('/config')
def config_page():
    return render_template('config.html')

@app.route('/api/config', methods=['GET', 'POST'])
def config_api():
    global config
    if request.method == 'POST':
        try:
            new_config = request.json
            if new_config:
                config.update(new_config)
            save_config()
            return jsonify({"status": "success", "message": "配置保存成功"})
        except Exception as e:
            return jsonify({"status": "error", "message": f"保存配置失败: {str(e)}"})
    else:
        return jsonify(config)

@app.route('/api/task', methods=['POST'])
def create_task():
    """创建新任务"""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({"status": "error", "message": "请求数据为空"})
            
        param_lists = request_data.get('parameters', [])
        task_config = request_data.get('config', {})
        
        if not param_lists:
            return jsonify({"status": "error", "message": "参数列表为空"})
        
        # 验证必要字段
        if not task_config.get('spreadsheet_id'):
            return jsonify({"status": "error", "message": "请提供电子表格ID或URL"})
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务
        tasks[task_id] = {
            'status': 'pending',
            'parameters': param_lists,
            'config': task_config,
            'start_time': None,
            'end_time': None,
            'current_combination_index': 0,
            'total_combinations': 0,
            'error_message': None,
            'logs': [],
            'results': []
        }
        
        # 保存任务状态
        save_task_status()
        
        # 启动后台任务执行
        thread = threading.Thread(target=execute_task_background, args=(task_id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({"status": "success", "task_id": task_id, "message": "任务创建成功"})
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"创建任务失败: {str(e)}"})

@app.route('/api/task/<task_id>/events')
def task_events_stream(task_id):
    """SSE事件流，用于任务状态更新和确认请求"""
    def event_stream():
        if task_id not in task_events:
            task_events[task_id] = queue.Queue()
        
        try:
            while True:
                # 检查任务是否存在
                if task_id not in tasks:
                    break
                    
                # 从事件队列获取事件
                try:
                    event = task_events[task_id].get(timeout=1)
                    yield f"data: {json.dumps(event)}\n\n"
                except:
                    # 超时，发送心跳
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    
                # 检查任务是否已完成或取消
                if tasks[task_id]['status'] in ['completed', 'cancelled', 'error']:
                    break
        except GeneratorExit:
            pass
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
    
    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/api/task/<task_id>/confirm', methods=['POST'])
def confirm_task(task_id):
    """确认任务继续执行"""
    try:
        request_data = request.get_json()
        confirmed = False
        if request_data:
            confirmed = request_data.get('confirmed', False)
        
        if task_id in task_events:
            task_events[task_id].put({
                "type": "confirmation",
                "data": {
                    "confirmed": confirmed
                }
            })
            return jsonify({"status": "success", "message": "确认已发送"})
        else:
            return jsonify({"status": "error", "message": "任务事件队列不存在"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"确认失败: {str(e)}"})

@app.route('/api/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """获取任务状态"""
    if task_id in tasks:
        task = tasks[task_id].copy()
        # 不返回参数数据给前端（保护数据安全）
        if task['status'] in ['completed', 'error', 'cancelled']:
            task['parameters'] = []
        return jsonify({"status": "success", "task": task})
    else:
        return jsonify({"status": "error", "message": "任务不存在"})

@app.route('/api/task/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """取消任务"""
    if task_id in tasks:
        tasks[task_id]['status'] = 'cancelled'
        save_task_status()
        return jsonify({"status": "success", "message": "任务已取消"})
    else:
        return jsonify({"status": "error", "message": "任务不存在"})

@app.route('/api/tasks', methods=['GET'])
def get_all_tasks():
    """获取所有任务列表"""
    task_list = []
    for task_id, task in tasks.items():
        task_list.append({
            'task_id': task_id,
            'status': task['status'],
            'start_time': task['start_time'],
            'end_time': task['end_time'],
            'current_combination_index': task['current_combination_index'],
            'total_combinations': task['total_combinations'],
            'error_message': task['error_message']
        })
    return jsonify({"status": "success", "tasks": task_list})

@app.route('/api/task/<task_id>/logs', methods=['GET'])
def get_task_logs(task_id):
    """获取任务日志"""
    if task_id in tasks:
        return jsonify({"status": "success", "logs": tasks[task_id]['logs']})
    else:
        return jsonify({"status": "error", "message": "任务不存在"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)