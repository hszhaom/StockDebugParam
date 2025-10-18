"""
结果验证工具模块
用于验证函数返回的字典结果是否有效
"""

from functools import wraps
from typing import Dict, Any, Tuple
from app.utils.logger import get_logger
from app.services.config_manager import get_config_manager
logger = get_logger(__name__)


def validate_result_dict(none_values: Tuple[Any, ...] = (None, '', ' ', 0, '0', '0.0', '0.00')):
    """
    装饰器：验证返回的字典中是否包含空值或无效值
    
    Args:
        none_values: 被认为是"空"的值列表，默认包含 None, '', ' ', 0, '0', '0.0', '0.00'
    
    Returns:
        如果字典中包含空值，则返回 (False, {})，否则返回原始结果
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # 执行原函数
                success, result_dict = func(*args, **kwargs)
                
                # 如果函数本身返回失败，直接返回
                if not success:
                    logger.warning(f"函数 {func.__name__} 返回失败状态，跳过验证")
                    return success, result_dict
                
                # 如果结果不是字典，直接返回
                if not isinstance(result_dict, dict):
                    logger.warning(f"函数 {func.__name__} 返回的不是字典，跳过验证")
                    return success, result_dict
                
                # 检查字典是否为空
                if not result_dict:
                    logger.warning(f"函数 {func.__name__} 返回空字典")
                    return False, {}
                
                # 检查字典中是否有任何空值或无效值
                empty_keys = []
                for key, value in result_dict.items():
                    if value in none_values:
                        empty_keys.append(key)
                    elif isinstance(value, str) and value.strip() == '':
                        empty_keys.append(key)
                    elif isinstance(value, (int, float)) and value == 0:
                        empty_keys.append(key)
                
                # 如果发现空值，记录日志并返回失败
                if empty_keys:
                    logger.warning(f"函数 {func.__name__} 返回的字典包含空值，键: {empty_keys}")
                    return False, {}
                
                # 所有检查通过，返回原始结果
                return success, result_dict
                
            except Exception as e:
                logger.error(f"验证函数 {func.__name__} 结果时出错: {str(e)}")
                return False, {}
        
        return wrapper
    return decorator


def validate_google_sheet_result(result_dict: Dict[str, Any]) -> Tuple[bool, str]:
    """
    专门验证 Google Sheet 结果的字典
    
    Args:
        result_dict: 包含 Google Sheet 结果的字典
        
    Returns:
        (是否有效, 错误信息)
    """
    if not result_dict:
        return False, "结果字典为空"
    config = get_config_manager()
    # 定义必需的键
    _required_keys = ['B6', 'B7', 'B9', 'B10', 'B11', 'B12']  # 参数键
    _result_keys = ['I15', 'I16', 'I17', 'I18', 'I19', 'I20', 'I21', 'I22', 'I23']  # 结果键
    required_keys = config.get('parameter_positions',_required_keys)  # 参数键
    result_keys = config.get('result_positions',_result_keys)  # 结果键
    
    missing_keys = []
    empty_keys = []
    
    # 检查必需键是否存在
    all_keys = required_keys + result_keys
    for key in all_keys:
        if key not in result_dict:
            missing_keys.append(key)
        elif result_dict[key] is None:
            empty_keys.append(key)
        elif isinstance(result_dict[key], str) and result_dict[key].strip() == '':
            empty_keys.append(key)
        elif isinstance(result_dict[key], (int, float)) and result_dict[key] == 0:
            # 对于某些键，0 可能是有效值，需要进一步检查
            if key in result_keys:
                # 结果键为0可能表示计算错误
                empty_keys.append(key)
    
    if missing_keys:
        return False, f"缺少必需的键: {missing_keys}"
    
    if empty_keys:
        return False, f"以下键的值为空或无效: {empty_keys}"
    
    return True, "验证通过"


def is_valid_result_value(value: Any, allow_zero: bool = False) -> bool:
    """
    检查单个值是否为有效的结果值
    
    Args:
        value: 要检查的值
        allow_zero: 是否允许0作为有效值
        
    Returns:
        是否有效
    """
    if value is None:
        return False
    
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == '':
            return False
        if stripped in ['#N/A', '#DIV/0!', '#ERROR!', '#VALUE!', '#REF!', '#NAME?', '#NUM!']:
            return False
        return True
    
    if isinstance(value, (int, float)):
        if not allow_zero and value == 0:
            return False
        if isinstance(value, float) and (value != value or value == float('inf') or value == float('-inf')):
            return False  # 检查 NaN 和无穷大
        return True
    
    return False
