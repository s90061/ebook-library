# 📚 電子書書庫 Ebook Library

一個跑在自己電腦(或 Raspberry Pi)上的本地端電子書收藏庫。**貼上書本網址就自動抓取封面、書名、作者等資訊**並加入書庫;以卡片方式呈現,點擊卡片可看完整書籍資料。

支援平台:**Readmoo 讀墨**、**Kobo**、**HyRead**。

---

## 功能

- 貼上書本網址即自動抓取:封面、書名、作者、出版社、ISBN、簡介
- 卡片式書庫:顯示封面 / 書名 / 購買平台 / 作者
- 點擊卡片檢視完整資料,可「前往購買頁」或「刪除」
- 自動去重、資料以 `library.json` 儲存(純文字、可備份)
- 伺服器僅綁定本機 `127.0.0.1`,不對外開放

---

## 安裝與啟動

### Windows

雙擊 **`start.bat`**(自動建立環境、安裝套件與 Chromium、啟動並開啟瀏覽器)。

或手動:

```bash
pip install -r requirements.txt
playwright install chromium
python app.py
```

### Linux / Raspberry Pi 5 (Ubuntu, ARM64)

```bash
bash start.sh
```

`start.sh` 會建立虛擬環境、安裝套件與 Chromium,並在**無桌面環境**時自動用 `Xvfb` 提供虛擬螢幕(某些網站需要「有頭」瀏覽器才抓得到)。首次請先安裝系統相依:

```bash
sudo apt update
sudo apt install -y python3-venv xvfb
# 若 Chromium 缺函式庫:
sudo .venv/bin/python -m playwright install-deps
```

啟動後開啟瀏覽器前往 <http://127.0.0.1:5000>。

---

## 使用方式

1. 在上方輸入框貼上書本頁面網址,例如:
   - `https://readmoo.com/book/210482520000101`
   - `https://www.kobo.com/tw/zh/ebook/6bsbvQwEmD2rVu9Oc0o4Ww`
   - `https://ebook.hyread.com.tw/bookDetail.jsp?id=504740`
2. 按「新增書本」(或 Enter),自動抓取並加入書庫。
3. 點卡片檢視詳細資料。

---

## 運作原理

抓取採「輕量優先、瀏覽器保底」的分層策略:

1. **靜態抓取(requests)**:解析頁面的 JSON-LD 結構化資料與 Open Graph meta,再依各平台格式客製化切割書名/作者/出版社。多數網路環境到這步就足夠,不需開瀏覽器。
2. **瀏覽器渲染(備援)**:若靜態被擋(例如企業網路的 WAF 回 400/403/503)或內容需 JavaScript,才改用瀏覽器渲染,依序嘗試:
   - **CloakBrowser**(選配,stealth Chromium)
   - **nodriver**(選配,stealth CDP)
   - **Playwright 有頭瀏覽器**(保底,最穩定)

各後端可在 `scraper.py` 最上方的常數切換(`STATIC_FIRST`、`USE_CLOAKBROWSER`、`USE_NODRIVER`、`CLOAK_HEADLESS` 等)。

### 關於企業網路 / WAF

部分網路(如公司網路)的防火牆 / WAF 會阻擋「程式化請求」與「無頭瀏覽器」,只放行真正的**有頭**瀏覽器。實測中 `requests`、`curl`、無頭瀏覽器、甚至 stealth 方案都可能被擋,唯有**有頭瀏覽器**能成功。此時:
- 桌面環境:直接用 Playwright 有頭(會短暫彈出視窗)。
- 無桌面伺服器(如 Pi):用 `Xvfb` 提供虛擬螢幕跑「有頭」瀏覽器(`start.sh` 已內建處理)。

在不受限的網路上,靜態抓取即可完成,完全不需開瀏覽器。

---

## 選配:更強的反偵測後端

```bash
# CloakBrowser(pip 套件,首次自動下載 stealth Chromium)
pip install cloakbrowser

# nodriver
pip install nodriver
```

在 `scraper.py` 設定 `USE_CLOAKBROWSER=True` 或 `USE_NODRIVER=True` 即會優先嘗試。
> 註:CloakBrowser 目前主要提供 x86_64 binary,ARM(Pi)可能不適用。

---

## API

| 方法 | 路徑 | 說明 |
| --- | --- | --- |
| `GET` | `/api/books` | 取得所有書本(依加入時間新到舊) |
| `POST` | `/api/books` | 新增書本,body:`{"url": "書本網址"}` |
| `DELETE` | `/api/books/<id>` | 依 id 刪除書本 |

---

## 專案結構

```
ebook-library/
├── app.py             # Flask 伺服器與 API
├── scraper.py         # 三平台書本資訊抓取器(靜態 + 多種瀏覽器後端)
├── templates/
│   └── index.html     # 卡片式前端(單檔,含 CSS/JS)
├── requirements.txt   # 相依套件
├── start.bat          # Windows 一鍵啟動
├── start.sh           # Linux / Raspberry Pi 啟動(含 Xvfb)
├── diagnose.py        # 診斷:檢視某網址渲染後的 meta / JSON-LD
├── test_browser.py    # 比較不同瀏覽器設定是否能通過
├── test_cloak.py      # 測試 CloakBrowser
├── test_nodriver.py   # 測試 nodriver
└── fix_nodriver.py    # 修補 nodriver 在 Python 3.14 的編碼問題
```

---

## 疑難排解

- **抓取失敗:HTTP 400 / 403 / 503** — 平台擋下程式化請求。確認已裝 Playwright 與 Chromium;無桌面伺服器請用 `start.sh`(Xvfb)以有頭模式抓取。
- **抓不到書名** — 網址可能不是「書本詳細頁」,或平台改版。用 `python diagnose.py "網址"` 檢視實際收到的內容。
- **Playwright 逾時** — 網路較慢或頁面資源多,重試通常即可。

---

## 授權

MIT License,詳見 [LICENSE](LICENSE)。
