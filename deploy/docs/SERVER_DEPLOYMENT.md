# SecLab Linux 部署说明

目标效果：校园局域网终端访问 `http://<服务器IP>:8088/`，进入 SecLab 前端，登录后可启动共享靶机和个人 noVNC 操作环境。

## 约定

- 项目目录：`/opt/seclab/SecLab`
- MySQL 容器：`seclab-mysql`
- 前端静态目录：`/opt/seclab/SecLab/SecLab-FrontEnd-2/dist`
- AI Agent：`127.0.0.1:8010`
- user-service：`127.0.0.1:8083`
- experiment-module-service：`127.0.0.1:8084`
- nginx 入口：`0.0.0.0:8088`

## 服务器预装

```bash
sudo apt update
sudo apt install -y openjdk-17-jdk python3 python3-venv python3-pip nodejs npm nginx docker.io docker-compose-plugin
sudo usermod -aG docker $USER
```

加 Docker 组后重新登录一次 SSH。

## 上传项目

把 `D:\Seclab\SecLab-Merged` 上传为 `/opt/seclab/SecLab`：

```bash
sudo mkdir -p /opt/seclab
sudo chown -R $USER:$USER /opt/seclab
rsync -av --delete ./SecLab-Merged/ user@server:/opt/seclab/SecLab/
```

## 一键部署

```bash
cd /opt/seclab/SecLab
sudo bash deploy/scripts/deploy-all.sh
```

脚本会执行：

1. 启动 MySQL 8 容器并导入必要的 `database/sql/` 和 `DataStr/` SQL。
2. 安装 AI Agent Python 依赖。
3. 构建 `user-service` 和 `experiment-module-service`。
4. 构建 `seclab-op-web-tools:1.0` noVNC 操作机镜像。
5. 启动 6 个靶场 compose。
6. 构建前端。
7. 安装 systemd 和 nginx 配置。

## 前端 API 地址

当前前端在生产构建下默认使用相对路径：

- user-service：`/stu/*`、`/admin/*`
- experiment-module-service：`/course/*`、`/stu/module/*`
- AI Agent/noVNC：`/api/*`、`/api/docker/*`

这些路径由 nginx 分发，所以校园网其他终端不会把请求打到自己电脑的 `localhost`。

## Nginx 关键点

`deploy/nginx/seclab.conf` 已包含 noVNC WebSocket 配置：

- `/api/docker/vnc/` 在 `/api/docker/` 前面。
- `proxy_http_version 1.1`、`Upgrade`、`Connection` 已配置。
- `proxy_read_timeout 86400s`，避免 VNC 默认 60 秒断开。

## 验证

```bash
systemctl status seclab-ai-agent seclab-user-service seclab-experiment-module
docker ps
curl http://127.0.0.1:8010/docs
curl http://127.0.0.1:8084/course/overview-list
curl http://127.0.0.1:8088/
```

浏览器访问：

1. 打开 `http://<服务器IP>:8088/`。
2. 登录 `admin / 123456`。
3. 进入实验模块，点“开始挑战”。
4. 点“启动操作环境”，应看到 noVNC 桌面。
5. 在操作环境内访问类似 `http://sqli-lab-web-1/index.php` 的容器内地址。

## 已知注意事项

- `init_database.sql` 编码损坏，不要导入；脚本没有导入它。脚本也没有导入会 `DROP TABLE` 的旧 dump，而是按需创建 `course/module/module_course` 并导入 seed。
- `getModuleDetail` 已改到 8084，但当前后端没有完整任务点详情接口。前端会 fallback 到本地 `src/data` 数据，保证能进入实验。后续若要完全接口化，需要补任务点/题目表和详情接口。
- 共享靶机在“结束实验”时不停止，避免影响其他测试同学；只销毁当前用户的 operation 容器。
- AI Agent 用 `uvicorn main:app` 启动，不用 `python main.py`，避免 reload 进程抢端口。
