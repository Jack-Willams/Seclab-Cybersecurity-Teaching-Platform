@echo off
chcp 65001 >nul
echo ========================================
echo    更新所有微服务Dockerfile为Java 17
echo ========================================
echo.

set SERVICES=eureka gateway user-service experiment-module-service image-service docker-service

for %%s in (%SERVICES%) do (
    echo 更新 %%s 的Dockerfile...
    cd %%s
    if exist Dockerfile (
        powershell -Command "(Get-Content Dockerfile) -replace 'FROM openjdk:21-jdk-slim', 'FROM openjdk:17-jdk-slim' -replace 'FROM eclipse-temurin:21-jdk', 'FROM eclipse-temurin:17-jdk' | Set-Content Dockerfile"
        echo %%s Dockerfile已更新
    ) else (
        echo 警告: 找不到 %%s 的Dockerfile
    )
    cd ..
)

echo.
echo ========================================
echo    所有Dockerfile已更新为Java 17
echo ========================================
echo.
echo 接下来请重新构建所有微服务镜像: .\rebuild-services.bat
echo.
pause 