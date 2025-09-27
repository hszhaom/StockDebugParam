from datetime import datetime
from app.extensions import db
import json

class Task(db.Model):
    """任务模型"""
    __tablename__ = 'tasks'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    name = db.Column(db.String(255), nullable=False)  # 任务名称
    description = db.Column(db.Text)  # 任务描述
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, cancelled, error
    task_type = db.Column(db.String(50), default='google_sheet')  # 任务类型
    
    # 配置信息
    config = db.Column(db.Text)  # JSON格式的配置
    
    # 执行信息
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    current_step = db.Column(db.Integer, default=0)
    total_steps = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    logs = db.relationship('TaskLog', backref='task', lazy=True, cascade='all, delete-orphan')
    results = db.relationship('TaskResult', backref='task', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'task_type': self.task_type,
            'config': json.loads(self.config) if self.config else {},
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def get_progress_percentage(self):
        if self.total_steps == 0:
            return 0
        return round((self.current_step / self.total_steps) * 100, 2)

class TaskLog(db.Model):
    """任务日志模型"""
    __tablename__ = 'task_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(36), db.ForeignKey('tasks.id'), nullable=False)
    level = db.Column(db.String(20), default='info')  # info, warning, error
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'level': self.level,
            'message': self.message,
            'timestamp': self.timestamp.isoformat()
        }

class TaskResult(db.Model):
    """任务结果模型"""
    __tablename__ = 'task_results'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(36), db.ForeignKey('tasks.id'), nullable=False)
    step_index = db.Column(db.Integer, nullable=False)
    parameters = db.Column(db.Text)  # JSON格式的参数
    result = db.Column(db.Text)  # JSON格式的结果
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'step_index': self.step_index,
            'parameters': json.loads(self.parameters) if self.parameters else {},
            'result': json.loads(self.result) if self.result else {},
            'success': self.success,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat()
        }

class SystemConfig(db.Model):
    """系统配置模型"""
    __tablename__ = 'system_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self):
        return {
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
