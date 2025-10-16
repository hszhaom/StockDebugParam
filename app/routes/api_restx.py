from flask_restx import Namespace, Resource, fields
from flask import request, Response
from app.services.task_manager import task_manager
from app.services.config_manager import get_config_manager
from app.models import Task, TaskLog, TaskTemplate, TaskResult, db
import json

# 通用响应结构
resp_success = {'status': fields.String, 'message': fields.String}
task_model = {
    'id': fields.String,
    'name': fields.String,
    'description': fields.String,
    'task_type': fields.String,
    'status': fields.String,
    'created_at': fields.String,
    'error_message': fields.String,
}
task_input = {
    'name': fields.String(required=True, description='任务名称', example='校验Sheet配置'),
    'description': fields.String(description='任务描述', example='批量校验A项目配置'),
    'task_type': fields.String(description='任务类型', example='google_sheet'),
    'config': fields.Raw(required=True, description='任务配置', example={'spreadsheet_id': '1AbcXYZ...', 'worksheet': 'Sheet1'})
}

api_ns = Namespace('任务管理', description='任务相关API')
config_ns = Namespace('系统配置', description='配置相关API')
template_ns = Namespace('任务模板', description='模板相关API')
result_ns = Namespace('任务结果', description='结果相关API')
logs_ns = Namespace('系统日志', description='日志相关API')
gsheet_ns = Namespace('GoogleSheet', description='Google Sheet相关API')

# 任务管理
@api_ns.route('/tasks')
class TaskListResource(Resource):
    @api_ns.doc('get_tasks')
    def get(self):
        """获取所有任务（示例响应：{'status':'success','tasks':[...] }）"""
        tasks = task_manager.get_all_tasks()
        return {'status': 'success', 'tasks': tasks}

    @api_ns.doc('create_task')
    @api_ns.expect(api_ns.model('NewTask', task_input), validate=True)
    def post(self):
        """创建新任务（示例请求：{'name':'校验Sheet配置','config':{'spreadsheet_id':'1AbcXYZ...'}}）"""
        data = request.get_json()
        name = data.get('name')
        description = data.get('description')
        task_type = data.get('task_type', 'google_sheet')
        config = data.get('config')
        task_id = task_manager.create_task(name, description, task_type, config)
        started = task_manager.start_task(task_id)
        return {'status': 'success' if started else 'error', 'task_id': task_id}

@api_ns.route('/tasks/<string:task_id>')
@api_ns.param('task_id', '任务ID')
class TaskResource(Resource):
    def get(self, task_id):
        """获取任务详情"""
        task = task_manager.get_task_status(task_id)
        if not task:
            return {'status': 'error', 'message': '任务不存在'}, 404
        return {'status': 'success', 'task': task}

    def delete(self, task_id):
        """删除任务"""
        success = task_manager.delete_task(task_id)
        return {'status': 'success' if success else 'error'}

@api_ns.route('/tasks/<string:task_id>/cancel')
@api_ns.param('task_id', '任务ID')
class TaskCancelResource(Resource):
    def post(self, task_id):
        """取消任务"""
        if task_manager.cancel_task(task_id):
            return {'status': 'success'}
        return {'status': 'error'}, 400

# 任务管理（续）
@api_ns.route('/tasks/<string:task_id>/results')
@api_ns.param('task_id', '任务ID')
class TaskResultsResource(Resource):
    def get(self, task_id):
        """获取任务结果"""
        results = task_manager.get_task_results(task_id)
        return {'status': 'success', 'results': results}

@api_ns.route('/tasks/<string:task_id>/logs')
@api_ns.param('task_id', '任务ID')
class TaskLogsResource(Resource):
    def get(self, task_id):
        """获取任务日志"""
        logs = task_manager.get_task_logs(task_id)
        return {'status': 'success', 'logs': logs}

@api_ns.route('/tasks/<string:task_id>/status-check')
@api_ns.param('task_id', '任务ID')
class TaskStatusCheckResource(Resource):
    def get(self, task_id):
        """检查任务本地状态"""
        status_check = task_manager.check_local_task_status(task_id)
        return {'status': 'success', 'status_check': status_check}

restart_input = api_ns.model('RestartInput', {
    'resume_from_checkpoint': fields.Boolean(description='是否从检查点恢复', example=True)
})

@api_ns.route('/tasks/<string:task_id>/restart')
@api_ns.param('task_id', '任务ID')
class TaskRestartResource(Resource):
    @api_ns.expect(restart_input)
    def post(self, task_id):
        """重启任务（示例请求：{'resume_from_checkpoint':true}）"""
        data = request.get_json() or {}
        resume_from_checkpoint = data.get('resume_from_checkpoint', True)
        result = task_manager.restart_task(task_id, resume_from_checkpoint)
        if result.get('status') == 'success':
            return result
        return result, 400

confirm_input = api_ns.model('ConfirmInput', {
    'confirmed': fields.Boolean(required=True, description='是否确认继续执行', example=True)
})

@api_ns.route('/tasks/<string:task_id>/create-restart')
@api_ns.param('task_id', '任务ID')
class TaskCreateRestartResource(Resource):
    def post(self, task_id):
        """基于原任务创建新的重启任务并尝试启动"""
        new_task_id = task_manager.create_restart_task(task_id)
        started = task_manager.start_task(new_task_id)
        return {
            'status': 'success',
            'new_task_id': new_task_id,
            'message': '重启任务创建并启动成功' if started else '重启任务创建成功，但启动失败'
        }

@api_ns.route('/tasks/<string:task_id>/confirm')
@api_ns.param('task_id', '任务ID')
class TaskConfirmResource(Resource):
    @api_ns.expect(confirm_input, validate=True)
    def post(self, task_id):
        """确认任务继续执行（示例请求：{'confirmed':true}）"""
        data = request.get_json() or {}
        confirmed = data.get('confirmed', False)
        if task_id in task_manager.task_events:
            task_manager.task_events[task_id].put({
                'type': 'confirmation',
                'data': {'confirmed': confirmed}
            })
            return {'status': 'success', 'message': '确认已发送'}
        return {'status': 'error', 'message': '任务事件队列不存在'}, 400

@api_ns.route('/tasks/<string:task_id>/events')
@api_ns.param('task_id', '任务ID')
class TaskEventsStream(Resource):
    def get(self, task_id):
        """SSE事件流（服务端推送）"""
        def event_stream():
            if task_id not in task_manager.task_events:
                yield 'data: {"type": "error", "data": "Task not found"}\n\n'
                return
            event_queue = task_manager.task_events[task_id]
            import queue as _q
            while True:
                try:
                    event = event_queue.get(timeout=1)
                    yield f"data: {json.dumps(event)}\n\n"
                except _q.Empty:
                    yield "data: {\"type\": \"heartbeat\"}\n\n"
                if task_id not in task_manager.task_events:
                    break
        return Response(event_stream(), mimetype='text/event-stream')

# 系统配置
config_update_model = config_ns.model('ConfigUpdate', {
    'any_key': fields.Raw(description='配置键值（示例）', example={'LOG_LEVEL': 'INFO'})
})

gs_config_update_model = config_ns.model('GoogleSheetConfig', {
    'credentials_file': fields.String(description='凭证文件路径', example='data/credentials.json'),
    'token_file': fields.String(description='Token文件路径', example='data/token.json'),
    'proxy_url': fields.String(description='HTTP代理（可选）', example='http://127.0.0.1:7890')
})

@config_ns.route('/config')
class ConfigResource(Resource):
    def get(self):
        """获取系统配置（示例响应：{'status':'success','config':{...}}）"""
        cm = get_config_manager()
        cm.refresh_cache()
        configs = cm.get_all_configs()
        return {'status': 'success', 'config': configs}

    @config_ns.expect(config_update_model)
    def post(self):
        """更新系统配置（示例：{'LOG_LEVEL':'DEBUG'}）"""
        data = request.get_json() or {}
        cm = get_config_manager()
        success = cm.update_configs(data)
        if success:
            cm.refresh_cache()
            return {'status': 'success', 'message': '配置更新成功，已立即生效'}
        return {'status': 'error', 'message': '配置更新失败'}, 500

@config_ns.route('/config/google-sheet')
class GoogleSheetConfigResource(Resource):
    def get(self):
        """获取Google Sheet配置"""
        cm = get_config_manager()
        return {'status': 'success', 'config': cm.get_google_sheet_config()}

    @config_ns.expect(gs_config_update_model, validate=True)
    def post(self):
        """更新Google Sheet配置（示例：{'credentials_file':'data/credentials.json'}）"""
        data = request.get_json() or {}
        cm = get_config_manager()
        if cm.set_google_sheet_config(data):
            return {'status': 'success', 'message': 'Google Sheet配置更新成功'}
        return {'status': 'error', 'message': 'Google Sheet配置更新失败'}, 500

@config_ns.route('/config/refresh')
class ConfigRefreshResource(Resource):
    def post(self):
        """强制刷新配置缓存"""
        cm = get_config_manager()
        cm.refresh_cache()
        return {'status': 'success', 'message': '配置缓存已刷新'}

@config_ns.route('/config/validate')
class ConfigValidateResource(Resource):
    def get(self):
        """验证配置状态（数据库、缓存、Google Sheet配置）"""
        cm = get_config_manager()
        from app.models import SystemConfig
        db_configs = {cfg.key: cfg.value for cfg in SystemConfig.query.all()}
        cache_configs = cm._cache.copy()
        gs_config = cm.get_google_sheet_config()
        return {
            'status': 'success',
            'validation': {
                'database_configs': db_configs,
                'cache_configs': cache_configs,
                'google_sheet_config': gs_config,
                'cache_size': len(cache_configs),
                'db_size': len(db_configs)
            }
        }

# 模板管理
template_create_model = template_ns.model('TemplateCreate', {
    'name': fields.String(required=True, description='模板名称', example='GS参数校验模板'),
    'description': fields.String(description='模板描述', example='校验所需字段是否齐全'),
    'config': fields.Raw(required=True, description='模板配置JSON', example={'required_columns': ['name','id']})
})

template_update_model = template_ns.model('TemplateUpdate', {
    'name': fields.String(description='模板名称', example='新模板名'),
    'description': fields.String(description='模板描述', example='更新描述'),
    'config': fields.Raw(description='模板配置JSON', example={'required_columns': ['name','id','status']})
})

@template_ns.route('/templates')
class TemplateListResource(Resource):
    def get(self):
        """获取所有任务模板"""
        templates = TaskTemplate.query.order_by(TaskTemplate.created_at.desc()).all()
        return {'status': 'success', 'templates': [t.to_dict() for t in templates]}

    @template_ns.expect(template_create_model, validate=True)
    def post(self):
        """创建新任务模板（示例：{'name':'GS参数校验模板','config':{...}}）"""
        data = request.get_json() or {}
        if 'name' not in data:
            return {'status': 'error', 'message': '模板名称不能为空'}, 400
        if 'config' not in data:
            return {'status': 'error', 'message': '配置信息不能为空'}, 400
        try:
            if isinstance(data['config'], str):
                config_json = json.loads(data['config'])
                config_str = json.dumps(config_json)
            else:
                config_str = json.dumps(data['config'])
        except json.JSONDecodeError:
            return {'status': 'error', 'message': '配置信息不是有效的JSON格式'}, 400
        template = TaskTemplate(
            name=data['name'],
            description=data.get('description', ''),
            config=config_str
        )
        db.session.add(template)
        db.session.commit()
        return {'status': 'success', 'message': '模板创建成功', 'template': template.to_dict()}

@template_ns.route('/templates/<int:template_id>')
@template_ns.param('template_id', '模板ID')
class TemplateResource(Resource):
    def get(self, template_id):
        """获取模板详情"""
        template = TaskTemplate.query.get(template_id)
        if not template:
            return {'status': 'error', 'message': '模板不存在'}, 404
        return template.to_dict()

    @template_ns.expect(template_update_model)
    def put(self, template_id):
        """更新任务模板（示例：{'name':'新模板名'}）"""
        template = TaskTemplate.query.get(template_id)
        if not template:
            return {'status': 'error', 'message': '模板不存在'}, 404
        data = request.get_json() or {}
        template.name = data.get('name', template.name)
        template.description = data.get('description', template.description)
        cfg = data.get('config', template.config)
        template.config = json.dumps(cfg) if isinstance(cfg, (dict, list)) else cfg
        db.session.commit()
        return {'status': 'success', 'template': template.to_dict()}

    def delete(self, template_id):
        """删除任务模板"""
        template = TaskTemplate.query.get(template_id)
        if not template:
            return {'status': 'error', 'message': '模板不存在'}, 404
        db.session.delete(template)
        db.session.commit()
        return {'status': 'success', 'message': '模板已删除'}

# 结果管理
@result_ns.route('/results')
class ResultsListResource(Resource):
    def get(self):
        """获取任务结果列表（示例：/results?page=1&per_page=20&task_id=xxx）"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        task_id = request.args.get('task_id')
        query = TaskResult.query
        if task_id:
            query = query.filter_by(task_id=task_id)
        pagination = query.order_by(TaskResult.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
        results = [r.to_dict() for r in pagination.items]
        return {
            'results': results,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }

@result_ns.route('/results/<int:result_id>')
@result_ns.param('result_id', '结果ID')
class ResultResource(Resource):
    def get(self, result_id):
        """获取任务结果详情"""
        result = TaskResult.query.get(result_id)
        if not result:
            return {'status': 'error', 'message': '结果不存在'}, 404
        return result.to_dict()

    def delete(self, result_id):
        """删除任务结果"""
        result = TaskResult.query.get(result_id)
        if not result:
            return {'status': 'error', 'message': '结果不存在'}, 404
        db.session.delete(result)
        db.session.commit()
        return {'status': 'success', 'message': '结果已删除'}

# 系统日志
@logs_ns.route('/logs')
class LogsResource(Resource):
    def get(self):
        """获取系统日志（示例：/logs?level=info&search=error&limit=50）"""
        import os, re
        from app.config import Config
        limit = request.args.get('limit', 100, type=int)
        level_filter = request.args.get('level', '')
        search = request.args.get('search', '')
        date_filter = request.args.get('date', '')
        task_id_filter = request.args.get('task_id', '')
        log_file = Config.LOG_FILE
        parsed_logs = []
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_lines = lines[-limit*3:] if len(lines) > limit*3 else lines
                log_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([^-]+) - (\w+) - (.+)'
                for line in recent_lines:
                    line = line.strip()
                    if not line:
                        continue
                    match = re.match(log_pattern, line)
                    if match:
                        timestamp_str, source, level, message = match.groups()
                        try:
                            from datetime import datetime
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                            iso_timestamp = timestamp.isoformat()
                        except Exception:
                            iso_timestamp = timestamp_str
                        log_entry = {
                            'timestamp': iso_timestamp,
                            'level': level.lower(),
                            'message': message.strip(),
                            'source': source.strip()
                        }
                        if level_filter and log_entry['level'] != level_filter.lower():
                            continue
                        if search and search.lower() not in log_entry['message'].lower():
                            continue
                        if date_filter and not iso_timestamp.startswith(date_filter):
                            continue
                        if task_id_filter:
                            task_pattern = f"[Task-{task_id_filter[:8]}]"
                            if task_pattern not in log_entry['message'] and task_id_filter not in log_entry['message']:
                                continue
                        parsed_logs.append(log_entry)
                    else:
                        parsed_logs.append({'timestamp': '', 'level': 'info', 'message': line, 'source': 'unknown'})
                parsed_logs.reverse()
                parsed_logs = parsed_logs[:limit]
        return {'status': 'success', 'logs': parsed_logs}

@logs_ns.route('/logs/latest')
class LatestLogsResource(Resource):
    def get(self):
        """获取最新日志（示例：/logs/latest?since=2025-10-16T10:00:00&limit=50）"""
        import os, re
        from app.config import Config
        since = request.args.get('since', '')
        limit = request.args.get('limit', 50, type=int)
        log_file = Config.LOG_FILE
        latest_logs = []
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_lines = lines[-limit*2:] if len(lines) > limit*2 else lines
                log_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([^-]+) - (\w+) - (.+)'
                for line in recent_lines:
                    line = line.strip()
                    if not line:
                        continue
                    match = re.match(log_pattern, line)
                    if match:
                        timestamp_str, source, level, message = match.groups()
                        try:
                            from datetime import datetime
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                            iso_timestamp = timestamp.isoformat()
                        except Exception:
                            iso_timestamp = timestamp_str
                        if since and iso_timestamp <= since:
                            continue
                        latest_logs.append({
                            'timestamp': iso_timestamp,
                            'level': level.lower(),
                            'message': message.strip(),
                            'source': source.strip()
                        })
                latest_logs.sort(key=lambda x: x['timestamp'])
                latest_logs = latest_logs[-limit:]
        return {'status': 'success', 'logs': latest_logs}

@logs_ns.route('/tasks/<string:task_id>/system-logs')
@logs_ns.param('task_id', '任务ID')
class TaskSystemLogsResource(Resource):
    def get(self, task_id):
        """获取任务相关的系统日志（示例：/tasks/{task_id}/system-logs?limit=200&level=error）"""
        import os, re
        from app.config import Config
        limit = request.args.get('limit', 200, type=int)
        level_filter = request.args.get('level', '')
        log_file = Config.LOG_FILE
        task_logs = []
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                log_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([^-]+) - (\w+) - (.+)'
                task_patterns = [f"[Task-{task_id[:8]}]", f"任务 {task_id}", task_id]
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    contains_task = any(p in line for p in task_patterns)
                    if not contains_task:
                        continue
                    match = re.match(log_pattern, line)
                    if match:
                        timestamp_str, source, level, message = match.groups()
                        try:
                            from datetime import datetime
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                            iso_timestamp = timestamp.isoformat()
                        except Exception:
                            iso_timestamp = timestamp_str
                        log_entry = {
                            'timestamp': iso_timestamp,
                            'level': level.lower(),
                            'message': message.strip(),
                            'source': source.strip(),
                            'task_id': task_id
                        }
                        if level_filter and log_entry['level'] != level_filter.lower():
                            continue
                        task_logs.append(log_entry)
                task_logs.sort(key=lambda x: x['timestamp'])
                task_logs = task_logs[-limit:]
        return {'status': 'success', 'logs': task_logs, 'task_id': task_id, 'total_found': len(task_logs)}

# Google Sheet
worksheet_request_model = gsheet_ns.model('WorksheetRequest', {
    'spreadsheet_id': fields.String(required=True, description='表格ID', example='1AbcXYZ...'),
    'token_file': fields.String(description='Token文件路径', example='data/token.json'),
    'proxy_url': fields.String(description='HTTP代理（可选）', example='http://127.0.0.1:7890')
})

@gsheet_ns.route('/google-sheet/worksheets')
class WorksheetsResource(Resource):
    @gsheet_ns.expect(worksheet_request_model, validate=True)
    def post(self):
        """获取Google Sheet中的所有工作表名称（示例：{'spreadsheet_id':'1AbcXYZ...'}）"""
        data = request.get_json() or {}
        spreadsheet_id = data.get('spreadsheet_id')
        token_file = data.get('token_file', 'data/token.json')
        proxy_url = data.get('proxy_url')
        if not spreadsheet_id:
            return {'status': 'error', 'message': '缺少spreadsheet_id参数'}, 400
        from app.services.google_sheet_service import GoogleSheetService
        worksheets = GoogleSheetService.get_worksheets(spreadsheet_id, token_file, proxy_url)
        return {'status': 'success', 'worksheets': worksheets}
