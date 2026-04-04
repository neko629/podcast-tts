@echo off
chcp 65001 >nul
echo ==========================================
echo     Podcast TTS Generator - Restart Script
echo ==========================================
echo.

echo Stopping running services (if any)...
taskkill /F /FI "WINDOWTITLE eq Backend*" 2>nul
taskkill /F /FI "WINDOWTITLE eq Frontend*" 2>nul
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
echo [OK] Services stopped
echo.

timeout /t 2 /nobreak >nul

echo [1/3] Starting backend service...
echo     Backend: http://localhost:8000
echo.
start "Backend" cmd /c "cd /d "%~dp0backend" && "%~dp0venv\Scripts\python.exe" run.py"

timeout /t 3 /nobreak >nul

echo [2/3] Starting frontend service...
echo     Frontend: http://localhost:5173
echo.
start "Frontend" cmd /c "cd /d "%~dp0frontend" && npm run dev"

timeout /t 3 /nobreak >nul

echo [3/3] Services started!
echo.
echo ==========================================
echo  Backend API docs: http://localhost:8000/docs
echo  Frontend:        http://localhost:5173
echo ==========================================
echo.
echo Press any key to open browser...
pause >nul

start http://localhost:5173

echo.
echo Note: Closing this window won't stop services.
echo       Please manually close the background CMD windows.
echo.
pause
