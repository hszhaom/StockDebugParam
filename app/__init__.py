from flask import Flask
from app.config import Config
from app.extensions import db, migrate
from app.routes import register_blueprints

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
    
    # 注册蓝图
    register_blueprints(app)
    
    return app
