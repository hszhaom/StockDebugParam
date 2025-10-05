import os
from pathlib import Path

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        import secrets
        SECRET_KEY = secrets.token_hex(32)
        print("WARNING: Using generated SECRET_KEY. Set SECRET_KEY environment variable in production!")
    
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
    from app.models import SystemConfig
    
    config_manager = get_config_manager()
    
    # 默认配置 - 只在配置不存在时设置
    default_configs = {
        'spreadsheet_id': '',
        'sheet_name': 'data',
        'token_file': 'data/token.json',
        'proxy_url': None,
        'max_concurrent_tasks': 5,
        'task_timeout': 36000,
        'task_status_check_timeout': 600,  # 10分钟，任务状态检查超时
        'execution_delay_min': 20,  # 执行延迟最小值（秒）
        'execution_delay_max': 30,  # 执行延迟最大值（秒）
        'api_retry_max_attempts': 10,  # API重试最大次数
        'api_retry_delay': 30,  # API重试延迟（秒）
        'frontend_polling_interval': 15000,  # 前端轮询间隔（毫秒）
        'dashboard_refresh_interval': 30000,  # 仪表板刷新间隔（毫秒）
        'detail_refresh_interval': 60000,  # 详情页刷新间隔（毫秒）
        'log_polling_interval': 3000,  # 日志轮询间隔（毫秒）
        'log_realtime_interval': 3000,  # 日志实时更新间隔（毫秒）
        'tasks_admin_refresh_interval': 30000,  # 管理页面任务刷新间隔（毫秒）
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
    
    # 只设置不存在的配置项，避免覆盖用户修改的配置
    for key, value in default_configs.items():
        existing_config = SystemConfig.query.filter_by(key=key).first()
        if not existing_config:
            config_manager.set_config(key, value)
            print(f"初始化默认配置: {key}")
        else:
            print(f"配置已存在，跳过: {key}")
    