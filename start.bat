@chcp 65001 >nul
@cd /d "%~dp0"

start "backend" cmd /c "cd /d %~dp0backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8765"

ping 127.0.0.1 -n 3 >nul

"%~dp0node_modules\electron\dist\electron.exe" . --dev
pause
