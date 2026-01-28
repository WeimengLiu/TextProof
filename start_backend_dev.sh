#!/bin/bash

# 启动后端服务脚本（开发模式 - 热重载）

cd "$(dirname "$0")/backend"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "警告: .env 文件不存在，请从 .env.example 复制并配置"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "已创建 .env 文件，请编辑并填入API密钥"
    fi
fi

# 启动服务（开发模式）
echo "启动后端服务（开发模式 - 热重载）..."
echo "代码修改后会自动重启服务"
python main.py --dev
