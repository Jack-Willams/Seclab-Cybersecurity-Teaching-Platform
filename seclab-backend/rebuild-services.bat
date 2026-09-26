@echo off
chcp 65001 >nul
echo ========================================
echo    SecLab 微服务Docker镜像重建脚本
echo ========================================
echo.

echo 正在重新构建所有微服务镜像...
echo.

echo [1/6] 构建Eureka服务注册中心...
cd eureka
docker build -t saclab-eureka .
cd ..

echo [2/6] 构建Gateway网关服务...
cd gateway
docker build -t saclab-gateway .
cd ..

echo [3/6] 构建用户服务...
cd user-service
docker build -t saclab-user-service .
cd ..

echo [4/6] 构建实验模块服务...
cd experiment-module-service
docker build -t saclab-experiment-module-service .
cd ..

echo [5/6] 构建镜像服务...
cd image-service
docker build -t saclab-image-service .
cd ..

echo [6/6] 构建Docker服务...
cd docker-service
docker build -t saclab-docker-service .
cd ..

echo.
echo ========================================
echo    所有微服务镜像构建完成！
echo ========================================
echo.
echo 启动所有服务: .\start-all-services.bat
echo.
pause 