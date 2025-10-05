from flask import Blueprint, request, jsonify, Response
import json
import queue
from app.services.task_manager import task_manager
from app.services.config_manager import get_config_manager
from app.models import Task, TaskLog, db
from app.utils.logger import get_logger
from flask import current_app

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
            return jsonify({"status": "error", "task_id": task_id, "message": "任务创建成功，但启动失败"})
            
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

@api_bp.route('/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    try:
        success = task_manager.delete_task(task_id)
        if success:
            return jsonify({"status": "success", "message": "任务已删除"})
        else:
            return jsonify({"status": "error", "message": "删除任务失败"}), 400
    except Exception as e:
        logger.error(f"删除任务失败: {str(e)}")
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

@api_bp.route('/tasks/<task_id>/status-check', methods=['GET'])
def check_task_status(task_id):
    """检查任务本地状态"""
    try:
        status_check = task_manager.check_local_task_status(task_id)
        return jsonify({"status": "success", "status_check": status_check})
    except Exception as e:
        logger.error(f"检查任务状态失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/tasks/<task_id>/restart', methods=['POST'])
def restart_task(task_id):
    """重启任务"""
    try:
        data = request.get_json() or {}
        resume_from_checkpoint = data.get('resume_from_checkpoint', True)
        
        result = task_manager.restart_task(task_id, resume_from_checkpoint)
        if result["status"] == "success":
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"重启任务失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/tasks/<task_id>/create-restart', methods=['POST'])
def create_restart_task_api(task_id):
    """基于原任务创建新的重启任务"""
    try:
        new_task_id = task_manager.create_restart_task(task_id)
        
        # 自动启动新任务
        if task_manager.start_task(new_task_id):
            return jsonify({
                "status": "success", 
                "new_task_id": new_task_id,
                "message": "重启任务创建并启动成功"
            })
        else:
            return jsonify({
                "status": "success", 
                "new_task_id": new_task_id,
                "message": "重启任务创建成功，但启动失败"
            })
    except Exception as e:
        logger.error(f"创建重启任务失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/tasks/<task_id>/events')
def task_events_stream(task_id):
    """SSE事件流，用于任务状态更新和确认请求"""
    def event_stream():
        if task_id not in task_manager.task_events:
            yield f"data: {json.dumps({'type': 'error', 'data': 'Task not found'})}\n\n"
            return
        
        event_queue = task_manager.task_events[task_id]
        
        try:
            while True:
                # 从事件队列获取事件
                try:
                    event = event_queue.get(timeout=1)
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    # 超时，发送心跳
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                
                # 检查事件队列是否还存在（任务管理器会清理完成的队列）
                if task_id not in task_manager.task_events:
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
        # 强制刷新缓存，确保获取最新配置
        config_manager.refresh_cache()
        configs = config_manager.get_all_configs()
        logger.debug(f"返回配置数据: {configs}")
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
        
        logger.info(f"接收到配置更新请求: {data}")
        
        config_manager = get_config_manager()
        success = config_manager.update_configs(data)
        if success:
            # 强制刷新缓存，确保配置立即生效
            config_manager.refresh_cache()
            logger.info("配置更新成功，缓存已刷新")
            return jsonify({"status": "success", "message": "配置更新成功，已立即生效"})
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

@api_bp.route('/config/refresh', methods=['POST'])
def refresh_config():
    """强制刷新配置缓存"""
    try:
        config_manager = get_config_manager()
        config_manager.refresh_cache()
        return jsonify({"status": "success", "message": "配置缓存已刷新"})
    except Exception as e:
        logger.error(f"刷新配置缓存失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/config/validate', methods=['GET'])
def validate_config():
    """验证配置状态"""
    try:
        config_manager = get_config_manager()
        
        # 获取数据库中的配置
        from app.models import SystemConfig
        db_configs = {}
        configs = SystemConfig.query.all()
        for config in configs:
            db_configs[config.key] = config.value
        
        # 获取缓存中的配置
        cache_configs = config_manager._cache.copy()
        
        # 获取Google Sheet配置
        gs_config = config_manager.get_google_sheet_config()
        
        return jsonify({
            "status": "success",
            "validation": {
                "database_configs": db_configs,
                "cache_configs": cache_configs,
                "google_sheet_config": gs_config,
                "cache_size": len(cache_configs),
                "db_size": len(db_configs)
            }
        })
    except Exception as e:
        logger.error(f"验证配置失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/logs', methods=['GET'])
def get_logs():
    """获取系统日志"""
    try:
        import os
        import re
        from app.config import Config
        
        # 获取查询参数
        limit = request.args.get('limit', 100, type=int)
        level_filter = request.args.get('level', '')
        search = request.args.get('search', '')
        date_filter = request.args.get('date', '')
        
        log_file = Config.LOG_FILE
        parsed_logs = []
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 读取最后的日志行
                recent_lines = lines[-limit*3:] if len(lines) > limit*3 else lines
                
                # 解析日志格式: 2025-09-28 20:53:48,938 - __main__ - INFO - 消息
                log_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([^-]+) - (\w+) - (.+)'
                
                for line in recent_lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    match = re.match(log_pattern, line)
                    if match:
                        timestamp_str, source, level, message = match.groups()
                        
                        # 转换时间格式
                        try:
                            from datetime import datetime
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                            iso_timestamp = timestamp.isoformat()
                        except:
                            iso_timestamp = timestamp_str
                        
                        log_entry = {
                            'timestamp': iso_timestamp,
                            'level': level.lower(),
                            'message': message.strip(),
                            'source': source.strip()
                        }
                        
                        # 应用过滤器
                        if level_filter and log_entry['level'] != level_filter.lower():
                            continue
                        if search and search.lower() not in log_entry['message'].lower():
                            continue
                        if date_filter and not iso_timestamp.startswith(date_filter):
                            continue
                            
                        parsed_logs.append(log_entry)
                    else:
                        # 如果无法解析，保留原始格式
                        parsed_logs.append({
                            'timestamp': '',
                            'level': 'info',
                            'message': line,
                            'source': 'unknown'
                        })
                
                # 按时间倒序排列，最新的在前
                parsed_logs.reverse()
                
                # 限制结果数量
                parsed_logs = parsed_logs[:limit]
        
        return jsonify({"status": "success", "logs": parsed_logs})
    except Exception as e:
        logger.error(f"获取日志失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
@api_bp.route('/logs/latest', methods=['GET'])
def get_latest_logs():
    """获取最新的日志（用于实时更新）"""
    try:
        import os
        import re
        from app.config import Config
        
        # 获取查询参数
        since = request.args.get('since', '')  # 获取指定时间之后的日志
        limit = request.args.get('limit', 50, type=int)
        
        log_file = Config.LOG_FILE
        latest_logs = []
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 只读取最后的一些行以提高性能
                recent_lines = lines[-limit*2:] if len(lines) > limit*2 else lines
                
                # 解析日志格式
                log_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([^-]+) - (\w+) - (.+)'
                
                for line in recent_lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    match = re.match(log_pattern, line)
                    if match:
                        timestamp_str, source, level, message = match.groups()
                        
                        # 转换时间格式
                        try:
                            from datetime import datetime
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                            iso_timestamp = timestamp.isoformat()
                        except:
                            iso_timestamp = timestamp_str
                        
                        # 如果指定了since参数，只返回该时间之后的日志
                        if since and iso_timestamp <= since:
                            continue
                        
                        log_entry = {
                            'timestamp': iso_timestamp,
                            'level': level.lower(),
                            'message': message.strip(),
                            'source': source.strip()
                        }
                        
                        latest_logs.append(log_entry)
                
                # 按时间正序排列（最新的在后面）
                latest_logs.sort(key=lambda x: x['timestamp'])
                
                # 限制结果数量
                latest_logs = latest_logs[-limit:]
        
        return jsonify({"status": "success", "logs": latest_logs})
    except Exception as e:
        logger.error(f"获取最新日志失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
