import os
from pathlib import Path

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 文件路径配置
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / 'data'
    LOGS_DIR = BASE_DIR / 'logs'
    CONFIG_DIR = BASE_DIR / 'config'
    
    # 确保目录存在
    DATA_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    # CONFIG_DIR.mkdir(exist_ok=True)
    
    # 任务配置
    MAX_CONCURRENT_TASKS = int(os.environ.get('MAX_CONCURRENT_TASKS', 5))
    TASK_TIMEOUT = int(os.environ.get('TASK_TIMEOUT', 3600))  # 1小时
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = LOGS_DIR / 'app.log'
    

def init_config():
    from app.services.config_manager import get_config_manager
    
    # 检查是否已经初始化过
    config_manager = get_config_manager()
    
    default_configs = {
        'spreadsheet_id': '',
        'sheet_name': 'data',
        'token_file': 'data/token.json',
        'proxy_url': None,
        'max_concurrent_tasks': 5,
        'task_timeout': 36000,
        'parameter_positions': [
            'B6',
            'B7',
            'B9',
            'B10',
            'B11',
            'B12'
        ],
        'check_positions': [
            'I6',
            'I7',
            'I9',
            'I10',
            'I11',
            'I12'
        ],
        'result_positions': [
            'I15',
            'I16',
            'I17',
            'I18',
            'I19',
            'I20',
            'I21',
            'I22',
            'I23',
        ]
    }
    
    for key, value in default_configs.items():
        config_manager.set_config(key, value)
    