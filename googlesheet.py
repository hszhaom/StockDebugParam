import os
import time
import traceback

import gspread
import requests
from google.oauth2.credentials import Credentials
from gspread import Cell
from gspread.utils import convert_credentials

from logger import TextLogger
import httpx
from typing import Optional
from google.auth.transport.requests import Request, AuthorizedSession
from gspread import Client

class GoogleSheet:
    def __init__(self, spreadsheet_id, sheecode='data',token_file="data/token.json",proxy_url=None):
        # google 验证
        # SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        # creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        # client = gspread.authorize(creds)
        # # 页面功能
        # self.sheet = client.open_by_key(spreadsheet_id)
        # self.worksheet = self.sheet.worksheet(sheecode)  # 指定工作表名称 data control


        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

        try:

            # 加载凭证
            creds = Credentials.from_authorized_user_file(token_file, scopes=SCOPES)

            # # 确保凭证有效（处理令牌刷新）
            # if creds.expired and creds.refresh_token:
            #     creds.refresh(Request())

            client = gspread.authorize(credentials = creds)
            if proxy_url:
                TextLogger.info(f"使用代理：{proxy_url}")
                # 设置代理环境变量
                os.environ['HTTP_PROXY'] = proxy_url
                os.environ['HTTPS_PROXY'] =  proxy_url

            # 打开电子表格和工作表
            self.sheet = client.open_by_key(spreadsheet_id)
            self.worksheet = self.sheet.worksheet(sheecode)
        except Exception as e:
            TextLogger.info(f'打开表格错误。错误内容：{traceback.format_exc()}')
            raise e

    def get(self,name):
        return getattr(self,name)

    def get_row(self,row):
        return self.worksheet.row_values(row)

    def get_last_row(self, col_letter):
        try:
            """通过反向遍历快速定位最后非空行"""
            col_data = self.worksheet.col_values(
                ord(col_letter) - ord('A') + 1)  # 字母转数字列号
            return len(col_data) if col_data else 0
        except Exception as e:
            TextLogger.info(f'获取最后非空行错误。错误内容：{str(e)}')
            return -1

    @staticmethod
    def col_letter_to_num(col_letter):
        # 将Excel列字母转换为数字
        num = 0
        for c in col_letter:
            num = num * 26 + (ord(c) - ord('A') + 1)
        return num

    @staticmethod
    def num_to_col_letter(num):
        # 将数字转换为Excel列字母
        if num <= 0:
            return ""
        result = ""
        while num > 0:
            num -= 1  # Adjust for 1-based indexing
            result = chr(num % 26 + ord('A')) + result
            num //= 26
        return result

    def calculate_stock_column(self, start_cell, stock_index,is_number=False):
        """
        动态计算股票在表格中的列位置
        :param start_cell: 起始单元格，例如'I1'
        :param stock_index: 股票序号（从1开始）
        :return: (当前股票列, 后一列) 例如 ('M1', 'N1')
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

        # # 调试信息
        # TextLogger.info(
        #     f"stock_index: {stock_index}, start_col_num: {start_col_num}, base_col_offset: {base_col_offset}, current_col_num: {current_col_num}, current_col_letter: {current_col_letter}")
        if is_number:
            return current_col_num,next_col_num
        return f"{current_col_letter}{start_row}", f"{next_col_letter}{start_row}"

    def update_row(self, sheet_row, sheet_value):
        try:
            pass
            TextLogger.info(f"写入：sheet_rows：{sheet_row}, sheet_values：{sheet_value}")
            self.worksheet.update(sheet_row, [[sheet_value]], value_input_option="USER_ENTERED")
        except Exception as e:
            TextLogger.info(f'设置表格{sheet_row},值:{sheet_value}错误。错误内容：{str(e)}')
            return f'设置表格{sheet_row},值:{sheet_value}错误。错误内容：{str(e)}'


    def clear_row(self, sheet_rows):
        self.worksheet.range(sheet_rows).clear()


    def update_rows(self, sheet_rows, sheet_values):
        try:
            pass
            TextLogger.info(f"批量写入：sheet_rows：{sheet_rows}, sheet_values：{sheet_values}")
            self.worksheet.update(sheet_rows, sheet_values, value_input_option="USER_ENTERED")
        except Exception as e:
            TextLogger.info(f'设置表格{sheet_rows},值:{sheet_values}错误。错误内容：{str(e)}')
            return f'设置表格{sheet_rows},值:{sheet_values}错误。错误内容：{str(e)}'

    def update_jumped_cells(self, cell_updates):
        """
        更新跳跃的单元格

        参数:
        cell_updates: 字典，格式为 {单元格地址: 新值}
        例如: {"A1": "姓名", "I1": "年龄", "N1": "城市", "AI1": "职业"}
        """
        if not self.worksheet:
            raise Exception("请先选择工作表")

        try:
            # 创建Cell对象列表
            cells = []
            for cell_address, value in cell_updates.items():
                # 将A1表示法转换为行列号
                row, col = gspread.utils.a1_to_rowcol(cell_address)
                cells.append(Cell(row, col, value))

            # 批量更新单元格
            return self.worksheet.update_cells(cells)

        except Exception as e:
            TextLogger.info(f"更新跳跃单元格失败: {e}")

    def get_cell(self,cell_ref):
        return self.worksheet.get(cell_ref)[0][0]


    def get_trade_count_with_retry(self, cell_ref, max_retries=10, delay=30):
        retry_count = 0
        while retry_count < max_retries:
            try:
                trade_count = self.worksheet.get(cell_ref)[0][0]
                if trade_count != '#DIV/0!' and trade_count.find("target") == -1:
                    return trade_count
            except Exception as e:
                TextLogger.info(f'获取交易数量出错: {str(e)}')
            TextLogger.info(f'重试中，已尝试{retry_count}次')
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(delay)
        TextLogger.info(f'多次尝试后，仍无法获取有效的交易数量，返回0')
        return '0'
