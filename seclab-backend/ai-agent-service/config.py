import os

from dotenv import load_dotenv

load_dotenv()

# Dify Agent configuration
DIFY_API_URL = os.getenv("DIFY_API_URL", "")
DIFY_API_KEY = os.getenv("DIFY_API_KEY", "")
DIFY_WORKFLOW_ID = os.getenv("DIFY_WORKFLOW_ID", "")
DIFY_APP_ID = os.getenv("DIFY_APP_ID", "")
ENABLE_FAKE_LLM_FOR_TEST = os.getenv("ENABLE_FAKE_LLM_FOR_TEST", "false")

# 直连 LLM 配置（OpenAI 兼容接口，例如 DeepSeek）。
# 填了 LLM_API_KEY 就优先直连模型，不再经过 Dify；LLM_PROVIDER=dify 可强制走回 Dify。
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").strip().lower()
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.deepseek.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))

# AI agent service listener
SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8010"))

# Frontend CORS allowlist
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # Vite 会在 5173 被占用时自动顺延到 5174/5175，这里一并放行避免开第二个前端时 CORS 报错
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    "http://localhost:80",
    "http://127.0.0.1:80",
    "http://localhost",
    "http://127.0.0.1",
    "http://192.168.1.106:5173",
]

configured_cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

CORS_ORIGINS = list(dict.fromkeys(configured_cors_origins + DEFAULT_CORS_ORIGINS))

# Docker tool container name allowlist
ALLOWED_CONTAINER_PREFIXES = os.getenv(
    "ALLOWED_CONTAINER_PREFIXES",
    "sqli,xss,csrf,upload,dir,cmd,command,command-inject,sec-code,operation,stack",
).split(",")

# Maximum log lines returned by Docker tools
MAX_LOG_LINES = int(os.getenv("MAX_LOG_LINES", "200"))

# Operation environment (noVNC desktop) settings
OPERATION_IMAGE = os.getenv("OPERATION_IMAGE", "seclab-op-web-tools:1.0")
OPERATION_VNC_PASSWORD = os.getenv("OPERATION_VNC_PASSWORD", "123456")
OPERATION_VNC_HOST = os.getenv("OPERATION_VNC_HOST", "127.0.0.1")
OPERATION_SESSION_TIMEOUT_SECONDS = int(os.getenv("OPERATION_SESSION_TIMEOUT_SECONDS", str(2 * 60 * 60)))
OPERATION_CLEANUP_INTERVAL_SECONDS = int(os.getenv("OPERATION_CLEANUP_INTERVAL_SECONDS", str(10 * 60)))

# Static map: module baseId -> target container names that should join the operation network.
# baseId is derived from module_id in the frontend (id // 100 for >=100, else id),
# mirroring SecLab-FrontEnd-2/src/pages/User/Module/index.vue:getBaseLabId().
OPERATION_TARGET_CONTAINERS = {
    1: ["sqli-lab-web-1"],
    2: ["xss-lab-web-1"],
    3: ["csrf-lab-web-1"],
    4: ["command-inject-web-1"],
    5: ["file-upload-lab-web-1"],
    6: ["directory-traversal-lab-web-1"],
    15: ["stack-overflow-lab-web-1"],  # 栈溢出 pwn 靶机（TCP:70），挂到操作桌面会话网络
}

# MySQL persistence for learning events and profile snapshots
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "seclab_app")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "Seclab@123")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "seclab_profile")
MYSQL_CHARSET = os.getenv("MYSQL_CHARSET", "utf8mb4")
