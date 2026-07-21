@echo off
cd /d "%~dp0"
title 小悠 v2

echo ================================
echo   小悠 v2 — Starting...
echo ================================

:: Check .env
if not exist ".env" (
    echo [WARN] .env not found. Create one with: DEEPSEEK_API_KEY=your_key
)

:: Start backend
echo [1/2] Starting backend...
start "xiaoyou-backend" /min cmd /c "cd /d %~dp0backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8765"

:: Wait for backend
echo Waiting for backend...
timeout /t 3 /nobreak >nul

:: Start frontend
echo [2/2] Starting frontend...
call npx electron . --dev

echo.
echo 小悠已关闭.
pause
