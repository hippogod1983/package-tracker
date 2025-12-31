# -*- coding: utf-8 -*-
"""
蝦皮查詢 WebView 獨立視窗
此檔案由主程式呼叫，用於顯示蝦皮查詢結果
"""
import sys
import webview

def main():
    if len(sys.argv) < 3:
        print("用法: python webview_window.py <包裹編號> <URL>")
        sys.exit(1)
    
    tracking_no = sys.argv[1]
    url = sys.argv[2]
    
    window = webview.create_window(
        title=f"蝦皮店到店查詢 - {tracking_no}",
        url=url,
        width=900,
        height=700,
        resizable=True,
        text_select=True,
        confirm_close=False
    )
    webview.start()

if __name__ == "__main__":
    main()
