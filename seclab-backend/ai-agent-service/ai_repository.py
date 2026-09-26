import json
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from database import ensure_database, get_connection


AI_CHAT_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS ai_conversation (
        conversation_id VARCHAR(64) NOT NULL,
        user_id BIGINT NULL,
        class_id BIGINT NULL,
        course_id BIGINT NULL,
        module_id BIGINT NULL,
        task_id BIGINT NULL,
        question_id BIGINT NULL,
        lab_session_id VARCHAR(64) NULL,
        dify_conversation_id VARCHAR(128) NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'active',
        source VARCHAR(64) NOT NULL DEFAULT 'ai-agent-service',
        start_time DATETIME(6) NOT NULL,
        last_message_at DATETIME(6) NOT NULL,
        created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
        updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
        PRIMARY KEY (conversation_id),
        UNIQUE KEY uk_ai_conversation_dify_id (dify_conversation_id),
        KEY idx_ai_conversation_user_time (user_id, last_message_at),
        KEY idx_ai_conversation_module_time (module_id, last_message_at),
        KEY idx_ai_conversation_lab_session (lab_session_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_message (
        message_id VARCHAR(64) NOT NULL,
        conversation_id VARCHAR(64) NOT NULL,
        role VARCHAR(32) NOT NULL,
        content LONGTEXT NOT NULL,
        content_length INT NOT NULL DEFAULT 0,
        token_count INT NULL,
        event_name VARCHAR(64) NULL,
        hint_level VARCHAR(32) NULL,
        contains_context TINYINT(1) NOT NULL DEFAULT 0,
        contains_error_excerpt TINYINT(1) NOT NULL DEFAULT 0,
        raw_payload_json JSON NULL,
        created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
        PRIMARY KEY (message_id),
        KEY idx_ai_message_conversation_time (conversation_id, created_at),
        KEY idx_ai_message_role_time (role, created_at),
        CONSTRAINT fk_ai_message_conversation
            FOREIGN KEY (conversation_id) REFERENCES ai_conversation (conversation_id)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_tool_call (
        tool_call_id VARCHAR(64) NOT NULL,
        conversation_id VARCHAR(64) NOT NULL,
        message_id VARCHAR(64) NULL,
        tool_name VARCHAR(128) NOT NULL,
        tool_input_json JSON NULL,
        tool_output_json JSON NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'unknown',
        error_message TEXT NULL,
        created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
        PRIMARY KEY (tool_call_id),
        KEY idx_ai_tool_call_conversation_time (conversation_id, created_at),
        KEY idx_ai_tool_call_message (message_id),
        KEY idx_ai_tool_call_tool (tool_name),
        CONSTRAINT fk_ai_tool_call_conversation
            FOREIGN KEY (conversation_id) REFERENCES ai_conversation (conversation_id)
            ON DELETE CASCADE,
        CONSTRAINT fk_ai_tool_call_message
            FOREIGN KEY (message_id) REFERENCES ai_message (message_id)
            ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_context_injection (
        id BIGINT NOT NULL AUTO_INCREMENT,
        conversation_id VARCHAR(64) NOT NULL,
        message_id VARCHAR(64) NULL,
        context_type VARCHAR(64) NOT NULL,
        context_summary TEXT NULL,
        context_size INT NOT NULL DEFAULT 0,
        raw_context_json JSON NULL,
        created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
        PRIMARY KEY (id),
        KEY idx_ai_context_conversation_time (conversation_id, created_at),
        KEY idx_ai_context_message (message_id),
        CONSTRAINT fk_ai_context_conversation
            FOREIGN KEY (conversation_id) REFERENCES ai_conversation (conversation_id)
            ON DELETE CASCADE,
        CONSTRAINT fk_ai_context_message
            FOREIGN KEY (message_id) REFERENCES ai_message (message_id)
            ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """,
]

_schema_ready = False


def ensure_ai_schema() -> None:
    """Create AI chat persistence tables once per process."""
    global _schema_ready
    if _schema_ready:
        return
    ensure_database()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for sql in AI_CHAT_TABLES_SQL:
                cursor.execute(sql)
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


def _json_or_none(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    return _json_dumps(value)


def _safe_json_value(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {"text": value}
    return value


def _estimate_token_count(content: str) -> int:
    if not content:
        return 0
    return max(1, len(content) // 4)


def _contains_error_excerpt(content: str) -> bool:
    lowered = content.lower()
    return any(marker in lowered for marker in ("error", "exception", "traceback", "failed", "失败", "错误"))


def extract_chat_context(request_data: dict[str, Any]) -> dict[str, Any]:
    """Extract profile dimensions from request fields first, then from inputs."""
    inputs = request_data.get("inputs") or {}
    return {
        "user_id": _to_int(request_data.get("user_id") or inputs.get("user_id") or request_data.get("user")),
        "class_id": _to_int(request_data.get("class_id") or inputs.get("class_id")),
        "course_id": _to_int(request_data.get("course_id") or inputs.get("course_id")),
        "module_id": _to_int(request_data.get("module_id") or inputs.get("module_id")),
        "task_id": _to_int(request_data.get("task_id") or inputs.get("task_id")),
        "question_id": _to_int(request_data.get("question_id") or inputs.get("question_id")),
        "lab_session_id": request_data.get("lab_session_id") or inputs.get("lab_session_id") or None,
        "source": request_data.get("source") or inputs.get("source") or "floating-chat",
    }


def summarize_context(inputs: dict[str, Any]) -> str:
    if not inputs:
        return ""
    keys = ", ".join(sorted(str(key) for key in inputs.keys()))
    compact = _json_dumps(inputs)
    if len(compact) > 1200:
        compact = compact[:1200] + "...[truncated]"
    return f"keys=[{keys}] {compact}"


def get_or_create_conversation(
    *,
    request_conversation_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Find by local conversation_id or Dify conversation_id; create a local conversation if missing."""
    ensure_ai_schema()
    now = datetime.utcnow()
    lookup_id = (request_conversation_id or "").strip() or None

    with get_connection() as conn:
        with conn.cursor() as cursor:
            row = None
            if lookup_id:
                cursor.execute(
                    """
                    SELECT conversation_id, dify_conversation_id
                    FROM ai_conversation
                    WHERE conversation_id = %(id)s OR dify_conversation_id = %(id)s
                    LIMIT 1
                    """,
                    {"id": lookup_id},
                )
                row = cursor.fetchone()

            if row:
                conversation_id = row["conversation_id"]
                cursor.execute(
                    """
                    UPDATE ai_conversation
                    SET
                        user_id = COALESCE(%(user_id)s, user_id),
                        class_id = COALESCE(%(class_id)s, class_id),
                        course_id = COALESCE(%(course_id)s, course_id),
                        module_id = COALESCE(%(module_id)s, module_id),
                        task_id = COALESCE(%(task_id)s, task_id),
                        question_id = COALESCE(%(question_id)s, question_id),
                        lab_session_id = COALESCE(%(lab_session_id)s, lab_session_id),
                        last_message_at = %(now)s,
                        status = 'active'
                    WHERE conversation_id = %(conversation_id)s
                    """,
                    {**context, "conversation_id": conversation_id, "now": now},
                )
            else:
                conversation_id = f"conv-{uuid4()}"
                cursor.execute(
                    """
                    INSERT INTO ai_conversation (
                        conversation_id, user_id, class_id, course_id, module_id,
                        task_id, question_id, lab_session_id, dify_conversation_id,
                        status, source, start_time, last_message_at
                    ) VALUES (
                        %(conversation_id)s, %(user_id)s, %(class_id)s, %(course_id)s,
                        %(module_id)s, %(task_id)s, %(question_id)s, %(lab_session_id)s,
                        %(dify_conversation_id)s, 'active', %(source)s, %(now)s, %(now)s
                    )
                    """,
                    {
                        **context,
                        "conversation_id": conversation_id,
                        "dify_conversation_id": lookup_id,
                        "now": now,
                    },
                )
        conn.commit()

    return {"conversation_id": conversation_id, "request_conversation_id": lookup_id}


def update_conversation_after_stream(
    *,
    conversation_id: str,
    dify_conversation_id: Optional[str],
    status: str = "active",
) -> None:
    ensure_ai_schema()
    now = datetime.utcnow()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE ai_conversation
                SET
                    dify_conversation_id = COALESCE(%(dify_conversation_id)s, dify_conversation_id),
                    status = %(status)s,
                    last_message_at = %(now)s
                WHERE conversation_id = %(conversation_id)s
                """,
                {
                    "conversation_id": conversation_id,
                    "dify_conversation_id": dify_conversation_id,
                    "status": status,
                    "now": now,
                },
            )
        conn.commit()


def save_ai_message(
    *,
    conversation_id: str,
    role: str,
    content: str,
    event_name: Optional[str] = None,
    hint_level: Optional[str] = None,
    contains_context: bool = False,
    raw_payload: Optional[dict[str, Any]] = None,
    message_id: Optional[str] = None,
) -> dict[str, Any]:
    ensure_ai_schema()
    message_id = message_id or f"msg-{uuid4()}"
    if len(message_id) > 64:
        message_id = f"msg-{uuid4()}"
    content = content or ""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ai_message (
                    message_id, conversation_id, role, content, content_length,
                    token_count, event_name, hint_level, contains_context,
                    contains_error_excerpt, raw_payload_json
                ) VALUES (
                    %(message_id)s, %(conversation_id)s, %(role)s, %(content)s,
                    %(content_length)s, %(token_count)s, %(event_name)s, %(hint_level)s,
                    %(contains_context)s, %(contains_error_excerpt)s, %(raw_payload_json)s
                )
                """,
                {
                    "message_id": message_id,
                    "conversation_id": conversation_id,
                    "role": role,
                    "content": content,
                    "content_length": len(content),
                    "token_count": _estimate_token_count(content),
                    "event_name": event_name,
                    "hint_level": hint_level,
                    "contains_context": 1 if contains_context else 0,
                    "contains_error_excerpt": 1 if _contains_error_excerpt(content) else 0,
                    "raw_payload_json": _json_or_none(raw_payload),
                },
            )
            cursor.execute(
                """
                UPDATE ai_conversation
                SET last_message_at = %(now)s, status = 'active'
                WHERE conversation_id = %(conversation_id)s
                """,
                {"conversation_id": conversation_id, "now": datetime.utcnow()},
            )
        conn.commit()
    return {"message_id": message_id, "conversation_id": conversation_id}


def save_context_injection(
    *,
    conversation_id: str,
    message_id: str,
    context_type: str,
    raw_context: dict[str, Any],
) -> Optional[int]:
    ensure_ai_schema()
    if not raw_context:
        return None

    raw_json = _json_dumps(raw_context)
    summary = summarize_context(raw_context)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ai_context_injection (
                    conversation_id, message_id, context_type, context_summary,
                    context_size, raw_context_json
                ) VALUES (
                    %(conversation_id)s, %(message_id)s, %(context_type)s,
                    %(context_summary)s, %(context_size)s, %(raw_context_json)s
                )
                """,
                {
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                    "context_type": context_type,
                    "context_summary": summary,
                    "context_size": len(raw_json),
                    "raw_context_json": raw_json,
                },
            )
            row_id = cursor.lastrowid
        conn.commit()
    return row_id


def save_tool_calls(
    *,
    conversation_id: str,
    message_id: str,
    tool_calls: list[dict[str, Any]],
) -> None:
    ensure_ai_schema()
    if not tool_calls:
        return

    with get_connection() as conn:
        with conn.cursor() as cursor:
            for tool_call in tool_calls:
                tool_call_id = str(tool_call.get("tool_call_id") or tool_call.get("id") or f"tool-{uuid4()}")
                if len(tool_call_id) > 64:
                    tool_call_id = f"tool-{uuid4()}"
                cursor.execute(
                    """
                    INSERT INTO ai_tool_call (
                        tool_call_id, conversation_id, message_id, tool_name,
                        tool_input_json, tool_output_json, status, error_message
                    ) VALUES (
                        %(tool_call_id)s, %(conversation_id)s, %(message_id)s,
                        %(tool_name)s, %(tool_input_json)s, %(tool_output_json)s,
                        %(status)s, %(error_message)s
                    )
                    ON DUPLICATE KEY UPDATE
                        message_id = VALUES(message_id),
                        tool_input_json = VALUES(tool_input_json),
                        tool_output_json = VALUES(tool_output_json),
                        status = VALUES(status),
                        error_message = VALUES(error_message)
                    """,
                    {
                        "tool_call_id": tool_call_id,
                        "conversation_id": conversation_id,
                        "message_id": message_id,
                        "tool_name": str(tool_call.get("tool_name") or tool_call.get("tool") or "unknown"),
                        "tool_input_json": _json_or_none(_safe_json_value(tool_call.get("tool_input"))),
                        "tool_output_json": _json_or_none(_safe_json_value(tool_call.get("tool_output"))),
                        "status": str(tool_call.get("status") or "unknown"),
                        "error_message": tool_call.get("error_message"),
                    },
                )
        conn.commit()
