@echo off
chcp 65001 >nul
echo ==========================================
echo      播客TTS生成器 - 停止服务脚本
echo ==========================================
echo.

echo 正在停止后端服务...
taskkill /F /FI "WINDOWTITLE eq 后端服务*" 2>nul
taskkill /F /IM python.exe 2>nul
echo [OK] 后端服务已停止
echo.

echo 正在停止前端服务...
taskkill /F /FI "WINDOWTITLE eq 前端服务*" 2>nul
taskkill /F /IM node.exe 2>nul
echo [OK] 前端服务已停止
echo.

echo ==========================================
echo          所有服务已停止
echo ==========================================
pause
