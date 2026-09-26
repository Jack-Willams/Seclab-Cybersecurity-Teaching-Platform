@echo off
chcp 65001 >nul
echo ========================================
echo    SecLab 系统综合修复和部署脚本
echo ========================================
echo.

echo 第1步: 修复Kotlin JVM目标版本...
call .\fix-kotlin-jvm.bat

echo 第2步: 修复Docker镜像问题...
call .\fix-docker-images.bat

echo 第3步: 重新编译所有微服务...
call .\rebuild-all.bat

echo 第4步: 重新构建所有微服务Docker镜像...
call .\rebuild-services.bat

echo 第5步: 启动所有服务...
call .\start-all-services.bat

echo.
echo ========================================
echo    部署完成！
echo ========================================
echo.
echo 服务访问地址：
echo - 前端: http://localhost
echo - Eureka服务注册中心: http://localhost:8761
echo - Gateway网关: http://localhost:8085
echo - 用户服务: http://localhost:8081
echo - 实验模块服务: http://localhost:8082
echo - 镜像服务: http://localhost:8083
echo - Docker服务: http://localhost:8084
echo.
echo 实验环境访问地址：
echo - SQL注入实验: http://localhost:8091
echo - XSS实验: http://localhost:8092
echo - CSRF实验: http://localhost:8093
echo - 文件上传实验: http://localhost:8094
echo - 目录遍历实验: http://localhost:8095
echo - 命令注入实验: http://localhost:8090
echo - 安全代码容器: http://localhost:8080
echo.
echo 查看容器状态: docker ps
echo 停止所有服务: .\stop-all-services.bat
echo.
pause 