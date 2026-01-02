# 通用包裹查詢程式

> **版本: 1.7.0** (PyQt6 版本 + 並行查詢)

自動查詢包裹物流狀態的跨平台視窗應用程式，支援多家物流平台。

## 支援平台

| 平台 | 說明 |
|------|------|
| 🏠 全家便利商店 | 自動辨識驗證碼（ddddocr） |
| 🐱 宅急便 | 黑貓 T-CAT 直接查詢 |
| 🏪 7-11 交貨便 | 自動辨識驗證碼（ddddocr） |
| 📮 郵局掛號 | Playwright + ddddocr 辨識驗證碼 |
| 🦐 蝦皮店到店 | Playwright 無頭瀏覽器抓取 |

## 功能特色

- ✅ **跨平台支援** - Windows、Ubuntu、macOS
- ✅ **現代化介面** - PyQt6 暖色調主題
- ✅ **視窗置頂** - 程式啟動後自動置頂
- ✅ **分頁式介面** - 輕鬆切換不同物流平台
- ✅ **模組化架構** - 透過 `@register_carrier` 輕鬆擴展
- ✅ **自動驗證碼** - 全家、7-11、郵局使用 ddddocr 辨識
- ✅ **無頭瀏覽器** - 蝦皮、郵局使用 Playwright headless 抓取
- ✅ **並行查詢** - 全家、宅急便、7-11 支援同時查詢多個包裹
- ✅ **即時進度條** - 顯示查詢進度百分比
- ✅ **快捷操作** - Enter 查詢
- ✅ **自動保存** - 記住上次查詢的包裹編號
- ✅ **錯誤處理** - 指數退避重試機制、區分錯誤類型
- ✅ **獨立執行檔** - 打包後包含 Chromium 和 ddddocr 模型，無需額外安裝

## 快速開始

### 方式一：直接下載執行檔（推薦）

1. 下載 `PackageTracker.exe`
2. 雙擊執行即可使用

> ⚠️ 執行檔約 400 MB，因內含 Chromium 瀏覽器和 OCR 模型

### 方式二：從原始碼執行

#### 1. 安裝 Python 3.11

下載並安裝 [Python 3.11](https://www.python.org/downloads/)

> ⚠️ **重要**：安裝時勾選 "Add Python to PATH"

#### 2. 安裝 uv（推薦）

打開 PowerShell（系統管理員），執行：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### 3. 安裝依賴

```bash
cd package-tracker
uv sync
```

#### 4. 安裝 Playwright 瀏覽器（首次執行）

```bash
uv run playwright install chromium
```

#### 5. 執行程式

```bash
uv run python gui_app.py
```

### Ubuntu/macOS 安裝

```bash
# 安裝依賴
uv sync

# 安裝 Playwright 瀏覽器
uv run playwright install chromium

# 執行程式
uv run python gui_app.py
```

### 打包成 exe（Windows）

```powershell
uv run pyinstaller --onefile --windowed --icon=icon.ico --name="PackageTracker" `
    --add-data "$env:USERPROFILE\AppData\Local\ms-playwright\chromium-1200;ms-playwright/chromium-1200" `
    --collect-all ddddocr gui_app.py
```

> ⚠️ **重要**：
> - 必須使用 `--collect-all ddddocr` 否則驗證碼功能會失效
> - 必須加入 Chromium 瀏覽器否則蝦皮、郵局查詢會失敗

## 擴展新快遞

建立 `query_xxx.py`：

```python
from base_query import BasePackageQuery, register_carrier

@register_carrier
class XXXPackageQuery(BasePackageQuery):
    NAME = "XXX快遞"
    ICON = ""
    MAX_BATCH = 10
    
    def _query_batch(self, tracking_numbers):
        # 實作查詢邏輯
        ...
```

在 `gui_app.py` 匯入：

```python
import query_xxx  # 自動註冊並建立頁籤
```

## 專案結構

```
├── gui_app.py          # 主程式 GUI (PyQt6)
├── base_query.py       # 抽象基類 + 錯誤處理
├── query_package.py    # 全家查詢模組
├── query_tcat.py       # 宅急便查詢模組
├── query_7eleven.py    # 7-11 交貨便模組
├── query_post.py       # 郵局掛號模組 (Playwright)
├── query_shopee.py     # 蝦皮店到店模組 (Playwright)
├── config.yaml         # 設定檔（自動生成）
├── icon.ico            # Windows 圖標
├── icon_hd.png         # 高解析度圖標
├── pyproject.toml      # 專案設定
├── requirements.txt    # 依賴套件
└── CHANGELOG.md        # 更新日誌
```

## 依賴套件

- `PyQt6` - GUI 框架
- `requests` - HTTP 請求
- `beautifulsoup4` - HTML 解析
- `ddddocr` - 驗證碼辨識
- `playwright` - 無頭瀏覽器
- `pyyaml` - YAML 設定檔解析

## 注意事項

- ⚠️ 需要 Python 3.11 (ddddocr 限制)
- 每次最多查詢 4 個包裹
- 蝦皮、郵局首次查詢需要下載 Chromium (~200MB)
- 打包後 exe 約 400MB（含 Chromium）

## 授權

MIT License
