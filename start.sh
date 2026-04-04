#!/bin/bash

echo "=========================================="
echo "     播客TTS生成器 - 一键启动脚本"
echo "=========================================="
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到python3，请确保Python已安装"
    exit 1
fi

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "[错误] 未找到node，请确保Node.js已安装"
    exit 1
fi

echo "[1/3] 正在启动后端服务..."
echo "     后端地址: http://localhost:8000"
echo ""

# 启动后端服务
cd "$SCRIPT_DIR/backend" || exit 1
python3 run.py &
BACKEND_PID=$!
echo $BACKEND_PID > "$SCRIPT_DIR/.backend.pid"

# 等待后端启动
sleep 3

echo "[2/3] 正在启动前端服务..."
echo "     前端地址: http://localhost:5173"
echo ""

# 启动前端服务
cd "$SCRIPT_DIR/frontend" || exit 1
npm run dev &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$SCRIPT_DIR/.frontend.pid"

# 等待前端启动
sleep 3

echo "[3/3] 服务启动完成！"
echo ""
echo "=========================================="
echo " 后端API文档: http://localhost:8000/docs"
echo " 前端页面:   http://localhost:5173"
echo "=========================================="
echo ""

# 尝试打开浏览器
if command -v open &> /dev/null; then
    # macOS
    open "http://localhost:5173"
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open "http://localhost:5173"
fi

echo "提示: 使用 ./stop.sh 停止服务"
echo ""

# 等待用户输入以保持窗口打开
read -p "按回车键退出此窗口（服务仍在后台运行）..."
