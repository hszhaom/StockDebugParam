"""
数据库操作工具模块
提供事务管理、连接管理等功能
"""
import functools
from sqlalchemy.exc import IntegrityError, OperationalError
from app.extensions import db
from app.utils.logger import get_logger

logger = get_logger(__name__)


def transaction_required(func):
    """
    数据库事务装饰器
    自动处理事务提交、回滚和异常处理
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            db.session.commit()
            return result
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"数据库完整性错误: {str(e)}")
            raise
        except OperationalError as e:
            db.session.rollback()
            logger.error(f"数据库操作错误: {str(e)}")
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"数据库操作异常: {str(e)}")
            raise
    return wrapper


def safe_delete(model_class, **filters):
    """
    安全删除操作
    
    Args:
        model_class: 模型类
        **filters: 过滤条件
    
    Returns:
        int: 删除的记录数
    """
    try:
        query = model_class.query.filter_by(**filters)
        count = query.count()
        query.delete()
        db.session.commit()
        logger.info(f"成功删除 {count} 条 {model_class.__name__} 记录")
        return count
    except Exception as e:
        db.session.rollback()
        logger.error(f"删除 {model_class.__name__} 记录失败: {str(e)}")
        raise


def safe_update(model_instance, commit=True, **updates):
    """
    安全更新操作
    
    Args:
        model_instance: 模型实例
        commit: 是否立即提交事务
        **updates: 更新字段
    
    Returns:
        model_instance: 更新后的实例
    """
    try:
        for key, value in updates.items():
            if hasattr(model_instance, key):
                setattr(model_instance, key, value)
        
        if commit:
            db.session.commit()
        logger.debug(f"成功更新 {model_instance.__class__.__name__} 记录")
        return model_instance
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新记录失败: {str(e)}")
        raise


def safe_create(model_class, commit=False, **fields):
    """
    安全创建操作
    
    Args:
        model_class: 模型类
        commit: 是否立即提交事务
        **fields: 字段值
    
    Returns:
        model_instance: 创建的实例
    """
    try:
        instance = model_class(**fields)
        db.session.add(instance)
        if commit:
            db.session.commit()
        logger.debug(f"成功创建 {model_class.__name__} 记录")
        return instance
    except Exception as e:
        db.session.rollback()
        logger.error(f"创建 {model_class.__name__} 记录失败: {str(e)}")
        raise


class DatabaseManager:
    """数据库管理器"""
    
    @staticmethod
    def get_or_create(model_class, defaults=None, **kwargs):
        """
        获取或创建记录
        
        Args:
            model_class: 模型类
            defaults: 创建时的默认值
            **kwargs: 查询条件
        
        Returns:
            tuple: (instance, created)
        """
        try:
            instance = model_class.query.filter_by(**kwargs).first()
            if instance:
                return instance, False
            
            # 创建新记录
            params = kwargs.copy()
            if defaults:
                params.update(defaults)
            
            instance = model_class(**params)
            db.session.add(instance)
            db.session.commit()
            return instance, True
        except Exception as e:
            db.session.rollback()
            logger.error(f"get_or_create 操作失败: {str(e)}")
            raise
    
    @staticmethod
    def bulk_create(model_class, data_list):
        """
        批量创建记录
        
        Args:
            model_class: 模型类
            data_list: 数据列表
        
        Returns:
            list: 创建的实例列表
        """
        try:
            instances = [model_class(**data) for data in data_list]
            db.session.bulk_save_objects(instances)
            db.session.commit()
            logger.info(f"批量创建 {len(instances)} 条 {model_class.__name__} 记录")
            return instances
        except Exception as e:
            db.session.rollback()
            logger.error(f"批量创建失败: {str(e)}")
            raise
    
    @staticmethod
    def execute_in_transaction(operations):
        """
        在单个事务中执行多个操作
        
        Args:
            operations: 操作函数列表
        
        Returns:
            list: 操作结果列表
        """
        try:
            results = []
            for operation in operations:
                result = operation()
                results.append(result)
            
            db.session.commit()
            return results
        except Exception as e:
            db.session.rollback()
            logger.error(f"事务执行失败: {str(e)}")
            raise
