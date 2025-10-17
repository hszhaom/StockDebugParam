from flask import Flask
from app.config import Config
from app.extensions import db, migrate
from app.routes import register_blueprints
from flask_restx import Api
from app.routes.api_restx import api_ns, config_ns, template_ns, result_ns, logs_ns, gsheet_ns
from app.utils.ding_talk_notifier import DingTalkNotifier

def create_app():
    # 获取应用根目录
    import os
    from pathlib import Path
    
    # 获取当前文件所在目录的父目录（即项目根目录）
    current_dir = Path(__file__).parent.parent
    template_dir = current_dir / 'templates'
    static_dir = current_dir / 'static'
    
    app = Flask(__name__, 
                template_folder=str(template_dir), 
                static_folder=str(static_dir))
                
    app.config.from_object(Config)
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)

    # 注册API文档
    api = Api(app, version='1.0', title='Google Sheet Task API',
              description='自动生成Swagger接口文档 - 访问 /swagger',
              doc='/swagger')
    api.add_namespace(api_ns, path='/api')
    api.add_namespace(config_ns, path='/api')
    api.add_namespace(template_ns, path='/api')
    api.add_namespace(result_ns, path='/api')
    api.add_namespace(logs_ns, path='/api')
    api.add_namespace(gsheet_ns, path='/api')
    # 保留原有蓝图注册
    register_blueprints(app)
    
    notifier = DingTalkNotifier(
        access_token=Config.dd_access_token,
        secret=Config.dd_secret
    )

    app.notifier = notifier

    return app
