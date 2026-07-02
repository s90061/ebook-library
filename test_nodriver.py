# -*- coding: utf-8 -*-
"""單獨測試 nodriver 是否能繞過 HyRead WAF。
用法:
    python test_nodriver.py
    python test_nodriver.py "C:\\path\\to\\CloakBrowser\\chrome.exe"   # 指定自訂瀏覽器
會分別以「無頭」與「有頭」測試,印出 og:title 是否抓到。
"""
import sys, asyncio
from bs4 import BeautifulSoup

URL = "https://ebook.hyread.com.tw/bookDetail.jsp?id=504740"
BIN = sys.argv[1] if len(sys.argv) > 1 else None

try:
    import nodriver as uc
except ImportError:
    print("尚未安裝 nodriver,請先執行: pip install nodriver")
    sys.exit()

async def run(headless):
    kwargs = {"headless": headless, "lang": "zh-TW"}
    if BIN:
        kwargs["browser_executable_path"] = BIN
    browser = await uc.start(**kwargs)
    try:
        page = await browser.get(URL)
        try:
            await page.select('meta[property="og:title"]', timeout=15)
        except Exception:
            await page.sleep(3)
        html = await page.get_content()
    finally:
        try:
            browser.stop()
        except Exception:
            pass
    m = BeautifulSoup(html, "lxml").find("meta", attrs={"property": "og:title"})
    og = (m.get("content") or "") if m else ""
    print(f"  headless={headless}: 長度={len(html)} og:title={og[:60] or '(空)'}")

async def main():
    print("瀏覽器 binary:", BIN or "(系統 Chrome)")
    print("測試 nodriver 無頭 / 有頭 ...")
    for hl in (True, False):
        try:
            await run(hl)
        except Exception as e:
            print(f"  headless={hl}: 錯誤 {e!r}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
