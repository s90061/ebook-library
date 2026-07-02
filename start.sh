#!/usr/bin/env bash
# ===== Ebook Library - Linux / Raspberry Pi 啟動腳本 =====
set -e
cd "$(dirname "$0")"

# 1) 建立/啟用虛擬環境
if [ ! -d ".venv" ]; then
  echo "建立虛擬環境 (首次)..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# 2) 安裝套件
echo "安裝相依套件..."
pip install --upgrade pip >/dev/null
pip install -r requirements.txt

# 3) 安裝 Playwright 的 Chromium（選裝，抓取保底用）
echo "安裝 Chromium (Playwright)..."
python -m playwright install chromium 2>/dev/null || true

# 4) 初始化資料庫
python init_db.py

# 5) 啟動伺服器
PORT=8086
echo "啟動伺服器: http://127.0.0.1:$PORT"
exec python main.py