@echo off
chcp 65001 >nul
echo ========================================
echo    SecLab 微服务重新编译脚本
echo ========================================
echo.

echo 正在重新编译所有微服务...
echo.

echo [1/6] 编译Eureka服务注册中心...
cd eureka
call gradlew clean build -x test
cd ..

echo [2/6] 编译Gateway网关服务...
cd gateway
call gradlew clean build -x test
cd ..

echo [3/6] 编译用户服务...
cd user-service
call gradlew clean build -x test
cd ..

echo [4/6] 编译实验模块服务...
cd experiment-module-service
call gradlew clean build -x test
cd ..

echo [5/6] 编译镜像服务...
cd image-service
call gradlew clean build -x test
cd ..

echo [6/6] 编译Docker服务...
cd docker-service
call gradlew clean build -x test
cd ..

echo.
echo ========================================
echo    所有微服务编译完成！
echo ========================================
echo.
echo 接下来请重新构建Docker镜像并启动服务：
echo 1. 构建Docker镜像: .\rebuild-services.bat
echo 2. 启动所有服务: .\start-all-services.bat
echo.
pause 