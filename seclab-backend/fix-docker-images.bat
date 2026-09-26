@echo off
chcp 65001 >nul
echo ========================================
echo    修复Docker镜像问题
echo ========================================
echo.

set SERVICES=eureka gateway user-service experiment-module-service image-service docker-service

for %%s in (%SERVICES%) do (
    echo 更新 %%s 的Dockerfile...
    cd %%s
    if exist Dockerfile (
        echo 备份原始Dockerfile...
        copy Dockerfile Dockerfile.bak
        
        echo 修改Dockerfile为使用可用的Java镜像...
        
        echo FROM openjdk:17-jdk-slim > Dockerfile.new
        echo WORKDIR /app >> Dockerfile.new
        echo COPY build/libs/*.jar app.jar >> Dockerfile.new
        
        if "%%s"=="eureka" (
            echo EXPOSE 8761 >> Dockerfile.new
        ) else if "%%s"=="gateway" (
            echo EXPOSE 8085 >> Dockerfile.new
        ) else if "%%s"=="user-service" (
            echo EXPOSE 8081 >> Dockerfile.new
        ) else if "%%s"=="experiment-module-service" (
            echo EXPOSE 8082 >> Dockerfile.new
        ) else if "%%s"=="image-service" (
            echo EXPOSE 8083 >> Dockerfile.new
        ) else if "%%s"=="docker-service" (
            echo EXPOSE 8084 >> Dockerfile.new
        )
        
        echo ENTRYPOINT ["java", "-jar", "app.jar"] >> Dockerfile.new
        
        move /y Dockerfile.new Dockerfile
        echo %%s Dockerfile已更新
    ) else (
        echo 警告: 找不到 %%s 的Dockerfile
    )
    cd ..
)

echo.
echo ========================================
echo    所有Dockerfile已更新为可用的镜像源
echo ========================================
echo.
echo 接下来请执行以下步骤：
echo 1. 运行 .\fix-kotlin-jvm.bat 修复Kotlin JVM版本问题
echo 2. 运行 .\rebuild-all.bat 重新编译所有微服务
echo 3. 运行 .\rebuild-services.bat 重新构建Docker镜像
echo 4. 运行 .\start-all-services.bat 启动所有服务
echo.
pause 