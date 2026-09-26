import json
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from database import ensure_database, get_connection
from event_repository import LEARNING_EVENT_TABLE_SQL


ERROR_EVENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS error_event (
    error_id VARCHAR(64) NOT NULL,
    lab_session_id VARCHAR(64) NULL,
    user_id BIGINT NULL,
    class_id BIGINT NULL,
    course_id BIGINT NULL,
    module_id BIGINT NULL,
    task_id BIGINT NULL,
    container_name VARCHAR(128) NULL,
    command_id VARCHAR(64) NULL,
    error_signature VARCHAR(64) NOT NULL,
    error_category VARCHAR(64) NOT NULL,
    raw_excerpt VARCHAR(1024) NULL,
    severity VARCHAR(32) NOT NULL DEFAULT 'low',
    source VARCHAR(64) NOT NULL DEFAULT 'api',
    request_id VARCHAR(64) NULL,
    occurred_at DATETIME(6) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (error_id),
    KEY idx_error_event_session_time (lab_session_id, occurred_at),
    KEY idx_error_event_user_time (user_id, occurred_at),
    KEY idx_error_event_module_time (module_id, occurred_at),
    KEY idx_error_event_command (command_id),
    KEY idx_error_event_signature_time (error_signature, occurred_at),
    KEY idx_error_event_category_time (error_category, occurred_at),
    KEY idx_error_event_request_id (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

SIGNATURE_CATEGORY = {
    "permission_denied": "permission",
    "command_not_found": "runtime",
    "syntax_error": "syntax",
    "connection_refused": "network",
    "file_not_found": "file",
    "flag_incorrect": "flag",
    "timeout": "network",
    "runtime_error": "runtime",
    "other": "other",
}

SIGNATURE_SEVERITY = {
    "permission_denied": "high",
    "connection_refused": "high",
    "timeout": "high",
    "runtime_error": "high",
    "syntax_error": "medium",
    "file_not_found": "medium",
    "flag_incorrect": "medium",
    "command_not_found": "medium",
    "other": "low",
}

VALID_SIGNATURES = set(SIGNATURE_CATEGORY)
VALID_CATEGORIES = {"permission", "syntax", "network", "file", "flag", "runtime", "other"}
VALID_SEVERITIES = {"low", "medium", "high"}
MAX_EXCERPT_LENGTH = 1024

_schema_ready = False


def ensure_error_schema() -> None:
    """Create error-event and learning-event tables once per process."""
    global _schema_ready
    if _schema_ready:
        return
    ensure_database()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(ERROR_EVENT_TABLE_SQL)
            cursor.execute(LEARNING_EVENT_TABLE_SQL)
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
    return text[:max_length]


def classify_error_excerpt(raw_excerpt: Any, *, exit_code: Any = None) -> dict[str, str]:
    """Rule-based error parser for command output/exit code; no profiling logic."""
    excerpt = str(raw_excerpt or "")
    text = excerpt.lower()
    code = _to_int(exit_code)

    if "permission denied" in text or "operation not permitted" in text or "eacces" in text or code == 126:
        signature = "permission_denied"
    elif "command not found" in text or (re.search(r"\bnot found\b", text) and code == 127) or code == 127:
        signature = "command_not_found"
    elif "syntax error" in text or "unexpected token" in text or "parse error" in text:
        signature = "syntax_error"
    elif "connection refused" in text or "could not connect" in text or "couldn't connect" in text:
        signature = "connection_refused"
    elif "no such file or directory" in text or "cannot stat" in text or "file not found" in text:
        signature = "file_not_found"
    elif "timed out" in text or "timeout" in text:
        signature = "timeout"
    elif "traceback" in text or "exception" in text or "fatal error" in text or "segmentation fault" in text or (code is not None and code != 0):
        signature = "runtime_error"
    else:
        signature = "other"

    return {
        "error_signature": signature,
        "error_category": SIGNATURE_CATEGORY[signature],
        "severity": SIGNATURE_SEVERITY[signature],
    }


def normalize_error_fields(data: dict[str, Any]) -> dict[str, str]:
    signature = str(data.get("error_signature") or "").strip().lower()
    if not signature or signature not in VALID_SIGNATURES:
        parsed = classify_error_excerpt(data.get("raw_excerpt"), exit_code=data.get("exit_code"))
        signature = parsed["error_signature"]
        category = parsed["error_category"]
        severity = parsed["severity"]
    else:
        category = str(data.get("error_category") or SIGNATURE_CATEGORY.get(signature) or "other").strip().lower()
        if category not in VALID_CATEGORIES:
            category = SIGNATURE_CATEGORY.get(signature, "other")
        severity = str(data.get("severity") or SIGNATURE_SEVERITY.get(signature) or "low").strip().lower()
        if severity not in VALID_SEVERITIES:
            severity = SIGNATURE_SEVERITY.get(signature, "low")
    return {
        "error_signature": signature,
        "error_category": category,
        "severity": severity,
    }


def build_error_from_command(command_row: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Derive one structured error from a command event when we have enough signal."""
    exit_code = _to_int(command_row.get("exit_code"))
    excerpt = command_row.get("output_digest") or ""
    if (exit_code is None or exit_code == 0) and not excerpt:
        return None

    parsed = classify_error_excerpt(excerpt, exit_code=exit_code)
    if parsed["error_signature"] == "other" and (exit_code is None or exit_code == 0):
        return None

    raw_excerpt = excerpt or f"command exited with code {exit_code}: {command_row.get('command') or ''}"
    return {
        "lab_session_id": command_row.get("lab_session_id"),
        "user_id": command_row.get("user_id"),
        "class_id": command_row.get("class_id"),
        "course_id": command_row.get("course_id"),
        "module_id": command_row.get("module_id"),
        "task_id": command_row.get("task_id"),
        "container_name": command_row.get("container_name"),
        "command_id": command_row.get("command_id"),
        "raw_excerpt": raw_excerpt,
        "source": "command_hook",
        "request_id": f"err-{command_row.get('request_id') or command_row.get('command_id')}",
        "occurred_at": command_row.get("executed_at"),
        **parsed,
    }


def insert_error_event(cursor, data: dict[str, Any]) -> dict[str, Any]:
    """Insert error_event and mirrored ERROR_EVENT learning_event using an existing transaction."""
    normalized = normalize_error_fields(data)
    error_id = str(data.get("error_id") or f"err-{uuid4()}")
    request_id = str(data.get("request_id") or error_id)
    occurred_at = _parse_datetime(data.get("occurred_at"))
    row = {
        "error_id": error_id,
        "lab_session_id": data.get("lab_session_id") or None,
        "user_id": _to_int(data.get("user_id")),
        "class_id": _to_int(data.get("class_id")),
        "course_id": _to_int(data.get("course_id")),
        "module_id": _to_int(data.get("module_id")),
        "task_id": _to_int(data.get("task_id")),
        "container_name": _limit_text(data.get("container_name"), 128) or None,
        "command_id": _limit_text(data.get("command_id"), 64) or None,
        "error_signature": normalized["error_signature"],
        "error_category": normalized["error_category"],
        "raw_excerpt": _limit_text(data.get("raw_excerpt"), MAX_EXCERPT_LENGTH) or None,
        "severity": normalized["severity"],
        "source": _limit_text(data.get("source") or "api", 64) or "api",
        "request_id": request_id,
        "occurred_at": occurred_at,
    }
    cursor.execute(
        """
        INSERT INTO error_event (
            error_id, lab_session_id, user_id, class_id, course_id, module_id,
            task_id, container_name, command_id, error_signature, error_category,
            raw_excerpt, severity, source, request_id, occurred_at
        ) VALUES (
            %(error_id)s, %(lab_session_id)s, %(user_id)s, %(class_id)s,
            %(course_id)s, %(module_id)s, %(task_id)s, %(container_name)s,
            %(command_id)s, %(error_signature)s, %(error_category)s,
            %(raw_excerpt)s, %(severity)s, %(source)s, %(request_id)s,
            %(occurred_at)s
        )
        """,
        row,
    )

    payload = {
        "event_id": data.get("event_id"),
        "event_time": data.get("event_time") or data.get("occurred_at") or occurred_at,
        "error_id": error_id,
        "lab_session_id": row["lab_session_id"],
        "container_name": row["container_name"],
        "command_id": row["command_id"],
        "error_signature": row["error_signature"],
        "error_category": row["error_category"],
        "raw_excerpt": row["raw_excerpt"],
        "severity": row["severity"],
        "source": row["source"],
        "request_id": request_id,
        "extra": data.get("extra") if isinstance(data.get("extra"), dict) else {},
    }
    cursor.execute(
        """
        INSERT INTO learning_event (
            event_id, user_id, class_id, course_id, module_id, task_id,
            question_id, lab_session_id, event_type, event_time, payload_json,
            source, request_id
        ) VALUES (
            %(event_id)s, %(user_id)s, %(class_id)s, %(course_id)s,
            %(module_id)s, %(task_id)s, NULL, %(lab_session_id)s,
            'ERROR_EVENT', %(event_time)s, %(payload_json)s,
            %(source)s, %(request_id)s
        )
        """,
        {
            "event_id": str(data.get("event_id") or f"evt-{uuid4()}"),
            "user_id": row["user_id"],
            "class_id": row["class_id"],
            "course_id": row["course_id"],
            "module_id": row["module_id"],
            "task_id": row["task_id"],
            "lab_session_id": row["lab_session_id"],
            "event_time": occurred_at,
            "payload_json": _json_dumps(payload),
            "source": row["source"],
            "request_id": request_id,
        },
    )
    return {
        "error_id": error_id,
        "saved": True,
        "error_signature": row["error_signature"],
        "error_category": row["error_category"],
        "severity": row["severity"],
        "message": "error event saved",
    }


def save_error_event(data: dict[str, Any]) -> dict[str, Any]:
    """Persist one structured error and mirror it into learning_event."""
    ensure_error_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            result = insert_error_event(cursor, data)
        conn.commit()
    return result
