@echo off
REM ===== Ebook Library - one click startup (Windows) =====
REM Uses your system Python directly (no virtual environment).
REM Installs Playwright + Chromium so blocked networks can render via a real browser.
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ==================================================
echo   Ebook Library - Startup
echo ==================================================

REM --- 1. Find Python (try "python", then "py") ---
set "PYCMD=python"
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found. Install Python 3 from:
        echo         https://www.python.org/downloads/
        echo         Tick "Add Python to PATH" during installation.
        pause
        exit /b 1
    ) else (
        set "PYCMD=py"
    )
)

REM --- 2. Install required packages ---
echo Installing packages, please wait...
%PYCMD% -m pip install --user Flask requests beautifulsoup4 lxml playwright
if errorlevel 1 (
    echo [ERROR] Package install failed. Check your internet connection and retry.
    pause
    exit /b 1
)

REM --- 3. Install the Chromium browser used for rendering (first run downloads ~150MB) ---
echo Ensuring Chromium browser is installed...
%PYCMD% -m playwright install chromium

REM --- 4. Start server and open browser ---
echo.
echo Starting server at http://127.0.0.1:5000
echo Close this window to stop the server.
echo.
start "" http://127.0.0.1:5000
%PYCMD% app.py
pause
