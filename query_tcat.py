# -*- coding: utf-8 -*-
"""
黑貓宅急便包裹查詢程式
使用 requests 發送查詢請求並解析 HTML 結果
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional

from base_query import BasePackageQuery, register_carrier

# 版本號
VERSION = "1.0.0"


@register_carrier
class TCatPackageQuery(BasePackageQuery):
    """黑貓宅急便包裹查詢類別"""
    
    # 快遞屬性
    NAME = "宅急便"
    ICON = ""
    MAX_BATCH = 10
    
    BASE_URL = "https://www.t-cat.com.tw/Inquire/Trace.aspx"
    DETAIL_URL = "https://www.t-cat.com.tw/Inquire/TraceDetail.aspx"
    
    def __init__(self, max_retries: int = 3):
        """
        初始化查詢器
        
        Args:
            max_retries: 最大重試次數
        """
        super().__init__(max_retries)
        self.session = requests.Session()
        
        # 設定 User-Agent 模擬瀏覽器
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        })
    
    def _get_asp_fields(self) -> Dict[str, str]:
        """
        取得 ASP.NET 必要的隱藏欄位
        
        Returns:
            包含 __VIEWSTATE 等欄位的字典
        """
        response = self.session.get(self.BASE_URL)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        fields = {}
        for field_name in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
            field = soup.find('input', {'name': field_name})
            if field:
                fields[field_name] = field.get('value', '')
        
        return fields
    
    def _query_tracking(self, tracking_numbers: List[str], asp_fields: Dict[str, str]) -> str:
        """
        發送查詢請求
        
        Args:
            tracking_numbers: 追蹤碼清單 (最多 10 個)
            asp_fields: ASP.NET 隱藏欄位
            
        Returns:
            回應的 HTML 內容
        """
        data = asp_fields.copy()
        
        # 填入追蹤碼 (最多 10 個輸入欄位)
        for i, tracking_no in enumerate(tracking_numbers[:10], 1):
            data[f'ctl00$ContentPlaceHolder1$txtQuery{i}'] = tracking_no
        
        # 其餘欄位填空
        for i in range(len(tracking_numbers) + 1, 11):
            data[f'ctl00$ContentPlaceHolder1$txtQuery{i}'] = ''
        
        # 送出按鈕
        data['ctl00$ContentPlaceHolder1$btnSend'] = '確認送出'
        
        response = self.session.post(self.BASE_URL, data=data)
        response.raise_for_status()
        
        return response.text
    
    def _parse_results(self, html: str, tracking_numbers: List[str]) -> List[Dict]:
        """
        解析查詢結果 HTML
        
        Args:
            html: 回應的 HTML 內容
            tracking_numbers: 原始查詢的追蹤碼清單
            
        Returns:
            查詢結果清單
        """
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # 儲存 HTML 供調試

        
        # 尋找結果容器 (orderlist-box)
        result_boxes = soup.find_all('div', class_='orderlist-box')
        
        if result_boxes:
            for box in result_boxes:
                result_data = {
                    '包裹編號': '',
                    '訂單編號': '-',
                    '狀態': '',
                }
                
                # 找到 order-list
                order_list = box.find('ul', class_='order-list')
                if order_list:
                    items = order_list.find_all('li')
                    
                    for item in items:
                        col1 = item.find('div', class_='col-1')
                        col2 = item.find('div', class_='col-2')
                        
                        if col1 and col2:
                            label = col1.get_text(strip=True)
                            value = col2.get_text(strip=True)
                            
                            if '包裹查詢號碼' in label:
                                result_data['包裹編號'] = value
                            elif '目前狀態' in label:
                                result_data['狀態'] = value
                            elif '資料登入時間' in label:
                                result_data['狀態'] += f" ({value})"
                
                if result_data['包裹編號']:
                    results.append(result_data)
        
        # 如果沒有找到 orderlist-box，檢查是否有錯誤訊息
        if not results:
            # 檢查是否有「查無資料」或錯誤訊息
            error_text = None
            
            # 尋找錯誤訊息
            alert_div = soup.find('div', class_='alert')
            if alert_div:
                error_text = alert_div.get_text(strip=True)
            
            # 尋找「很抱歉」訊息
            sorry_text = soup.find(string=re.compile(r'很抱歉'))
            if sorry_text:
                error_text = '查無訂單資料'
            
            # 如果找到任何結果文字但無法解析
            result_header = soup.find(string=re.compile(r'查詢結果如下'))
            if result_header and not error_text:
                # 可能有其他格式，嘗試取得頁面內容
                content = soup.find('div', {'id': 'ContentPlaceHolder1_pnlResult'})
                if content:
                    # 嘗試從頁面文字中提取狀態
                    text = content.get_text()
                    for tracking_no in tracking_numbers:
                        if tracking_no in text:
                            # 找到包裹編號，嘗試提取狀態
                            status_match = re.search(r'目前狀態[：:]\s*(.+?)(?:\n|$)', text)
                            status = status_match.group(1).strip() if status_match else '狀態解析中'
                            results.append({
                                '包裹編號': tracking_no,
                                '訂單編號': '-',
                                '狀態': status,
                            })
            
            # 如果仍然沒有結果，返回錯誤
            if not results:
                for tracking_no in tracking_numbers:
                    results.append({
                        '包裹編號': tracking_no,
                        '訂單編號': '-',
                        '狀態': error_text or '查無訂單資料',
                    })
        
        return results
    
    def query(self, tracking_numbers: List[str]) -> List[Dict]:
        """
        查詢包裹狀態
        
        Args:
            tracking_numbers: 要查詢的追蹤碼清單
            
        Returns:
            查詢結果清單
        """
        all_results = []
        
        # 每次最多查詢 10 個，分批處理
        for i in range(0, len(tracking_numbers), 10):
            batch = tracking_numbers[i:i + 10]
            print(f"\n正在查詢第 {i + 1} 到 {min(i + 10, len(tracking_numbers))} 個包裹...")
            
            result = self._query_batch(batch)
            if result:
                all_results.extend(result)
        
        return all_results
    
    def _query_batch(self, tracking_numbers: List[str]) -> Optional[List[Dict]]:
        """
        查詢一批包裹（最多 10 個）
        
        Args:
            tracking_numbers: 追蹤碼清單（最多 10 個）
            
        Returns:
            查詢結果或 None
        """
        for attempt in range(self.max_retries):
            try:
                print(f"  嘗試第 {attempt + 1} 次...")
                
                # 取得 ASP.NET 欄位
                asp_fields = self._get_asp_fields()
                
                # 發送查詢
                html = self._query_tracking(tracking_numbers, asp_fields)
                
                # 解析結果
                results = self._parse_results(html, tracking_numbers)
                
                if results:
                    return results
                    
            except Exception as e:
                print(f"  發生錯誤: {e}")
                if attempt < self.max_retries - 1:
                    import time
                    time.sleep(1)
                continue
        
        print(f"  已達最大重試次數 ({self.max_retries})，放棄此批查詢")
        return None


if __name__ == "__main__":
    # 測試用
    query = TCatPackageQuery()
    results = query.query(["123456789012"])
    for r in results:
        print(r)
