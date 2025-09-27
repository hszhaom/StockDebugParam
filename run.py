#!/usr/bin/env python3
"""
应用启动文件
"""
import os
from app import create_app
from app.extensions import db
from app.models import Task, TaskLog, TaskResult, SystemConfig

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
    from app.services.config_manager import get_config_manager
    
    default_configs = {
        'spreadsheet_id': '',
        'sheet_name': 'data',
        'token_file': 'data/token.json',
        'proxy_url': None,
        'max_concurrent_tasks': 5,
        'task_timeout': 36000,
        'parameter_positions': {
            'param1': 'B6',
            'param2': 'B7',
            'param4': 'B9',
            'param5': 'B10',
            'param6': 'B11'
        },
        'check_positions': {
            'check1': 'I6',
            'check2': 'I7',
            'check4': 'I9',
            'check5': 'I10',
            'check6': 'I11'
        },
        'result_positions': {
            'result1': 'I15',
            'result2': 'I16',
            'result3': 'I17',
            'result4': 'I18',
            'result5': 'I19',
            'result6': 'I20'
        }
    }
    
    config_manager = get_config_manager()
    for key, value in default_configs.items():
        config_manager.set_config(key, value)
    
    print("默认配置初始化完成")

if __name__ == '__main__':
    # 确保必要的目录存在
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # 创建应用实例
    app = create_app()
    
    # 初始化数据库
    with app.app_context():
        db.create_all()
        print("数据库初始化完成")
    
    # 运行应用
    app.run(debug=True, host='0.0.0.0', port=5000)
