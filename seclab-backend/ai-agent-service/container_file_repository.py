import json
import os
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from database import ensure_database, get_connection
from event_repository import LEARNING_EVENT_TABLE_SQL


CONTAINER_FILE_EVENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS container_file_event (
    file_event_id VARCHAR(64) NOT NULL,
    lab_session_id VARCHAR(64) NULL,
    user_id BIGINT NULL,
    class_id BIGINT NULL,
    course_id BIGINT NULL,
    module_id BIGINT NULL,
    task_id BIGINT NULL,
    container_name VARCHAR(128) NULL,
    file_path VARCHAR(2048) NOT NULL,
    file_ext VARCHAR(32) NULL,
    action VARCHAR(32) NOT NULL,
    size_before BIGINT NULL,
    size_after BIGINT NULL,
    sha256 VARCHAR(64) NULL,
    is_key_file TINYINT(1) NOT NULL DEFAULT 0,
    source VARCHAR(64) NOT NULL DEFAULT 'watcher',
    request_id VARCHAR(64) NULL,
    changed_at DATETIME(6) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (file_event_id),
    KEY idx_container_file_session_time (lab_session_id, changed_at),
    KEY idx_container_file_user_time (user_id, changed_at),
    KEY idx_container_file_module_time (module_id, changed_at),
    KEY idx_container_file_container_time (container_name, changed_at),
    KEY idx_container_file_action_time (action, changed_at),
    KEY idx_container_file_request_id (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

VALID_ACTIONS = {"create", "modify", "delete"}
MAX_PATH_LENGTH = 2048
KEY_FILE_NAMES = {"exploit.py", "payload.txt", "script.sh", "index.php", "config.php"}
KEY_FILE_EXTS = {".php", ".py", ".sh"}

_schema_ready = False


def ensure_container_file_schema() -> None:
    """Create file-event and learning-event tables once per process."""
    global _schema_ready
    if _schema_ready:
        return
    ensure_database()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(CONTAINER_FILE_EVENT_TABLE_SQL)
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


def _normalize_ext(value: Any, file_path: str) -> Optional[str]:
    ext = str(value or "").strip().lower()
    if not ext:
        ext = os.path.splitext(file_path)[1].lower()
    if ext and not ext.startswith("."):
        ext = f".{ext}"
    return _limit_text(ext, 32) or None


def _normalize_sha256(value: Any) -> Optional[str]:
    text = str(value or "").strip().lower()
    if not text:
        return None
    if len(text) == 64 and all(ch in "0123456789abcdef" for ch in text):
        return text
    return None


def is_key_file_path(file_path: str, file_ext: Optional[str]) -> bool:
    name = os.path.basename(file_path).lower()
    ext = (file_ext or os.path.splitext(file_path)[1]).lower()
    return name in KEY_FILE_NAMES or ext in KEY_FILE_EXTS


def save_container_file_event(data: dict[str, Any]) -> dict[str, Any]:
    """Persist one container file event and mirror it into learning_event as FILE_CHANGE."""
    ensure_container_file_schema()

    file_path = _limit_text(data.get("file_path"), MAX_PATH_LENGTH)
    if not file_path:
        raise ValueError("file_path is required")

    action = str(data.get("action") or "").strip().lower()
    if action not in VALID_ACTIONS:
        raise ValueError("action must be one of create, modify, delete")

    file_ext = _normalize_ext(data.get("file_ext"), file_path)
    provided_is_key = data.get("is_key_file")
    is_key_file = bool(provided_is_key) if provided_is_key is not None else is_key_file_path(file_path, file_ext)
    file_event_id = str(data.get("file_event_id") or f"file-{uuid4()}")
    request_id = str(data.get("request_id") or file_event_id)
    changed_at = _parse_datetime(data.get("changed_at"))

    row = {
        "file_event_id": file_event_id,
        "lab_session_id": data.get("lab_session_id") or None,
        "user_id": _to_int(data.get("user_id")),
        "class_id": _to_int(data.get("class_id")),
        "course_id": _to_int(data.get("course_id")),
        "module_id": _to_int(data.get("module_id")),
        "task_id": _to_int(data.get("task_id")),
        "container_name": _limit_text(data.get("container_name"), 128) or None,
        "file_path": file_path,
        "file_ext": file_ext,
        "action": action,
        "size_before": _to_int(data.get("size_before")),
        "size_after": _to_int(data.get("size_after")),
        "sha256": _normalize_sha256(data.get("sha256")),
        "is_key_file": 1 if is_key_file else 0,
        "source": _limit_text(data.get("source") or "watcher", 64) or "watcher",
        "request_id": request_id,
        "changed_at": changed_at,
    }

    event_id = str(data.get("event_id") or f"evt-{uuid4()}")
    event_payload = {
        "event_id": event_id,
        "event_time": data.get("event_time") or data.get("changed_at") or changed_at,
        "file_event_id": file_event_id,
        "lab_session_id": row["lab_session_id"],
        "container_name": row["container_name"],
        "file_path": file_path,
        "file_ext": file_ext,
        "action": action,
        "size_before": row["size_before"],
        "size_after": row["size_after"],
        "sha256": row["sha256"],
        "is_key_file": bool(is_key_file),
        "source": row["source"],
        "request_id": request_id,
        "extra": data.get("extra") if isinstance(data.get("extra"), dict) else {},
    }

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO container_file_event (
                    file_event_id, lab_session_id, user_id, class_id, course_id,
                    module_id, task_id, container_name, file_path, file_ext,
                    action, size_before, size_after, sha256, is_key_file,
                    source, request_id, changed_at
                ) VALUES (
                    %(file_event_id)s, %(lab_session_id)s, %(user_id)s, %(class_id)s,
                    %(course_id)s, %(module_id)s, %(task_id)s, %(container_name)s,
                    %(file_path)s, %(file_ext)s, %(action)s, %(size_before)s,
                    %(size_after)s, %(sha256)s, %(is_key_file)s, %(source)s,
                    %(request_id)s, %(changed_at)s
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
                    'FILE_CHANGE', %(event_time)s, %(payload_json)s,
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
                    "event_time": changed_at,
                    "payload_json": _json_dumps(event_payload),
                    "source": row["source"],
                    "request_id": request_id,
                },
            )
        conn.commit()

    return {
        "file_event_id": file_event_id,
        "saved": True,
        "is_key_file": bool(is_key_file),
        "message": "file event saved",
    }
