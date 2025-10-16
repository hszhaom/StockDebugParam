"""
数据库重试工具模块
专门处理SQLite数据库锁定和重试逻辑
"""
import time
import random
from functools import wraps
from typing import Callable, Any, Optional
from sqlalchemy.exc import OperationalError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseLockError(Exception):
    """数据库锁定异常"""
    pass


def db_retry(
    max_attempts: int = 5,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
    exponential_base: float = 2.0,
    jitter: bool = True
):
    """
    数据库操作重试装饰器
    专门处理SQLite数据库锁定问题
    
    Args:
        max_attempts: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        exponential_base: 指数退避基数
        jitter: 是否添加随机抖动
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    last_exception = e
                    error_str = str(e).lower()
                    
                    # 检查是否是数据库锁定错误
                    if 'database is locked' in error_str or 'database table is locked' in error_str:
                        if attempt < max_attempts - 1:  # 不是最后一次尝试
                            # 计算延迟时间
                            delay = min(base_delay * (exponential_base ** attempt), max_delay)
                            
                            # 添加随机抖动
                            if jitter:
                                delay *= (0.5 + random.random() * 0.5)
                            
                            logger.warning(
                                f"数据库锁定，第 {attempt + 1} 次重试，等待 {delay:.2f} 秒后重试"
                            )
                            time.sleep(delay)
                            continue
                        else:
                            logger.error(f"数据库锁定重试失败，已达到最大重试次数 {max_attempts}")
                            raise DatabaseLockError(f"数据库锁定重试失败: {str(e)}")
                    else:
                        # 其他数据库错误，直接抛出
                        raise e
                except Exception as e:
                    # 非数据库错误，直接抛出
                    raise e
            
            # 如果所有重试都失败了
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def safe_db_operation(
    operation: Callable,
    max_attempts: int = 5,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
    *args,
    **kwargs
) -> Any:
    """
    安全执行数据库操作
    
    Args:
        operation: 要执行的数据库操作函数
        max_attempts: 最大重试次数
        base_delay: 基础延迟时间
        max_delay: 最大延迟时间
        *args: 操作函数的参数
        **kwargs: 操作函数的关键字参数
    
    Returns:
        操作结果
    """
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return operation(*args, **kwargs)
        except OperationalError as e:
            last_exception = e
            error_str = str(e).lower()
            
            if 'database is locked' in error_str or 'database table is locked' in error_str:
                if attempt < max_attempts - 1:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    delay *= (0.5 + random.random() * 0.5)  # 添加抖动
                    
                    logger.warning(f"数据库锁定，第 {attempt + 1} 次重试，等待 {delay:.2f} 秒")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"数据库锁定重试失败，已达到最大重试次数 {max_attempts}")
                    raise DatabaseLockError(f"数据库锁定重试失败: {str(e)}")
            else:
                raise e
        except Exception as e:
            raise e
    
    if last_exception:
        raise last_exception


class DatabaseRetryManager:
    """数据库重试管理器"""
    
    def __init__(
        self,
        max_attempts: int = 5,
        base_delay: float = 0.1,
        max_delay: float = 2.0,
        exponential_base: float = 2.0
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """执行带重试的数据库操作"""
        return safe_db_operation(
            operation,
            self.max_attempts,
            self.base_delay,
            self.max_delay,
            *args,
            **kwargs
        )
    
    def commit_with_retry(self, session):
        """带重试的提交操作"""
        def commit_operation():
            session.commit()
        
        return self.execute_with_retry(commit_operation)
    
    def flush_with_retry(self, session):
        """带重试的刷新操作"""
        def flush_operation():
            session.flush()
        
        return self.execute_with_retry(flush_operation)


# 全局重试管理器实例
db_retry_manager = DatabaseRetryManager()
