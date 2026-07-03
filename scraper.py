# -*- coding: utf-8 -*-
"""
scraper.py — 從電子書平台網址抓取書本資訊

支援平台:
  - Readmoo 讀墨   (readmoo.com)
  - Kobo           (kobo.com)
  - HyRead         (ebook.hyread.com.tw)

策略(依序):
  1. 靜態抓取(requests):解析 JSON-LD + Open Graph meta,再依平台客製化補強。
  2. 若靜態被擋(如企業網路 WAF 回 400/403/503)或內容需 JavaScript,
     改用瀏覽器渲染:CloakBrowser(選配)-> nodriver(選配)-> Playwright 有頭(保底)。
  可用最上方常數切換各後端(見「渲染後端設定」)。
"""

import json
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# 模擬真實瀏覽器的完整請求標頭,降低被平台(尤其 Kobo)擋下的機率
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

TIMEOUT = 25

# ---------------------------------------------------------------------------
# 渲染後端設定(依序嘗試:CloakBrowser -> nodriver -> Playwright 有頭保底)
# ---------------------------------------------------------------------------
# CloakBrowser:pip install cloakbrowser,Playwright 的 drop-in 替代,
# 底層為 C++ 改指紋的 stealth Chromium,常可繞過 WAF(首次執行自動下載約 200MB)。
# 先嘗試輕量靜態抓取(requests);失敗或被擋才開瀏覽器。一般網路可完全不開瀏覽器。
STATIC_FIRST = True

USE_CLOAKBROWSER = False  # 實測本環境 CloakBrowser 無頭/有頭都被擋(93 bytes),故關閉,直接走 Playwright 有頭
CLOAK_HEADLESS = True     # 先試無頭(其 C++ patch 可能連無頭都能過);若被擋改成 False
CLOAK_HUMANIZE = True     # 模擬人類滑鼠/鍵盤/捲動
CLOAK_PROXY = None        # 需要時填住宅代理: "http://user:pass@host:port"

# nodriver:次選的 stealth 後端(pip install nodriver)
USE_NODRIVER = False
NODRIVER_HEADLESS = True
NODRIVER_BROWSER_PATH = None   # 指定自訂瀏覽器執行檔;None=自動找系統 Chrome


# ---------------------------------------------------------------------------
# 平台判斷
# ---------------------------------------------------------------------------
def detect_platform(url):
    """依網域判斷平台代碼。"""
    host = (urlparse(url).hostname or "").lower()
    if "readmoo.com" in host:
        return "readmoo"
    if "kobo.com" in host:
        return "kobo"
    if "hyread.com.tw" in host:
        return "hyread"
    return "unknown"


PLATFORM_NAMES = {
    "readmoo": "Readmoo 讀墨",
    "kobo": "Kobo",
    "hyread": "HyRead",
    "unknown": "其他",
}


# ---------------------------------------------------------------------------
# 共用小工具
# ---------------------------------------------------------------------------
def _clean(text):
    """清理空白與 &nbsp;。"""
    if not text:
        return ""
    text = text.replace("\xa0", " ").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def _meta(soup, key):
    """讀取 <meta property=key> 或 <meta name=key> 的 content。"""
    tag = soup.find("meta", attrs={"property": key}) or soup.find(
        "meta", attrs={"name": key}
    )
    return _clean(tag.get("content")) if tag and tag.get("content") else ""


def _parse_jsonld(soup):
    """解析頁面中所有 JSON-LD 區塊,回傳與書籍相關的物件清單。"""
    results = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text() or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in list(candidates):
            if isinstance(item, dict) and isinstance(item.get("@graph"), list):
                candidates.extend(item["@graph"])
        for item in candidates:
            if isinstance(item, dict):
                results.append(item)
    return results


def _extract_author_from_jsonld(item):
    """從 JSON-LD 物件取出作者字串(可能是字串、dict 或 list)。"""
    author = item.get("author")
    names = []
    if isinstance(author, str):
        names.append(author)
    elif isinstance(author, dict):
        if author.get("name"):
            names.append(author["name"])
    elif isinstance(author, list):
        for a in author:
            if isinstance(a, str):
                names.append(a)
            elif isinstance(a, dict) and a.get("name"):
                names.append(a["name"])
    return _clean(", ".join(names))


# ---------------------------------------------------------------------------
# 各平台專屬解析
# ---------------------------------------------------------------------------
def _parse_readmoo(soup):
    """Readmoo 讀墨:以 JSON-LD 為主,OG meta 為輔。

    作者以頁面上的 /contributor 連結為準(Readmoo 作者連結格式),
    可能有多位(作者、譯者等)會合併;出版社另由 /publisher 連結取得。
    """
    info = {}
    for item in _parse_jsonld(soup):
        t = item.get("@type", "")
        types = t if isinstance(t, list) else [t]
        if any(x in ("Book", "Product") for x in types):
            info["title"] = info.get("title") or _clean(item.get("name"))
            info["author"] = info.get("author") or _extract_author_from_jsonld(item)
            img = item.get("image")
            if isinstance(img, list):
                img = img[0] if img else ""
            if isinstance(img, dict):
                img = img.get("url", "")
            info["cover"] = info.get("cover") or _clean(img)
            pub = item.get("publisher")
            if isinstance(pub, dict):
                pub = pub.get("name", "")
            info["publisher"] = info.get("publisher") or _clean(pub)
            info["isbn"] = info.get("isbn") or _clean(item.get("isbn"))

    # 標題與封面
    title = _meta(soup, "og:title")
    title = re.sub(r"\s*[-|｜]\s*Readmoo.*$", "", title).strip()
    info["title"] = info.get("title") or title
    info["cover"] = info.get("cover") or _meta(soup, "og:image")
    info["description"] = _meta(soup, "og:description") or _meta(soup, "description")

    # 作者:Readmoo 的作者/原文作者/譯者都是 /contributor 連結,
    # 頁面下方「推薦書」也是 /contributor,因此需靠連結旁的角色標籤鎖定書籍資訊區,
    # 並區分角色 — 只把「作者」放進作者欄,排除譯者/推薦書。
    def _role_of(text):
        # 角色詞必須出現在該列「開頭」(如「作者:…」),才算是標籤;
        # 順序上先比對較長/特定的,避免「原文作者」被當成「作者」。
        text = text.lstrip()
        for kw in ("譯者", "原文作者", "編者", "繪者", "審訂", "作者"):
            if text.startswith(kw):
                return kw
        return ""

    authors, others = [], []
    for a in soup.find_all("a", href=re.compile(r"/contributor")):
        name = _clean(a.get_text())
        if not name or name.isdigit() or len(name) > 40:
            continue
        # 只往上找 2 層(避免碰到含全部標籤的大容器/ body),
        # 取第一個「開頭即角色標籤」的區塊(=書籍資訊列)
        block, node = "", a
        for _ in range(2):
            node = node.parent
            if node is None:
                break
            txt = _clean(node.get_text())
            if _role_of(txt):
                block = txt
                break
        role = _role_of(block)
        if not role:
            continue  # 沒有角色標籤 → 多半是推薦書,略過
        if role == "作者":
            if name not in authors:
                authors.append(name)
        elif name not in others:
            others.append(name)

    if authors:
        info["author"] = ", ".join(authors)
    elif others:            # 沒有明確「作者」時,退而用其他貢獻者(如原文作者/譯者)
        info["author"] = ", ".join(others)

    # 若仍無作者,最後退而求其次用 meta
    if not info.get("author"):
        info["author"] = _meta(soup, "book:author") or _meta(soup, "author")

    # 出版社:用 /publisher 連結補強(不會被當成作者)
    if not info.get("publisher"):
        pub_link = soup.find("a", href=re.compile(r"/publisher"))
        if pub_link:
            info["publisher"] = _clean(pub_link.get_text())

    return info


def _parse_kobo(soup):
    """Kobo:og:title 形如「書名 電子書 by 作者 - Rakuten Kobo」。"""
    info = {}
    og_title = _meta(soup, "og:title")
    title = re.sub(r"\s*-\s*Rakuten Kobo\s*$", "", og_title)
    m = re.search(r"(.*?)\s*電子書\s*by\s*(.+)$", title)
    if m:
        info["title"] = _clean(m.group(1))
        info["author"] = _clean(m.group(2))
    else:
        info["title"] = _clean(title)

    if not info.get("author"):
        a = soup.find("a", href=re.compile(r"/author/"))
        if a:
            info["author"] = _clean(a.get_text())

    info["cover"] = _meta(soup, "og:image")
    info["description"] = _meta(soup, "og:description")
    info["price"] = _meta(soup, "og:price")
    info["currency"] = _meta(soup, "og:currency_code")
    return info


def _parse_hyread(soup):
    """HyRead:og:title 形如「書名 | 作者 | 出版社 | HyRead ebook 電子書店」。"""
    info = {}
    og_title = _meta(soup, "og:title")
    parts = [p.strip() for p in og_title.split("|") if p.strip()]
    parts = [p for p in parts if "HyRead" not in p]
    if parts:
        info["title"] = _clean(parts[0])
    if len(parts) >= 2:
        info["author"] = _clean(parts[1])
    if len(parts) >= 3:
        info["publisher"] = _clean(parts[2])

    info["cover"] = _meta(soup, "og:image")
    info["description"] = _meta(soup, "og:description")
    info["isbn"] = _meta(soup, "books:isbn")
    return info


PARSERS = {
    "readmoo": _parse_readmoo,
    "kobo": _parse_kobo,
    "hyread": _parse_hyread,
}


def _parse_generic(soup):
    """未知平台:盡量用 OG meta 抓。"""
    return {
        "title": re.sub(r"\s*[-|｜].*$", "", _meta(soup, "og:title")),
        "author": _meta(soup, "author") or _meta(soup, "book:author"),
        "cover": _meta(soup, "og:image"),
        "description": _meta(soup, "og:description") or _meta(soup, "description"),
    }


# ---------------------------------------------------------------------------
# 抓取
# ---------------------------------------------------------------------------
def _looks_empty(html):
    """判斷靜態 HTML 是否幾乎空白(可能需 JavaScript 渲染)。"""
    if not html or len(html) < 500:
        return True
    soup = BeautifulSoup(html, "lxml")
    return not (_meta(soup, "og:title") or (soup.title and soup.title.get_text().strip()))


def _fetch_static(url):
    """用 requests Session 抓 HTML(自動跟隨轉址)。失敗時拋出帶狀態碼的錯誤。"""
    sess = requests.Session()
    sess.headers.update(HEADERS)
    resp = sess.get(url, timeout=TIMEOUT, allow_redirects=True)
    if resp.status_code != 200:
        raise ValueError("平台回應 HTTP %d(可能擋下了自動抓取)" % resp.status_code)
    resp.encoding = resp.apparent_encoding or resp.encoding
    return resp.text


def _fetch_rendered_cloak(url):
    """用 CloakBrowser(stealth Chromium,Playwright drop-in)渲染頁面,回傳 HTML。

    需 pip install cloakbrowser(首次執行會自動下載瀏覽器 binary)。
    未安裝時拋出 RuntimeError。
    """
    try:
        from cloakbrowser import launch
    except ImportError as e:
        raise RuntimeError("cloakbrowser 未安裝(pip install cloakbrowser)") from e

    kwargs = {"headless": CLOAK_HEADLESS, "humanize": CLOAK_HUMANIZE}
    if CLOAK_PROXY:
        kwargs["proxy"] = CLOAK_PROXY
    browser = launch(**kwargs)
    try:
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=40000)
        try:
            page.wait_for_selector('meta[property="og:title"]', timeout=10000)
        except Exception:
            pass
        return page.content()
    finally:
        try:
            browser.close()
        except Exception:
            pass


def _fetch_rendered_nodriver(url):
    """用 nodriver(stealth CDP 瀏覽器)渲染頁面,回傳 HTML。

    優點:可無頭執行且較不易被 WAF 偵測。未安裝時拋出 RuntimeError。
    可用 CLOAK_BROWSER_PATH 指定自訂瀏覽器執行檔(如 CloakBrowser)。
    """
    try:
        import nodriver as uc
    except ImportError as e:
        raise RuntimeError("nodriver 未安裝(pip install nodriver)") from e
    import asyncio

    async def _run():
        kwargs = {"headless": NODRIVER_HEADLESS, "lang": "zh-TW"}
        if NODRIVER_BROWSER_PATH:
            kwargs["browser_executable_path"] = NODRIVER_BROWSER_PATH
        browser = await uc.start(**kwargs)
        try:
            page = await browser.get(url)
            # 等待書本 meta 出現(最多約 15 秒)
            try:
                await page.select('meta[property="og:title"]', timeout=15)
            except Exception:
                await page.sleep(3)
            return await page.get_content()
        finally:
            try:
                browser.stop()
            except Exception:
                pass

    # 在獨立的事件迴圈執行(相容 Flask 工作執行緒)
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_run())
    finally:
        try:
            loop.close()
        except Exception:
            pass


def _render(url):
    """統一渲染入口:依序嘗試 CloakBrowser -> nodriver -> Playwright 有頭(保底)。

    任一後端成功且內容非空即回傳;全部失敗才用 Playwright 有頭。
    """
    backends = []
    if USE_CLOAKBROWSER:
        backends.append(_fetch_rendered_cloak)
    if USE_NODRIVER:
        backends.append(_fetch_rendered_nodriver)
    for fn in backends:
        try:
            html = fn(url)
            if html and not _looks_empty(html):
                return html
        except Exception:
            pass  # 該後端未裝或失敗 → 換下一個
    return _fetch_rendered(url)   # Playwright 有頭(已驗證可用)的最終保底


def _fetch_rendered(url):
    """備援:用「有頭」瀏覽器渲染後回傳 HTML。

    重要:實測此網路環境的 WAF 會擋「無頭 (headless)」瀏覽器與帶特殊
    啟動參數的瀏覽器,只放行「乾淨的有頭瀏覽器」。因此這裡刻意用最單純的
    headless=False,不加任何 args(視窗會短暫顯示,屬正常)。
    需先安裝: pip install playwright 並執行 playwright install chromium
    未安裝時拋出 RuntimeError。
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError("Playwright 未安裝") from e

    def _run(**launch):
        with sync_playwright() as p:
            browser = p.chromium.launch(**launch)
            try:
                page = browser.new_page(locale="zh-TW")
                page.goto(url, wait_until="domcontentloaded", timeout=40000)
                try:
                    page.wait_for_selector('meta[property="og:title"]', timeout=10000)
                except Exception:
                    pass
                return page.content()
            finally:
                browser.close()

    # 改為有頭模式 — 系統有 DISPLAY（Xorg / xrdp），但在背景進程需手動設定
    import os
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":10"
    try:
        return _run(headless=False)
    except Exception:
        # 不要 fallback 到 channel="chrome" — 我們用的是 Playwright 的 Chromium，不是系統 Chrome
        raise


def scrape(url):
    """主入口:輸入書本網址,回傳書本資訊 dict。"""
    url = url.strip()
    platform = detect_platform(url)
    parser = PARSERS.get(platform, _parse_generic)

    # 取得書本資訊:先試輕量靜態抓取,「實際解析到書名」才採用;
    # 否則(靜態被擋、需 JavaScript、或內容不足)退回瀏覽器渲染。
    def _try_parse(html):
        if not html:
            return None
        cand = parser(BeautifulSoup(html, "lxml"))
        return cand if cand.get("title") else None

    info = None
    if STATIC_FIRST:
        try:
            info = _try_parse(_fetch_static(url))
        except Exception:
            info = None  # 靜態被擋(403/400)等 → 改用瀏覽器

    if info is None:
        try:
            html = _render(url)
        except RuntimeError as e:
            raise ValueError(
                "無法渲染頁面。請安裝任一渲染後端後重試: "
                "pip install playwright 並執行 playwright install chromium "
                "(或 pip install nodriver / cloakbrowser)。(%s)" % e
            ) from None
        info = parser(BeautifulSoup(html, "lxml"))

    info.setdefault("title", "")
    info.setdefault("author", "")
    info.setdefault("cover", "")
    info.setdefault("publisher", "")
    info.setdefault("description", "")
    info.setdefault("isbn", "")
    info["platform"] = platform
    info["platform_name"] = PLATFORM_NAMES.get(platform, "其他")
    info["url"] = url

    if not info["title"]:
        raise ValueError("無法從此網址解析出書名,請確認網址是否為書本詳細頁。")

    return info


if __name__ == "__main__":
    import sys
    from pprint import pprint
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://ebook.hyread.com.tw/bookDetail.jsp?id=504740"
    pprint(scrape(test_url))
