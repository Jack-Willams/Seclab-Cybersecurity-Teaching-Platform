import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import pymysql

from database import ensure_database, get_connection


LEARNING_EVENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS learning_event (
    id BIGINT NOT NULL AUTO_INCREMENT,
    event_id VARCHAR(64) NOT NULL,
    user_id BIGINT NULL,
    class_id BIGINT NULL,
    course_id BIGINT NULL,
    module_id BIGINT NULL,
    task_id BIGINT NULL,
    question_id BIGINT NULL,
    lab_session_id VARCHAR(64) NULL,
    event_type VARCHAR(64) NOT NULL,
    event_time DATETIME(6) NOT NULL,
    payload_json JSON NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'ai-agent-service',
    request_id VARCHAR(64) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uk_learning_event_event_id (event_id),
    KEY idx_learning_event_user_time (user_id, event_time),
    KEY idx_learning_event_module_time (module_id, event_time),
    KEY idx_learning_event_lab_session_time (lab_session_id, event_time),
    KEY idx_learning_event_type_time (event_type, event_time),
    KEY idx_learning_event_request_id (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

_schema_ready = False


def ensure_schema() -> None:
    """Create database/table once per process."""
    global _schema_ready
    if _schema_ready:
        return
    ensure_database()
    with get_connection() as conn:
        with conn.cursor() as cursor:
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


def _parse_event_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, str) and value.strip():
        raw = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(raw)
            if parsed.tzinfo:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
        except ValueError:
            pass
    return datetime.utcnow()


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def save_learning_event(event_data: dict[str, Any]) -> dict[str, Any]:
    """Persist one learning event and return the stored row projection."""
    ensure_schema()

    event_type = event_data.get("type") or event_data.get("event_type")
    if not event_type:
        raise ValueError("event_type is required")

    event_id = str(event_data.get("event_id") or uuid4())
    request_id = event_data.get("request_id") or event_id
    source = event_data.get("source") or "ai-agent-service"
    event_time = _parse_event_time(event_data.get("event_time") or event_data.get("timestamp"))
    payload_json = json.dumps(event_data, ensure_ascii=False, default=_json_default)

    row = {
        "event_id": event_id,
        "user_id": _to_int(event_data.get("user_id")),
        "class_id": _to_int(event_data.get("class_id")),
        "course_id": _to_int(event_data.get("course_id")),
        "module_id": _to_int(event_data.get("module_id")),
        "task_id": _to_int(event_data.get("task_id")),
        "question_id": _to_int(event_data.get("question_id")),
        "lab_session_id": event_data.get("lab_session_id") or None,
        "event_type": str(event_type),
        "event_time": event_time,
        "payload_json": payload_json,
        "source": str(source),
        "request_id": str(request_id) if request_id else None,
    }

    sql = """
        INSERT INTO learning_event (
            event_id, user_id, class_id, course_id, module_id, task_id,
            question_id, lab_session_id, event_type, event_time, payload_json,
            source, request_id
        ) VALUES (
            %(event_id)s, %(user_id)s, %(class_id)s, %(course_id)s,
            %(module_id)s, %(task_id)s, %(question_id)s, %(lab_session_id)s,
            %(event_type)s, %(event_time)s, %(payload_json)s,
            %(source)s, %(request_id)s
        )
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute(sql, row)
                row["id"] = cursor.lastrowid
            except pymysql.err.IntegrityError as exc:
                if exc.args and exc.args[0] == 1062:
                    cursor.execute(
                        "SELECT id, event_id FROM learning_event WHERE event_id = %(event_id)s",
                        {"event_id": event_id},
                    )
                    existing = cursor.fetchone()
                    if existing:
                        row["id"] = existing["id"]
                        row["event_id"] = existing["event_id"]
                    else:
                        raise
                else:
                    raise
        conn.commit()
    return row


def list_learning_events(
    *,
    page: int = 1,
    page_size: int = 50,
    user_id: Optional[int] = None,
    module_id: Optional[int] = None,
    lab_session_id: Optional[str] = None,
    event_type: Optional[str] = None,
) -> dict[str, Any]:
    """Query learning events with filters and pagination."""
    ensure_schema()

    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    offset = (page - 1) * page_size

    where = []
    params: dict[str, Any] = {"limit": page_size, "offset": offset}
    if user_id is not None:
        where.append("user_id = %(user_id)s")
        params["user_id"] = user_id
    if module_id is not None:
        where.append("module_id = %(module_id)s")
        params["module_id"] = module_id
    if lab_session_id:
        where.append("lab_session_id = %(lab_session_id)s")
        params["lab_session_id"] = lab_session_id
    if event_type:
        where.append("event_type = %(event_type)s")
        params["event_type"] = event_type

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    count_sql = f"SELECT COUNT(*) AS total FROM learning_event {where_sql}"
    query_sql = f"""
        SELECT
            id, event_id, user_id, class_id, course_id, module_id, task_id,
            question_id, lab_session_id, event_type, event_time, payload_json,
            source, request_id, created_at
        FROM learning_event
        {where_sql}
        ORDER BY event_time DESC, id DESC
        LIMIT %(limit)s OFFSET %(offset)s
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(count_sql, params)
            total = int(cursor.fetchone()["total"])
            cursor.execute(query_sql, params)
            rows = cursor.fetchall()

    for row in rows:
        for key in ("event_time", "created_at"):
            if isinstance(row.get(key), datetime):
                row[key] = row[key].isoformat()
        payload = row.get("payload_json")
        if isinstance(payload, str):
            try:
                row["payload_json"] = json.loads(payload)
            except json.JSONDecodeError:
                pass

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "events": rows,
    }
