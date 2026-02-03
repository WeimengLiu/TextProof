@echo off
chcp 65001 >nul
setlocal

REM 启动前端服务脚本（Windows）

cd /d "%~dp0frontend"

REM 检查 node_modules
if not exist "node_modules" (
    echo 安装依赖...
    call npm install
)

echo 启动前端服务...
call npm run dev

pause
