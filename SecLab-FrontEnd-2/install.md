# SecLab-FrontEnd 安装文档

本文档提供了安装和运行 SecLab-FrontEnd 项目的详细说明，包括常规安装方法和 Docker 容器化部署方法。

## 项目概述

SecLab-FrontEnd 是一个基于 Vue 3 + TypeScript + Vite 构建的网络安全漏洞综合实验平台前端项目。项目使用了以下主要技术栈：

- 前端框架: Vue 3
- 构建工具: Vite
- 语言: TypeScript
- CSS 框架: Tailwind CSS, DaisyUI
- 路由: Vue Router
- 状态管理: Pinia
- HTTP 客户端: Axios
- Markdown 渲染: markdown-it

## 系统要求

### 常规安装

- Node.js 18.x 或更高版本
- Yarn 4.x 或 npm

### Docker 安装

- Docker 20.10.x 或更高版本
- Docker Compose (可选，用于多容器部署)

## 常规安装方法

### 1. 克隆项目

```bash
git clone <项目仓库URL>
cd SecLab-FrontEnd
```

### 2. 安装依赖

使用 Yarn (推荐)：

```bash
yarn install
```

或使用 npm：

```bash
npm install
```

### 3. 开发环境运行

```bash
yarn dev
# 或
npm run dev
```

启动后，应用将在 http://localhost:5173 (默认端口) 运行。

### 4. 构建生产版本

```bash
yarn build
# 或
npm run build
```

构建后的文件将生成在 `dist` 目录中。

### 5. 预览生产构建

```bash
yarn preview
# 或
npm run preview
```

## Docker 部署方法

### 1. 创建 Dockerfile

在项目根目录创建 `Dockerfile` 文件，内容如下：

```dockerfile
# 构建阶段
FROM node:18-alpine as build-stage
WORKDIR /app
COPY package.json yarn.lock* package-lock.json* ./
RUN yarn install || npm install
COPY . .
RUN yarn build || npm run build

# 生产阶段
FROM nginx:stable-alpine as production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 2. 创建 Nginx 配置文件

在项目根目录创建 `nginx.conf` 文件，内容如下：

```nginx
server {
    listen 80;
    server_name localhost;

    root /usr/share/nginx/html;
    index index.html;

    # 处理 SPA 路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 静态资源缓存设置
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, max-age=31536000";
    }

    # 安全相关头信息
    add_header X-Content-Type-Options "nosniff";
    add_header X-XSS-Protection "1; mode=block";
    add_header X-Frame-Options "SAMEORIGIN";
}
```

### 3. 构建 Docker 镜像

```bash
docker build -t seclab-frontend .
```

### 4. 运行 Docker 容器

```bash
docker run -d -p 8080:80 --name seclab-frontend-container seclab-frontend
```

应用将在 http://localhost:8080 运行。

### 5. 使用 Docker Compose (可选)

在项目根目录创建 `docker-compose.yml` 文件，内容如下：

```yaml
version: '3'

services:
  frontend:
    build: .
    ports:
      - "8080:80"
    restart: unless-stopped
```

然后运行：

```bash
docker-compose up -d
```

## 环境变量配置

如需配置环境变量，可在项目根目录创建以下文件：

- `.env` - 所有环境通用的变量
- `.env.development` - 开发环境变量
- `.env.production` - 生产环境变量

环境变量示例：

```
VITE_API_BASE_URL=http://api.example.com
VITE_APP_TITLE=SecLab平台
```

## 常见问题解决

### 依赖安装失败

尝试清除缓存后重新安装：

```bash
yarn cache clean
# 或
npm cache clean --force
```

### 构建失败

检查 TypeScript 错误：

```bash
yarn vue-tsc --noEmit
# 或
npm run vue-tsc -- --noEmit
```

### Docker 相关问题

如果 Docker 构建失败，可尝试：

```bash
docker system prune -a
docker build --no-cache -t seclab-frontend .
```

## 部署到生产环境

### 使用脚本部署

项目包含一个 PowerShell 部署脚本 `upload.ps1`，可用于将构建后的文件上传到服务器：

```powershell
# 首先构建项目
yarn build

# 定义服务器和文件路径变量
$server = "your-server-ip"
$remotePath = "/var/www/"
$localPath = "./dist"

# 使用 SCP 传输文件
scp -r $localPath "user@${server}:${remotePath}"
```
