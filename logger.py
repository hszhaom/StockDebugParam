import logging
import os
from datetime import datetime

class TextLogger:
    def __init__(self, log_file="logs/app.log"):
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 配置日志
        self.logger = logging.getLogger("GoogleSheetLogger")
        self.logger.setLevel(logging.INFO)
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 创建格式器并添加到处理器
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器到日志记录器
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    @staticmethod
    def info(message):
        logger = logging.getLogger("GoogleSheetLogger")
        if not logger.handlers:
            TextLogger()  # 初始化日志记录器
        logger.info(message)
    
    @staticmethod
    def error(message):
        logger = logging.getLogger("GoogleSheetLogger")
        if not logger.handlers:
            TextLogger()  # 初始化日志记录器
        logger.error(message)
    
    @staticmethod
    def warning(message):
        logger = logging.getLogger("GoogleSheetLogger")
        if not logger.handlers:
            TextLogger()  # 初始化日志记录器
        logger.warning(message)

# 创建logs目录
if not os.path.exists("logs"):
    os.makedirs("logs")