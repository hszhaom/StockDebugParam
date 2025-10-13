from flask import Blueprint, render_template, request, jsonify, url_for, redirect
from app.services.task_manager import task_manager
from app.services.config_manager import get_config_manager
from app.utils.logger import get_logger
from app.models import TaskTemplate

logger = get_logger(__name__)

google_sheet_bp = Blueprint('google_sheet', __name__)

@google_sheet_bp.route('/')
def index():
    """Google Sheet参数批量校验首页"""
    return render_template('google_sheet/index.html')

@google_sheet_bp.route('/create')
def create():
    """创建Google Sheet任务页面"""
    template_id = request.args.get('template_id')
    template = None
    
    if template_id:
        try:
            template = TaskTemplate.query.get(int(template_id))
            if template:
                logger.info(f"加载模板 {template_id}: {template.name}")
                template_data = template.to_dict()
                
                # 确保配置是字典格式
                if isinstance(template_data['config'], str):
                    try:
                        template_data['config'] = json.loads(template_data['config'])
                    except json.JSONDecodeError:
                        logger.error(f"模板配置解析失败: {template_data['config']}")
                        template_data['config'] = {}
                
                # 修改模板名称，表明这是从模板创建的
                template_data['name'] = f"{template_data['name']} - 从模板创建"
                
                return render_template('google_sheet/create.html', 
                                     template=template_data,
                                     template_id=template_id)
            else:
                logger.warning(f"模板不存在: {template_id}")
                flash('模板不存在', 'error')
        except Exception as e:
            logger.error(f"加载模板失败: {str(e)}")
            flash('加载模板失败: ' + str(e), 'error')
    
    return render_template('google_sheet/create.html')

@google_sheet_bp.route('/detail')
def detail():
    """任务详情页面"""
    return render_template('google_sheet/detail.html')

@google_sheet_bp.route('/create-restart/<task_id>')
def create_restart(task_id):
    """重启任务页面，预填充原任务的配置"""
    from app.services.task_manager import task_manager
    
    # 获取原任务
    task = task_manager.get_task_status(task_id)
    if not task:
        logger.error(f"原任务不存在: {task_id}")
        return render_template('google_sheet/create.html')
    
    # 将原任务配置传递给模板
    return render_template('google_sheet/create.html', restart_config=task['config'], original_task_id=task_id)