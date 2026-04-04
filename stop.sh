#!/bin/bash

echo "=========================================="
echo "     播客TTS生成器 - 停止服务脚本"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "正在停止后端服务..."
if [ -f "$SCRIPT_DIR/.backend.pid" ]; then
    BACKEND_PID=$(cat "$SCRIPT_DIR/.backend.pid")
    kill $BACKEND_PID 2>/dev/null
    rm -f "$SCRIPT_DIR/.backend.pid"
    echo "[OK] 后端服务已停止"
else
    # 尝试查找并杀死Python进程
    pkill -f "python.*run.py" 2>/dev/null
    echo "[OK] 后端服务已停止"
fi
echo ""

echo "正在停止前端服务..."
if [ -f "$SCRIPT_DIR/.frontend.pid" ]; then
    FRONTEND_PID=$(cat "$SCRIPT_DIR/.frontend.pid")
    kill $FRONTEND_PID 2>/dev/null
    rm -f "$SCRIPT_DIR/.frontend.pid"
    echo "[OK] 前端服务已停止"
else
    # 尝试查找并杀死npm/vite进程
    pkill -f "vite" 2>/dev/null
    echo "[OK] 前端服务已停止"
fi
echo ""

echo "=========================================="
echo "         所有服务已停止"
echo "=========================================="
