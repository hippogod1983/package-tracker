# -*- coding: utf-8 -*-
"""
包裹查詢抽象基類
定義統一的查詢介面，便於擴展新快遞
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time
import random


# ============================================================
# 自訂例外類別
# ============================================================

class QueryError(Exception):
    """查詢錯誤基類"""
    pass


class NetworkError(QueryError):
    """網路錯誤（連線失敗、超時等）"""
    pass


class ParseError(QueryError):
    """解析錯誤（HTML 結構變更、資料格式異常）"""
    pass


class NotFoundError(QueryError):
    """查無資料"""
    pass


class CaptchaError(QueryError):
    """驗證碼錯誤"""
    pass


# ============================================================
# 重試機制
# ============================================================

def exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 30.0) -> float:
    """
    計算指數退避延遲時間
    
    Args:
        attempt: 當前嘗試次數（從 0 開始）
        base_delay: 基礎延遲秒數
        max_delay: 最大延遲秒數
        
    Returns:
        計算後的延遲秒數（含隨機抖動）
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = delay * 0.1 * random.random()  # 加入 10% 隨機抖動
    return delay + jitter


def retry_with_backoff(func, max_retries: int = 3, 
                       retryable_exceptions: tuple = (NetworkError, CaptchaError)):
    """
    使用指數退避的重試裝飾器
    
    Args:
        func: 要執行的函數
        max_retries: 最大重試次數
        retryable_exceptions: 可重試的例外類型
        
    Returns:
        函數執行結果
    """
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except retryable_exceptions as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = exponential_backoff(attempt)
                    print(f"  重試 {attempt + 1}/{max_retries}，等待 {delay:.1f} 秒...")
                    time.sleep(delay)
        raise last_exception
    return wrapper


@dataclass
class QueryResult:
    """統一查詢結果格式"""
    tracking_number: str
    order_number: str = "-"
    status: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    
    def to_dict(self) -> Dict:
        """轉換為字典格式（向後相容）"""
        return {
            '包裹編號': self.tracking_number,
            '訂單編號': self.order_number,
            '狀態': self.status,
        }


class BasePackageQuery(ABC):
    """
    包裹查詢抽象基類
    
    新增快遞步驟：
    1. 建立 query_xxx.py 繼承此類別
    2. 設定 NAME, ICON, MAX_BATCH 類別屬性
    3. 實作 _query_batch() 方法
    4. 在 gui_app.py 的 CARRIERS 列表註冊
    """
    
    # 子類別必須覆寫的類別屬性
    NAME: str = "未定義"      # 快遞名稱（顯示在頁籤）
    ICON: str = "📦"          # 快遞圖標
    MAX_BATCH: int = 5        # 單次最大查詢數量
    SUPPORTS_PARALLEL: bool = True  # 是否支援並行查詢（Playwright 模組設為 False）
    
    def __init__(self, max_retries: int = 3):
        """
        初始化查詢器
        
        Args:
            max_retries: 最大重試次數
        """
        self.max_retries = max_retries
    
    @abstractmethod
    def _query_batch(self, tracking_numbers: List[str]) -> Optional[List[Dict]]:
        """
        查詢一批包裹（子類必須實作）
        
        Args:
            tracking_numbers: 追蹤碼清單
            
        Returns:
            查詢結果清單，格式為 [{'包裹編號': ..., '訂單編號': ..., '狀態': ...}, ...]
            失敗時返回 None
        """
        pass
    
    def query(self, tracking_numbers: List[str]) -> List[Dict]:
        """
        查詢包裹狀態（共用邏輯）
        
        Args:
            tracking_numbers: 要查詢的追蹤碼清單
            
        Returns:
            查詢結果清單
        """
        all_results = []
        
        # 分批處理
        for i in range(0, len(tracking_numbers), self.MAX_BATCH):
            batch = tracking_numbers[i:i + self.MAX_BATCH]
            print(f"\n正在查詢第 {i + 1} 到 {min(i + self.MAX_BATCH, len(tracking_numbers))} 個包裹...")
            
            result = self._query_batch(batch)
            if result:
                all_results.extend(result)
            
            # 避免太頻繁請求
            if i + self.MAX_BATCH < len(tracking_numbers):
                time.sleep(1)
        
        return all_results
    
    @classmethod
    def get_display_name(cls) -> str:
        """取得顯示名稱（含圖標）"""
        return f"{cls.ICON} {cls.NAME}"


# 快遞註冊表（在此新增快遞類別即可自動建立頁籤）
CARRIERS: List[type] = []


def register_carrier(carrier_class: type) -> type:
    """
    裝飾器：註冊快遞類別
    
    Usage:
        @register_carrier
        class MyCarrierQuery(BasePackageQuery):
            ...
    """
    CARRIERS.append(carrier_class)
    return carrier_class
