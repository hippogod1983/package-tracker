# 更新日誌 (Changelog)

所有重要變更都會記錄在此檔案。

## [1.4.0] - 2025-12-31

### 新增
- 🎁 **獨立執行檔支援** - 打包後的 exe 包含 Chromium 瀏覽器和 ddddocr 模型
- 📦 新增 `get_chromium_path()` 函數自動偵測內嵌 Chromium 路徑
- 🔧 使用 UV 管理相依性

### 變更
- 更新 `requirements.txt` 同步 `pyproject.toml` 版本
- 蝦皮查詢模組支援 PyInstaller 打包環境

### 修復
- 修正打包後 Playwright 找不到 Chromium 的問題
- 修正 Chromium 目錄名稱（chrome-win64）

---

## [1.3.0] - 2025-12-30

### 新增
- 🦐 蝦皮店到店查詢功能（Playwright headless）

---

## [1.2.1] - 2025-12-30

### 變更
- 視窗啟動後預設置頂，移除置頂切換按鈕
- 蝦皮查詢改用輪詢機制（最多 15 秒），確保頁面載入完成後才擷取資料

---

## [1.1.0] - 2025-12-30

### 新增
- 抽象基類架構 `BasePackageQuery`，便於擴展新快遞
- `@register_carrier` 裝飾器自動註冊快遞
- `QueryResult` 統一結果資料類別

### 變更
- 程式名稱：「全家包裹查詢」→「通用包裹查詢」
- GUI 改用動態載入頁籤（透過 CARRIERS 註冊機制）
- Tab 頁籤樣式：選中綠色突出，未選中紅色

### 修復
- 宅急便查詢 HTML 解析（orderlist-box 結構）
- 高解析度圖標顯示（16-256px 多尺寸）

---

## [1.0.0] - 2025-12-26

### 新增
- 🏪 全家便利商店查詢（自動驗證碼辨識）
- 🐱 宅急便查詢
- Tab 分頁式 GUI 介面
- Enter 查詢、Ctrl+V 貼上、雙擊複製
- 視窗置頂功能
- 現代化深色主題

---

## 如何新增快遞

1. 建立 `query_xxx.py` 繼承 `BasePackageQuery`
2. 設定 `NAME`、`ICON`、`MAX_BATCH` 類別屬性
3. 實作 `_query_batch()` 方法
4. 加上 `@register_carrier` 裝飾器
5. 在 `gui_app.py` 匯入模組即完成
