# -*- coding: utf-8 -*-
"""測試哪種瀏覽器設定能通過 HyRead 的封鎖。用法: python test_browser.py"""
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

url = "https://ebook.hyread.com.tw/bookDetail.jsp?id=504740"

def try_cfg(label, **launch):
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(**launch)
            pg = b.new_page(locale="zh-TW")
            resp = pg.goto(url, wait_until="domcontentloaded", timeout=40000)
            status = resp.status if resp else "?"
            try:
                pg.wait_for_selector('meta[property="og:title"]', timeout=8000)
            except Exception:
                pass
            html = pg.content()
            m = BeautifulSoup(html, "lxml").find("meta", attrs={"property": "og:title"})
            og = (m.get("content") or "") if m else ""
            print(f"{label}: 狀態={status} 長度={len(html)} og:title={og[:60] or '(空)'}")
            b.close()
    except Exception as e:
        print(f"{label}: 錯誤 {e!r}")

print("測試 4 種瀏覽器設定(2、4 會彈出可見視窗,屬正常)...")
try_cfg("1 內建chromium headless", headless=True)
try_cfg("2 內建chromium headed ", headless=False)
try_cfg("3 真實Chrome  headless", headless=True, channel="chrome")
try_cfg("4 真實Chrome  headed  ", headless=False, channel="chrome")
print("完成,請貼回四行結果。哪一行 og:title 有書名就是可用設定。")
