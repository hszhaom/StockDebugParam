#!/usr/bin/env python3
"""
应用启动文件
"""
import os
from datetime import datetime
from app import create_app
from app.extensions import db
from app.models import Task, TaskLog, TaskResult, SystemConfig
from app.config import init_config as init_config2
from app.utils.logger import initialize_logging
app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'Task': Task,
        'TaskLog': TaskLog,
        'TaskResult': TaskResult,
        'SystemConfig': SystemConfig
    }

@app.cli.command()
def init_db():
    """初始化数据库"""
    db.create_all()
    print("数据库初始化完成")

@app.cli.command()
def init_config():
    """初始化默认配置"""
    init_config2()
    print("默认配置初始化完成")

def check_and_cleanup_dead_tasks():
    """启动时检查并清理挂死的任务"""
    from app.services.task_manager import task_manager
    from app.utils.logger import get_logger
    
    logger = get_logger('startup')
    
    with app.app_context():
        try:
            # 获取所有运行状态的任务
            running_tasks = Task.query.filter_by(status='running').all()
            
            if not running_tasks:
                logger.info("没有发现运行中的任务")
                return
            
            logger.info(f"发现 {len(running_tasks)} 个运行中的任务，开始检查状态")
            
            for task in running_tasks:
                status_check = task_manager.check_local_task_status(task.id)
                
                if status_check.get("can_restart", False):
                    logger.info(f"发现中断的任务: {task.id} - {status_check.get('restart_reason')}")
                    
                    # 重置任务状态为pending，允许用户重新启动
                    task.status = 'pending'
                    task.error_message = None  # 清除之前的错误信息
                    task.end_time = None  # 清除结束时间
                    
                    # 添加日志
                    task_manager._add_task_log(
                        task.id, 
                        'info', 
                        f"应用重启时检测到任务中断，已重置为待启动状态: {status_check.get('restart_reason')}"
                    )
                    
                    logger.info(f"已将任务 {task.id} 重置为pending状态，用户可选择重新启动")
                else:
                    logger.info(f"任务 {task.id} 状态正常")
            
            db.session.commit()
            logger.info("任务状态检查完成")
            
        except Exception as e:
            logger.error(f"检查任务状态时出错: {str(e)}")

if __name__ == '__main__':
    # 确保必要的目录存在
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    # 初始化日志系统（在应用上下文之前）
    initialize_logging()

    # 初始化数据库
    with app.app_context():
        db.create_all()
        init_config2()

    # 检查并清理挂死的任务
    check_and_cleanup_dead_tasks()

    # 运行应用
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes', 'on')
    app.run(debug=debug_mode, host='127.0.0.1', port=5000)
