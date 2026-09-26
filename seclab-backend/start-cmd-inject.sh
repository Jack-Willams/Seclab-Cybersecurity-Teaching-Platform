#!/bin/bash

# 停止并移除可能已存在的容器
docker-compose -f command-inject/docker-compose.yml down 2>/dev/null

# 启动命令注入靶机
cd command-inject
docker-compose up -d

# 获取容器的IP地址和端口
PORT=$(docker-compose port web 80 | cut -d':' -f2)
HOST=$(hostname -I | awk '{print $1}')

# 如果没有获取到主机IP，使用localhost
if [ -z "$HOST" ]; then
  HOST="localhost"
fi

# 输出靶机访问URL
echo "{\"success\":true,\"data\":{\"url\":\"http://$HOST:$PORT\"}}" 