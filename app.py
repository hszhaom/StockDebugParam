#!/usr/bin/env python3
"""
旧版应用文件 - 已重构为新架构
请使用 run.py 启动新版本应用
"""
import os
import sys
from flask import Flask, render_template, redirect, url_for

# 添加新应用路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)

@app.route('/')
def index():
    """重定向到新版本管理面板"""
    return redirect('/admin/')

@app.route('/create')
def create_task_page():
    """重定向到新版本创建页面"""
    return redirect('/google-sheet/create')

@app.route('/detail')
def task_detail_page():
    """重定向到新版本详情页面"""
    return redirect('/google-sheet/detail')

@app.route('/config')
def config_page():
    """重定向到新版本配置页面"""
    return redirect('/admin/config')

if __name__ == '__main__':
    print("=" * 60)
    print("注意：此版本已重构为新架构")
    print("请使用以下命令启动新版本：")
    print("python run.py")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)