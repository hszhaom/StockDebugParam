from flask import Blueprint, request, jsonify, Response
import json
from app.services.task_manager import task_manager
from app.services.config_manager import get_config_manager
from app.models import Task, TaskLog, db
from app.utils.logger import get_logger

logger = get_logger(__name__)

api_bp = Blueprint('api', __name__)

# 任务相关API
@api_bp.route('/tasks', methods=['GET'])
def get_tasks():
    """获取所有任务"""
    try:
        tasks = task_manager.get_all_tasks()
        return jsonify({"status": "success", "tasks": tasks})
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/tasks', methods=['POST'])
def create_task():
    """创建新任务"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "请求数据为空"}), 400
        
        name = data.get('name', '未命名任务')
        description = data.get('description', '')
        task_type = data.get('task_type', 'google_sheet')
        config = data.get('config', {})
        
        if not config:
            return jsonify({"status": "error", "message": "任务配置为空"}), 400
        
        task_id = task_manager.create_task(name, description, task_type, config)
        
        # 自动启动任务
        if task_manager.start_task(task_id):
            return jsonify({"status": "success", "task_id": task_id, "message": "任务创建并启动成功"})
        else:
            return jsonify({"status": "success", "task_id": task_id, "message": "任务创建成功，但启动失败"})
            
    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取任务详情"""
    try:
        task = task_manager.get_task_status(task_id)
        if not task:
            return jsonify({"status": "error", "message": "任务不存在"}), 404
        
        return jsonify({"status": "success", "task": task})
    except Exception as e:
        logger.error(f"获取任务详情失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """取消任务"""
    try:
        success = task_manager.cancel_task(task_id)
        if success:
            return jsonify({"status": "success", "message": "任务已取消"})
        else:
            return jsonify({"status": "error", "message": "取消任务失败"}), 400
    except Exception as e:
        logger.error(f"取消任务失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/tasks/<task_id>/logs', methods=['GET'])
def get_task_logs(task_id):
    """获取任务日志"""
    try:
        logs = task_manager.get_task_logs(task_id)
        return jsonify({"status": "success", "logs": logs})
    except Exception as e:
        logger.error(f"获取任务日志失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/tasks/<task_id>/results', methods=['GET'])
def get_task_results(task_id):
    """获取任务结果"""
    try:
        results = task_manager.get_task_results(task_id)
        return jsonify({"status": "success", "results": results})
    except Exception as e:
        logger.error(f"获取任务结果失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/tasks/<task_id>/events')
def task_events_stream(task_id):
    """SSE事件流，用于任务状态更新和确认请求"""
    def event_stream():
        if task_id not in task_manager.task_events:
            return
        
        event_queue = task_manager.task_events[task_id]
        
        try:
            while True:
                # 检查任务是否存在
                task = Task.query.get(task_id)
                if not task:
                    break
                
                # 从事件队列获取事件
                try:
                    event = event_queue.get(timeout=1)
                    yield f"data: {json.dumps(event)}\n\n"
                except:
                    # 超时，发送心跳
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                
                # 检查任务是否已完成或取消
                if task.status in ['completed', 'cancelled', 'error']:
                    break
        except GeneratorExit:
            pass
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
    
    return Response(event_stream(), mimetype='text/event-stream')

@api_bp.route('/tasks/<task_id>/confirm', methods=['POST'])
def confirm_task(task_id):
    """确认任务继续执行"""
    try:
        data = request.get_json()
        confirmed = data.get('confirmed', False) if data else False
        
        if task_id in task_manager.task_events:
            task_manager.task_events[task_id].put({
                "type": "confirmation",
                "data": {
                    "confirmed": confirmed
                }
            })
            return jsonify({"status": "success", "message": "确认已发送"})
        else:
            return jsonify({"status": "error", "message": "任务事件队列不存在"}), 400
    except Exception as e:
        logger.error(f"确认任务失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 配置相关API
@api_bp.route('/config', methods=['GET'])
def get_config():
    """获取系统配置"""
    try:
        config_manager = get_config_manager()
        configs = config_manager.get_all_configs()
        return jsonify({"status": "success", "config": configs})
    except Exception as e:
        logger.error(f"获取配置失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/config', methods=['POST'])
def update_config():
    """更新系统配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "请求数据为空"}), 400
        
        config_manager = get_config_manager()
        success = config_manager.update_configs(data)
        if success:
            return jsonify({"status": "success", "message": "配置更新成功"})
        else:
            return jsonify({"status": "error", "message": "配置更新失败"}), 500
    except Exception as e:
        logger.error(f"更新配置失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/config/google-sheet', methods=['GET'])
def get_google_sheet_config():
    """获取Google Sheet配置"""
    try:
        config_manager = get_config_manager()
        config = config_manager.get_google_sheet_config()
        return jsonify({"status": "success", "config": config})
    except Exception as e:
        logger.error(f"获取Google Sheet配置失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/config/google-sheet', methods=['POST'])
def update_google_sheet_config():
    """更新Google Sheet配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "请求数据为空"}), 400
        
        config_manager = get_config_manager()
        success = config_manager.set_google_sheet_config(data)
        if success:
            return jsonify({"status": "success", "message": "Google Sheet配置更新成功"})
        else:
            return jsonify({"status": "error", "message": "Google Sheet配置更新失败"}), 500
    except Exception as e:
        logger.error(f"更新Google Sheet配置失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
