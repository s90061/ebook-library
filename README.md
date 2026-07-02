# 📚 電子書書庫 Ebook Library

一個跑在自己電腦（或 Raspberry Pi）上的本地端電子書收藏庫。**貼上書本網址就自動抓取封面、書名、作者等資訊**並加入書庫；以卡片方式呈現，點擊卡片可看完整書籍資料與平台連結。

支援平台：**Readmoo 讀墨**、**Kobo**、**HyRead**。

---

## 功能

- 貼上書本網址即自動抓取：封面、書名、作者、出版社、ISBN、簡介
- 暗色主題卡片式書庫，顯示封面 / 書名 / 平台標籤 / 作者
- 點擊卡片滑出詳細面板，可調整閱讀狀態（欲讀／閱讀中／完讀）、評分、筆記
- 一書多平台：記錄同一本書在多個電子書平台的連結與價格
- 支援搜尋與狀態篩選
- 自動封面抓取（從博客來補封面）
- 伺服器僅綁定本機，不對外開放

---

## 快速開始

### Windows

雙擊 **`start.bat`**（自動建立環境、安裝套件與 Chromium、啟動並開啟瀏覽器）。

### Linux / Raspberry Pi 5 (Ubuntu, ARM64)

```bash
bash start.sh
```

首次請先安裝系統相依：

```bash
sudo apt update
sudo apt install -y python3-venv xvfb
```

啟動後開啟瀏覽器前往 <http://127.0.0.1:8086>。

---

## 使用方式

1. 點擊右上角「+ 新增」按鈕
2. 貼上書本頁面網址，例如：
   - `https://readmoo.com/book/210481242000101`
   - `https://ebook.hyread.com.tw/bookDetail.jsp?id=504740`
3. 自動填入書名、作者、出版社、ISBN 等資訊
4. 點擊「儲存」即加入書庫

---

## 技術架構

### 兩種後端可選

| 版本 | 檔案 | 說明 |
| --- | --- | --- |
| **FastAPI + SQLite (v2)** | `main.py` | 現代化版本，支援狀態管理、評分、筆記、多平台連結（**建議使用**） |
| **Flask + JSON (v1)** | `app.py` | 原始版本，輕量、相容性高 |

### 抓取引擎（scraper.py）

採用「輕量優先、瀏覽器保底」的分層策略：

1. **靜態抓取 (requests)** — 解析 JSON-LD 與 Open Graph meta
2. **CloakBrowser** — stealth Chromium，可繞過多數 WAF
3. **nodriver + CloakBrowser binary** — 繞過 HyRead Tomcat WAF（HTTP 400）
4. **Playwright 有頭瀏覽器** — 最終保底（透過 Xvfb 支援無桌面環境）

各後端可在 `scraper.py` 最上方常數切換。

---

## API

| 方法 | 路徑 | 說明 |
| --- | --- | --- |
| `GET` | `/api/books` | 取得所有書本（支援 `?status=` 與 `?search=` 過濾） |
| `GET` | `/api/books/<id>` | 取得單一書本詳細資訊（含平台連結） |
| `POST` | `/api/books` | 新增書本 |
| `PUT` | `/api/books/<id>` | 更新書本（狀態、評分、筆記） |
| `DELETE` | `/api/books/<id>` | 刪除書本 |
| `POST` | `/api/books/<id>/platforms` | 新增平台連結 |

---

## 專案結構

```
ebook-library/
├── main.py             # FastAPI 伺服器 (v2, 建議使用)
├── app.py              # Flask 伺服器 (v1, 備用)
├── scraper.py          # 跨平台書本資訊抓取器
├── init_db.py          # 資料庫初始化
├── templates/
│   └── index.html      # 前端 UI
├── static/
│   ├── css/style.css   # 暗色主題樣式
│   └── js/app.js       # 前端邏輯
├── requirements.txt    # 相依套件
├── start.bat           # Windows 一鍵啟動
├── start.sh            # Linux / Raspberry Pi 啟動
├── diagnose.py         # 診斷工具
├── test_browser.py     # 瀏覽器測試
├── test_cloak.py       # CloakBrowser 測試
├── test_nodriver.py    # nodriver 測試
├── fix_nodriver.py     # nodriver 修補
├── library.db          # 書庫資料庫（自動產生，不進版控）
└── LICENSE             # MIT 授權
```

---

## 授權

MIT License，詳見 [LICENSE](LICENSE)。