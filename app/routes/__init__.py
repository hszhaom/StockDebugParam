from flask import Blueprint

def register_blueprints(app):
    """注册所有蓝图"""
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.google_sheet import google_sheet_bp
    
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(google_sheet_bp, url_prefix='/google-sheet')
