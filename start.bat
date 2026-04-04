@echo off
chcp 65001 >nul
echo ==========================================
echo      播客TTS生成器 - 一键启动脚本
echo ==========================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请确保Python已安装并添加到PATH
    pause
    exit /b 1
)

:: 检查Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Node.js，请确保Node.js已安装并添加到PATH
    pause
    exit /b 1
)

echo [1/3] 正在启动后端服务...
echo     后端地址: http://localhost:8000
echo.
start "后端服务" cmd /c "cd /d "%~dp0backend" && python run.py"

:: 等待后端启动
timeout /t 3 /nobreak >nul

echo [2/3] 正在启动前端服务...
echo     前端地址: http://localhost:5173
echo.
start "前端服务" cmd /c "cd /d "%~dp0frontend" && npm run dev"

:: 等待前端启动
timeout /t 3 /nobreak >nul

echo [3/3] 服务启动完成！
echo.
echo ==========================================
echo  后端API文档: http://localhost:8000/docs
echo  前端页面:   http://localhost:5173
echo ==========================================
echo.
echo 按任意键打开浏览器访问前端页面...
pause >nul

:: 打开浏览器
start http://localhost:5173

echo.
echo 提示: 关闭此窗口不会停止服务，请手动关闭后台的CMD窗口
echo.
pause
