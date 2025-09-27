#!/usr/bin/env python3
"""
应用启动文件
"""
import os
from app import create_app
from app.extensions import db
from app.models import Task, TaskLog, TaskResult, SystemConfig
from app.config import init_config as init_config2
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

if __name__ == '__main__':
    # 确保必要的目录存在
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # 初始化数据库ss
    with app.app_context():
        db.create_all()

    # 运行应用
    app.run(debug=True, host='127.0.0.1', port=5000)
