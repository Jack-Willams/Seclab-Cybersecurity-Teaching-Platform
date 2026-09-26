import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from database import ensure_database, get_connection
from error_repository import ERROR_EVENT_TABLE_SQL, build_error_from_command, insert_error_event
from event_repository import LEARNING_EVENT_TABLE_SQL


CONTAINER_COMMAND_EVENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS container_command_event (
    command_id VARCHAR(64) NOT NULL,
    lab_session_id VARCHAR(64) NULL,
    user_id BIGINT NULL,
    class_id BIGINT NULL,
    course_id BIGINT NULL,
    module_id BIGINT NULL,
    task_id BIGINT NULL,
    container_name VARCHAR(128) NULL,
    command VARCHAR(2048) NOT NULL,
    normalized_command VARCHAR(2048) NOT NULL,
    cmd_category VARCHAR(64) NOT NULL DEFAULT 'other',
    cwd VARCHAR(1024) NULL,
    exit_code INT NULL,
    duration_ms INT NULL,
    output_digest VARCHAR(512) NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'hook',
    request_id VARCHAR(64) NULL,
    executed_at DATETIME(6) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (command_id),
    KEY idx_container_command_session_time (lab_session_id, executed_at),
    KEY idx_container_command_user_time (user_id, executed_at),
    KEY idx_container_command_module_time (module_id, executed_at),
    KEY idx_container_command_container_time (container_name, executed_at),
    KEY idx_container_command_category_time (cmd_category, executed_at),
    KEY idx_container_command_request_id (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

MAX_COMMAND_LENGTH = 2048
MAX_CWD_LENGTH = 1024
MAX_OUTPUT_DIGEST_LENGTH = 512

_schema_ready = False


def ensure_container_command_schema() -> None:
    """Create command-event and learning-event tables once per process."""
    global _schema_ready
    if _schema_ready:
        return
    ensure_database()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(CONTAINER_COMMAND_EVENT_TABLE_SQL)
            cursor.execute(LEARNING_EVENT_TABLE_SQL)
            cursor.execute(ERROR_EVENT_TABLE_SQL)
        conn.commit()
    _schema_ready = True


def _to_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=_json_default)


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, str) and value.strip():
        raw = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(raw)
            if parsed.tzinfo:
                return parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
        except ValueError:
            pass
    return datetime.utcnow()


def _limit_text(value: Any, max_length: int) -> str:
    text = str(value or "").replace("\x00", "").strip()
    if len(text) <= max_length:
        return text
    digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"{text[: max_length - 24]}...[sha256:{digest}]"


def normalize_command(command: str) -> str:
    """Normalize unstable command arguments so later aggregation can group similar behavior."""
    text = re.sub(r"\s+", " ", command.strip())
    text = re.sub(r"https?://\S+", "<url>", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<ip>", text)
    text = re.sub(r"(?<!\w)/(?:[\w.\-]+/)*[\w.\-]+", "<path>", text)
    text = re.sub(r"\b[0-9a-f]{16,}\b", "<hex>", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d+\b", "<num>", text)
    text = re.sub(r"'[^']*'|\"[^\"]*\"", "<str>", text)
    return _limit_text(text, MAX_COMMAND_LENGTH)


def classify_command(command: str) -> str:
    """Small rule set for first-pass behavior categories; no profiling/model logic here."""
    text = command.strip().lower()
    first = text.split(" ", 1)[0] if text else ""

    if re.search(r"(;|&&|\|\||\$\(|`|nc\s+-e|/bin/(ba)?sh|bash\s+-c|python\d?\s+-c|perl\s+-e|php\s+-r|msfconsole|payload|exploit)", text):
        return "exploit_attempt"
    if first in {"sudo", "su", "passwd"} or "/etc/shadow" in text or "suid" in text or " -perm " in text:
        return "privilege_escalation"
    if first in {"nmap", "masscan", "ping", "traceroute", "nc", "netcat", "telnet", "ssh", "ftp", "dig", "nslookup", "ifconfig", "ip"}:
        return "network_scan"
    if first in {"curl", "wget", "http", "httpie", "nikto", "sqlmap", "gobuster", "dirb", "dirsearch", "ffuf", "wfuzz", "hydra"}:
        return "web_test"
    if first in {"ls", "cat", "less", "more", "head", "tail", "cp", "mv", "rm", "touch", "mkdir", "rmdir", "chmod", "chown", "find", "grep", "sed", "awk", "tar", "zip", "unzip"}:
        return "file_op"
    if first in {"pwd", "whoami", "id", "uname", "ps", "top", "env", "printenv", "which", "whereis", "history", "netstat", "ss", "lsof", "dmesg"}:
        return "debugging"
    return "other"


def _output_digest(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    text = str(value).replace("\x00", "").strip()
    if len(text) <= MAX_OUTPUT_DIGEST_LENGTH:
        return text
    digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
    return f"{text[:430]}...[sha256:{digest}]"


def save_container_command_event(data: dict[str, Any]) -> dict[str, Any]:
    """Persist one container command event and mirror it into learning_event as COMMAND_EXEC."""
    ensure_container_command_schema()

    command = _limit_text(data.get("command"), MAX_COMMAND_LENGTH)
    if not command:
        raise ValueError("command is required")

    command_id = str(data.get("command_id") or f"cmd-{uuid4()}")
    request_id = str(data.get("request_id") or command_id)
    normalized_command = normalize_command(command)
    cmd_category = classify_command(command)
    executed_at = _parse_datetime(data.get("executed_at"))

    row = {
        "command_id": command_id,
        "lab_session_id": data.get("lab_session_id") or None,
        "user_id": _to_int(data.get("user_id")),
        "class_id": _to_int(data.get("class_id")),
        "course_id": _to_int(data.get("course_id")),
        "module_id": _to_int(data.get("module_id")),
        "task_id": _to_int(data.get("task_id")),
        "container_name": _limit_text(data.get("container_name"), 128) or None,
        "command": command,
        "normalized_command": normalized_command,
        "cmd_category": cmd_category,
        "cwd": _limit_text(data.get("cwd"), MAX_CWD_LENGTH) or None,
        "exit_code": _to_int(data.get("exit_code")),
        "duration_ms": _to_int(data.get("duration_ms")),
        "output_digest": _output_digest(data.get("output_digest")),
        "source": _limit_text(data.get("source") or "hook", 64) or "hook",
        "request_id": request_id,
        "executed_at": executed_at,
    }

    event_id = str(data.get("event_id") or f"evt-{uuid4()}")
    event_payload = {
        "event_id": event_id,
        "event_time": data.get("event_time") or data.get("executed_at") or executed_at,
        "command_id": command_id,
        "lab_session_id": row["lab_session_id"],
        "container_name": row["container_name"],
        "command": command,
        "normalized_command": normalized_command,
        "cmd_category": cmd_category,
        "cwd": row["cwd"],
        "exit_code": row["exit_code"],
        "duration_ms": row["duration_ms"],
        "output_digest": row["output_digest"],
        "source": row["source"],
        "request_id": request_id,
        "extra": data.get("extra") if isinstance(data.get("extra"), dict) else {},
    }

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO container_command_event (
                    command_id, lab_session_id, user_id, class_id, course_id,
                    module_id, task_id, container_name, command, normalized_command,
                    cmd_category, cwd, exit_code, duration_ms, output_digest,
                    source, request_id, executed_at
                ) VALUES (
                    %(command_id)s, %(lab_session_id)s, %(user_id)s, %(class_id)s,
                    %(course_id)s, %(module_id)s, %(task_id)s, %(container_name)s,
                    %(command)s, %(normalized_command)s, %(cmd_category)s, %(cwd)s,
                    %(exit_code)s, %(duration_ms)s, %(output_digest)s, %(source)s,
                    %(request_id)s, %(executed_at)s
                )
                """,
                row,
            )
            cursor.execute(
                """
                INSERT INTO learning_event (
                    event_id, user_id, class_id, course_id, module_id, task_id,
                    question_id, lab_session_id, event_type, event_time, payload_json,
                    source, request_id
                ) VALUES (
                    %(event_id)s, %(user_id)s, %(class_id)s, %(course_id)s,
                    %(module_id)s, %(task_id)s, NULL, %(lab_session_id)s,
                    'COMMAND_EXEC', %(event_time)s, %(payload_json)s,
                    %(source)s, %(request_id)s
                )
                """,
                {
                    "event_id": event_id,
                    "user_id": row["user_id"],
                    "class_id": row["class_id"],
                    "course_id": row["course_id"],
                    "module_id": row["module_id"],
                    "task_id": row["task_id"],
                    "lab_session_id": row["lab_session_id"],
                    "event_time": executed_at,
                    "payload_json": _json_dumps(event_payload),
                    "source": row["source"],
                    "request_id": request_id,
                },
            )
            derived_error = build_error_from_command(row)
            if derived_error:
                insert_error_event(cursor, derived_error)
        conn.commit()

    return {
        "command_id": command_id,
        "saved": True,
        "normalized_command": normalized_command,
        "cmd_category": cmd_category,
        "message": "command event saved",
    }
