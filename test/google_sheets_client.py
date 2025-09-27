#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Sheets API 客户端实现
"""

import os
import json
from typing import Dict, List, Optional, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)

# Google Sheets API 权限范围
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


class GoogleSheetsClient:
    """Google Sheets API客户端"""
    
    def __init__(self, credentials_path: str = None, spreadsheet_id: str = None, token_path: str = None):
        """
        初始化Google Sheets客户端
        
        Args:
            credentials_path: 服务账号凭据文件路径或OAuth客户端配置文件路径
            spreadsheet_id: Google Sheets ID
            token_path: OAuth token文件路径
        """
        self.spreadsheet_id = spreadsheet_id
        self.credentials_path = credentials_path
        self.token_path = token_path or 'token.json'
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """认证并初始化服务"""
        creds = None
        
        # 检查是否有已保存的token
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # 如果没有有效的凭据，则进行认证
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if self.credentials_path and os.path.exists(self.credentials_path):
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                else:
                    raise FileNotFoundError("未找到凭据文件，请确保credentials_path指向有效的OAuth客户端配置文件")
            
            # 保存凭据供下次使用
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        # 构建服务
        self.service = build('sheets', 'v4', credentials=creds)
        logger.info("Google Sheets API 认证成功")
    
    def get_sheet_by_name(self, sheet_name: str) -> Optional[Dict]:
        """
        获取指定名称的工作表信息
        
        Args:
            sheet_name: 工作表名称
            
        Returns:
            工作表信息字典或None
        """
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            
            for sheet in sheets:
                if sheet['properties']['title'] == sheet_name:
                    return sheet
            
            logger.warning(f"未找到工作表: {sheet_name}")
            return None
            
        except HttpError as error:
            logger.error(f"获取工作表时出错: {error}")
            return None
    
    def get_range_value(self, sheet_name: str, range_address: str) -> str:
        """
        获取指定范围的值
        
        Args:
            sheet_name: 工作表名称
            range_address: 范围地址，如 "B6"
            
        Returns:
            单元格值
        """
        try:
            range_name = f"{sheet_name}!{range_address}"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if values and len(values) > 0 and len(values[0]) > 0:
                return str(values[0][0])
            else:
                return "0"
                
        except HttpError as error:
            logger.error(f"获取范围值时出错: {error}")
            return "0"
    
    def set_range_value(self, sheet_name: str, range_address: str, value: Any):
        """
        设置指定范围的值
        
        Args:
            sheet_name: 工作表名称
            range_address: 范围地址，如 "B6"
            value: 要设置的值
        """
        try:
            range_name = f"{sheet_name}!{range_address}"
            body = {
                'values': [[value]]
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logger.debug(f"设置 {range_name} = {value} 成功")
            
        except HttpError as error:
            logger.error(f"设置范围值时出错: {error}")
    
    def batch_update_values(self, sheet_name: str, updates: Dict[str, Any]):
        """
        批量更新多个范围的值
        
        Args:
            sheet_name: 工作表名称
            updates: 更新字典，键为范围地址，值为要设置的值
        """
        try:
            data = []
            for range_address, value in updates.items():
                range_name = f"{sheet_name}!{range_address}"
                data.append({
                    'range': range_name,
                    'values': [[value]]
                })
            
            body = {
                'valueInputOption': 'RAW',
                'data': data
            }
            
            result = self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            ).execute()
            
            logger.info(f"批量更新 {len(updates)} 个范围成功")
            
        except HttpError as error:
            logger.error(f"批量更新值时出错: {error}")
    
    def flush(self):
        """强制刷新数据（在Google Sheets API中通常不需要）"""
        # Google Sheets API 是实时的，不需要手动刷新
        pass
    
    def get_all_sheets(self) -> List[Dict]:
        """
        获取所有工作表信息
        
        Returns:
            工作表信息列表
        """
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            return spreadsheet.get('sheets', [])
            
        except HttpError as error:
            logger.error(f"获取所有工作表时出错: {error}")
            return []
    
    def create_sheet(self, sheet_name: str) -> bool:
        """
        创建新工作表
        
        Args:
            sheet_name: 工作表名称
            
        Returns:
            是否创建成功
        """
        try:
            body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
            }
            
            result = self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            ).execute()
            
            logger.info(f"创建工作表 {sheet_name} 成功")
            return True
            
        except HttpError as error:
            logger.error(f"创建工作表时出错: {error}")
            return False
    
    def delete_sheet(self, sheet_id: int) -> bool:
        """
        删除工作表
        
        Args:
            sheet_id: 工作表ID
            
        Returns:
            是否删除成功
        """
        try:
            body = {
                'requests': [{
                    'deleteSheet': {
                        'sheetId': sheet_id
                    }
                }]
            }
            
            result = self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            ).execute()
            
            logger.info(f"删除工作表 ID {sheet_id} 成功")
            return True
            
        except HttpError as error:
            logger.error(f"删除工作表时出错: {error}")
            return False


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 初始化客户端
    # 需要提供有效的spreadsheet_id和credentials_path
    client = GoogleSheetsClient(
        spreadsheet_id="your_spreadsheet_id_here",
        credentials_path="credentials.json"
    )
    
    # 测试功能
    try:
        # 获取所有工作表
        sheets = client.get_all_sheets()
        print(f"找到 {len(sheets)} 个工作表")
        
        # 测试读写操作
        if sheets:
            sheet_name = sheets[0]['properties']['title']
            print(f"测试工作表: {sheet_name}")
            
            # 读取值
            value = client.get_range_value(sheet_name, "A1")
            print(f"A1 的值: {value}")
            
            # 设置值
            client.set_range_value(sheet_name, "A1", "Hello Python!")
            print("设置 A1 = 'Hello Python!'")
            
            # 读取新值
            new_value = client.get_range_value(sheet_name, "A1")
            print(f"A1 的新值: {new_value}")
            
    except Exception as e:
        print(f"测试时出错: {e}")
