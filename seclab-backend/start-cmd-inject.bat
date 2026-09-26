@echo off
REM 停止并移除可能已存在的容器
cd /d %~dp0\command-inject
docker-compose down 2>nul

REM 启动命令注入靶机
docker-compose up -d

REM 获取容器的端口映射
for /f "tokens=2 delims=:" %%i in ('docker-compose port web 80') do set PORT=%%i

REM 输出靶机访问URL
echo {"success":true,"data":{"url":"http://localhost:%PORT%"}} 