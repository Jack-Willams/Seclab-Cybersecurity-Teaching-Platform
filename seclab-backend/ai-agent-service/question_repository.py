import json
from datetime import datetime
import hashlib
from typing import Any, Optional
from uuid import uuid4

from database import ensure_database, get_connection
from event_repository import LEARNING_EVENT_TABLE_SQL


QUESTION_SUBMISSION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS question_submission (
    submission_id VARCHAR(64) NOT NULL,
    user_id BIGINT NULL,
    class_id BIGINT NULL,
    course_id BIGINT NULL,
    module_id BIGINT NULL,
    task_id BIGINT NULL,
    question_id BIGINT NOT NULL,
    question_uid VARCHAR(128) NULL,
    question_type VARCHAR(64) NOT NULL,
    answer_json JSON NOT NULL,
    standard_answer_json JSON NULL,
    question_snapshot_json JSON NULL,
    is_correct TINYINT(1) NULL,
    score DECIMAL(8,2) NOT NULL DEFAULT 0,
    cost_time INT NULL,
    question_source VARCHAR(64) NOT NULL DEFAULT 'course_question',
    training_session_id VARCHAR(64) NULL,
    knowledge_point_id BIGINT NULL,
    request_id VARCHAR(64) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (submission_id),
    KEY idx_question_submission_user_time (user_id, created_at),
    KEY idx_question_submission_module_time (module_id, created_at),
    KEY idx_question_submission_question_time (question_id, created_at),
    KEY idx_question_submission_uid (question_uid),
    KEY idx_question_submission_training (training_session_id, created_at),
    KEY idx_question_submission_kp_time (knowledge_point_id, created_at),
    KEY idx_question_submission_source_time (question_source, created_at),
    KEY idx_question_submission_request_id (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

_schema_ready = False


def ensure_question_schema() -> None:
    """Create submission and learning_event tables once per process."""
    global _schema_ready
    if _schema_ready:
        return
    ensure_database()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(QUESTION_SUBMISSION_TABLE_SQL)
            _ensure_question_submission_columns(cursor)
            cursor.execute(LEARNING_EVENT_TABLE_SQL)
        conn.commit()
    _schema_ready = True


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE %(column_name)s", {"column_name": column_name})
    return cursor.fetchone() is not None


def _index_exists(cursor, table_name: str, index_name: str) -> bool:
    cursor.execute(f"SHOW INDEX FROM {table_name} WHERE Key_name = %(index_name)s", {"index_name": index_name})
    return cursor.fetchone() is not None


def _ensure_question_submission_columns(cursor) -> None:
    additions = [
        ("question_uid", "ALTER TABLE question_submission ADD COLUMN question_uid VARCHAR(128) NULL AFTER question_id"),
        (
            "question_source",
            "ALTER TABLE question_submission ADD COLUMN question_source VARCHAR(64) NOT NULL DEFAULT 'course_question' AFTER cost_time",
        ),
        (
            "question_snapshot_json",
            "ALTER TABLE question_submission ADD COLUMN question_snapshot_json JSON NULL AFTER standard_answer_json",
        ),
        (
            "training_session_id",
            "ALTER TABLE question_submission ADD COLUMN training_session_id VARCHAR(64) NULL AFTER question_source",
        ),
        (
            "knowledge_point_id",
            "ALTER TABLE question_submission ADD COLUMN knowledge_point_id BIGINT NULL AFTER training_session_id",
        ),
    ]
    for column_name, sql in additions:
        if not _column_exists(cursor, "question_submission", column_name):
            cursor.execute(sql)

    indexes = [
        ("idx_question_submission_uid", "CREATE INDEX idx_question_submission_uid ON question_submission (question_uid)"),
        (
            "idx_question_submission_training",
            "CREATE INDEX idx_question_submission_training ON question_submission (training_session_id, created_at)",
        ),
        (
            "idx_question_submission_kp_time",
            "CREATE INDEX idx_question_submission_kp_time ON question_submission (knowledge_point_id, created_at)",
        ),
        (
            "idx_question_submission_source_time",
            "CREATE INDEX idx_question_submission_source_time ON question_submission (question_source, created_at)",
        ),
    ]
    for index_name, sql in indexes:
        if not _index_exists(cursor, "question_submission", index_name):
            cursor.execute(sql)


def _to_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def question_numeric_id(value: Any) -> int:
    direct = _to_int(value)
    if direct is not None:
        return direct
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("question_id is required")
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return int.from_bytes(digest[:7], "big")


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=_json_default)


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    raw = str(value or "").strip()
    if not raw:
        return datetime.utcnow()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return datetime.utcnow()


def _extract_standard_answer(data: dict[str, Any]) -> Any:
    question = data.get("question_snapshot") or data.get("question") or {}
    if data.get("standard_answer") is not None:
        return data.get("standard_answer")
    if data.get("reference_answer") is not None:
        return data.get("reference_answer")
    if isinstance(question, dict):
        if question.get("answer") is not None:
            return question.get("answer")
        if question.get("standard_answer") is not None:
            return question.get("standard_answer")
        if question.get("reference_answer") is not None:
            return question.get("reference_answer")
        if question.get("correctAnswer") is not None:
            return question.get("correctAnswer")
    return None


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _answer_to_indices(value: Any, options: list[Any]) -> list[int]:
    option_text_to_index = {str(option): index for index, option in enumerate(options)}
    letter_to_index = {chr(ord("A") + index): index for index in range(len(options))}
    result: list[int] = []
    for item in _as_list(value):
        if isinstance(item, int):
            result.append(item)
            continue
        if isinstance(item, str):
            text = item.strip()
            if text in option_text_to_index:
                result.append(option_text_to_index[text])
            elif text.upper() in letter_to_index:
                result.append(letter_to_index[text.upper()])
            else:
                try:
                    result.append(int(text))
                except ValueError:
                    pass
    return sorted(set(result))


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _judge_answer(data: dict[str, Any]) -> dict[str, Any]:
    question_type = str(data.get("question_type") or "").strip()
    normalized_type = question_type.replace("-", "_")
    question = data.get("question_snapshot") or data.get("question") or {}
    options = question.get("options") if isinstance(question, dict) else []
    options = options if isinstance(options, list) else []
    standard_answer = _extract_standard_answer(data)
    user_answer = data.get("answer")
    max_score = float(data.get("question_score") or (question.get("score") if isinstance(question, dict) else 0) or 0)

    if standard_answer is None:
        return {
            "is_correct": None,
            "score": 0,
            "standard_answer": None,
            "message": "提交已记录；当前题目暂无标准答案，暂不自动判分。",
        }

    if normalized_type in ("single_choice", "multiple_choice", "single", "choice"):
        expected = _answer_to_indices(standard_answer, options)
        actual = _answer_to_indices(user_answer, options)
        is_correct = actual == expected
    else:
        expected_values = [_normalize_text(item) for item in _as_list(standard_answer)]
        actual_text = _normalize_text(user_answer)
        is_correct = actual_text in expected_values

    return {
        "is_correct": is_correct,
        "score": max_score if is_correct else 0,
        "standard_answer": standard_answer,
        "message": "答案正确。" if is_correct else "答案错误，请重试。",
    }


def save_question_submission(data: dict[str, Any]) -> dict[str, Any]:
    """Judge a question submission and persist submission + QUESTION_SUBMIT event atomically."""
    ensure_question_schema()

    question_uid = str(data.get("question_uid") or data.get("question_id") or "").strip()
    question_id = question_numeric_id(data.get("question_numeric_id") or data.get("question_id"))
    question_type = str(data.get("question_type") or "")
    if not question_type:
        raise ValueError("question_type is required")
    question_source = str(data.get("question_source") or "course_question")

    result = _judge_answer(data)
    submission_id = str(data.get("submission_id") or f"sub-{uuid4()}")
    request_id = str(data.get("request_id") or submission_id)
    now = datetime.utcnow()
    answer_json = _json_dumps(data.get("answer"))
    standard_answer_json = _json_dumps(result["standard_answer"]) if result["standard_answer"] is not None else None
    question_snapshot = data.get("question_snapshot") or data.get("question")
    question_snapshot_json = _json_dumps(question_snapshot) if isinstance(question_snapshot, dict) else None

    row = {
        "submission_id": submission_id,
        "user_id": _to_int(data.get("user_id")),
        "class_id": _to_int(data.get("class_id")),
        "course_id": _to_int(data.get("course_id")),
        "module_id": _to_int(data.get("module_id")),
        "task_id": _to_int(data.get("task_id")),
        "question_id": question_id,
        "question_uid": question_uid or str(question_id),
        "question_type": question_type,
        "answer_json": answer_json,
        "standard_answer_json": standard_answer_json,
        "question_snapshot_json": question_snapshot_json,
        "is_correct": None if result["is_correct"] is None else (1 if result["is_correct"] else 0),
        "score": result["score"],
        "cost_time": _to_int(data.get("cost_time")),
        "question_source": question_source,
        "training_session_id": data.get("training_session_id") or None,
        "knowledge_point_id": _to_int(data.get("knowledge_point_id")),
        "request_id": request_id,
    }

    event_id = str(data.get("event_id") or f"evt-{uuid4()}")
    event_payload = {
        "event_id": event_id,
        "event_time": data.get("event_time") or now,
        "submission_id": submission_id,
        "lab_session_id": data.get("lab_session_id") or None,
        "question_id": question_id,
        "question_uid": row["question_uid"],
        "question_type": question_type,
        "question_source": question_source,
        "training_session_id": row["training_session_id"],
        "knowledge_point_id": row["knowledge_point_id"],
        "is_correct": result["is_correct"],
        "score": result["score"],
        "cost_time": row["cost_time"],
        "answer": data.get("answer"),
        "standard_answer": result["standard_answer"],
        "source": data.get("source") or "ai-agent-service",
        "request_id": request_id,
        "extra": data.get("extra") if isinstance(data.get("extra"), dict) else {},
    }

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO question_submission (
                    submission_id, user_id, class_id, course_id, module_id,
                    task_id, question_id, question_uid, question_type, answer_json,
                    standard_answer_json, question_snapshot_json, is_correct, score, cost_time,
                    question_source, training_session_id, knowledge_point_id, request_id
                ) VALUES (
                    %(submission_id)s, %(user_id)s, %(class_id)s, %(course_id)s,
                    %(module_id)s, %(task_id)s, %(question_id)s, %(question_uid)s,
                    %(question_type)s, %(answer_json)s, %(standard_answer_json)s,
                    %(question_snapshot_json)s, %(is_correct)s, %(score)s, %(cost_time)s, %(question_source)s,
                    %(training_session_id)s, %(knowledge_point_id)s, %(request_id)s
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
                    %(module_id)s, %(task_id)s, %(question_id)s, %(lab_session_id)s,
                    'QUESTION_SUBMIT', %(event_time)s, %(payload_json)s,
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
                    "question_id": row["question_id"],
                    "lab_session_id": data.get("lab_session_id") or None,
                    "event_time": _parse_datetime(data.get("event_time")) if data.get("event_time") else now,
                    "payload_json": _json_dumps(event_payload),
                    "source": event_payload["source"],
                    "request_id": request_id,
                },
            )
        conn.commit()

    return {
        "submission_id": submission_id,
        "question_id": row["question_uid"],
        "question_numeric_id": row["question_id"],
        "question_source": row["question_source"],
        "training_session_id": row["training_session_id"],
        "knowledge_point_id": row["knowledge_point_id"],
        "is_correct": result["is_correct"],
        "score": result["score"],
        "correct_answer": result["standard_answer"],
        "message": result["message"],
    }
