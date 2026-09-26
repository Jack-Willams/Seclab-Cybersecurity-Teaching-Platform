# SecLab · Cybersecurity Lab Education Platform

An integrated platform for cybersecurity lab education, covering **course management, containerized labs,
an AI teaching assistant, skill profiling and teaching analytics**. It brings the AI assistant into real
lab sessions, closing the loop from **skill diagnosis -> personalized training -> instructor support**.

Built with a Vue 3 + TypeScript frontend, a Spring Boot + FastAPI multi-service backend, and
browser-based lab environments delivered through Docker + noVNC.

> 中文文档：[`README.md`](README.md) · Full setup and troubleshooting runbook (Chinese): [`docs/RUNBOOK.md`](docs/RUNBOOK.md)

## Tech Stack

| Layer | Technologies |
| --- | --- |
| Frontend | Vue 3 · TypeScript · Vue Router · Pinia · Tailwind CSS / daisyUI · Chart.js · Vue Flow · noVNC |
| Backend | Kotlin · Spring Boot · Spring Cloud (Eureka / Gateway) · FastAPI · Python |
| Data & Deployment | MySQL · Docker · Docker Compose · Nginx · systemd · noVNC |

## Scope

- **Teaching side** — Course and class management, lab orchestration, learning-behavior-based skill profiling and teaching analytics
- **Lab side** — Dynamic creation of Docker-based target containers, session network attachment, noVNC remote desktop, and full lifecycle management of lab environments
- **Intelligence side** — Dual-path integration of OpenAI-compatible APIs and Dify, SSE streaming output, multi-turn context management, and tool calls for Docker status and logs
- **Architecture side** — Multi-service decomposition by business domain, with JWT authentication plus role-based and resource-ownership authorization

## Built-in Labs

Each lab is an independent Docker Compose environment on its own port:

| Lab | Directory | Port |
| --- | --- | --- |
| Command injection | `seclab-backend/command-inject` | 8090 |
| SQL injection | `seclab-backend/sqli-lab` | 8091 |
| XSS | `seclab-backend/xss-lab` | 8092 |
| CSRF | `seclab-backend/csrf-lab` | 8093 |
| File upload | `seclab-backend/file-upload-lab` | 8094 |
| Directory traversal | `seclab-backend/directory-traversal-lab` | 8095 |
| Stack overflow (pwn, TCP) | `seclab-backend/stack-overflow-lab` | 8096 |
| Protocol analysis (3 stages) | `seclab-backend/protocol-analysis-lab` | 8896 |

## Services and Ports

| Service | Port | Purpose |
| --- | --- | --- |
| Frontend (Vite) | `5173` | Shifts to 5174/5175 when occupied |
| AI Agent (FastAPI) | `8010` | Teaching assistant, teaching analytics, noVNC orchestration, container tools |
| docker-api-server | `3000` | Backs the frontend "prepare target" action |
| user-service | `8083` | Auth, teaching classes, profiling base data |
| experiment-module-service | `8084` | Courses / modules / experiment catalog |
| Gateway | `8085` | API gateway |
| image-service | `8086` | Avatar and image storage |
| docker-service | `8087` | Container orchestration service |
| Eureka | `8761` | Service registry |

## Repository Layout

```
SecLab-OpenSource/
├── SecLab-FrontEnd-2/              # Vue 3 + TypeScript frontend (the only frontend)
├── seclab-backend/                 # Backend services and lab environments
│   ├── ai-agent-service/           # FastAPI: assistant, teaching analytics, noVNC orchestration
│   ├── user-service/               # Spring Boot: users, teaching classes, profiling data
│   ├── experiment-module-service/  # Spring Boot: courses / modules / experiment catalog
│   ├── gateway/ eureka/ image-service/ docker-service/
│   ├── *-lab/ command-inject/ protocol-analysis-lab/   # Docker lab environments
│   ├── operation-image/            # noVNC operation-environment image
│   ├── docker-api-server.js        # Docker API used by the frontend
│   └── start-all-services.bat      # One-shot backend + lab launcher
├── database/                       # SQL init scripts (sql/ current, legacy/ archived)
├── deploy/                         # Nginx config, systemd units, deploy scripts
└── docs/RUNBOOK.md                 # Full setup, troubleshooting and shutdown runbook
```

## Quick Start

**Prerequisites:** Docker Desktop, Node.js 18+, JDK 17, Python 3.10+, MySQL 8.

### 1. Initialize the database

Run the scripts in `database/sql/` in order. All use `CREATE TABLE IF NOT EXISTS` / `INSERT IGNORE`
and are safe to re-run:

```text
init_seclab_db.sql
init_seclab_profile.sql
user-service-local-init.sql
experiment-module-service-local-init.sql
teacher_knowledge_analysis.sql
teacher_intervention.sql
```

### 2. Install dependencies

```powershell
cd SecLab-FrontEnd-2
npm install

cd ..\seclab-backend\ai-agent-service
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
```

### 3. Configure

```powershell
Copy-Item SecLab-FrontEnd-2\.env.example SecLab-FrontEnd-2\.env.local
Copy-Item seclab-backend\ai-agent-service\.env.example seclab-backend\ai-agent-service\.env
```

Edit `ai-agent-service/.env` and set at least `LLM_API_KEY`.

### 4. Run

```powershell
# Backend services + lab containers
cd seclab-backend
$env:START_AI_AGENT="false"
.\start-all-services.bat

# AI Agent (separate window)
cd ai-agent-service
.\venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8010

# Frontend (separate window)
cd SecLab-FrontEnd-2
npm run dev
```

Open <http://localhost:5173>.

## Configuration

Key environment variables (documented inline in `.env.example`):

| Variable | Location | Purpose |
| --- | --- | --- |
| `LLM_API_KEY` | `ai-agent-service/.env` | OpenAI-compatible key; when set, the model is called directly instead of via Dify |
| `LLM_API_BASE` / `LLM_MODEL` | same | Defaults to `https://api.deepseek.com/v1` + `deepseek-chat` |
| `LLM_PROVIDER` | same | Set to `dify` to fall back to Dify while keeping the key |
| `MYSQL_*` | same | Learning-event and profiling database connection |
| `VITE_API_BASE_URL` | `SecLab-FrontEnd-2/.env.local` | user-service address |
| `VITE_AGENT_BASE_URL` | same | AI Agent address |
| `VITE_IMAGE_SERVICE_BASE_URL` | same | image-service address |
| `VITE_DOCKER_API_URL` | same | Docker API address |

> **Security note:** the database password and JWT secret in `application.yml` and `.env.example`
> (for example `MYSQL_PASSWORD`, `USER_SERVICE_JWT_SECRET`) are local development defaults.
> Override them through environment variables before deploying anywhere reachable.

## Tests

```powershell
# AI Agent (17 test modules)
cd seclab-backend\ai-agent-service
.\venv\Scripts\python.exe -m unittest discover -p "test_*.py"

# Frontend unit tests
cd SecLab-FrontEnd-2
npm run test

# Type check + production build
npm run build

# user-service (Kotlin)
cd ..\seclab-backend\user-service
.\gradlew.bat test
```

## Deployment

The `deploy/` directory provides an Nginx reverse-proxy config, systemd units and deploy scripts.
See [`deploy/docs/SERVER_DEPLOYMENT.md`](deploy/docs/SERVER_DEPLOYMENT.md).

## Course Videos

The course videos (~5 GB) live in `SecLab-FrontEnd-2/public/video/` and are **not included in this repository**.
Place the video files back into that directory for local use; their absence only affects video playback.

## License

[MIT](LICENSE)
