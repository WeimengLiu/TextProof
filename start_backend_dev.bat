@echo off
chcp 65001 >nul
setlocal

REM 启动后端服务脚本（开发模式 - 热重载）（Windows）
REM 使用 UTF-8，避免 .env / 中文路径等被 gbk 解码报错
set PYTHONUTF8=1

cd /d "%~dp0backend"

REM 检查虚拟环境
if not exist "venv" (
    echo 创建 Python 虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo 请确保已安装 Python 并加入 PATH
        pause
        exit /b 1
    )
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 安装依赖
echo 安装依赖...
pip install -r requirements.txt

REM 检查 .env 文件
if not exist ".env" (
    echo 警告: .env 文件不存在，请从 .env.example 复制并配置
    if exist ".env.example" (
        copy .env.example .env
        echo 已创建 .env 文件，请编辑并填入 API 密钥
    )
)

echo 启动后端服务（开发模式 - 热重载）...
echo 代码修改后会自动重启服务
python main.py --dev

pause
