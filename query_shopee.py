# -*- coding: utf-8 -*-
"""
蝦皮店到店包裹查詢程式
使用 Playwright 無頭瀏覽器抓取 JavaScript 渲染的 SPA 網頁
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time
import sys
import os

from base_query import BasePackageQuery, register_carrier


def get_chromium_path() -> Optional[str]:
    """取得 Chromium 瀏覽器執行檔路徑（支援 PyInstaller 打包環境）"""
    # PyInstaller 打包後的臨時目錄
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        # 打包時放在 ms-playwright/chromium-1200 目錄
        chromium_dir = os.path.join(base_path, 'ms-playwright', 'chromium-1200')
        if os.path.exists(chromium_dir):
            # 嘗試不同的目錄名稱（chrome-win64 或 chrome-win）
            for chrome_folder in ['chrome-win64', 'chrome-win']:
                chrome_exe = os.path.join(chromium_dir, chrome_folder, 'chrome.exe')
                if os.path.exists(chrome_exe):
                    return chrome_exe
    return None

# 版本號
VERSION = "3.0.0"


@register_carrier
class ShopeePackageQuery(BasePackageQuery):
    """蝦皮店到店包裹查詢類別"""
    
    # 快遞屬性
    NAME = "蝦皮店到店"
    ICON = ""
    MAX_BATCH = 5  # 可批量查詢
    SUPPORTS_PARALLEL = False  # Playwright 不支援並行
    
    # 蝦皮店到店追蹤網址
    DETAIL_URL = "https://spx.tw/detail/"
    
    # 不使用 WebView，改用 Playwright headless
    USE_WEBVIEW = False
    
    def __init__(self, max_retries: int = 3):
        """
        初始化查詢器
        
        Args:
            max_retries: 最大重試次數
        """
        super().__init__(max_retries)
        self._browser = None
        self._playwright = None
    
    def _init_browser(self):
        """延遲初始化 Playwright 瀏覽器（headless 模式）"""
        if self._browser is None:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            
            # 取得內嵌的 Chromium 路徑（如果是打包環境）
            chromium_path = get_chromium_path()
            
            launch_options = {
                'headless': True,
                'args': ['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage']
            }
            
            if chromium_path:
                launch_options['executable_path'] = chromium_path
            
            self._browser = self._playwright.chromium.launch(**launch_options)
    
    def _close_browser(self):
        """關閉瀏覽器"""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
    
    def _query_single(self, tracking_no: str) -> Dict:
        """
        查詢單一包裹
        
        Args:
            tracking_no: 追蹤碼
            
        Returns:
            查詢結果字典
        """
        tracking_no = tracking_no.strip()
        if not tracking_no:
            return None
        
        url = f"{self.DETAIL_URL}{tracking_no}"
        
        try:
            self._init_browser()
            
            # 建立新頁面
            page = self._browser.new_page()
            page.set_default_timeout(15000)  # 15 秒超時
            
            try:
                # 導航到追蹤頁面
                page.goto(url, wait_until='networkidle')
                
                # 等待物流狀態元素出現
                # 嘗試多種選擇器
                selectors = [
                    '.detail-list-item',
                    '.order-status-title',
                    '[class*="tracking"]',
                    '[class*="status"]',
                ]
                
                status_text = ""
                
                for selector in selectors:
                    try:
                        page.wait_for_selector(selector, timeout=5000)
                        
                        # 取得最新狀態
                        if selector == '.detail-list-item':
                            # 取得第一個（最新的）物流項目
                            item = page.query_selector('.detail-list-item')
                            if item:
                                date_el = item.query_selector('.item-date')
                                text_el = item.query_selector('.item-text-box')
                                
                                date_text = date_el.inner_text() if date_el else ""
                                info_text = text_el.inner_text() if text_el else ""
                                
                                status_text = f"{date_text} {info_text}".strip()
                        else:
                            element = page.query_selector(selector)
                            if element:
                                status_text = element.inner_text().strip()
                        
                        if status_text:
                            break
                            
                    except Exception:
                        continue
                
                # 如果還是沒有找到，嘗試取得頁面全部文字並解析
                if not status_text:
                    try:
                        body_text = page.inner_text('body')
                        # 尋找包含日期格式的文字
                        import re
                        date_pattern = r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}[^\n]*'
                        match = re.search(date_pattern, body_text, re.IGNORECASE)
                        if match:
                            status_text = match.group(0).strip()
                    except Exception:
                        pass
                
                if not status_text:
                    status_text = "⚠️ 無法取得物流狀態"
                
                # 截斷過長的狀態文字
                if len(status_text) > 80:
                    status_text = status_text[:77] + "..."
                
                return {
                    '包裹編號': tracking_no,
                    '訂單編號': '-',
                    '狀態': status_text,
                }
                
            finally:
                page.close()
                
        except Exception as e:
            return {
                '包裹編號': tracking_no,
                '訂單編號': '-',
                '狀態': f'❌ 查詢失敗: {str(e)[:40]}',
            }
    
    def _query_batch(self, tracking_numbers: List[str]) -> Optional[List[Dict]]:
        """
        查詢一批包裹
        
        使用 Playwright headless 瀏覽器抓取 JavaScript 渲染的頁面
        
        Args:
            tracking_numbers: 追蹤碼清單
            
        Returns:
            查詢結果或 None
        """
        results = []
        
        try:
            for tracking_no in tracking_numbers:
                result = self._query_single(tracking_no)
                if result:
                    results.append(result)
                time.sleep(0.5)  # 避免太頻繁請求
        finally:
            self._close_browser()
        
        return results if results else None
    
    def __del__(self):
        """清理資源"""
        self._close_browser()


if __name__ == "__main__":
    # 測試用
    query = ShopeePackageQuery()
    results = query.query(["TW254618236452X"])
    for r in results:
        print(r)
