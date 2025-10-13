import logging
import logging.handlers
import os
from pathlib import Path
from app.config import Config
from typing import Optional


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器"""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    # 设置日志级别
    logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO))

    # 创建格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 确保日志目录存在
    log_path = Path(Config.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 使用原生的TimedRotatingFileHandler按天切割
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=Config.LOG_FILE,
        when='midnight',  # 每天午夜切割
        interval=1,  # 间隔1天
        backupCount=30,  # 保留30天的日志
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d.log"  # 设置备份文件的后缀格式

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 关键修复：阻止向父级logger传播，避免重复日志
    logger.propagate = False

    return logger


class TaskLogger:
    """任务专用日志记录器，自动添加任务ID前缀"""
    
    def __init__(self, task_id: str, logger_name: str = None):
        self.task_id = task_id
        self.logger = get_logger(logger_name or __name__)
        self.prefix = f"[Task-{task_id[:8]}]"  # 使用任务ID前8位作为前缀
    
    def _format_message(self, message: str) -> str:
        """格式化消息，添加任务ID前缀"""
        return f"{self.prefix} {message}"
    
    def debug(self, message: str):
        """记录debug级别日志"""
        self.logger.debug(self._format_message(message))
    
    def info(self, message: str):
        """记录info级别日志"""
        self.logger.info(self._format_message(message))
    
    def warning(self, message: str):
        """记录warning级别日志"""
        self.logger.warning(self._format_message(message))
    
    def error(self, message: str):
        """记录error级别日志"""
        self.logger.error(self._format_message(message))
    
    def exception(self, message: str):
        """记录异常信息"""
        self.logger.exception(self._format_message(message))
    
    def step_info(self, step: int, total: int, message: str):
        """记录执行步骤信息"""
        step_msg = f"[Step {step}/{total}] {message}"
        self.info(step_msg)
    
    def progress_info(self, percentage: float, message: str):
        """记录进度信息"""
        progress_msg = f"[Progress {percentage:.1f}%] {message}"
        self.info(progress_msg)
    
    def api_info(self, action: str, details: str = ""):
        """记录API调用信息"""
        api_msg = f"[API] {action}"
        if details:
            api_msg += f" - {details}"
        self.info(api_msg)
    
    def api_error(self, action: str, error: str):
        """记录API错误信息"""
        api_msg = f"[API_ERROR] {action} - {error}"
        self.error(api_msg)


def get_task_logger(task_id: str, logger_name: str = None) -> TaskLogger:
    """获取任务专用日志记录器"""
    return TaskLogger(task_id, logger_name)