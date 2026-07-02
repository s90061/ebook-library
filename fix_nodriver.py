# -*- coding: utf-8 -*-
"""修補 nodriver 在 Python 3.14 的編碼問題(非 UTF-8 原始碼)。
用法: python fix_nodriver.py
會掃描 nodriver 套件內所有 .py,將無法以 UTF-8 解碼的檔案
以 latin-1 讀入、重新存成 UTF-8(這些多為自動產生的 CDP 檔,僅少數符號非 ASCII)。
"""
import os
import nodriver

root = os.path.dirname(nodriver.__file__)
print("nodriver 路徑:", root)
fixed = 0
scanned = 0
for dirpath, _, files in os.walk(root):
    for fn in files:
        if not fn.endswith(".py"):
            continue
        path = os.path.join(dirpath, fn)
        scanned += 1
        with open(path, "rb") as f:
            data = f.read()
        try:
            data.decode("utf-8")
            continue  # 已是合法 UTF-8,略過
        except UnicodeDecodeError:
            pass
        # 以 latin-1 解碼(不會失敗),再存成 UTF-8
        text = data.decode("latin-1")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        fixed += 1
        print("  已修補:", os.path.relpath(path, root))

print(f"掃描 {scanned} 個 .py,修補 {fixed} 個。")
# 驗證是否可以匯入
try:
    import importlib
    importlib.reload(nodriver)
    import nodriver as uc  # noqa
    print("nodriver 現在可以匯入 ✅")
except Exception as e:
    print("仍無法匯入:", repr(e))
    print("建議直接改用 Playwright 有頭(scraper.py 已預設如此)。")
