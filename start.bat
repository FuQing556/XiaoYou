@echo off
title 小悠 v2

echo ================================
echo   小悠 v2 — Starting...
echo ================================

:: 检查 .env
if not exist ".env" (
    echo [WARN] .env not found. Create one with: DEEPSEEK_API_KEY=your_key
)

:: 启动后端
echo [1/2] Starting backend...
start "小悠后端" cmd /c "cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8765"

:: 等后端启动
timeout /t 2 /nobreak >nul

:: 安装依赖 (首次)
if not exist "node_modules\electron" (
    echo [INFO] Installing Electron...
    npm install electron --save-dev
)

:: 启动前端
echo [2/2] Starting frontend...
npx electron . --dev

echo.
echo 小悠已关闭.
pause
