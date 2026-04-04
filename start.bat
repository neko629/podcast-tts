@echo off
chcp 65001 >nul
echo ==========================================
echo      Podcast TTS Generator - Startup Script
echo ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not found. Please install Python and add to PATH
    pause
    exit /b 1
)

:: Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Node.js not found. Please install Node.js and add to PATH
    pause
    exit /b 1
)

echo [1/3] Starting backend service...
echo     Backend: http://localhost:8000
echo.
start "Backend" cmd /c "cd /d "%~dp0backend" && "%~dp0venv\Scripts\python.exe" run.py"

:: Wait for backend
timeout /t 3 /nobreak >nul

echo [2/3] Starting frontend service...
echo     Frontend: http://localhost:5173
echo.
start "Frontend" cmd /c "cd /d "%~dp0frontend" && npm run dev"

:: Wait for frontend
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

:: Open browser
start http://localhost:5173

echo.
echo Note: Closing this window won't stop services.
echo       Please manually close the background CMD windows.
echo.
pause
