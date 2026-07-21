@echo off
cd /d "%~dp0"
title XiaoYou v2

echo ================================
echo   XiaoYou v2
echo ================================
echo.

echo [1/2] Starting backend on port 8765...
start "xiaoyou-backend" cmd /c "cd /d %~dp0backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 && pause"

ping 127.0.0.1 -n 3 >nul

echo [2/2] Starting frontend...
echo.
"%~dp0node_modules\electron\dist\electron.exe" "%~dp0" --dev
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Electron exited with code %errorlevel%
)

echo.
echo XiaoYou closed.
pause
