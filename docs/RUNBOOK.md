# SecLab 启动与排障手册

> 快速上手见 [README](../README.md)。本文是完整的本地启动、调试与关闭手册。

## 一、服务端口总表

| 服务 | 端口 | 说明 |
|---|---|---|
| 前端 Vite | `5173` | 被占用时自动顺延 5174/5175，后端 CORS 已放行 |
| AI Agent (FastAPI) | `8010` | 教学分析、noVNC 编排、实验事件、容器工具 |
| docker-api-server | `3000` | 前端「准备靶机」按钮走这里 |
| user-service | `8083` | 登录注册、教学班、画像基础数据 |
| experiment-module-service | `8084` | 课程 / 模块 / 实验目录 |
| Gateway | `8085` | |
| image-service | `8086` | |
| docker-service | `8087` | |
| Eureka | `8761` | |
| 安全代码容器 | `8080` | |
| 命令注入 / SQL注入 / XSS / CSRF / 文件上传 / 目录遍历 | `8090`–`8095` | |
| 栈溢出 pwn 靶机 | `8096` | TCP 服务 |
| 协议分析靶场 | `8896` | 三关：TCP/IP 分析 -> HTTP 分析 -> 安全事件分析 |

## 二、启动前确认

1. 打开 Docker Desktop，确认 Docker 正常运行。
2. 确认本机 MySQL 已启动（默认 `3306`）。
   - `user-service` 是 `ddl-auto: update`，教师相关表和 `user.user_role` 列会自动补。
   - `experiment-module-service` 是 **`ddl-auto: none`**，课程/模块表结构变更**不会**自动补，需跑第三节的 SQL。
3. 如果改动过 noVNC 操作环境镜像 `operation-image`，才需要重建（平时不用）：

```powershell
cd seclab-backend\operation-image
.\build.ps1
```

## 三、首次准备（仅第一次 / 依赖有变时）

### 1. 依赖

```powershell
# 前端依赖（含 vitest，跑单元测试需要）
cd SecLab-FrontEnd-2
npm install

# ai-agent 虚拟环境
cd ..\seclab-backend\ai-agent-service
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
```

### 2. 数据库脚本

按顺序执行 `database\sql\` 下的脚本。**全部是 `CREATE TABLE IF NOT EXISTS` / `INSERT IGNORE`，可重复执行，不会破坏已有数据。**

```text
init_seclab_db.sql                       业务库（含 user.user_role、course.created_by）
init_seclab_profile.sql                  画像库全量表（含教师分析/干预/知识点分析全套）
user-service-local-init.sql              教学班相关表 + 本地管理员
experiment-module-service-local-init.sql 课程/模块表 + created_by 老库自愈迁移
teacher_knowledge_analysis.sql           知识点 AI 分析 + 例题审核表
teacher_intervention.sql                 教学干预 + 例题快照表
```

教师端演示数据（可选，32 名学生 / 40 道生成题 / 17 条错答）：

```text
seed_teacher_showcase.sql   只维护 showcase-20260715-* 前缀数据，可重复执行
```

## 四、启动项目（3 个 PowerShell 窗口）

### 1. 后端与靶场容器

```powershell
cd seclab-backend
$env:START_AI_AGENT="false"
.\start-all-services.bat
```

脚本会依次启动：

- 靶场容器 `8090`–`8095`、协议分析靶场 `8896`
- Eureka `8761` / Gateway `8085`（仅当本地已有对应镜像）
- **user-service `8083`**（gradle bootRun，首次稍慢）
- **experiment-module-service `8084`**
- **image-service `8086`**（头像上传走这里，不起就传不了头像）
- docker-service `8087`（仅当本地已有对应镜像）
- docker-api-server `3000`、安全代码容器 `8080`

脚本会先 `netstat` 检查端口，**已在监听的服务会自动跳过，可重复执行不会起重复进程**。

脚本窗口不要关；弹出的 `SecLab user-service 8083`、`SecLab experiment-module-service 8084` 两个窗口也不要关。

可选开关：

```powershell
$env:START_LOCAL_USER_SERVICE="false"              # 改用 Docker 镜像跑 user-service
$env:START_LOCAL_EXPERIMENT_MODULE_SERVICE="false" # 改用 Docker 镜像跑 experiment-module
$env:START_LOCAL_IMAGE_SERVICE="false"             # 改用 Docker 镜像跑 image-service
$env:START_AI_AGENT="false"                        # 不由脚本启动 8010（推荐，手动起便于看日志）
$env:START_CPOLAR="true"                           # 额外开 cpolar 隧道
```

### 2. AI Agent（教学分析 + noVNC 操作环境编排）

```powershell
cd seclab-backend\ai-agent-service
.\venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8010
```

窗口不要关。noVNC 操作环境、容器编排、实验事件、栈溢出靶机准备、**教师端教学分析、学生能力成长、解题记录**都走 `8010`。

AI 模型在 `ai-agent-service\.env` 里配（`.env` 不入库，参考 `.env.example`）：

| 变量 | 说明 |
|---|---|
| `LLM_API_KEY` | OpenAI 兼容接口的 key。**填了就直连模型**，助手对话、教师端 AI 分析、AI 出题都不再经过 Dify |
| `LLM_API_BASE` / `LLM_MODEL` | 默认 `https://api.deepseek.com/v1` + `deepseek-chat` |
| `LLM_PROVIDER` | 设成 `dify` 可在保留 key 的情况下切回 Dify |

直连模式下助手的人设与 Docker 工具调用由 `chat_agent_service.py` 负责（原本在 Dify 应用里配），
前端 SSE 事件格式不变。自检：`curl http://127.0.0.1:8010/health/ai-analysis`。

### 3. 前端

```powershell
cd SecLab-FrontEnd-2
npm run dev
```

浏览器打开 `http://localhost:5173`。

## 五、跑测试

```powershell
# 后端 AI Agent 用例
cd seclab-backend\ai-agent-service
.\venv\Scripts\python.exe -m unittest discover -p "test_*.py"

# 前端用例
cd SecLab-FrontEnd-2
npm run test

# 前端生产构建（顺带查类型和导入错误）
npm run build

# user-service Kotlin 测试
# 注意：seclab-backend 根目录没有 gradle wrapper，各服务各自带 gradlew.bat
cd seclab-backend\user-service
.\gradlew.bat test
```

## 六、调试

### 前端（Chrome DevTools）

```text
F12 看 Console / Network。
实验详情页（栈溢出 module 15）：右侧靶机「已就绪」、任务点代码块彩色可见、flag 提交。
教师端 /teacher/analysis：知识点风险饼图 -> 点扇区开详情抽屉 -> AI 分析 / 例题审核 / 下发。
学生端 /user/profile：解题记录（真实题干+错题筛选）、能力成长（证据链+样本量）。
```

### 后端日志

```text
各服务：start-all-services.bat 弹出的窗口即日志。
AI Agent：uvicorn 窗口即日志；改了 config.py / main.py / teacher_*.py / capability_growth_*.py 需重启。
```

### 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 课程列表 500 `Unknown column 'created_by'` | 老库缺列，`ddl-auto: none` 不会补 | 跑 `experiment-module-service-local-init.sql` |
| experiment-module 起不来，报 `seclab.jwt.secret` | 该属性无默认值，缺了 Spring 上下文直接失败 | `application.yml` 已内置默认值；如需覆盖设 `USER_SERVICE_JWT_SECRET` |
| 教师端报 CORS 错误 | 后端某接口抛未捕获异常返回裸 500，绕过了 CORS 中间件 | 看 uvicorn 窗口的真实堆栈，不要只看浏览器的 CORS 提示 |
| AI 分析显示「暂不可用」 | 模型未配置或不可达（`LLM_API_KEY` 没填，或 Dify 不通）；若机器设了 `ALL_PROXY=socks5://` 还需 `pip install "httpx[socks]"` | 先看 `/health/ai-analysis`；不影响作答统计、饼图、画像等真实数据 |
| 例题编辑接口 405 | 走 Gateway 时 CORS 需放行 PATCH | `gateway/application.yml` 已加 |
| 头像传不上去 / 传完还是空 | image-service 没起，8086 连不上 | 启动脚本已默认本地起；单独起：`cd image-service && .\gradlew.bat bootRun` |
| 换了机器后头像全裂图 | 库里存的是文件名，靠 `VITE_IMAGE_SERVICE_BASE_URL` 拼地址 | 确认该环境变量指向能访问到的 image-service |
| 课程视频无法播放 | `SecLab-FrontEnd-2/public/video/` 未随仓库分发 | 把视频文件放回该目录即可，不影响其他功能 |

### 端口排查

```powershell
$ports = 5173,3000,8010,8080,8083,8084,8085,8086,8087,8761,8090,8091,8092,8093,8094,8095,8096,8896
Get-NetTCPConnection -State Listen -LocalPort $ports -ErrorAction SilentlyContinue |
  Select-Object LocalPort, OwningProcess
```

## 七、关闭项目

优先正常关闭：

1. 前端窗口 `Ctrl+C`
2. AI Agent 窗口 `Ctrl+C`
3. `SecLab user-service 8083`、`SecLab experiment-module-service 8084` 窗口 `Ctrl+C` 或直接关
4. `start-all-services.bat` 窗口可以关
5. 开了 cpolar 就关掉 cpolar 窗口

然后清理 Docker 容器与 noVNC 临时环境：

```powershell
cd seclab-backend

docker compose -f sqli-lab\docker-compose.yml down
docker compose -f xss-lab\docker-compose.yml down
docker compose -f csrf-lab\docker-compose.yml down
docker compose -f file-upload-lab\docker-compose.yml down
docker compose -f directory-traversal-lab\docker-compose.yml down
docker compose -f command-inject\docker-compose.yml down
docker compose -f stack-overflow-lab\docker-compose.yml down
docker compose -f protocol-analysis-lab\docker-compose.yml down

docker rm -f sec-code-container 2>$null

docker ps --filter "name=operation_" -q | ForEach-Object { docker rm -f $_ }
docker network ls --filter "name=seclab-op-" -q | ForEach-Object { docker network rm $_ }

docker rm -f saclab-eureka saclab-gateway saclab-user-service saclab-experiment-module-service saclab-image-service saclab-docker-service seclab-ai-agent 2>$null
```

端口仍被占用时再按端口强制清理。**执行前先确认这些端口确实是 SecLab 进程，别误杀 Docker Desktop / wslrelay：**

```powershell
$ports = 5173,3000,8010,8080,8083,8084,8085,8086,8087,8761,8090,8091,8092,8093,8094,8095,8096,8896
Get-NetTCPConnection -State Listen -LocalPort $ports -ErrorAction SilentlyContinue |
  Select-Object LocalPort, OwningProcess
```

确认无误后：

```powershell
$ports = 5173,3000,8010,8080,8083,8084,8085,8086,8087,8761,8090,8091,8092,8093,8094,8095,8096,8896
Get-NetTCPConnection -State Listen -LocalPort $ports -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

Get-Process cpolar -ErrorAction SilentlyContinue | Stop-Process -Force
```

## 八、关闭后检查

```powershell
docker ps
$ports = 5173,3000,8010,8080,8083,8084,8085,8086,8087,8761,8090,8091,8092,8093,8094,8095,8096,8896
Get-NetTCPConnection -State Listen -LocalPort $ports -ErrorAction SilentlyContinue
```

`docker ps` 无 SecLab 相关容器、上述端口无监听，即已关闭干净。
