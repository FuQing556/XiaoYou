@echo off
cd /d "%~dp0"
title 小悠 v2

echo ================================
echo   小悠 v2
echo ================================
echo.

:: 1. Backend
echo [1/2] Starting backend on port 8765...
start "xiaoyou-backend" cmd /c "cd /d %~dp0backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 && pause"

:: 2. Wait
ping 127.0.0.1 -n 3 >nul

:: 3. Frontend
echo [2/2] Starting frontend...
echo.
"%~dp0node_modules\electron\dist\electron.exe" "%~dp0" --dev
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Electron failed (code: %errorlevel%)
)

echo.
echo 小悠已关闭.
pause
