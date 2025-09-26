from flask import Blueprint, render_template, request, jsonify
from app.services.task_manager import task_manager
from app.services.config_manager import config_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)

google_sheet_bp = Blueprint('google_sheet', __name__)

@google_sheet_bp.route('/')
def index():
    """Google Sheet参数批量校验首页"""
    return render_template('google_sheet/index.html')

@google_sheet_bp.route('/create')
def create():
    """创建Google Sheet任务页面"""
    return render_template('google_sheet/create.html')

@google_sheet_bp.route('/detail')
def detail():
    """任务详情页面"""
    return render_template('google_sheet/detail.html')
