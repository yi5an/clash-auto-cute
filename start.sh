#!/bin/bash

# Clash Auto Switch 启动脚本

echo "======================================"
echo "Clash Auto Switch"
echo "======================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python 3"
    echo "请先安装 Python 3.8 或更高版本"
    exit 1
fi

echo "✓ Python 版本: $(python3 --version)"
echo ""

# 检查依赖
echo "检查依赖..."
python3 -c "import flask, requests, flask_socketio" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠ 未安装依赖，正在安装..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "错误: 依赖安装失败"
        exit 1
    fi
fi
echo "✓ 依赖已安装"
echo ""

# 检查 Clash
echo "检查 Clash API..."
curl -s http://127.0.0.1:9090 > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "⚠ 警告: 无法连接到 Clash API (http://127.0.0.1:9090)"
    echo "请确保 Clash 正在运行并且 RESTful API 已启用"
    echo ""
    read -p "是否继续启动? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✓ Clash API 可用"
fi
echo ""

# 启动服务
echo "启动 Clash Auto Switch 服务..."
echo "Web 界面: http://127.0.0.1:5000"
echo ""
echo "按 Ctrl+C 停止服务"
echo "======================================"
echo ""

python3 app.py
