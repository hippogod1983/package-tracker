---
description: 使用 UV 和 PyInstaller 將包裹查詢程式打包成 Windows 執行檔
---

# 打包流程

## 前置條件
// turbo
1. 使用 UV 同步依賴套件
```powershell
uv sync
```

## 打包指令
// turbo
2. 使用 UV 執行 PyInstaller 打包（包含 Playwright Chromium 瀏覽器）
```powershell
uv run pyinstaller --noconfirm --onefile --windowed --icon=icon.ico --name="包裹查詢" --add-data "icon.ico;." --add-data "$env:USERPROFILE\AppData\Local\ms-playwright\chromium-1200;ms-playwright/chromium-1200" --collect-data ddddocr --hidden-import ddddocr gui_app.py
```

### 參數說明
| 參數 | 說明 |
|------|------|
| `--noconfirm` | 覆蓋現有輸出，不詢問確認 |
| `--onefile` | 打包成單一執行檔 |
| `--windowed` | 不顯示命令列視窗 |
| `--icon=icon.ico` | 設定應用程式圖示 |
| `--name="包裹查詢"` | 執行檔名稱 |
| `--add-data "icon.ico;."` | 內嵌圖示檔案 |
| `--add-data "...chromium-1200;..."` | 內嵌 Playwright Chromium 瀏覽器（蝦皮查詢需要） |
| `--collect-data ddddocr` | 收集 ddddocr 的 ONNX 模型檔案 |
| `--hidden-import ddddocr` | 確保 ddddocr 被正確打包 |

## 輸出位置
// turbo
3. 打包完成後，執行檔位於
```
dist/包裹查詢.exe
```

## 清理暫存檔案（選用）
4. 清理 build 資料夾和 spec 檔案
```powershell
Remove-Item -Recurse -Force build, *.spec
```

## 注意事項
- 執行檔約 200MB（因包含 ddddocr 的 ONNX 模型）
- 首次啟動可能需要幾秒鐘載入
- 確保目標電腦有 Windows 10 以上版本
