#!/bin/bash

echo "=========================================="
echo "     播客TTS生成器 - 一键重启脚本"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "正在停止运行中的服务（如有）..."

if [ -f "$SCRIPT_DIR/.backend.pid" ]; then
    kill $(cat "$SCRIPT_DIR/.backend.pid") 2>/dev/null
    rm -f "$SCRIPT_DIR/.backend.pid"
fi
pkill -f "venv/bin/python.*run.py" 2>/dev/null

if [ -f "$SCRIPT_DIR/.frontend.pid" ]; then
    kill $(cat "$SCRIPT_DIR/.frontend.pid") 2>/dev/null
    rm -f "$SCRIPT_DIR/.frontend.pid"
fi
pkill -f "vite" 2>/dev/null

echo "[OK] 服务已停止"
echo ""

sleep 2

echo "[1/3] 正在启动后端服务..."
echo "     后端地址: http://localhost:8000"
echo ""

cd "$SCRIPT_DIR/backend" || exit 1
"$SCRIPT_DIR/venv/bin/python" run.py &
BACKEND_PID=$!
echo $BACKEND_PID > "$SCRIPT_DIR/.backend.pid"

sleep 3

echo "[2/3] 正在启动前端服务..."
echo "     前端地址: http://localhost:5173"
echo ""

cd "$SCRIPT_DIR/frontend" || exit 1
npm run dev &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$SCRIPT_DIR/.frontend.pid"

sleep 3

echo "[3/3] 服务启动完成！"
echo ""
echo "=========================================="
echo " 后端API文档: http://localhost:8000/docs"
echo " 前端页面:   http://localhost:5173"
echo "=========================================="
echo ""

if command -v open &> /dev/null; then
    open "http://localhost:5173"
elif command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:5173"
fi

echo "提示: 使用 ./stop.sh 停止服务"
echo ""

read -p "按回车键退出此窗口（服务仍在后台运行）..."
