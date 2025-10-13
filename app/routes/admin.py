from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.services.task_manager import task_manager
from app.services.config_manager import get_config_manager
from app.models import Task, TaskLog, db
from app.utils.logger import get_logger

logger = get_logger(__name__)

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
def dashboard():
    """管理面板首页"""
    # 获取任务统计
    total_tasks = Task.query.count()
    completed_tasks = Task.query.filter_by(status='completed').count()
    running_tasks = Task.query.filter_by(status='running').count()
    error_tasks = Task.query.filter_by(status='error').count()
    
    # 获取最近的任务
    recent_tasks = Task.query.order_by(Task.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html', 
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         running_tasks=running_tasks,
                         error_tasks=error_tasks,
                         recent_tasks=recent_tasks)

@admin_bp.route('/tasks')
def tasks():
    """任务管理页面"""
    return render_template('admin/tasks.html')

@admin_bp.route('/config')
def config():
    """配置管理页面"""
    return render_template('admin/config.html')

@admin_bp.route('/logs')
def logs():
    """日志管理页面"""
    return render_template('admin/logs.html')

@admin_bp.route('/templates')
def templates():
    """任务模板管理页面"""
    return render_template('admin/templates.html')

@admin_bp.route('/results')
def results():
    """任务结果管理页面"""
    return render_template('admin/results.html')
