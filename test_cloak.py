# -*- coding: utf-8 -*-
"""單獨測試 CloakBrowser 是否能繞過 HyRead WAF(逐步印出進度)。
先安裝: pip install cloakbrowser
用法:   python test_cloak.py
第一次執行會自動下載約 200MB 的瀏覽器,可能需要數分鐘,請耐心等候。
"""
import sys, time
from bs4 import BeautifulSoup

URL = "https://ebook.hyread.com.tw/bookDetail.jsp?id=504740"

def log(msg):
    print(msg, flush=True)

log("[1/4] 匯入 cloakbrowser ...")
try:
    from cloakbrowser import launch
except ImportError:
    log("  ✗ 尚未安裝,請先執行: pip install cloakbrowser")
    sys.exit()
log("  ✓ 匯入成功")

def run(headless):
    log(f"\n===== 測試 headless={headless} =====")
    t0 = time.time()
    log("[2/4] 啟動瀏覽器(首次會下載約 200MB,請耐心等)...")
    browser = launch(headless=headless, humanize=True)
    log(f"  ✓ 瀏覽器已啟動(耗時 {time.time()-t0:.1f}s)")
    try:
        page = browser.new_page()
        log("[3/4] 前往 HyRead 頁面 ...")
        page.goto(URL, wait_until="domcontentloaded", timeout=40000)
        log("  ✓ 頁面載入完成")
        try:
            page.wait_for_selector('meta[property="og:title"]', timeout=10000)
        except Exception:
            log("  (等 og:title 逾時,仍嘗試取內容)")
        html = page.content()
        log(f"[4/4] 取得 HTML,長度 {len(html)}")
    finally:
        try:
            browser.close()
        except Exception:
            pass
    m = BeautifulSoup(html, "lxml").find("meta", attrs={"property": "og:title"})
    og = (m.get("content") or "") if m else ""
    log(f"  >>> og:title = {og[:70] or '(空,可能被擋)'}")

for hl in (True, False):
    try:
        run(hl)
    except Exception as e:
        log(f"  ✗ headless={hl} 發生錯誤: {e!r}")

log("\n完成。")
