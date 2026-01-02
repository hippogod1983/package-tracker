# -*- coding: utf-8 -*-
"""
通用包裹查詢 - 跨平台視窗化應用程式 (PyQt6 版本)
支援多種快遞查詢（透過註冊機制擴展）
現代化暖色調主題介面

支援平台: Windows, Ubuntu (Linux), macOS
"""

import sys
import os
import platform
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
import threading
import queue

import yaml
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QFrame, QProgressBar, QMessageBox,
    QHeaderView, QGroupBox, QGridLayout, QStatusBar, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QPixmap

# 導入基礎類別和快遞註冊表
from base_query import CARRIERS

# 導入查詢模組（會自動註冊到 CARRIERS）
import query_package
import query_tcat
import query_shopee
import query_7eleven
import query_post


def get_resource_path(relative_path):
    """取得資源檔案的絕對路徑（支援 PyInstaller 打包）"""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path


def get_config_path():
    """取得設定檔路徑"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / "config.yaml"
    return Path(__file__).parent / "config.yaml"


def load_saved_tracking_numbers():
    """載入保存的包裹編號"""
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            return config.get('saved_tracking_numbers', {})
        except Exception as e:
            print(f"載入設定失敗: {e}")
    return {}


def save_tracking_numbers(data: dict):
    """保存包裹編號到設定檔"""
    config_path = get_config_path()
    try:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}
        config['saved_tracking_numbers'] = data
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    except Exception as e:
        print(f"保存設定失敗: {e}")


class ModernStyle:
    """現代化暖色調主題"""
    
    # 主色調 - 暖橘色
    PRIMARY = "#d97706"
    PRIMARY_LIGHT = "#f59e0b"
    PRIMARY_DARK = "#b45309"
    
    # 背景色系
    BG_MAIN = "#fef7ed"
    BG_WHITE = "#fffbf5"
    BG_CARD = "#fffbf5"
    
    # 狀態色彩
    SUCCESS = "#16a34a"
    SUCCESS_BG = "#f0fdf4"
    WARNING = "#ea580c"
    WARNING_BG = "#fff7ed"
    ERROR = "#dc2626"
    ERROR_BG = "#fef2f2"
    
    # 文字色彩
    TEXT_PRIMARY = "#78350f"
    TEXT_SECONDARY = "#a16207"
    TEXT_MUTED = "#ca8a04"
    
    # 邊框
    BORDER = "#fde68a"
    BORDER_FOCUS = "#d97706"
    
    @classmethod
    def get_stylesheet(cls) -> str:
        """取得 QSS 樣式表"""
        return f"""
            QMainWindow {{
                background-color: {cls.BG_MAIN};
            }}
            
            QWidget {{
                font-family: 'Noto Sans CJK TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif;
                font-size: 13px;
                color: {cls.TEXT_PRIMARY};
            }}
            
            QTabWidget::pane {{
                border: 1px solid {cls.BORDER};
                background-color: {cls.BG_WHITE};
                border-radius: 8px;
            }}
            
            QTabBar::tab {{
                background-color: {cls.BG_MAIN};
                color: {cls.TEXT_SECONDARY};
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 14px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {cls.BG_WHITE};
                color: {cls.PRIMARY};
                font-weight: bold;
            }}
            
            QTabBar::tab:hover {{
                background-color: {cls.BG_CARD};
            }}
            
            QGroupBox {{
                background-color: {cls.BG_WHITE};
                border: 1px solid {cls.BORDER};
                border-radius: 8px;
                margin-top: 16px;
                padding: 16px;
                font-weight: bold;
                color: {cls.PRIMARY};
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
            }}
            
            QLineEdit {{
                background-color: {cls.BG_WHITE};
                border: 2px solid {cls.BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                font-family: 'DejaVu Sans Mono', 'SF Mono', 'Consolas', monospace;
            }}
            
            QLineEdit:focus {{
                border-color: {cls.PRIMARY};
            }}
            
            QPushButton {{
                background-color: {cls.BG_WHITE};
                border: 2px solid {cls.BORDER};
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                color: {cls.TEXT_PRIMARY};
            }}
            
            QPushButton:hover {{
                background-color: {cls.BG_CARD};
                border-color: {cls.PRIMARY_LIGHT};
            }}
            
            QPushButton:pressed {{
                background-color: {cls.BORDER};
            }}
            
            QPushButton#primaryButton {{
                background-color: {cls.PRIMARY};
                color: white;
                border: none;
                font-weight: bold;
            }}
            
            QPushButton#primaryButton:hover {{
                background-color: {cls.PRIMARY_DARK};
            }}
            
            QTableWidget {{
                background-color: {cls.BG_WHITE};
                border: 1px solid {cls.BORDER};
                border-radius: 8px;
                gridline-color: {cls.BORDER};
            }}
            
            QTableWidget::item {{
                padding: 8px;
            }}
            
            QTableWidget::item:selected {{
                background-color: {cls.PRIMARY_LIGHT};
                color: white;
            }}
            
            QHeaderView::section {{
                background-color: {cls.BG_MAIN};
                color: {cls.TEXT_PRIMARY};
                padding: 10px;
                border: none;
                border-bottom: 2px solid {cls.BORDER};
                font-weight: bold;
            }}
            
            QProgressBar {{
                background-color: {cls.BORDER};
                border: none;
                border-radius: 4px;
                height: 6px;
            }}
            
            QProgressBar::chunk {{
                background-color: {cls.PRIMARY};
                border-radius: 4px;
            }}
            
            QStatusBar {{
                background-color: {cls.BG_MAIN};
                color: {cls.TEXT_SECONDARY};
            }}
            
            QLabel#titleLabel {{
                font-size: 24px;
                font-weight: bold;
                color: {cls.TEXT_PRIMARY};
            }}
            
            QLabel#subtitleLabel {{
                font-size: 13px;
                color: {cls.TEXT_SECONDARY};
            }}
        """


class QueryWorker(QThread):
    """查詢工作執行緒（支援並行/序列查詢）"""
    
    result_ready = pyqtSignal(dict)
    status_update = pyqtSignal(str)
    progress_update = pyqtSignal(int, int)  # (當前, 總數)
    finished_signal = pyqtSignal()
    
    def __init__(self, query_class, tracking_numbers: List[str]):
        super().__init__()
        self.query_class = query_class
        self.tracking_numbers = tracking_numbers
    
    def _query_single(self, query, tracking_no: str) -> Dict:
        """查詢單一包裹"""
        try:
            results = query._query_batch([tracking_no])
            if results:
                return results[0]
            else:
                return {
                    '包裹編號': tracking_no,
                    '訂單編號': '-',
                    '狀態': '⚠️ 查無結果'
                }
        except Exception as e:
            return {
                '包裹編號': tracking_no,
                '訂單編號': '-',
                '狀態': f'❌ 查詢失敗: {str(e)}'
            }
    
    def run(self):
        try:
            query = self.query_class(max_retries=5)
            total = len(self.tracking_numbers)
            
            # 檢查是否支援並行查詢
            supports_parallel = getattr(self.query_class, 'SUPPORTS_PARALLEL', True)
            
            if supports_parallel and total > 1:
                # 使用 ThreadPoolExecutor 並行查詢
                self.status_update.emit(f"⚡ 並行查詢 {total} 個包裹...")
                self.progress_update.emit(0, total)
                
                from concurrent.futures import ThreadPoolExecutor, as_completed
                
                completed = 0
                with ThreadPoolExecutor(max_workers=min(total, 4)) as executor:
                    # 提交所有任務
                    future_to_tracking = {
                        executor.submit(self._query_single, query, tn): tn 
                        for tn in self.tracking_numbers
                    }
                    
                    # 處理完成的結果
                    for future in as_completed(future_to_tracking):
                        tracking_no = future_to_tracking[future]
                        completed += 1
                        self.progress_update.emit(completed, total)
                        self.status_update.emit(f"⚡ 並行查詢 {completed}/{total}")
                        
                        try:
                            result = future.result()
                            self.result_ready.emit(result)
                        except Exception as e:
                            self.result_ready.emit({
                                '包裹編號': tracking_no,
                                '訂單編號': '-',
                                '狀態': f'❌ 查詢失敗: {str(e)}'
                            })
            else:
                # 序列查詢（Playwright 模組或只有一個包裹）
                for i, tracking_no in enumerate(self.tracking_numbers, 1):
                    self.status_update.emit(f"查詢 {i}/{total}: {tracking_no}")
                    self.progress_update.emit(i, total)
                    
                    result = self._query_single(query, tracking_no)
                    self.result_ready.emit(result)
            
            self.status_update.emit(f"查詢完成！({datetime.now().strftime('%H:%M:%S')})")
            
        except Exception as e:
            self.status_update.emit(f"❌ 發生錯誤: {str(e)}")
        
        finally:
            self.finished_signal.emit()


class QueryTab(QWidget):
    """查詢頁籤"""
    
    def __init__(self, query_class, tab_name: str, parent=None):
        super().__init__(parent)
        self.query_class = query_class
        self.tab_name = tab_name
        self.max_inputs = 4  # 固定 4 個輸入欄位
        self.entry_fields: List[QLineEdit] = []
        self.is_querying = False
        self.worker: Optional[QueryWorker] = None
        
        self._setup_ui()
        self._load_saved_numbers()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # 輸入區
        input_group = QGroupBox(" 包裹編號 ")
        input_layout = QGridLayout(input_group)
        input_layout.setSpacing(12)
        
        # 建立輸入欄位（2 列佈局）
        num_rows = (self.max_inputs + 1) // 2
        for row in range(num_rows):
            for col in range(2):
                idx = row * 2 + col
                if idx >= self.max_inputs:
                    break
                
                label = QLabel(f"包裹 {idx+1}:")
                entry = QLineEdit()
                entry.setPlaceholderText("輸入包裹編號...")
                entry.returnPressed.connect(self._start_query)
                
                input_layout.addWidget(label, row, col * 2)
                input_layout.addWidget(entry, row, col * 2 + 1)
                self.entry_fields.append(entry)
        
        layout.addWidget(input_group)
        
        # 按鈕區
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        self.query_button = QPushButton("🔍 開始查詢")
        self.query_button.setObjectName("primaryButton")
        self.query_button.clicked.connect(self._start_query)
        self.query_button.setMinimumHeight(44)
        
        self.clear_button = QPushButton("🗑️ 清除")
        self.clear_button.clicked.connect(self._clear_all)
        self.clear_button.setMinimumHeight(44)
        
        self.copy_button = QPushButton("📋 複製")
        self.copy_button.clicked.connect(self._copy_results)
        self.copy_button.setMinimumHeight(44)
        
        button_layout.addWidget(self.query_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.copy_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # 結果區
        result_group = QGroupBox(" 查詢結果 ")
        result_layout = QVBoxLayout(result_group)
        
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(3)
        self.result_table.setHorizontalHeaderLabels(['包裹編號', '狀態', '查詢時間'])
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.result_table.horizontalHeader().setMinimumSectionSize(100)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setMinimumHeight(250)
        
        result_layout.addWidget(self.result_table)
        layout.addWidget(result_group)
    
    def _get_tracking_numbers(self) -> List[str]:
        """取得所有非空的包裹編號"""
        return [entry.text().strip() for entry in self.entry_fields if entry.text().strip()]
    
    def _start_query(self):
        """開始查詢"""
        if self.is_querying:
            QMessageBox.warning(self, "提示", "查詢進行中，請稍候...")
            return
        
        tracking_numbers = self._get_tracking_numbers()
        if not tracking_numbers:
            QMessageBox.warning(self, "提示", "請輸入至少一個包裹編號")
            return
        
        self._save_numbers()
        self.is_querying = True
        self.query_button.setEnabled(False)
        self.result_table.setRowCount(0)
        
        # 取得主視窗更新狀態列
        main_window = self.window()
        if hasattr(main_window, 'status_bar'):
            main_window.status_bar.showMessage(f"[{self.tab_name}] 開始查詢 {len(tracking_numbers)} 個包裹...")
        if hasattr(main_window, 'progress_bar'):
            main_window.progress_bar.setMaximum(len(tracking_numbers))
            main_window.progress_bar.setValue(0)
        
        # 啟動工作執行緒
        self.worker = QueryWorker(self.query_class, tracking_numbers)
        self.worker.result_ready.connect(self._on_result)
        self.worker.status_update.connect(self._on_status_update)
        self.worker.progress_update.connect(self._on_progress_update)  # 新增
        self.worker.finished_signal.connect(self._on_query_finished)
        self.worker.start()

    
    def _on_result(self, result: dict):
        """處理查詢結果"""
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        
        self.result_table.setItem(row, 0, QTableWidgetItem(result.get('包裹編號', 'N/A')))
        
        status = result.get('狀態', 'N/A')
        status_item = QTableWidgetItem(status)
        
        # 根據狀態設定顏色
        if any(k in status for k in ['可取貨', '已取貨', '已送達', '完成']):
            status_item.setForeground(QColor(ModernStyle.SUCCESS))
        elif any(k in status for k in ['配送中', '運送中', '處理中', '已出貨']):
            status_item.setForeground(QColor(ModernStyle.WARNING))
        elif any(k in status for k in ['查無', '失敗', '異常']):
            status_item.setForeground(QColor(ModernStyle.ERROR))
        
        self.result_table.setItem(row, 1, status_item)
        self.result_table.setItem(row, 2, QTableWidgetItem(datetime.now().strftime('%H:%M:%S')))
    
    def _on_status_update(self, status: str):
        """更新狀態"""
        main_window = self.window()
        if hasattr(main_window, 'status_bar'):
            main_window.status_bar.showMessage(f"[{self.tab_name}] {status}")
    
    def _on_progress_update(self, current: int, total: int):
        """更新進度條"""
        main_window = self.window()
        if hasattr(main_window, 'progress_bar'):
            main_window.progress_bar.setMaximum(total)
            main_window.progress_bar.setValue(current)
    
    def _on_query_finished(self):
        """查詢完成"""
        self.is_querying = False
        self.query_button.setEnabled(True)
        
        main_window = self.window()
        if hasattr(main_window, 'progress_bar'):
            main_window.progress_bar.setMaximum(100)
            main_window.progress_bar.setValue(100)
    
    def _clear_all(self):
        """清除所有內容"""
        for entry in self.entry_fields:
            entry.clear()
        self.result_table.setRowCount(0)
    
    def _copy_results(self):
        """複製結果到剪貼簿"""
        if self.result_table.rowCount() == 0:
            QMessageBox.information(self, "提示", "沒有結果可複製")
            return
        
        lines = []
        for row in range(self.result_table.rowCount()):
            row_data = []
            for col in range(self.result_table.columnCount()):
                item = self.result_table.item(row, col)
                row_data.append(item.text() if item else '')
            lines.append('\t'.join(row_data))
        
        text = '\n'.join(lines)
        QApplication.clipboard().setText(text)
        
        main_window = self.window()
        if hasattr(main_window, 'status_bar'):
            main_window.status_bar.showMessage("已複製到剪貼簿", 3000)
    
    def _load_saved_numbers(self):
        """載入保存的包裹編號"""
        saved = load_saved_tracking_numbers()
        numbers = saved.get(self.tab_name, [])
        for i, num in enumerate(numbers):
            if i < len(self.entry_fields):
                self.entry_fields[i].setText(num)
    
    def _save_numbers(self):
        """保存當前的包裹編號"""
        saved = load_saved_tracking_numbers()
        saved[self.tab_name] = [entry.text() for entry in self.entry_fields]
        save_tracking_numbers(saved)


class PackageQueryApp(QMainWindow):
    """主應用程式視窗"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("通用包裹查詢 v1.7.0")
        self.setMinimumSize(800, 650)
        self.resize(900, 700)
        
        # 設定視窗圖標
        self._set_window_icon()
        
        # 套用樣式
        self.setStyleSheet(ModernStyle.get_stylesheet())
        
        # 建立 UI
        self._setup_ui()
        
        # 視窗置頂
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    
    def _set_window_icon(self):
        """設定視窗圖標（使用 .ico 檔案確保一致性）"""
        try:
            # 優先使用 .ico 檔案（與桌面圖示一致）
            icon_path = get_resource_path('icon.ico')
            if icon_path.exists():
                icon = QIcon(str(icon_path))
                self.setWindowIcon(icon)
                # 同時設定應用程式圖示（確保工作列也顯示正確）
                QApplication.instance().setWindowIcon(icon)
        except Exception as e:
            print(f"載入圖標失敗: {e}")
    
    def _setup_ui(self):
        """建立主介面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 10)
        main_layout.setSpacing(16)
        
        # 標題區
        title_layout = QVBoxLayout()
        
        title_label = QLabel("📦 通用包裹查詢")
        title_label.setObjectName("titleLabel")
        title_layout.addWidget(title_label)
        
        subtitle_label = QLabel("支援全家、宅急便、7-11、郵局、蝦皮 | v1.7.0 並行查詢")
        subtitle_label.setObjectName("subtitleLabel")
        title_layout.addWidget(subtitle_label)
        
        main_layout.addLayout(title_layout)
        
        # 分頁區
        self.tab_widget = QTabWidget()
        self.tabs: Dict[str, QueryTab] = {}
        
        # 根據註冊的快遞建立頁籤
        for carrier_class in CARRIERS:
            tab_name = carrier_class.get_display_name()
            tab = QueryTab(carrier_class, tab_name)
            self.tab_widget.addTab(tab, tab_name)
            self.tabs[tab_name] = tab
        
        main_layout.addWidget(self.tab_widget)
        
        # 進度條
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        main_layout.addWidget(self.progress_bar)
        
        # 狀態列
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就緒")


def main():
    """主程式"""
    # 高 DPI 支援
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("通用包裹查詢")
    app.setApplicationVersion("1.4.0")
    
    window = PackageQueryApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
