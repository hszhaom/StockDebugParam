import os
import time
import traceback
from typing import Optional

import gspread
from google.oauth2.credentials import Credentials
from gspread import Cell
from app.utils.logger import get_logger

logger = get_logger(__name__)

class GoogleSheet:
    """Google Sheet客户端类"""
    
    def __init__(self, spreadsheet_id, sheet_name='data', token_file="data/token.json", proxy_url=None):
        """
        初始化Google Sheet连接
        
        Args:
            spreadsheet_id: 电子表格ID
            sheet_name: 工作表名称，默认为'data'
            token_file: 认证文件路径
            proxy_url: 代理URL
        """
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

        try:
            # 加载凭证
            creds = Credentials.from_authorized_user_file(token_file, scopes=SCOPES)

            client = gspread.authorize(credentials=creds)
            if proxy_url:
                logger.info(f"使用代理：{proxy_url}")
                # 设置代理环境变量
                os.environ['HTTP_PROXY'] = proxy_url
                os.environ['HTTPS_PROXY'] = proxy_url

            # 打开电子表格和工作表
            self.sheet = client.open_by_key(spreadsheet_id)
            self.worksheet = self.sheet.worksheet(sheet_name)
            logger.info(f"Google Sheet连接成功: {spreadsheet_id}/{sheet_name}")
            
        except Exception as e:
            logger.error(f'打开表格错误。错误内容：{traceback.format_exc()}')
            raise e

    def get(self, name):
        """获取属性"""
        return getattr(self, name)

    def get_row(self, row):
        """获取指定行的值"""
        return self.worksheet.row_values(row)

    def get_last_row(self, col_letter):
        """获取指定列的最后非空行"""
        try:
            col_data = self.worksheet.col_values(
                ord(col_letter) - ord('A') + 1)  # 字母转数字列号
            return len(col_data) if col_data else 0
        except Exception as e:
            logger.error(f'获取最后非空行错误。错误内容：{str(e)}')
            return -1

    @staticmethod
    def col_letter_to_num(col_letter):
        """将Excel列字母转换为数字"""
        num = 0
        for c in col_letter:
            num = num * 26 + (ord(c) - ord('A') + 1)
        return num

    @staticmethod
    def num_to_col_letter(num):
        """将数字转换为Excel列字母"""
        if num <= 0:
            return ""
        result = ""
        while num > 0:
            num -= 1  # Adjust for 1-based indexing
            result = chr(num % 26 + ord('A')) + result
            num //= 26
        return result

    def calculate_stock_column(self, start_cell, stock_index, is_number=False):
        """
        动态计算股票在表格中的列位置
        
        Args:
            start_cell: 起始单元格，例如'I1'
            stock_index: 股票序号（从1开始）
            is_number: 是否返回数字格式
            
        Returns:
            (当前股票列, 后一列) 例如 ('M1', 'N1')
        """
        # 解析起始单元格
        start_col_letter = ''.join(filter(str.isalpha, start_cell))
        start_row = ''.join(filter(str.isdigit, start_cell))

        # 起始列号（I=9）
        start_col_num = self.col_letter_to_num(start_col_letter)

        # 第一支股票从M列开始（M=13）
        # 计算M列相对于起始列的偏移量
        base_col_offset = 13 - start_col_num

        # 计算当前股票应该在的列号
        # 第一支股票在M列，第二支在V列，第三支在AE列，间隔9列
        current_col_num = start_col_num + base_col_offset + (stock_index - 1) * 9
        current_col_letter = self.num_to_col_letter(current_col_num)

        # 计算后一列
        next_col_num = current_col_num + 1
        next_col_letter = self.num_to_col_letter(next_col_num)

        if is_number:
            return current_col_num, next_col_num
        return f"{current_col_letter}{start_row}", f"{next_col_letter}{start_row}"

    def update_row(self, sheet_row, sheet_value):
        """更新单行数据"""
        try:
            logger.info(f"写入：sheet_rows：{sheet_row}, sheet_values：{sheet_value}")
            self.worksheet.update(sheet_row, [[sheet_value]], value_input_option="USER_ENTERED")
        except Exception as e:
            logger.error(f'设置表格{sheet_row},值:{sheet_value}错误。错误内容：{str(e)}')
            return f'设置表格{sheet_row},值:{sheet_value}错误。错误内容：{str(e)}'

    def clear_row(self, sheet_rows):
        """清除指定行"""
        self.worksheet.range(sheet_rows).clear()

    def update_rows(self, sheet_rows, sheet_values):
        """批量更新行数据"""
        try:
            logger.info(f"批量写入：sheet_rows：{sheet_rows}, sheet_values：{sheet_values}")
            self.worksheet.update(sheet_rows, sheet_values, value_input_option="USER_ENTERED")
        except Exception as e:
            logger.error(f'设置表格{sheet_rows},值:{sheet_values}错误。错误内容：{str(e)}')
            return f'设置表格{sheet_rows},值:{sheet_values}错误。错误内容：{str(e)}'

    def update_jumped_cells(self, cell_updates):
        """
        更新跳跃的单元格

        Args:
            cell_updates: 字典，格式为 {单元格地址: 新值}
            例如: {"A1": "姓名", "I1": "年龄", "N1": "城市", "AI1": "职业"}
        """
        if not self.worksheet:
            raise Exception("请先选择工作表")

        # 检查cell_updates是否为空
        if not cell_updates:
            logger.warning("cell_updates为空，跳过更新操作")
            return None

        try:
            # 创建Cell对象列表
            cells = []
            for cell_address, value in cell_updates.items():
                # 验证单元格地址格式
                if not cell_address or not isinstance(cell_address, str):
                    logger.warning(f"无效的单元格地址: {cell_address}")
                    continue
                
                # 将A1表示法转换为行列号
                row, col = gspread.utils.a1_to_rowcol(cell_address)
                cells.append(Cell(row, col, value))

            # 如果没有有效的单元格，直接返回
            if not cells:
                logger.warning("没有有效的单元格需要更新")
                return None

            # 批量更新单元格
            return self.worksheet.update_cells(cells)

        except Exception as e:
            logger.error(f"更新跳跃单元格失败: {e}", exc_info=True)
            return None

    def get_cell(self, cell_ref):
        """获取指定单元格的值"""
        return self.worksheet.get(cell_ref)[0][0]

    def get_cells_batch(self, cell_refs):
        """
        批量获取多个单元格的值
        
        Args:
            cell_refs: 单元格引用列表，例如 ['A1', 'B2', 'C3']
            
        Returns:
            字典，格式为 {单元格地址: 值}
        """
        if not self.worksheet:
            raise Exception("请先选择工作表")
        
        if not cell_refs:
            logger.warning("cell_refs为空，返回空字典")
            return {}
        
        try:
            # 构建批量获取的单元格范围
            # 如果单元格不连续，我们需要分别获取每个单元格
            results = {}
            
            # 使用 batch_get 方法批量获取
            # 将单个单元格引用转换为范围格式
            ranges = [f"{ref}" for ref in cell_refs]
            
            # 批量获取值
            batch_values = self.worksheet.batch_get(ranges)
            
            # 将结果转换为字典格式
            for i, cell_ref in enumerate(cell_refs):
                if i < len(batch_values) and batch_values[i]:
                    # batch_values[i] 是一个列表，包含该单元格的值
                    value = batch_values[i][0][0] if batch_values[i][0] else ""
                    results[cell_ref] = value
                else:
                    results[cell_ref] = ""
            
            logger.info(f"批量获取了 {len(results)} 个单元格的值")
            return results
            
        except Exception as e:
            logger.error(f"批量获取单元格失败: {e}", exc_info=True)
            # 如果批量获取失败，回退到逐个获取
            logger.info("回退到逐个获取单元格值")
            results = {}
            for cell_ref in cell_refs:
                try:
                    value = self.get_cell(cell_ref)
                    results[cell_ref] = value
                except Exception as cell_error:
                    logger.error(f"获取单元格 {cell_ref} 失败: {cell_error}")
                    results[cell_ref] = ""
            return results

    def get_trade_count_with_retry(self, cell_ref, max_retries=10, delay=30):
        """带重试机制获取交易数量"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                trade_count = self.worksheet.get(cell_ref)[0][0]
                if trade_count != '#DIV/0!' and trade_count.find("target") == -1:
                    return trade_count
            except Exception as e:
                logger.error(f'获取交易数量出错: {str(e)}')
            logger.info(f'重试中，已尝试{retry_count}次')
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(delay)
        logger.warning(f'多次尝试后，仍无法获取有效的交易数量，返回0')
        return '0'
