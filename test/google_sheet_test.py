#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Sheets 参数批量校验工具 - Python版本
从Google Apps Script转换而来
"""

import time
import random
import json
from typing import Dict, List, Optional, Tuple
import logging

# 导入自定义模块
from google_sheets_client import GoogleSheetsClient
from stock_api_client import StockAPIClient

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StockParameterValidator:
    """股票参数批量校验器"""
    
    def __init__(self, sheets_client: GoogleSheetsClient, api_client: StockAPIClient):
        self.sheets_client = sheets_client
        self.api_client = api_client
        
        # 参数数组定义
        self.xm_arr = [3, 3.5, 4]  # 波动率调参1
        self.tp_arr = [0.82, 0.83, 0.84, 0.85, 0.86, 0.87, 0.88, 0.89, 0.90, 0.91, 0.92]
        self.zl_arr = [0.3]
        self.zg_arr = [1]
        self.ywfs_arr = [0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1]
        self.ywfb_arr = [0.18, 0.19, 0.2, 0.21, 0.22, 0.23, 0.24, 0.25, 0.26, 0.27]
        
    def generate_random_number(self) -> int:
        """生成20-30之间的随机数"""
        return random.randint(20, 30)
    
    def get_single_stock_template_param(self, stock_no: str) -> Optional[Dict]:
        """
        获取单个股票模板参数
        
        Args:
            stock_no: 股票编号
            
        Returns:
            股票参数字典或None
        """
        return self.api_client.get_single_stock_template_param(stock_no)
    
    def send_stock_template_param_data(self, payload: Dict) -> int:
        """
        发送股票模板参数数据
        
        Args:
            payload: 参数数据字典
            
        Returns:
            返回的ID或0
        """
        return self.api_client.insert_stock_template_param(payload)
    
    def get_value6(self, index: int) -> List[float]:
        """
        根据索引计算6个参数的值
        
        Args:
            index: 参数组合索引
            
        Returns:
            6个参数值的列表
        """
        tp_count = len(self.tp_arr) * len(self.zl_arr) * len(self.zg_arr) * len(self.ywfs_arr) * len(self.ywfb_arr)
        zl_count = len(self.zl_arr) * len(self.zg_arr) * len(self.ywfs_arr) * len(self.ywfb_arr)
        zg_count = len(self.zg_arr) * len(self.ywfs_arr) * len(self.ywfb_arr)
        ywfs_count = len(self.ywfs_arr) * len(self.ywfb_arr)
        ywfb_count = len(self.ywfb_arr)
        
        xm_index = index // tp_count
        tp_index = (index % tp_count) // zl_count
        zl_index = (index % zl_count) // zg_count
        zg_index = (index % zg_count) // ywfs_count
        ywfs_index = (index % ywfs_count) // ywfb_count
        ywfb_index = index % ywfb_count
        
        return [
            self.xm_arr[xm_index],
            self.tp_arr[tp_index],
            self.zl_arr[zl_index],
            self.zg_arr[zg_index],
            self.ywfs_arr[ywfs_index],
            self.ywfb_arr[ywfb_index]
        ]
    
    def stock_calc_default(self, sheet_code: str, multiplier_value: float, 
                          danbian_value: float, xiancang_value: float,
                          zhishu_value: float, smoothing_value: float, 
                          bordering_value: float):
        """
        设置默认股票计算参数
        
        Args:
            sheet_code: 工作表代码
            multiplier_value: 乘数
            danbian_value: 单边保护
            xiancang_value: 限仓
            zhishu_value: 指数
            smoothing_value: 平滑
            bordering_value: 边界
        """
        try:
            # 设置参数值到Google Sheets
            self.sheets_client.set_range_value(sheet_code, "B6", multiplier_value)
            self.sheets_client.flush()
            
            self.sheets_client.set_range_value(sheet_code, "B7", danbian_value)
            self.sheets_client.flush()
            
            self.sheets_client.set_range_value(sheet_code, "B9", xiancang_value)
            self.sheets_client.flush()
            
            self.sheets_client.set_range_value(sheet_code, "B10", zhishu_value)
            self.sheets_client.flush()
            
            self.sheets_client.set_range_value(sheet_code, "B11", smoothing_value)
            self.sheets_client.flush()
            
            self.sheets_client.set_range_value(sheet_code, "B12", bordering_value)
            self.sheets_client.flush()
            
            # 随机休眠
            sleep_time = self.generate_random_number()
            logger.info(f"休眠 {sleep_time} 秒")
            time.sleep(sleep_time)
            
        except Exception as e:
            logger.error(f"设置默认参数时出错: {e}")
    
    def stock_push(self, sheet_code: str, stock_no: str, multiplier_index: int,
                   danbian_index: int, xiancang_index: int, zhishu_index: int,
                   smoothing_index: int, bordering_index: int):
        """
        推送股票数据
        
        Args:
            sheet_code: 工作表代码
            stock_no: 股票编号
            multiplier_index: 乘数索引
            danbian_index: 单边保护索引
            xiancang_index: 限仓索引
            zhishu_index: 指数索引
            smoothing_index: 平滑索引
            bordering_index: 边界索引
        """
        try:
            # 获取参数值
            multiplier = round(float(self.sheets_client.get_range_value(sheet_code, "B6")), 2)
            danbian = round(float(self.sheets_client.get_range_value(sheet_code, "B7")), 2)
            jiancang = round(float(self.sheets_client.get_range_value(sheet_code, "B9")), 2)
            zhishu = round(float(self.sheets_client.get_range_value(sheet_code, "B10")), 2)
            smoothing = round(float(self.sheets_client.get_range_value(sheet_code, "B11")), 2)
            bordering = round(float(self.sheets_client.get_range_value(sheet_code, "B12")), 2)
            
            # 获取计算结果值
            c_multiplier = round(float(self.sheets_client.get_range_value(sheet_code, "I6")), 2)
            c_danbian = round(float(self.sheets_client.get_range_value(sheet_code, "I7")), 2)
            c_jiancang = round(float(self.sheets_client.get_range_value(sheet_code, "I9")), 2)
            c_zhishu = round(float(self.sheets_client.get_range_value(sheet_code, "I10")), 2)
            c_smoothing = round(float(self.sheets_client.get_range_value(sheet_code, "I11")), 2)
            c_bordering = round(float(self.sheets_client.get_range_value(sheet_code, "I12")), 2)
            
            # 检查参数是否一致
            if (multiplier != c_multiplier or danbian != c_danbian or 
                jiancang != c_jiancang or zhishu != c_zhishu or 
                smoothing != c_smoothing or bordering != c_bordering):
                sleep_time = self.generate_random_number()
                logger.info(f"参数不一致，休眠 {sleep_time} 秒")
                time.sleep(sleep_time)
            
            # 获取结果数据
            return_rate = round(float(self.sheets_client.get_range_value(sheet_code, "I15")), 4)
            annualized_rate = round(float(self.sheets_client.get_range_value(sheet_code, "I16")), 4)
            maxdd = round(float(self.sheets_client.get_range_value(sheet_code, "I17")), 4)
            index_rate = round(float(self.sheets_client.get_range_value(sheet_code, "I18")), 4)
            index_annualized_rate = round(float(self.sheets_client.get_range_value(sheet_code, "I19")), 4)
            max_index_dd = round(float(self.sheets_client.get_range_value(sheet_code, "I20")), 4)
            fee_total = round(float(self.sheets_client.get_range_value(sheet_code, "I21")), 4)
            fee_annualized = round(float(self.sheets_client.get_range_value(sheet_code, "I22")), 4)
            year_rate = round(float(self.sheets_client.get_range_value(sheet_code, "I23")), 4)
            
            # 构建参数负载
            param_load = {
                "stock_no": stock_no,
                "multiplier": multiplier,
                "danbian": danbian,
                "xiancang": jiancang,
                "zhishu": zhishu,
                "smoothing": smoothing,
                "bordering": bordering,
                "multiplier_index": multiplier_index,
                "danbian_index": danbian_index,
                "xiancang_index": xiancang_index,
                "zhishu_index": zhishu_index,
                "smoothing_index": smoothing_index,
                "bordering_index": bordering_index,
                "return_rate": return_rate,
                "annualized_rate": annualized_rate,
                "maxdd": maxdd,
                "index_rate": index_rate,
                "index_annualized_rate": index_annualized_rate,
                "max_index_dd": max_index_dd,
                "fee_total": fee_total,
                "fee_annualized": fee_annualized,
                "year_rate": year_rate
            }
            
            # 发送数据
            param_id = self.send_stock_template_param_data(param_load)
            logger.info(f"参数数据已发送，ID: {param_id}")
            
        except Exception as e:
            logger.error(f"推送股票数据时出错: {e}")
    
    def get_bdl(self, stock_no: str, sheet_code: str, index_z: int):
        """
        批量参数测试主函数
        
        Args:
            stock_no: 股票编号
            sheet_code: 工作表代码
            index_z: 起始索引
        """
        try:
            all_count = (len(self.xm_arr) * len(self.tp_arr) * len(self.zl_arr) * 
                        len(self.zg_arr) * len(self.ywfs_arr) * len(self.ywfb_arr))
            
            logger.info(f'总共: {all_count} 参数')
            
            for index in range(index_z, all_count):
                result_data = self.get_value6(index)
                logger.info(f'index: {index} -- {result_data}')
                
                # 设置参数值
                self.sheets_client.set_range_value(sheet_code, "B6", result_data[0])
                self.sheets_client.flush()
                
                self.sheets_client.set_range_value(sheet_code, "B7", result_data[1])
                self.sheets_client.flush()
                
                self.sheets_client.set_range_value(sheet_code, "B9", result_data[2])
                self.sheets_client.flush()
                
                self.sheets_client.set_range_value(sheet_code, "B10", result_data[3])
                self.sheets_client.flush()
                
                self.sheets_client.set_range_value(sheet_code, "B11", result_data[4])
                self.sheets_client.flush()
                
                self.sheets_client.set_range_value(sheet_code, "B12", result_data[5])
                self.sheets_client.flush()
                
                # 随机休眠
                sleep_time = self.generate_random_number()
                logger.info(f"休眠 {sleep_time} 秒")
                time.sleep(sleep_time)
                
                # 推送数据
                self.stock_push(sheet_code, stock_no, index, 0, 0, 0, 0, 0)
                
        except Exception as e:
            logger.error(f"批量参数测试时出错: {e}")
    
    def miany(self, stock_no: str = "601899-bdl-1y-1", sheet_code: str = "data1y"):
        """
        主入口函数
        
        Args:
            stock_no: 股票编号
            sheet_code: 工作表代码
        """
        try:
            # 默认参数值
            multiplier_value = 4
            danbian_value = 0.85
            xiancang_value = 0.24
            zhishu_value = 0.88
            smoothing_value = 0.08
            bordering_value = 0.38
            
            # 获取股票参数
            stock_param = self.get_single_stock_template_param(stock_no)
            
            if stock_param is not None and stock_param != "error":
                multiplier_index = 0 if stock_param.get('multiplier_index', 0) == 0 else stock_param.get('multiplier_index', 0) + 1
                self.get_bdl(stock_no, sheet_code, multiplier_index)
            elif stock_param != "error":
                self.stock_calc_default(sheet_code, multiplier_value, danbian_value, 
                                      xiancang_value, zhishu_value, smoothing_value, bordering_value)
                self.get_bdl(stock_no, sheet_code, 0)
            else:
                logger.error("获取股票参数失败")
                
        except Exception as e:
            logger.error(f"主函数执行时出错: {e}")


def main():
    """主函数"""
    try:
        # 初始化Google Sheets客户端
        # 注意：这里需要根据实际情况配置Google Sheets API
        sheets_client = GoogleSheetsClient(
            spreadsheet_id="your_spreadsheet_id_here",
            credentials_path="credentials.json"
        )
        
        # 初始化股票API客户端
        api_client = StockAPIClient()
        
        # 初始化股票参数校验器
        validator = StockParameterValidator(sheets_client, api_client)
        
        # 执行主流程
        validator.miany()
        
    except Exception as e:
        logger.error(f"程序执行时出错: {e}")
    finally:
        # 清理资源
        if 'api_client' in locals():
            api_client.close()


if __name__ == "__main__":
    main()
