#!/bin/bash

# 停止并删除现有容器
echo "停止并删除现有容器..."
docker-compose down -v

# 删除任何可能的旧镜像
echo "删除旧镜像..."
docker rmi -f sqli-lab_web

# 清理任何悬空的镜像
echo "清理悬空镜像..."
docker image prune -f

# 重新构建并启动容器
echo "重新构建并启动容器..."
docker-compose up --build -d

echo "重建完成！现在可以访问 http://localhost:8091" 