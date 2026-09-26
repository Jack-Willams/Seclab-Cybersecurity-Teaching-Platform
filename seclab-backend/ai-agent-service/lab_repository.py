import json
import os
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from database import ensure_database, get_connection
from error_repository import ERROR_EVENT_TABLE_SQL, insert_error_event
from event_repository import LEARNING_EVENT_TABLE_SQL


LAB_SESSION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS lab_session (
    session_id VARCHAR(64) NOT NULL,
    user_id BIGINT NULL,
    class_id BIGINT NULL,
    course_id BIGINT NULL,
    module_id BIGINT NULL,
    task_id BIGINT NULL,
    container_name VARCHAR(128) NULL,
    container_id VARCHAR(128) NULL,
    target_url VARCHAR(512) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    start_time DATETIME(6) NOT NULL,
    end_time DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (session_id),
    KEY idx_lab_session_user_time (user_id, start_time),
    KEY idx_lab_session_module_time (module_id, start_time),
    KEY idx_lab_session_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

FLAG_SUBMISSION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS flag_submission (
    submission_id VARCHAR(64) NOT NULL,
    user_id BIGINT NULL,
    class_id BIGINT NULL,
    course_id BIGINT NULL,
    module_id BIGINT NULL,
    task_id BIGINT NULL,
    lab_session_id VARCHAR(64) NULL,
    container_name VARCHAR(128) NULL,
    flag_text VARCHAR(512) NOT NULL,
    is_correct TINYINT(1) NOT NULL DEFAULT 0,
    score DECIMAL(8,2) NOT NULL DEFAULT 0,
    request_id VARCHAR(64) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (submission_id),
    KEY idx_flag_submission_user_time (user_id, created_at),
    KEY idx_flag_submission_session_time (lab_session_id, created_at),
    KEY idx_flag_submission_module_time (module_id, created_at),
    KEY idx_flag_submission_request_id (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

CHALLENGE_COMPLETION_EVENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS challenge_completion_event (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id BIGINT NULL,
    class_id BIGINT NULL,
    course_id BIGINT NULL,
    module_id BIGINT NULL,
    task_id BIGINT NULL,
    lab_session_id VARCHAR(64) NULL,
    completion_status VARCHAR(32) NOT NULL,
    total_time_seconds INT NULL,
    total_ai_ask_count INT NOT NULL DEFAULT 0,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    KEY idx_completion_user_time (user_id, created_at),
    KEY idx_completion_session (lab_session_id),
    KEY idx_completion_module_time (module_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

DEFAULT_FLAG_ANSWERS: dict[str, str] = {
    "1": "flag{union_sqli_pwn3d_2024}",
    "2": "flag{xss_master_2024}",
    "3": "flag{csrf_master_2024}",
    "4": "flag{y0u_d1d_@_Go0d_j0b!]}",
    "5": "flag{file_upload_master_2024}",
    "6": "flag{directory_traversal_master_2024}",
    "sqli-lab-web-1": "flag{union_sqli_pwn3d_2024}",
    "xss-lab-web-1": "flag{xss_master_2024}",
    "csrf-lab-web-1": "flag{csrf_master_2024}",
    "cmd-inject-web-1": "flag{y0u_d1d_@_Go0d_j0b!]}",
    "upload-lab-web-1": "flag{file_upload_master_2024}",
    "dir-lab-web-1": "flag{directory_traversal_master_2024}",
    "15": "flag{Trick_or_Treat_St4ck_0verfl0w}",
    "stack-overflow-lab-web-1": "flag{Trick_or_Treat_St4ck_0verfl0w}",
}

_schema_ready = False


def ensure_lab_schema() -> None:
    """Create lab-session, flag, completion, and learning-event tables once per process."""
    global _schema_ready
    if _schema_ready:
        return
    ensure_database()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(LAB_SESSION_TABLE_SQL)
            cursor.execute(FLAG_SUBMISSION_TABLE_SQL)
            cursor.execute(CHALLENGE_COMPLETION_EVENT_TABLE_SQL)
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


def _insert_learning_event(cursor, *, event_type: str, context: dict[str, Any], payload: dict[str, Any]) -> str:
    event_id = str(context.get("event_id") or payload.get("event_id") or f"evt-{uuid4()}")
    request_id = context.get("request_id") or payload.get("request_id") or event_id
    source = str(context.get("source") or payload.get("source") or "ai-agent-service")
    event_time = _parse_datetime(context.get("event_time") or payload.get("event_time"))
    cursor.execute(
        """
        INSERT INTO learning_event (
            event_id, user_id, class_id, course_id, module_id, task_id,
            question_id, lab_session_id, event_type, event_time, payload_json,
            source, request_id
        ) VALUES (
            %(event_id)s, %(user_id)s, %(class_id)s, %(course_id)s,
            %(module_id)s, %(task_id)s, NULL, %(lab_session_id)s,
            %(event_type)s, %(event_time)s, %(payload_json)s,
            %(source)s, %(request_id)s
        )
        """,
        {
            "event_id": event_id,
            "user_id": _to_int(context.get("user_id")),
            "class_id": _to_int(context.get("class_id")),
            "course_id": _to_int(context.get("course_id")),
            "module_id": _to_int(context.get("module_id")),
            "task_id": _to_int(context.get("task_id")),
            "lab_session_id": context.get("lab_session_id") or None,
            "event_type": event_type,
            "event_time": event_time,
            "payload_json": _json_dumps(payload),
            "source": source,
            "request_id": str(request_id) if request_id else None,
        },
    )
    return event_id


def _flag_answers() -> dict[str, str]:
    answers = dict(DEFAULT_FLAG_ANSWERS)
    raw = os.getenv("FLAG_ANSWERS_JSON", "").strip()
    if raw:
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                answers.update({str(key): str(value) for key, value in loaded.items()})
        except json.JSONDecodeError:
            pass
    return answers


def _expected_flag(data: dict[str, Any]) -> Optional[str]:
    answers = _flag_answers()
    container_name = str(data.get("container_name") or "")
    module_id = data.get("module_id")
    task_id = data.get("task_id")
    for key in (container_name, str(module_id or ""), str(task_id or "")):
        if key and key in answers:
            return answers[key]
    return None


def _normalize_flag(value: Any) -> str:
    return str(value or "").strip()


def _count_ai_user_messages(cursor, session_id: str) -> int:
    if not session_id:
        return 0
    try:
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM ai_message m
            JOIN ai_conversation c ON c.conversation_id = m.conversation_id
            WHERE c.lab_session_id = %(session_id)s AND m.role = 'user'
            """,
            {"session_id": session_id},
        )
        return int((cursor.fetchone() or {}).get("total") or 0)
    except Exception:
        return 0


def start_lab_session(data: dict[str, Any]) -> dict[str, Any]:
    """Create a lab session and persist LAB_START."""
    ensure_lab_schema()

    session_id = str(data.get("session_id") or f"lab-{uuid4()}")
    now = datetime.utcnow()
    row = {
        "session_id": session_id,
        "user_id": _to_int(data.get("user_id")),
        "class_id": _to_int(data.get("class_id")),
        "course_id": _to_int(data.get("course_id")),
        "module_id": _to_int(data.get("module_id")),
        "task_id": _to_int(data.get("task_id")),
        "container_name": data.get("container_name") or None,
        "container_id": data.get("container_id") or None,
        "target_url": data.get("target_url") or None,
        "status": "running",
        "start_time": now,
    }

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO lab_session (
                    session_id, user_id, class_id, course_id, module_id, task_id,
                    container_name, container_id, target_url, status, start_time
                ) VALUES (
                    %(session_id)s, %(user_id)s, %(class_id)s, %(course_id)s,
                    %(module_id)s, %(task_id)s, %(container_name)s, %(container_id)s,
                    %(target_url)s, %(status)s, %(start_time)s
                )
                """,
                row,
            )
            _insert_learning_event(
                cursor,
                event_type="LAB_START",
                context={
                    **row,
                    "lab_session_id": session_id,
                    "request_id": data.get("request_id"),
                    "event_id": data.get("event_id"),
                    "event_time": data.get("event_time"),
                    "source": data.get("source"),
                },
                payload={
                    "event_id": data.get("event_id"),
                    "event_time": data.get("event_time"),
                    "source": data.get("source"),
                    "session_id": session_id,
                    "lab_session_id": session_id,
                    "container_name": row["container_name"],
                    "container_id": row["container_id"],
                    "target_url": row["target_url"],
                    "status": row["status"],
                    "extra": data.get("extra") if isinstance(data.get("extra"), dict) else {},
                },
            )
        conn.commit()

    return {
        "session_id": session_id,
        "status": row["status"],
        "start_time": now.isoformat(),
    }


def stop_lab_session(session_id: str, data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Stop a lab session and persist LAB_STOP."""
    ensure_lab_schema()

    now = datetime.utcnow()
    data = data or {}
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM lab_session WHERE session_id = %(session_id)s", {"session_id": session_id})
            session = cursor.fetchone()
            if not session:
                raise KeyError("lab_session not found")
            cursor.execute(
                """
                UPDATE lab_session
                SET status = 'stopped', end_time = %(end_time)s
                WHERE session_id = %(session_id)s
                """,
                {"session_id": session_id, "end_time": now},
            )
            context = {**session, "lab_session_id": session_id}
            _insert_learning_event(
                cursor,
                event_type="LAB_STOP",
                context={
                    **context,
                    "request_id": data.get("request_id"),
                    "event_id": data.get("event_id"),
                    "event_time": data.get("event_time"),
                    "source": data.get("source"),
                },
                payload={
                    "event_id": data.get("event_id"),
                    "event_time": data.get("event_time"),
                    "source": data.get("source"),
                    "session_id": session_id,
                    "lab_session_id": session_id,
                    "container_name": data.get("container_name") or session.get("container_name"),
                    "target_url": data.get("target_url") or session.get("target_url"),
                    "status": "stopped",
                    "end_time": now,
                    "extra": data.get("extra") if isinstance(data.get("extra"), dict) else {},
                },
            )
        conn.commit()

    return {
        "session_id": session_id,
        "status": "stopped",
        "end_time": now.isoformat(),
    }


def submit_flag(data: dict[str, Any]) -> dict[str, Any]:
    """Judge a flag, persist submission, and complete the lab when correct."""
    ensure_lab_schema()

    flag_text = _normalize_flag(data.get("flag_text"))
    if not flag_text:
        raise ValueError("flag_text is required")

    session_id = data.get("lab_session_id") or None
    submission_id = str(data.get("submission_id") or f"flag-{uuid4()}")
    request_id = str(data.get("request_id") or submission_id)
    expected = _expected_flag(data)
    is_correct = expected is not None and flag_text == expected
    score = float(data.get("score") or data.get("question_score") or (10 if is_correct else 0) or 0)
    if not is_correct:
        score = 0

    with get_connection() as conn:
        with conn.cursor() as cursor:
            session = None
            total_time_seconds = None
            if session_id:
                cursor.execute("SELECT * FROM lab_session WHERE session_id = %(session_id)s", {"session_id": session_id})
                session = cursor.fetchone()

            row_context = {
                "user_id": data.get("user_id") or (session or {}).get("user_id"),
                "class_id": data.get("class_id") or (session or {}).get("class_id"),
                "course_id": data.get("course_id") or (session or {}).get("course_id"),
                "module_id": data.get("module_id") or (session or {}).get("module_id"),
                "task_id": data.get("task_id") or (session or {}).get("task_id"),
                "lab_session_id": session_id,
                "request_id": request_id,
            }
            if session and session.get("start_time"):
                total_time_seconds = max(0, int((datetime.utcnow() - session["start_time"]).total_seconds()))

            cursor.execute(
                """
                INSERT INTO flag_submission (
                    submission_id, user_id, class_id, course_id, module_id, task_id,
                    lab_session_id, container_name, flag_text, is_correct, score, request_id
                ) VALUES (
                    %(submission_id)s, %(user_id)s, %(class_id)s, %(course_id)s,
                    %(module_id)s, %(task_id)s, %(lab_session_id)s, %(container_name)s,
                    %(flag_text)s, %(is_correct)s, %(score)s, %(request_id)s
                )
                """,
                {
                    "submission_id": submission_id,
                    "user_id": _to_int(row_context.get("user_id")),
                    "class_id": _to_int(row_context.get("class_id")),
                    "course_id": _to_int(row_context.get("course_id")),
                    "module_id": _to_int(row_context.get("module_id")),
                    "task_id": _to_int(row_context.get("task_id")),
                    "lab_session_id": session_id,
                    "container_name": data.get("container_name") or (session or {}).get("container_name"),
                    "flag_text": flag_text,
                    "is_correct": 1 if is_correct else 0,
                    "score": score,
                    "request_id": request_id,
                },
            )
            _insert_learning_event(
                cursor,
                event_type="FLAG_SUBMIT",
                context={
                    **row_context,
                    "event_id": data.get("event_id"),
                    "event_time": data.get("event_time"),
                    "source": data.get("source"),
                },
                payload={
                    "event_id": data.get("event_id"),
                    "event_time": data.get("event_time"),
                    "source": data.get("source"),
                    "submission_id": submission_id,
                    "lab_session_id": session_id,
                    "container_name": data.get("container_name") or (session or {}).get("container_name"),
                    "flag_text": flag_text,
                    "is_correct": is_correct,
                    "score": score,
                    "request_id": request_id,
                    "extra": data.get("extra") if isinstance(data.get("extra"), dict) else {},
                },
            )
            if not is_correct:
                insert_error_event(
                    cursor,
                    {
                        **row_context,
                        "container_name": data.get("container_name") or (session or {}).get("container_name"),
                        "command_id": None,
                        "error_signature": "flag_incorrect",
                        "error_category": "flag",
                        "raw_excerpt": "submitted flag is incorrect",
                        "severity": "medium",
                        "source": "api",
                        "request_id": f"err-{request_id}",
                        "occurred_at": datetime.utcnow(),
                    },
                )

            completion_id = None
            if is_correct:
                if session_id:
                    cursor.execute(
                        """
                        UPDATE lab_session
                        SET status = 'completed', end_time = COALESCE(end_time, %(end_time)s)
                        WHERE session_id = %(session_id)s
                        """,
                        {"session_id": session_id, "end_time": datetime.utcnow()},
                    )
                ai_count = _count_ai_user_messages(cursor, session_id or "")
                cursor.execute(
                    """
                    INSERT INTO challenge_completion_event (
                        user_id, class_id, course_id, module_id, task_id, lab_session_id,
                        completion_status, total_time_seconds, total_ai_ask_count
                    ) VALUES (
                        %(user_id)s, %(class_id)s, %(course_id)s, %(module_id)s,
                        %(task_id)s, %(lab_session_id)s, 'completed',
                        %(total_time_seconds)s, %(total_ai_ask_count)s
                    )
                    """,
                    {
                        "user_id": _to_int(row_context.get("user_id")),
                        "class_id": _to_int(row_context.get("class_id")),
                        "course_id": _to_int(row_context.get("course_id")),
                        "module_id": _to_int(row_context.get("module_id")),
                        "task_id": _to_int(row_context.get("task_id")),
                        "lab_session_id": session_id,
                        "total_time_seconds": total_time_seconds,
                        "total_ai_ask_count": ai_count,
                    },
                )
                completion_id = cursor.lastrowid
                _insert_learning_event(
                    cursor,
                    event_type="CHALLENGE_COMPLETED",
                    context={**row_context, "source": data.get("source")},
                    payload={
                        "completion_id": completion_id,
                        "submission_id": submission_id,
                        "lab_session_id": session_id,
                        "completion_status": "completed",
                        "total_time_seconds": total_time_seconds,
                        "total_ai_ask_count": ai_count,
                    },
                )
        conn.commit()

    return {
        "submission_id": submission_id,
        "is_correct": is_correct,
        "score": score,
        "completed": is_correct,
        "completion_id": completion_id,
        "message": "Flag 正确，实验已完成。" if is_correct else "Flag 错误，请继续尝试。",
    }
