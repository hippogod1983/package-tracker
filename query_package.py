# /// script
# requires-python = "==3.11.*"
# dependencies = [
#     "requests>=2.28.0",
#     "beautifulsoup4>=4.11.0",
#     "ddddocr>=1.4.0",
#     "pyyaml>=6.0",
# ]
# ///
"""
全家便利商店包裹查詢程式
使用 ddddocr 處理驗證碼，支援複數包裹查詢
"""

import requests
from bs4 import BeautifulSoup
# ddddocr 延遲載入：避免 ONNX Runtime 與 X11/Tkinter 衝突
# 改在 FamilyMartPackageQuery.__init__ 中按需載入
import yaml
import time
import re
import argparse
import shutil
from typing import List, Dict, Optional
from pathlib import Path

from base_query import BasePackageQuery, register_carrier

# 版本號
VERSION = "1.0.0"


@register_carrier
class FamilyMartPackageQuery(BasePackageQuery):
    """全家便利商店包裹查詢類別"""
    
    # 快遞屬性
    NAME = "全家便利商店"
    ICON = ""
    MAX_BATCH = 5
    
    # 查詢頁面 URL（iframe 內的實際查詢頁面）
    BASE_URL = "https://ecfme.fme.com.tw/FMEDCFPWebV2_II"
    QUERY_URL = f"{BASE_URL}/index.aspx"
    CAPTCHA_URL = f"{BASE_URL}/CodeHandler.ashx"
    
    def __init__(self, max_retries: int = 5):
        """
        初始化查詢器
        
        Args:
            max_retries: 驗證碼辨識失敗時的最大重試次數
        """
        super().__init__(max_retries)
        self.session = requests.Session()
        
        # 延遲載入 ddddocr（避免 ONNX Runtime 與 X11 衝突）
        import ddddocr
        self.ocr = ddddocr.DdddOcr(show_ad=False)
        
        # 設定 User-Agent 模擬瀏覽器
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://fmec.famiport.com.tw/FP_Entrance/QueryBox'
        })
    
    def _get_verification_code(self) -> tuple[str, bytes]:
        """
        呼叫 API 取得驗證碼參數和圖片
        
        Returns:
            tuple: (vcode, 驗證碼圖片 bytes)
        """
        # 先載入主頁面建立 session
        self.session.get(self.QUERY_URL, params={'orderno': ''})
        
        # 呼叫 GetVerificationCode API 取得驗證碼參數
        api_url = f"{self.QUERY_URL}/GetVerificationCode"
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        response = self.session.post(api_url, json={}, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        if 'd' not in result or not result['d']:
            raise Exception("無法取得驗證碼參數")
        
        import json
        code_data = json.loads(result['d'])
        vcode = code_data.get('Code', '')
        
        if not vcode:
            raise Exception("驗證碼參數為空")
        
        # 下載驗證碼圖片
        import urllib.parse
        captcha_url = f"{self.CAPTCHA_URL}?Code={urllib.parse.quote(vcode)}"
        captcha_response = self.session.get(captcha_url)
        captcha_bytes = captcha_response.content
        
        return vcode, captcha_bytes
    
    def _verify_captcha(self, captcha_code: str, vcode: str) -> bool:
        """
        驗證驗證碼是否正確
        
        Args:
            captcha_code: 辨識出的驗證碼
            vcode: 驗證碼 session 參數
            
        Returns:
            驗證是否成功
        """
        api_url = f"{self.QUERY_URL}/ChkVerificationCode"
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        data = {
            'P_CODE': captcha_code,
            'P_VCODE': vcode
        }
        
        response = self.session.post(api_url, json=data, headers=headers)
        
        if response.status_code != 200:
            return False
        
        try:
            result = response.json()
            if 'd' not in result or not result['d']:
                return False
            
            import json
            verify_result = json.loads(result['d'])
            return verify_result.get('success') == '1'
        except:
            return False
    
    def _query_packages(self, tracking_numbers: List[str]) -> str:
        """
        查詢包裹狀態
        
        Args:
            tracking_numbers: 包裹編號清單
            
        Returns:
            查詢結果 (dict)
        """
        # 先 POST 到 list.aspx 建立 session
        list_url = f"{self.BASE_URL}/list.aspx"
        data = {
            'ORDER_NO': ','.join(tracking_numbers)
        }
        self.session.post(list_url, data=data)
        
        # 呼叫 InquiryOrders API 取得實際結果
        api_url = f"{self.BASE_URL}/list.aspx/InquiryOrders"
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        response = self.session.post(
            api_url,
            json={'ListEC_ORDER_NO': ','.join(tracking_numbers)},
            headers=headers
        )
        response.raise_for_status()
        
        result = response.json()
        if 'd' not in result or not result['d']:
            return None
        
        import json
        return json.loads(result['d'])
    
    def _recognize_captcha(self, captcha_bytes: bytes) -> str:
        """
        使用 ddddocr 辨識驗證碼
        
        Args:
            captcha_bytes: 驗證碼圖片的 bytes
            
        Returns:
            辨識出的驗證碼文字
        """
        result = self.ocr.classification(captcha_bytes)
        # 移除空格和特殊字元，只保留英數字
        result = re.sub(r'[^a-zA-Z0-9]', '', result)
        return result
    
    def query(self, tracking_numbers: List[str]) -> List[Dict]:
        """
        查詢包裹狀態
        
        Args:
            tracking_numbers: 要查詢的包裹編號清單
            
        Returns:
            查詢結果清單
        """
        all_results = []
        
        # 每次最多查詢 5 個，分批處理
        for i in range(0, len(tracking_numbers), 5):
            batch = tracking_numbers[i:i + 5]
            print(f"\n正在查詢第 {i + 1} 到 {min(i + 5, len(tracking_numbers))} 個包裹...")
            
            result = self._query_batch(batch)
            if result:
                all_results.extend(result)
            
            # 避免太頻繁請求
            if i + 5 < len(tracking_numbers):
                time.sleep(1)
        
        return all_results
    
    def _query_batch(self, tracking_numbers: List[str]) -> Optional[List[Dict]]:
        """
        查詢一批包裹（最多 5 個）
        
        Args:
            tracking_numbers: 包裹編號清單（最多 5 個）
            
        Returns:
            查詢結果或 None
        """
        for attempt in range(self.max_retries):
            try:
                print(f"  嘗試第 {attempt + 1} 次...")
                
                # 取得驗證碼
                vcode, captcha_bytes = self._get_verification_code()
                
                # 辨識驗證碼
                captcha_code = self._recognize_captcha(captcha_bytes)
                print(f"  驗證碼辨識結果: {captcha_code}")
                
                if len(captcha_code) < 4:
                    print(f"  驗證碼長度不足，重新嘗試...")
                    continue
                
                # 驗證驗證碼
                if not self._verify_captcha(captcha_code, vcode):
                    print(f"  驗證碼錯誤，重新嘗試...")
                    continue
                
                print(f"  驗證碼驗證成功！")
                
                # 查詢包裹 (現在返回 JSON)
                result_data = self._query_packages(tracking_numbers)
                

                
                # 處理結果
                if result_data and result_data.get('ErrorCode') == '000':
                    package_list = result_data.get('List', [])
                    results = []
                    
                    for pkg in package_list:
                        result = {
                            '包裹編號': pkg.get('EC_ORDER_NO', ''),
                            '訂單編號': pkg.get('ORDER_NO', ''),
                            '狀態': pkg.get('ORDERMESSAGE', ''),
                            '數量': pkg.get('CNT', 0)
                        }
                        
                        # CNT = 0 表示查無資料
                        if pkg.get('CNT', 0) == 0:
                            result['狀態'] = '查無訂單資料'
                        
                        results.append(result)
                    
                    return results
                else:
                    error_msg = result_data.get('ErrorMessage', '未知錯誤') if result_data else '無回應'
                    print(f"  查詢失敗: {error_msg}")
                    return []
                    
            except Exception as e:
                import traceback
                print(f"  發生錯誤: {e}")
                print(f"  錯誤詳情: {traceback.format_exc()}")
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                continue
        
        print(f"  已達最大重試次數 ({self.max_retries})，放棄此批查詢")
        return None


def load_config(config_path: str = "config.yaml") -> dict:
    """
    載入設定檔
    
    Args:
        config_path: 設定檔路徑
        
    Returns:
        設定字典
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        print(f"設定檔 {config_path} 不存在，使用預設設定")
        return {
            'tracking_numbers': [],
            'max_retries': 5
        }
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def generate_requirements():
    """產生 requirements.txt 檔案"""
    requirements = [
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
        "ddddocr>=1.4.0",
        "pyyaml>=6.0",
    ]
    
    req_path = Path("requirements.txt")
    with open(req_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(requirements) + '\n')
    
    print(f"✅ 已產生 requirements.txt")
    print(f"   路徑: {req_path.absolute()}")
    print(f"   套件數量: {len(requirements)}")


def clean_generated_files():
    """清除所有產生的檔案"""
    files_to_clean = [
        "result.txt",
        "result.txt",
    ]
    
    dirs_to_clean = [
        "__pycache__",
    ]
    
    deleted_count = 0
    
    for file in files_to_clean:
        file_path = Path(file)
        if file_path.exists():
            file_path.unlink()
            print(f"🗑️  已刪除: {file}")
            deleted_count += 1
    
    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"🗑️  已刪除目錄: {dir_name}")
            deleted_count += 1
    
    if deleted_count == 0:
        print("ℹ️  沒有需要清除的檔案")
    else:
        print(f"\n✅ 共清除 {deleted_count} 個項目")


def parse_args():
    """解析命令列參數"""
    parser = argparse.ArgumentParser(
        description="全家便利商店包裹查詢程式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  uv run query_package.py           # 執行查詢
  uv run query_package.py -r        # 產生 requirements.txt
  uv run query_package.py -c        # 清除產生的檔案
  uv run query_package.py -v        # 顯示版本
        """
    )
    
    parser.add_argument(
        '-r', '--requirements',
        action='store_true',
        help='產生 requirements.txt 檔案'
    )
    
    parser.add_argument(
        '-c', '--clean',
        action='store_true',
        help='清除產生的檔案 (result.txt, debug_result.json, __pycache__)'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='store_true',
        help='顯示版本資訊'
    )
    
    return parser.parse_args()


def main():
    """主程式"""
    args = parse_args()
    
    # 處理 -v 顯示版本
    if args.version:
        print(f"全家便利商店包裹查詢程式 v{VERSION}")
        return
    
    # 處理 -r 產生 requirements.txt
    if args.requirements:
        generate_requirements()
        return
    
    # 處理 -c 清除產生的檔案
    if args.clean:
        clean_generated_files()
        return
    
    # 載入設定
    config = load_config()
    
    tracking_numbers = config.get('tracking_numbers', [])
    max_retries = config.get('max_retries', 5)
    output_file = config.get('output_file', 'result.txt')
    
    if not tracking_numbers:
        print("請在 config.yaml 中設定要查詢的包裹編號")
        print("範例:")
        print("tracking_numbers:")
        print('  - "your_tracking_number_1"')
        print('  - "your_tracking_number_2"')
        return
    
    print(f"將查詢 {len(tracking_numbers)} 個包裹")
    print(f"包裹編號: {tracking_numbers}")
    print("-" * 50)
    
    # 建立查詢器
    query = FamilyMartPackageQuery(max_retries=max_retries)
    
    # 執行查詢
    results = query.query(tracking_numbers)
    
    # 取得當前時間
    from datetime import datetime
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 準備輸出內容
    output_lines = []
    output_lines.append("=" * 50)
    output_lines.append(f"全家包裹查詢結果")
    output_lines.append(f"查詢時間: {current_time}")
    output_lines.append(f"查詢包裹數量: {len(tracking_numbers)}")
    output_lines.append("=" * 50)
    
    if results:
        for i, result in enumerate(results, 1):
            output_lines.append(f"\n結果 {i}:")
            for key, value in result.items():
                output_lines.append(f"  {key}: {value}")
    else:
        output_lines.append("\n未取得任何結果")
    
    output_lines.append("\n" + "=" * 50)
    output_lines.append("查詢完成")
    output_lines.append("=" * 50)
    
    # 輸出到終端
    print("\n" + "=" * 50)
    print("查詢結果:")
    print("=" * 50)
    
    if results:
        for i, result in enumerate(results, 1):
            print(f"\n結果 {i}:")
            for key, value in result.items():
                print(f"  {key}: {value}")
    else:
        print("未取得任何結果")
    
    # 儲存到檔案
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print(f"\n結果已儲存至: {output_path.absolute()}")


if __name__ == "__main__":
    main()

