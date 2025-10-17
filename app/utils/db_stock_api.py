#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP请求工具类
用于与股票API进行通信
"""

import requests
import json
import time
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class StockAPIClient:
    """股票API客户端"""

    def __init__(self, base_url: str = "http://sxapi.stplan.cn/api/Stock", timeout: int = 30):
        """
        初始化API客户端

        Args:
            base_url: API基础URL
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

        # 设置默认请求头
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Python Stock Parameter Validator/1.0'
        })

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None,
                      params: Optional[Dict] = None) -> Optional[Dict]:
        """
        发送HTTP请求

        Args:
            method: HTTP方法
            endpoint: API端点
            data: 请求数据
            params: URL参数

        Returns:
            响应数据字典或None
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        logger.debug(f"发送 {method} 请求到 {url}")

        if method.upper() == 'GET':
            response = self.session.get(url, params=params, timeout=self.timeout)
        elif method.upper() == 'POST':
            response = self.session.post(url, json=data, params=params, timeout=self.timeout)
        elif method.upper() == 'PUT':
            response = self.session.put(url, json=data, params=params, timeout=self.timeout)
        elif method.upper() == 'DELETE':
            response = self.session.delete(url, params=params, timeout=self.timeout)
        else:
            raise ValueError(f"不支持的HTTP方法: {method}")

        response.raise_for_status()

        # 检查响应状态
        if response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError:
                logger.warning(f"响应不是有效的JSON格式: {response.text}")
                return {"raw_response": response.text}
        raise requests.HTTPError(f"请求失败，状态码: {response.status_code}, 响应: {response.text}")

    def get_single_stock_template_param(self, stock_no: str) -> Optional[Dict]:
        """
        获取单个股票模板参数

        Args:
            stock_no: 股票编号

        Returns:
            股票参数字典或None
        """
        endpoint = "GetSingleStockTemplateParam"
        data = {"stock_no": stock_no}

        response = self._make_request('POST', endpoint, data=data)

        if response:
            ret_obj = response.get('ret_obj')
            if ret_obj:
                logger.info(f"获取股票参数成功: {ret_obj}")
                return ret_obj
            else:
                logger.warning(f"响应中没有ret_obj字段: {response}")
                return None
        else:
            logger.error("获取股票参数失败")
            return None

    def insert_stock_template_param(self, param_data: Dict) -> int:
        """
        插入股票模板参数

        Args:
            param_data: 参数数据字典

        Returns:
            返回的ID或0
        """
        endpoint = "InsertStockTemplateParam"

        response = self._make_request('POST', endpoint, data=param_data)

        if response:
            ret_count = response.get('ret_count', 0)
            logger.info(f"插入参数成功，返回ID: {ret_count}")
            return ret_count
        else:
            logger.error("插入参数失败")
            return 0

    def update_stock_template_param(self, param_id: int, param_data: Dict) -> bool:
        """
        更新股票模板参数

        Args:
            param_id: 参数ID
            param_data: 参数数据字典

        Returns:
            是否更新成功
        """
        endpoint = f"UpdateStockTemplateParam/{param_id}"

        response = self._make_request('PUT', endpoint, data=param_data)

        if response:
            logger.info(f"更新参数 {param_id} 成功")
            return True
        else:
            logger.error(f"更新参数 {param_id} 失败")
            return False

    def delete_stock_template_param(self, param_id: int) -> bool:
        """
        删除股票模板参数

        Args:
            param_id: 参数ID

        Returns:
            是否删除成功
        """
        endpoint = f"DeleteStockTemplateParam/{param_id}"

        response = self._make_request('DELETE', endpoint)

        if response:
            logger.info(f"删除参数 {param_id} 成功")
            return True
        else:
            logger.error(f"删除参数 {param_id} 失败")
            return False

    def get_stock_template_params(self, stock_no: str = None, limit: int = 100, offset: int = 0) -> Optional[Dict]:
        """
        获取股票模板参数列表

        Args:
            stock_no: 股票编号（可选）
            limit: 限制数量
            offset: 偏移量

        Returns:
            参数列表或None
        """
        endpoint = "GetStockTemplateParams"
        params = {
            "limit": limit,
            "offset": offset
        }

        if stock_no:
            params["stock_no"] = stock_no

        response = self._make_request('GET', endpoint, params=params)

        if response:
            logger.info(f"获取参数列表成功，共 {len(response.get('data', []))} 条记录")
            return response
        else:
            logger.error("获取参数列表失败")
            return None

    def health_check(self) -> bool:
        """
        健康检查

        Returns:
            是否健康
        """
        try:
            # 尝试获取参数列表来检查API是否可用
            response = self.get_stock_template_params(limit=1)
            return response is not None
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False

    def close(self):
        """关闭会话"""
        self.session.close()
        logger.info("API客户端会话已关闭")

