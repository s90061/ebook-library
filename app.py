# -*- coding: utf-8 -*-
"""
app.py — 本地端電子書書庫 Flask 伺服器

功能:
  GET  /                 首頁(卡片式書庫介面)
  GET  /api/books        取得所有書本
  POST /api/books        新增書本(body: {"url": "..."}),自動抓取資訊
  DELETE /api/books/<id> 刪除書本

資料以 library.json 儲存於本檔同目錄。
"""

import json
import os
import threading
import uuid
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_from_directory

import scraper

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "library.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__)
_lock = threading.Lock()  # 避免多請求同時寫檔造成資料毀損


# ---------------------------------------------------------------------------
# JSON 資料存取
# ---------------------------------------------------------------------------
def load_books():
    """讀取書庫;檔案不存在時回傳空清單。"""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        return []


def save_books(books):
    """將書庫寫回 JSON 檔(格式化、保留中文)。"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/css/style.css")
def css():
    """共用前端樣板 (templates/index.html) 走 /api/css/... 路徑取資源,
    這裡對齊 main.py (FastAPI) 的路由,讓 v1/v2 都能正常載入樣式與腳本。"""
    return send_from_directory(os.path.join(STATIC_DIR, "css"), "style.css", mimetype="text/css")


@app.route("/api/js/app.js")
def js():
    return send_from_directory(os.path.join(STATIC_DIR, "js"), "app.js", mimetype="application/javascript")


@app.route("/api/books", methods=["GET"])
def get_books():
    """回傳所有書本,最新加入的排在最前面。"""
    books = load_books()
    return jsonify(sorted(books, key=lambda b: b.get("added_at", ""), reverse=True))


@app.route("/api/books", methods=["POST"])
def add_book():
    """新增書本:接收網址 → 抓取資訊 → 存入書庫。"""
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()

    if not url:
        return jsonify({"error": "請提供書本網址。"}), 400
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "網址格式不正確,需以 http:// 或 https:// 開頭。"}), 400

    with _lock:
        books = load_books()

        # 避免重複加入相同網址
        for b in books:
            if b.get("url") == url:
                return jsonify({"error": "這本書已經在書庫中了。", "book": b}), 409

        # 抓取書本資訊
        try:
            info = scraper.scrape(url)
        except Exception as e:  # noqa: BLE001 抓取失敗一律回報給前端
            return jsonify({"error": f"抓取失敗:{e}"}), 502

        info["id"] = uuid.uuid4().hex
        info["added_at"] = datetime.now().isoformat(timespec="seconds")

        books.append(info)
        save_books(books)

    return jsonify(info), 201


@app.route("/api/books/<book_id>", methods=["DELETE"])
def delete_book(book_id):
    """依 id 刪除書本。"""
    with _lock:
        books = load_books()
        new_books = [b for b in books if b.get("id") != book_id]
        if len(new_books) == len(books):
            return jsonify({"error": "找不到這本書。"}), 404
        save_books(new_books)
    return jsonify({"ok": True})


if __name__ == "__main__":
    # 只綁定本機,避免對外開放
    print("電子書書庫已啟動 → 請用瀏覽器開啟 http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
