# SecLab · 网络安全实验教学平台

面向网络安全实验教学的一体化平台，覆盖**课程管理、容器化实训、智能助教、能力画像与教学分析**，
把 AI 助教接入真实攻防实验现场，串联「能力诊断 → 个性化训练 → 教师辅助教学」的教学闭环。

An integrated platform for cybersecurity lab education — course management, containerized labs,
an AI teaching assistant, skill profiling and teaching analytics. Built with Vue 3 + TypeScript,
a Spring Boot + FastAPI multi-service backend, and browser-based lab environments via Docker + noVNC.

> English documentation: [`README.en.md`](README.en.md) · 完整启动与排障手册： [`docs/RUNBOOK.md`](docs/RUNBOOK.md)

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 前端 | Vue 3 · TypeScript · Vue Router · Pinia · Tailwind CSS / daisyUI · Chart.js · Vue Flow · noVNC |
| 后端 | Kotlin · Spring Boot · Spring Cloud（Eureka / Gateway） · FastAPI · Python |
| 数据与部署 | MySQL · Docker · Docker Compose · Nginx · systemd · noVNC |

## 覆盖面

- **教学侧** — 课程与教学班管理、实验编排、基于学习行为的能力画像与教学分析
- **实训侧** — Docker 容器化靶机动态创建、会话网络挂接、noVNC 远程桌面与实验环境生命周期管理
- **智能侧** — OpenAI 兼容接口与 Dify 双路径接入、SSE 流式输出、多轮上下文与 Docker 状态／日志工具调用
- **架构侧** — 按业务领域拆分多服务，JWT 身份认证 + 角色与资源归属校验的权限控制

## 内置靶场

各靶场为独立 Docker Compose 环境，按端口区分：

| 实验 | 目录 | 端口 |
| --- | --- | --- |
| 命令注入 | `seclab-backend/command-inject` | 8090 |
| SQL 注入 | `seclab-backend/sqli-lab` | 8091 |
| XSS 跨站脚本 | `seclab-backend/xss-lab` | 8092 |
| CSRF 跨站请求伪造 | `seclab-backend/csrf-lab` | 8093 |
| 文件上传漏洞 | `seclab-backend/file-upload-lab` | 8094 |
| 目录遍历漏洞 | `seclab-backend/directory-traversal-lab` | 8095 |
| 栈溢出（pwn，TCP 服务） | `seclab-backend/stack-overflow-lab` | 8096 |
| 协议分析（三关） | `seclab-backend/protocol-analysis-lab` | 8896 |

## 服务与端口

| 服务 | 端口 | 说明 |
| --- | --- | --- |
| 前端 Vite | `5173` | 被占用时自动顺延 |
| AI Agent（FastAPI） | `8010` | 智能助教、教学分析、noVNC 编排、容器工具 |
| docker-api-server | `3000` | 前端「准备靶机」入口 |
| user-service | `8083` | 登录注册、教学班、画像基础数据 |
| experiment-module-service | `8084` | 课程 / 模块 / 实验目录 |
| Gateway | `8085` | API 网关 |
| image-service | `8086` | 头像等图片存取 |
| docker-service | `8087` | 容器编排服务 |
| Eureka | `8761` | 服务注册中心 |

## 目录结构

```
SecLab-OpenSource/
├── SecLab-FrontEnd-2/              # Vue 3 + TypeScript 前端（唯一前端目录）
├── seclab-backend/                 # 后端与靶场
│   ├── ai-agent-service/           # FastAPI：AI 助教、教学分析、noVNC 编排
│   ├── user-service/               # Spring Boot：用户、教学班、画像基础数据
│   ├── experiment-module-service/  # Spring Boot：课程 / 模块 / 实验目录
│   ├── gateway/ eureka/ image-service/ docker-service/
│   ├── *-lab/ command-inject/ protocol-analysis-lab/   # Docker 靶场
│   ├── operation-image/            # noVNC 操作环境镜像
│   ├── docker-api-server.js        # 前端「准备靶机」调用的 Docker API
│   └── start-all-services.bat      # 一键启动后端与靶场
├── database/                       # SQL 初始化脚本（sql/ 为当前版本，legacy/ 为历史归档）
├── deploy/                         # Nginx 配置、systemd 单元与部署脚本
└── docs/RUNBOOK.md                 # 完整启动、排障与关闭手册
```

## 快速开始

**前置依赖：** Docker Desktop、Node.js 18+、JDK 17、Python 3.10+、MySQL 8。

### 1. 初始化数据库

按顺序执行 `database/sql/` 下的脚本。均为 `CREATE TABLE IF NOT EXISTS` / `INSERT IGNORE`，可重复执行：

```text
init_seclab_db.sql
init_seclab_profile.sql
user-service-local-init.sql
experiment-module-service-local-init.sql
teacher_knowledge_analysis.sql
teacher_intervention.sql
```

### 2. 安装依赖

```powershell
cd SecLab-FrontEnd-2
npm install

cd ..\seclab-backend\ai-agent-service
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
```

### 3. 配置环境变量

```powershell
Copy-Item SecLab-FrontEnd-2\.env.example SecLab-FrontEnd-2\.env.local
Copy-Item seclab-backend\ai-agent-service\.env.example seclab-backend\ai-agent-service\.env
```

编辑 `ai-agent-service/.env`，至少填入 `LLM_API_KEY`（OpenAI 兼容接口的密钥）。

### 4. 启动

```powershell
# 后端微服务 + 靶场容器
cd seclab-backend
$env:START_AI_AGENT="false"
.\start-all-services.bat

# AI Agent（另开窗口）
cd ai-agent-service
.\venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8010

# 前端（另开窗口）
cd SecLab-FrontEnd-2
npm run dev
```

浏览器打开 <http://localhost:5173>。

## 配置说明

主要环境变量（完整注释见 `.env.example`）：

| 变量 | 位置 | 说明 |
| --- | --- | --- |
| `LLM_API_KEY` | `ai-agent-service/.env` | OpenAI 兼容接口密钥；填了就直连模型，不再经过 Dify |
| `LLM_API_BASE` / `LLM_MODEL` | 同上 | 默认 `https://api.deepseek.com/v1` + `deepseek-chat` |
| `LLM_PROVIDER` | 同上 | 设为 `dify` 可在保留 key 的情况下切回 Dify |
| `MYSQL_*` | 同上 | 学习事件与画像库连接信息 |
| `VITE_API_BASE_URL` | `SecLab-FrontEnd-2/.env.local` | 用户服务地址 |
| `VITE_AGENT_BASE_URL` | 同上 | AI Agent 地址 |
| `VITE_IMAGE_SERVICE_BASE_URL` | 同上 | 图片服务地址 |
| `VITE_DOCKER_API_URL` | 同上 | Docker API 地址 |

> **安全提示：** `application.yml` 与 `.env.example` 中的数据库密码、JWT 密钥均为本地开发默认值
> （如 `MYSQL_PASSWORD`、`USER_SERVICE_JWT_SECRET`）。部署到任何可访问的环境前，请务必通过环境变量覆盖。

## 测试

```powershell
# AI Agent（17 个测试文件）
cd seclab-backend\ai-agent-service
.\venv\Scripts\python.exe -m unittest discover -p "test_*.py"

# 前端单元测试
cd SecLab-FrontEnd-2
npm run test

# 类型检查 + 生产构建
npm run build

# user-service（Kotlin）
cd ..\seclab-backend\user-service
.\gradlew.bat test
```

## 部署

`deploy/` 目录提供 Nginx 反向代理配置、systemd 服务单元与部署脚本，参见 [`deploy/docs/SERVER_DEPLOYMENT.md`](deploy/docs/SERVER_DEPLOYMENT.md)。

## 课程视频

课程视频（约 5 GB）位于 `SecLab-FrontEnd-2/public/video/`，**未包含在本仓库中**。
本地运行时将视频文件放回该目录即可；缺失仅影响课程视频播放，不影响其他功能。

## 许可证

[MIT](LICENSE)
