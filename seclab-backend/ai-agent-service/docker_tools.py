"""
Docker SDK 工具模块
提供对靶场容器的状态查询、日志读取、指令执行、容器停止功能
以及容器运行数据采集（供事件上报使用）

【容器命名规则说明】
Docker Compose 未指定 container_name 时，自动生成规则为：
  <目录名>-<服务名>-<序号>
例如：sqli-lab 目录下的 web 服务 → sqli-lab-web-1
      sqli-lab 目录下的 db  服务 → sqli-lab-db-1

因此调用本模块时，container_name 应使用完整名称，如 sqli-lab-web-1
"""
import docker
import re
from docker.errors import NotFound, APIError
from datetime import datetime, timezone
from typing import Optional
from config import ALLOWED_CONTAINER_PREFIXES, MAX_LOG_LINES

# 延迟初始化，避免启动时 Docker 未就绪导致崩溃
_client = None


def get_client() -> docker.DockerClient:
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def _is_allowed(name: str) -> bool:
    """安全白名单校验：只允许操作靶场相关容器"""
    lower = name.lower()
    return any(lower.startswith(prefix) or prefix in lower
               for prefix in ALLOWED_CONTAINER_PREFIXES)


def get_container_status(container_name: Optional[str] = None) -> dict:
    """
    获取容器状态。
    - container_name 为 None 时返回所有靶场容器列表
    - 指定名称时返回单个容器详情（同样经过白名单校验）

    注意：sqli-lab 的 web 服务实际容器名为 sqli-lab-web-1
    """
    try:
        client = get_client()
        if container_name:
            # 修复 Bug 3：指定容器名时也必须经过白名单校验
            if not _is_allowed(container_name):
                return {"success": False, "error": f"不允许访问容器 '{container_name}'"}
            try:
                c = client.containers.get(container_name)
                return {
                    "success": True,
                    "data": {
                        "name": c.name,
                        "status": c.status,
                        "image": c.image.tags[0] if c.image.tags else str(c.image.id)[:12],
                        "ports": c.ports,
                        "started_at": c.attrs.get("State", {}).get("StartedAt", ""),
                    }
                }
            except NotFound:
                return {"success": False, "error": f"容器 '{container_name}' 不存在"}
        else:
            containers = client.containers.list(all=True)
            result = []
            for c in containers:
                if _is_allowed(c.name):
                    result.append({
                        "name": c.name,
                        "status": c.status,
                        "image": c.image.tags[0] if c.image.tags else str(c.image.id)[:12],
                        "ports": c.ports,
                    })
            return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_container_logs(container_name: str, tail: int = 100) -> dict:
    """获取容器最近 N 行日志"""
    if not _is_allowed(container_name):
        return {"success": False, "error": "不允许访问该容器"}
    tail = min(tail, MAX_LOG_LINES)
    try:
        client = get_client()
        c = client.containers.get(container_name)
        logs = c.logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")
        return {"success": True, "container": container_name, "logs": logs}
    except NotFound:
        return {"success": False, "error": f"容器 '{container_name}' 不存在"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def exec_in_container(container_name: str, command: str) -> dict:
    """在容器内执行命令（仅限运行中的容器）"""
    if not _is_allowed(container_name):
        return {"success": False, "error": "不允许操作该容器"}
    try:
        client = get_client()
        c = client.containers.get(container_name)
        if c.status != "running":
            return {"success": False, "error": f"容器 '{container_name}' 当前未运行（状态: {c.status}）"}
        exit_code, output = c.exec_run(command, demux=False)
        return {
            "success": True,
            "container": container_name,
            "command": command,
            "exit_code": exit_code,
            "output": output.decode("utf-8", errors="replace") if output else ""
        }
    except NotFound:
        return {"success": False, "error": f"容器 '{container_name}' 不存在"}
    except APIError as e:
        return {"success": False, "error": str(e)}


def stop_container(container_name: str, timeout: int = 10) -> dict:
    """停止指定容器"""
    if not _is_allowed(container_name):
        return {"success": False, "error": "不允许停止该容器"}
    try:
        client = get_client()
        c = client.containers.get(container_name)
        c.stop(timeout=timeout)
        return {"success": True, "message": f"容器 '{container_name}' 已停止"}
    except NotFound:
        return {"success": False, "error": f"容器 '{container_name}' 不存在"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_containers() -> dict:
    """获取所有靶场容器的简要列表（经白名单过滤）"""
    try:
        client = get_client()
        containers = client.containers.list(all=True)
        data = [
            {"name": c.name, "status": c.status}
            for c in containers
            if _is_allowed(c.name)
        ]
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


def start_container(container_name: str) -> dict:
    """启动指定容器（经白名单校验）"""
    if not _is_allowed(container_name):
        return {"success": False, "error": f"不允许启动容器 '{container_name}'"}
    try:
        client = get_client()
        c = client.containers.get(container_name)
        c.start()
        return {"success": True, "message": f"容器 '{container_name}' 已启动"}
    except NotFound:
        return {"success": False, "error": f"容器 '{container_name}' 不存在"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gen_id(prefix: str = "evt") -> str:
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


_SQL_PATTERNS = [
    re.compile(r"(sqlmap|union\s+select|order\s+by\s+\d+|'\s*OR\s+1\s*=\s*1|--|;\s*drop\s)", re.IGNORECASE),
]
_XSS_PATTERNS = [
    re.compile(r"(<script|javascript:|onerror\s*=|onload\s*=|alert\s*\()", re.IGNORECASE),
]
_CMD_PATTERNS = [
    re.compile(r"(;\s*(cat|ls|whoami|id|uname|pwd|ifconfig|netstat|ping|wget|curl|nc|bash|sh)\b)", re.IGNORECASE),
]
_FILE_PATTERNS = [
    re.compile(r"(\.\.\/|\.\.\\|/etc/passwd|/etc/shadow|/proc/self)", re.IGNORECASE),
]
_UPLOAD_PATTERNS = [
    re.compile(r"(\.php|\.jsp|\.asp|\.aspx|\.sh|\.py|webshell|backdoor)", re.IGNORECASE),
]
_ERROR_PATTERNS = [
    re.compile(r"(error|exception|syntax\s*error|fatal|warning|mysql).*?(?:near|at\s+line|in\s+)", re.IGNORECASE),
]
_HTTP_PATTERNS = [
    re.compile(r'"\w+\s+(\S+)\s+HTTP', re.IGNORECASE),
]


def collect_container_runtime_data(container_name: str, tail: int = 200) -> dict:
    """
    采集容器运行时数据，用于事件上报。
    返回结构化的运行时信息，包括：
      - 容器状态（运行/停止、启动时间、运行时长）
      - 资源使用（CPU、内存、网络IO、磁盘IO）
      - 容器日志解析为事件列表（COMMAND_EXEC, ERROR_EVENT, FILE_CHANGE 等）
      - 容器进程列表
    """
    if not _is_allowed(container_name):
        return {"success": False, "error": f"不允许访问容器 '{container_name}'"}

    result = {
        "success": True,
        "container_name": container_name,
        "collected_at": _now_iso(),
        "container_info": {},
        "resource_usage": {},
        "log_events": [],
        "processes": [],
    }

    try:
        client = get_client()
        c = client.containers.get(container_name)
    except NotFound:
        return {"success": False, "error": f"容器 '{container_name}' 不存在"}
    except Exception as e:
        return {"success": False, "error": str(e)}

    state = c.attrs.get("State", {})
    started_at = state.get("StartedAt", "")
    status = state.get("Status", "unknown")

    duration_seconds = 0
    if started_at and status == "running":
        try:
            start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            duration_seconds = int((datetime.now(timezone.utc) - start_dt).total_seconds())
        except Exception:
            pass

    result["container_info"] = {
        "name": c.name,
        "status": status,
        "image": c.image.tags[0] if c.image.tags else str(c.image.id)[:12],
        "image_id": str(c.image.id)[:19],
        "started_at": started_at,
        "duration_seconds": duration_seconds,
        "ports": c.ports,
        "exit_code": state.get("ExitCode"),
        "error": state.get("Error", ""),
    }

    if status == "running":
        try:
            stats = c.stats(stream=False)
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
            cpu_percent = 0.0
            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = round((cpu_delta / system_delta) * 100.0, 2)

            mem_usage = stats["memory_stats"].get("usage", 0)
            mem_limit = stats["memory_stats"].get("limit", 1)
            mem_percent = round((mem_usage / mem_limit) * 100.0, 2) if mem_limit > 0 else 0.0

            net_rx = 0
            net_tx = 0
            for _iface, data in stats.get("networks", {}).items():
                net_rx += data.get("rx_bytes", 0)
                net_tx += data.get("tx_bytes", 0)

            blk_read = 0
            blk_write = 0
            for entry in stats.get("blkio_stats", {}).get("io_service_bytes_recursive", []) or []:
                if entry.get("op") == "read":
                    blk_read += entry.get("value", 0)
                elif entry.get("op") == "write":
                    blk_write += entry.get("value", 0)

            result["resource_usage"] = {
                "cpu_percent": cpu_percent,
                "memory_usage_mb": round(mem_usage / (1024 * 1024), 2),
                "memory_limit_mb": round(mem_limit / (1024 * 1024), 2),
                "memory_percent": mem_percent,
                "network_rx_bytes": net_rx,
                "network_tx_bytes": net_tx,
                "block_read_bytes": blk_read,
                "block_write_bytes": blk_write,
            }
        except Exception as e:
            result["resource_usage"] = {"error": str(e)}

    if status == "running":
        try:
            top_info = c.top()
            result["processes"] = {
                "titles": top_info.get("Titles", []),
                "processes": top_info.get("Processes", [])[:20],
            }
        except Exception:
            result["processes"] = []

    try:
        raw_logs = c.logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")
        lines = raw_logs.strip().split("\n") if raw_logs.strip() else []
    except Exception as e:
        result["log_events"] = [{"error": f"日志读取失败: {e}"}]
        return result

    for line in lines:
        line = line.strip()
        if not line:
            continue

        log_time = _now_iso()
        ts_match = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line)
        if ts_match:
            log_time = ts_match.group(1) + "Z"

        content = re.sub(r"^\d{4}-\d{2}-\d{2}T[\d:.]+\w?\s*", "", line).strip()
        if not content:
            continue

        classified = False

        for pat in _SQL_PATTERNS:
            if pat.search(content):
                result["log_events"].append({
                    "event_id": _gen_id("evt-cmd"),
                    "event_type": "COMMAND_EXEC",
                    "event_time": log_time,
                    "container_name": container_name,
                    "command": content[:200],
                    "output_digest": content[:100],
                    "extra": {"category": "sql_injection", "raw_log": content[:500]},
                })
                classified = True
                break

        if not classified:
            for pat in _XSS_PATTERNS:
                if pat.search(content):
                    result["log_events"].append({
                        "event_id": _gen_id("evt-cmd"),
                        "event_type": "COMMAND_EXEC",
                        "event_time": log_time,
                        "container_name": container_name,
                        "command": content[:200],
                        "output_digest": content[:100],
                        "extra": {"category": "xss_attack", "raw_log": content[:500]},
                    })
                    classified = True
                    break

        if not classified:
            for pat in _CMD_PATTERNS:
                if pat.search(content):
                    result["log_events"].append({
                        "event_id": _gen_id("evt-cmd"),
                        "event_type": "COMMAND_EXEC",
                        "event_time": log_time,
                        "container_name": container_name,
                        "command": content[:200],
                        "output_digest": content[:100],
                        "extra": {"category": "command_injection", "raw_log": content[:500]},
                    })
                    classified = True
                    break

        if not classified:
            for pat in _FILE_PATTERNS:
                if pat.search(content):
                    result["log_events"].append({
                        "event_id": _gen_id("evt-file"),
                        "event_type": "FILE_CHANGE",
                        "event_time": log_time,
                        "container_name": container_name,
                        "file_path": content[:200],
                        "action": "access",
                        "is_key_file": True,
                        "extra": {"category": "path_traversal", "raw_log": content[:500]},
                    })
                    classified = True
                    break

        if not classified:
            for pat in _UPLOAD_PATTERNS:
                if pat.search(content):
                    result["log_events"].append({
                        "event_id": _gen_id("evt-file"),
                        "event_type": "FILE_CHANGE",
                        "event_time": log_time,
                        "container_name": container_name,
                        "file_path": content[:200],
                        "action": "upload",
                        "is_key_file": True,
                        "extra": {"category": "malicious_upload", "raw_log": content[:500]},
                    })
                    classified = True
                    break

        if not classified:
            for pat in _ERROR_PATTERNS:
                if pat.search(content):
                    result["log_events"].append({
                        "event_id": _gen_id("evt-error"),
                        "event_type": "ERROR_EVENT",
                        "event_time": log_time,
                        "container_name": container_name,
                        "error_signature": "syntax_error",
                        "error_category": "syntax",
                        "raw_excerpt": content[:200],
                        "severity": "medium",
                        "extra": {"raw_log": content[:500]},
                    })
                    classified = True
                    break

        if not classified:
            for pat in _HTTP_PATTERNS:
                match = pat.search(content)
                if match:
                    result["log_events"].append({
                        "event_id": _gen_id("evt-http"),
                        "event_type": "COMMAND_EXEC",
                        "event_time": log_time,
                        "container_name": container_name,
                        "command": match.group(0)[:200],
                        "output_digest": content[:100],
                        "extra": {"category": "http_request", "url": match.group(1), "raw_log": content[:500]},
                    })
                    classified = True
                    break

    return result
