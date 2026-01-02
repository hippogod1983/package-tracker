# -*- coding: utf-8 -*-
"""
7-ELEVEN 交貨便包裹查詢程式
使用 requests 發送查詢請求，ddddocr 辨識驗證碼
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from typing import List, Dict, Optional

from base_query import BasePackageQuery, register_carrier

# 版本號
VERSION = "1.0.0"


@register_carrier
class SevenElevenPackageQuery(BasePackageQuery):
    """7-ELEVEN 交貨便包裹查詢類別"""
    
    # 快遞屬性
    NAME = "7-11 交貨便"
    ICON = "🏪"
    MAX_BATCH = 1  # 每次只能查詢一個
    
    # 查詢相關 URL
    BASE_URL = "https://eservice.7-11.com.tw/e-tracking"
    QUERY_URL = f"{BASE_URL}/search.aspx"
    CAPTCHA_URL = f"{BASE_URL}/ValidateImage.aspx"
    
    def __init__(self, max_retries: int = 5):
        """
        初始化查詢器
        
        Args:
            max_retries: 驗證碼辨識失敗時的最大重試次數
        """
        super().__init__(max_retries)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Referer': self.QUERY_URL
        })
        self._ocr = None
    
    def _get_ocr(self):
        """延遲載入 OCR（避免啟動時載入過慢）"""
        if self._ocr is None:
            import ddddocr
            self._ocr = ddddocr.DdddOcr(show_ad=False)
        return self._ocr
    
    def _get_asp_fields(self) -> Dict[str, str]:
        """
        取得 ASP.NET 必要的隱藏欄位
        
        Returns:
            包含 __VIEWSTATE 等欄位的字典
        """
        response = self.session.get(self.QUERY_URL)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        fields = {}
        for field_name in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
            field = soup.find('input', {'name': field_name})
            if field:
                fields[field_name] = field.get('value', '')
        
        return fields
    
    def _get_captcha(self) -> bytes:
        """
        下載驗證碼圖片
        
        Returns:
            驗證碼圖片的 bytes
        """
        timestamp = int(time.time() * 1000)
        captcha_url = f"{self.CAPTCHA_URL}?ts={timestamp}"
        response = self.session.get(captcha_url)
        response.raise_for_status()
        return response.content
    
    def _recognize_captcha(self, captcha_bytes: bytes) -> str:
        """
        使用 ddddocr 辨識驗證碼
        
        Args:
            captcha_bytes: 驗證碼圖片的 bytes
            
        Returns:
            辨識出的驗證碼文字
        """
        ocr = self._get_ocr()
        result = ocr.classification(captcha_bytes)
        # 只保留英數字
        result = re.sub(r'[^a-zA-Z0-9]', '', result)
        return result[:4]  # 7-11 驗證碼為 4 碼
    
    def _query_tracking(self, tracking_no: str, captcha: str, asp_fields: Dict[str, str]) -> str:
        """
        發送查詢請求
        
        Args:
            tracking_no: 追蹤碼
            captcha: 驗證碼
            asp_fields: ASP.NET 隱藏欄位
            
        Returns:
            回應的 HTML 內容
        """
        data = {
            '__EVENTTARGET': 'submit',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': asp_fields.get('__VIEWSTATE', ''),
            '__VIEWSTATEGENERATOR': asp_fields.get('__VIEWSTATEGENERATOR', '3E7313DB'),
            'txtProductNum': tracking_no,
            'tbChkCode': captcha,
            'txtPage': '1'
        }
        
        if '__EVENTVALIDATION' in asp_fields:
            data['__EVENTVALIDATION'] = asp_fields['__EVENTVALIDATION']
        
        response = self.session.post(self.QUERY_URL, data=data)
        response.raise_for_status()
        return response.text
    
    def _parse_results(self, html: str, tracking_no: str) -> Optional[Dict]:
        """
        解析查詢結果 HTML
        
        Args:
            html: 回應的 HTML 內容
            tracking_no: 原始追蹤碼
            
        Returns:
            查詢結果字典
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 檢查是否有錯誤訊息（驗證碼錯誤等）
        error_msg = soup.find('span', {'id': 'lbErrMessage'})
        if error_msg and error_msg.text.strip():
            error_text = error_msg.text.strip()
            if '驗證碼' in error_text:
                return None  # 驗證碼錯誤，需要重試
            return {
                '包裹編號': tracking_no,
                '訂單編號': '-',
                '狀態': f'⚠️ {error_text}'
            }
        
        # 嘗試找到結果表格
        result_table = soup.find('table', {'class': 'listTb'})
        if not result_table:
            # 嘗試其他可能的結果區塊
            result_div = soup.find('div', {'class': 'result'})
            if result_div:
                status_text = result_div.get_text(strip=True)
                return {
                    '包裹編號': tracking_no,
                    '訂單編號': '-',
                    '狀態': status_text[:80] if len(status_text) > 80 else status_text
                }
            return {
                '包裹編號': tracking_no,
                '訂單編號': '-',
                '狀態': '⚠️ 查無資料'
            }
        
        # 解析表格中的資料
        rows = result_table.find_all('tr')
        status_text = ""
        
        for row in rows[1:]:  # 跳過表頭
            cells = row.find_all('td')
            if len(cells) >= 2:
                # 取得狀態欄位的文字
                cell_text = cells[-1].get_text(strip=True)
                if cell_text:
                    status_text = cell_text
                    break
        
        if not status_text:
            status_text = '已查詢'
        
        return {
            '包裹編號': tracking_no,
            '訂單編號': '-',
            '狀態': status_text
        }
    
    def _query_batch(self, tracking_numbers: List[str]) -> Optional[List[Dict]]:
        """
        查詢一批包裹（7-11 一次只能查一個）
        
        Args:
            tracking_numbers: 追蹤碼清單
            
        Returns:
            查詢結果或 None
        """
        results = []
        
        for tracking_no in tracking_numbers:
            tracking_no = tracking_no.strip()
            if not tracking_no:
                continue
            
            result = None
            
            for attempt in range(self.max_retries):
                try:
                    # 取得 ASP.NET 欄位
                    asp_fields = self._get_asp_fields()
                    
                    # 取得並辨識驗證碼
                    captcha_bytes = self._get_captcha()
                    captcha = self._recognize_captcha(captcha_bytes)
                    
                    if len(captcha) != 4:
                        print(f"  驗證碼辨識長度不正確: {captcha}，重試中...")
                        continue
                    
                    print(f"  辨識驗證碼: {captcha}")
                    
                    # 發送查詢
                    html = self._query_tracking(tracking_no, captcha, asp_fields)
                    
                    # 解析結果
                    result = self._parse_results(html, tracking_no)
                    
                    if result:
                        break
                    
                    print(f"  驗證碼可能錯誤，重試 {attempt + 1}/{self.max_retries}...")
                    time.sleep(0.5)
                    
                except requests.RequestException as e:
                    print(f"  網路錯誤: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(1)
                    continue
                except Exception as e:
                    print(f"  查詢錯誤: {e}")
                    result = {
                        '包裹編號': tracking_no,
                        '訂單編號': '-',
                        '狀態': f'❌ 查詢失敗: {str(e)[:30]}'
                    }
                    break
            
            if result is None:
                result = {
                    '包裹編號': tracking_no,
                    '訂單編號': '-',
                    '狀態': '❌ 驗證碼辨識失敗，請稍後再試'
                }
            
            results.append(result)
            
            # 避免太頻繁請求
            if len(tracking_numbers) > 1:
                time.sleep(1)
        
        return results if results else None


if __name__ == "__main__":
    # 測試用
    query = SevenElevenPackageQuery()
    results = query.query(["12345678"])  # 測試用追蹤碼
    for r in results:
        print(r)
