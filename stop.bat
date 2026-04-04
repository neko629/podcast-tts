@echo off
chcp 65001 >nul
echo ==========================================
echo      Podcast TTS Generator - Stop Script
echo ==========================================
echo.

echo Stopping backend service...
taskkill /F /FI "WINDOWTITLE eq Backend*" 2>nul
taskkill /F /IM python.exe 2>nul
echo [OK] Backend stopped
echo.

echo Stopping frontend service...
taskkill /F /FI "WINDOWTITLE eq Frontend*" 2>nul
taskkill /F /IM node.exe 2>nul
echo [OK] Frontend stopped
echo.

echo ==========================================
echo          All services stopped
echo ==========================================
pause
