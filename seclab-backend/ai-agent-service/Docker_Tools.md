openapi: 3.1.0
info:
  title: SecLab Docker Tools API
  description: 管理 SecLab 靶场 Docker 容器的工具集。支持获取日志、执行指令、启动和停止容器。
  version: 1.1.0
servers:
  - url: https://56f08634.r9.cpolar.top
    description: cpolar 公网穿透地址
paths:
  # --- 新增：获取容器列表（读取容器名字） ---
  /api/docker/list:
    get:
      operationId: list_containers
      summary: 获取所有容器列表
      description: 返回系统中所有容器的名称、ID 及当前运行状态，方便 Agent 识别可用容器。
      responses:
        '200':
          description: 成功返回容器数组
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    name:
                      type: string
                      description: 容器名称
                    status:
                      type: string
                      description: 容器状态（如 running, exited）

  /api/docker/containers:
    get:
      operationId: get_container_status
      summary: 获取指定容器详情
      parameters:
        - name: name
          in: query
          required: false
          description: 容器名称（如 sqli-lab-web-1）
          schema:
            type: string
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object

  /api/docker/logs/{container_name}:
    get:
      operationId: get_container_logs
      summary: 获取容器日志
      parameters:
        - name: container_name
          in: path
          required: true
          description: 目标容器名称
          schema:
            type: string
        - name: tail
          in: query
          required: false
          description: 返回最近行数
          schema:
            type: integer
            default: 100
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object

  /api/docker/exec/{container_name}:
    post:
      operationId: exec_in_container
      summary: 在容器内执行指令
      parameters:
        - name: container_name
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                command:
                  type: string
                  description: Shell命令
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object

  # --- 新增：开启容器 ---
  /api/docker/start/{container_name}:
    post:
      operationId: start_container
      summary: 启动已停止的容器
      parameters:
        - name: container_name
          in: path
          required: true
          description: 要启动的容器名称
          schema:
            type: string
      responses:
        '200':
          description: 容器启动成功
          content:
            application/json:
              schema:
                type: object

  /api/docker/stop/{container_name}:
    post:
      operationId: stop_container
      summary: 停止容器
      parameters:
        - name: container_name
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object

components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-SecLab-Token
security:
  - ApiKeyAuth: []