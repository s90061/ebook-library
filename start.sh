#!/usr/bin/env bash
# ===== Ebook Library - Linux / Raspberry Pi 啟動腳本 =====
# 用法: bash start.sh   (或 chmod +x start.sh 後 ./start.sh)
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

# 3) 安裝 Playwright 的 Chromium(首次;ARM64/Pi 亦支援)
echo "安裝 Chromium (Playwright)..."
python -m playwright install chromium || true
# 若缺系統函式庫,請執行: sudo python -m playwright install-deps

# 4) 啟動伺服器
#    無桌面(Pi 當伺服器)時,若某網站需要「有頭」瀏覽器,用 Xvfb 提供虛擬螢幕
echo "啟動伺服器: http://127.0.0.1:5000"
if [ -z "${DISPLAY:-}" ] && command -v xvfb-run >/dev/null 2>&1; then
  echo "(未偵測到顯示器 -> 使用 xvfb-run 虛擬螢幕)"
  exec xvfb-run -a python app.py
else
  exec python app.py
fi
