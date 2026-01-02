# -*- coding: utf-8 -*-
"""
中華郵政郵局掛號包裹查詢程式
使用 Playwright 無頭瀏覽器抓取 AngularJS SPA 網頁，ddddocr 辨識驗證碼
"""

import re
import time
import sys
import os
from typing import List, Dict, Optional

from base_query import BasePackageQuery, register_carrier


def get_chromium_path() -> Optional[str]:
    """取得 Chromium 瀏覽器執行檔路徑（支援 PyInstaller 打包環境）"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        chromium_dir = os.path.join(base_path, 'ms-playwright', 'chromium-1200')
        if os.path.exists(chromium_dir):
            for chrome_folder in ['chrome-win64', 'chrome-win']:
                chrome_exe = os.path.join(chromium_dir, chrome_folder, 'chrome.exe')
                if os.path.exists(chrome_exe):
                    return chrome_exe
    return None


# 版本號
VERSION = "1.0.0"


@register_carrier
class PostPackageQuery(BasePackageQuery):
    """中華郵政郵局掛號查詢類別"""
    
    # 快遞屬性
    NAME = "郵局掛號"
    ICON = "📮"
    MAX_BATCH = 5  # 郵局支援最多 5 個同時查詢
    SUPPORTS_PARALLEL = False  # Playwright 不支援並行
    
    # 查詢相關 URL
    QUERY_URL = "https://postserv.post.gov.tw/pstmail/main_mail.html"
    
    def __init__(self, max_retries: int = 5):
        """
        初始化查詢器
        
        Args:
            max_retries: 驗證碼辨識失敗時的最大重試次數
        """
        super().__init__(max_retries)
        self._browser = None
        self._playwright = None
        self._ocr = None
    
    def _get_ocr(self):
        """延遲載入 OCR（避免啟動時載入過慢）"""
        if self._ocr is None:
            import ddddocr
            self._ocr = ddddocr.DdddOcr(show_ad=False)
        return self._ocr
    
    def _init_browser(self):
        """延遲初始化 Playwright 瀏覽器（headless 模式）"""
        if self._browser is None:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            
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
    
    def _query_batch(self, tracking_numbers: List[str]) -> Optional[List[Dict]]:
        """
        查詢一批包裹（最多 5 個）
        
        使用 Playwright 操作郵局查詢頁面
        
        Args:
            tracking_numbers: 追蹤碼清單（最多 5 個）
            
        Returns:
            查詢結果或 None
        """
        results = []
        
        try:
            self._init_browser()
            page = self._browser.new_page()
            page.set_default_timeout(30000)
            
            for attempt in range(self.max_retries):
                try:
                    # 導航到查詢頁面
                    page.goto(self.QUERY_URL, wait_until='networkidle')
                    
                    # 等待頁面載入
                    page.wait_for_selector('input[name="MAILNO1"]', timeout=10000)
                    
                    # 填入追蹤碼（最多 5 個）
                    for i, tracking_no in enumerate(tracking_numbers[:5], 1):
                        field_name = f'MAILNO{i}'
                        input_field = page.query_selector(f'input[name="{field_name}"]')
                        if input_field:
                            input_field.fill(tracking_no.strip())
                    
                    # 取得並辨識驗證碼
                    captcha_img = page.query_selector('img[alt*="驗證碼"], img[src*="captcha"], .captcha-img img')
                    if not captcha_img:
                        # 嘗試其他選擇器
                        captcha_img = page.query_selector('img')
                        all_imgs = page.query_selector_all('img')
                        for img in all_imgs:
                            src = img.get_attribute('src') or ''
                            if 'captcha' in src.lower() or 'validate' in src.lower() or 'checkno' in src.lower():
                                captcha_img = img
                                break
                    
                    if captcha_img:
                        # 截圖驗證碼
                        captcha_bytes = captcha_img.screenshot()
                        
                        # 辨識驗證碼
                        ocr = self._get_ocr()
                        captcha_text = ocr.classification(captcha_bytes)
                        captcha_text = re.sub(r'[^a-zA-Z0-9]', '', captcha_text)
                        
                        print(f"  辨識驗證碼: {captcha_text}")
                        
                        # 填入驗證碼
                        captcha_input = page.query_selector('input[name="captcha"], input[id="captcha"], input[type="text"][maxlength="4"]')
                        if captcha_input:
                            captcha_input.fill(captcha_text)
                    
                    # 點擊查詢按鈕
                    submit_btn = page.query_selector('a.css_btn_class, button[type="submit"], input[type="submit"]')
                    if submit_btn:
                        submit_btn.click()
                    else:
                        # 嘗試按 Enter
                        page.keyboard.press('Enter')
                    
                    # 等待結果載入
                    time.sleep(2)
                    page.wait_for_load_state('networkidle', timeout=10000)
                    
                    # 解析結果
                    for i, tracking_no in enumerate(tracking_numbers[:5]):
                        tracking_no = tracking_no.strip()
                        if not tracking_no:
                            continue
                        
                        status_text = ""
                        
                        # 嘗試從頁面取得結果
                        try:
                            # 先檢查是否有錯誤訊息
                            error_elements = page.query_selector_all('.error, .errorMsg, [class*="error"]')
                            for err in error_elements:
                                err_text = err.inner_text()
                                if '驗證碼' in err_text:
                                    print(f"  驗證碼錯誤，重試...")
                                    raise Exception("驗證碼錯誤")
                            
                            # 尋找結果表格或區塊
                            result_tables = page.query_selector_all('table')
                            for table in result_tables:
                                table_text = table.inner_text()
                                if tracking_no in table_text or '郵件狀態' in table_text or '投遞' in table_text:
                                    # 取得表格中的狀態
                                    rows = table.query_selector_all('tr')
                                    for row in rows:
                                        row_text = row.inner_text().strip()
                                        if any(kw in row_text for kw in ['送達', '投遞', '招領', '退回', '處理', '運送']):
                                            status_text = row_text[:80]
                                            break
                                    if status_text:
                                        break
                            
                            if not status_text:
                                # 取得頁面文字尋找狀態
                                body_text = page.inner_text('body')
                                # 尋找包含日期的狀態文字
                                date_pattern = r'\d{4}[/-]\d{1,2}[/-]\d{1,2}[^\\n]*'
                                matches = re.findall(date_pattern, body_text)
                                if matches:
                                    status_text = matches[0][:80]
                        
                        except Exception as e:
                            if '驗證碼' in str(e):
                                raise
                            status_text = f"⚠️ 解析失敗: {str(e)[:30]}"
                        
                        if not status_text:
                            status_text = "⚠️ 查無資料或無法解析"
                        
                        results.append({
                            '包裹編號': tracking_no,
                            '訂單編號': '-',
                            '狀態': status_text
                        })
                    
                    # 成功取得結果，跳出重試迴圈
                    break
                    
                except Exception as e:
                    error_msg = str(e)
                    if '驗證碼' not in error_msg and attempt >= self.max_retries - 1:
                        # 最後一次嘗試失敗，返回錯誤結果
                        for tracking_no in tracking_numbers:
                            tracking_no = tracking_no.strip()
                            if tracking_no:
                                results.append({
                                    '包裹編號': tracking_no,
                                    '訂單編號': '-',
                                    '狀態': f'❌ 查詢失敗: {error_msg[:30]}'
                                })
                    elif '驗證碼' in error_msg:
                        print(f"  重試 {attempt + 1}/{self.max_retries}...")
                        time.sleep(1)
                        continue
                    else:
                        print(f"  錯誤: {error_msg}，重試...")
                        time.sleep(1)
                        continue
            
            page.close()
            
        except Exception as e:
            print(f"瀏覽器錯誤: {e}")
            for tracking_no in tracking_numbers:
                tracking_no = tracking_no.strip()
                if tracking_no:
                    results.append({
                        '包裹編號': tracking_no,
                        '訂單編號': '-',
                        '狀態': f'❌ 瀏覽器錯誤: {str(e)[:30]}'
                    })
        finally:
            self._close_browser()
        
        return results if results else None
    
    def __del__(self):
        """清理資源"""
        self._close_browser()


if __name__ == "__main__":
    # 測試用
    query = PostPackageQuery()
    results = query.query(["12345678901234"])  # 測試用追蹤碼
    for r in results:
        print(r)
