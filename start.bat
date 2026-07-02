@echo off
REM ===== Ebook Library - one click startup (Windows) =====
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ==================================================
echo   Ebook Library - Startup
echo ==================================================

REM --- 1. Find Python ---
set "PYCMD=python"
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found. Install Python 3 from:
        echo         https://www.python.org/downloads/
        pause
        exit /b 1
    ) else (
        set "PYCMD=py"
    )
)

REM --- 2. Install packages ---
echo Installing packages, please wait...
%PYCMD% -m pip install --user Flask fastapi uvicorn jinja2 requests beautifulsoup4 lxml
if errorlevel 1 (
    echo [ERROR] Package install failed.
    pause
    exit /b 1
)

REM --- 3. Init DB ---
%PYCMD% init_db.py

REM --- 4. Start server and open browser ---
echo.
echo Starting server at http://127.0.0.1:8086
echo.
start "" http://127.0.0.1:8086
%PYCMD% main.py
pause