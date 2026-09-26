import json
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional, Sequence
from uuid import uuid4

from database import ensure_database, get_connection
from question_repository import ensure_question_schema, question_numeric_id


KNOWLEDGE_POINT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_point (
    knowledge_point_id BIGINT NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(64) NULL,
    description TEXT NULL,
    difficulty_level VARCHAR(32) NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (knowledge_point_id),
    KEY idx_knowledge_point_category (category),
    KEY idx_knowledge_point_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

MODULE_KNOWLEDGE_POINT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS module_knowledge_point (
    id BIGINT NOT NULL AUTO_INCREMENT,
    module_id BIGINT NOT NULL,
    knowledge_point_id BIGINT NOT NULL,
    relevance_weight DECIMAL(5,2) NOT NULL DEFAULT 1.00,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uk_module_knowledge_point (module_id, knowledge_point_id),
    KEY idx_module_kp_module (module_id),
    KEY idx_module_kp_kp (knowledge_point_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

TASK_KNOWLEDGE_POINT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS task_knowledge_point (
    id BIGINT NOT NULL AUTO_INCREMENT,
    module_id BIGINT NULL,
    task_id BIGINT NOT NULL,
    knowledge_point_id BIGINT NOT NULL,
    relevance_weight DECIMAL(5,2) NOT NULL DEFAULT 1.00,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uk_task_knowledge_point (module_id, task_id, knowledge_point_id),
    KEY idx_task_kp_task (task_id),
    KEY idx_task_kp_module_task (module_id, task_id),
    KEY idx_task_kp_kp (knowledge_point_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

QUESTION_KNOWLEDGE_POINT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS question_knowledge_point (
    id BIGINT NOT NULL AUTO_INCREMENT,
    question_id BIGINT NULL,
    question_uid VARCHAR(128) NULL,
    generated_question_id VARCHAR(64) NULL,
    knowledge_point_id BIGINT NOT NULL,
    relevance_weight DECIMAL(5,2) NOT NULL DEFAULT 1.00,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    KEY idx_question_kp_question_id (question_id),
    KEY idx_question_kp_question_uid (question_uid),
    KEY idx_question_kp_generated (generated_question_id),
    KEY idx_question_kp_kp (knowledge_point_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

TRAINING_SESSION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS training_session (
    training_session_id VARCHAR(64) NOT NULL,
    user_id BIGINT NOT NULL,
    class_id BIGINT NULL,
    course_id BIGINT NULL,
    profile_snapshot_id VARCHAR(64) NULL,
    source_type VARCHAR(64) NOT NULL DEFAULT 'personalized_training',
    diagnose_result_json JSON NOT NULL,
    training_context_json JSON NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (training_session_id),
    KEY idx_training_session_user_time (user_id, created_at),
    KEY idx_training_session_course_time (course_id, created_at),
    KEY idx_training_session_profile (profile_snapshot_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

GENERATED_QUESTION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS generated_question (
    generated_question_id VARCHAR(64) NOT NULL,
    question_numeric_id BIGINT NOT NULL,
    training_session_id VARCHAR(64) NOT NULL,
    question_type VARCHAR(64) NOT NULL,
    knowledge_point_id BIGINT NULL,
    module_id BIGINT NULL,
    task_id BIGINT NULL,
    difficulty VARCHAR(32) NULL,
    title VARCHAR(255) NOT NULL,
    stem TEXT NOT NULL,
    options_json JSON NULL,
    standard_answer TEXT NULL,
    reference_answer TEXT NULL,
    explanation TEXT NULL,
    scoring_rubric_json JSON NULL,
    source_model VARCHAR(128) NULL,
    raw_ai_json JSON NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (generated_question_id),
    UNIQUE KEY uk_generated_question_numeric (question_numeric_id),
    KEY idx_generated_question_session (training_session_id),
    KEY idx_generated_question_kp (knowledge_point_id),
    KEY idx_generated_question_module_task (module_id, task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

GENERATED_QUESTION_ATTEMPT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS generated_question_attempt (
    attempt_id VARCHAR(64) NOT NULL,
    training_session_id VARCHAR(64) NOT NULL,
    generated_question_id VARCHAR(64) NOT NULL,
    user_id BIGINT NOT NULL,
    answer_json JSON NOT NULL,
    is_correct TINYINT(1) NULL,
    score DECIMAL(8,2) NOT NULL DEFAULT 0,
    cost_time INT NULL,
    submission_id VARCHAR(64) NULL,
    profile_rebuild_snapshot_id VARCHAR(64) NULL,
    submitted_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (attempt_id),
    KEY idx_generated_attempt_session (training_session_id, submitted_at),
    KEY idx_generated_attempt_question (generated_question_id, submitted_at),
    KEY idx_generated_attempt_user_time (user_id, submitted_at),
    KEY idx_generated_attempt_submission (submission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

_schema_ready = False


DEFAULT_KNOWLEDGE_POINTS = [
    (101, "SQL注入联合查询列数判断", "SQL注入", "通过ORDER BY、UNION SELECT等方式判断字段数和回显位。", "medium"),
    (102, "SQL盲注与时间延迟判断", "SQL注入", "通过布尔条件或sleep延迟推断数据库内容。", "medium"),
    (201, "XSS输入输出上下文判断", "XSS", "识别HTML、属性、脚本等上下文并选择合适payload。", "easy"),
    (301, "CSRF Token校验与请求伪造", "CSRF", "理解跨站请求伪造、Token绑定和Referer校验。", "medium"),
    (401, "无空格命令执行绕过", "命令执行", "使用IFS、变量替换、重定向等方式替代空格完成命令拼接。", "medium"),
    (402, "命令执行黑名单字符绕过", "命令执行", "针对过滤规则使用编码、拼接、环境变量或通配符绕过。", "hard"),
    (501, "文件上传类型校验绕过", "文件上传", "围绕后缀、MIME、Content-Type和解析差异构造上传绕过。", "medium"),
    (601, "目录遍历路径规范化绕过", "目录遍历", "理解../、编码、绝对路径和路径归一化绕过。", "medium"),
]

DEFAULT_MODULE_KP = [
    (1, 101),
    (1, 102),
    (2, 201),
    (3, 301),
    (4, 401),
    (4, 402),
    (5, 501),
    (6, 601),
]

DEFAULT_TASK_KP = [
    (1, 1, 101),
    (1, 2, 102),
    (2, 1, 201),
    (3, 1, 301),
    (4, 1, 401),
    (4, 2, 402),
    (5, 1, 501),
    (6, 1, 601),
]


def ensure_training_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    ensure_question_schema()
    ensure_database()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for sql in (
                KNOWLEDGE_POINT_TABLE_SQL,
                MODULE_KNOWLEDGE_POINT_TABLE_SQL,
                TASK_KNOWLEDGE_POINT_TABLE_SQL,
                QUESTION_KNOWLEDGE_POINT_TABLE_SQL,
                TRAINING_SESSION_TABLE_SQL,
                GENERATED_QUESTION_TABLE_SQL,
                GENERATED_QUESTION_ATTEMPT_TABLE_SQL,
            ):
                cursor.execute(sql)
            _seed_default_knowledge_points(cursor)
        conn.commit()
    _schema_ready = True


def _seed_default_knowledge_points(cursor) -> None:
    for kp_id, name, category, description, difficulty in DEFAULT_KNOWLEDGE_POINTS:
        cursor.execute(
            """
            INSERT INTO knowledge_point (
                knowledge_point_id, name, category, description, difficulty_level, is_active
            ) VALUES (
                %(knowledge_point_id)s, %(name)s, %(category)s, %(description)s, %(difficulty_level)s, 1
            )
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                category = VALUES(category),
                description = VALUES(description),
                difficulty_level = VALUES(difficulty_level),
                is_active = 1
            """,
            {
                "knowledge_point_id": kp_id,
                "name": name,
                "category": category,
                "description": description,
                "difficulty_level": difficulty,
            },
        )
    for module_id, kp_id in DEFAULT_MODULE_KP:
        cursor.execute(
            """
            INSERT IGNORE INTO module_knowledge_point (module_id, knowledge_point_id, relevance_weight)
            VALUES (%(module_id)s, %(knowledge_point_id)s, 1.00)
            """,
            {"module_id": module_id, "knowledge_point_id": kp_id},
        )
    for module_id, task_id, kp_id in DEFAULT_TASK_KP:
        cursor.execute(
            """
            INSERT IGNORE INTO task_knowledge_point (module_id, task_id, knowledge_point_id, relevance_weight)
            VALUES (%(module_id)s, %(task_id)s, %(knowledge_point_id)s, 1.00)
            """,
            {"module_id": module_id, "task_id": task_id, "knowledge_point_id": kp_id},
        )


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=_json_default)


def _json_loads(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _to_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _serialize_time(value: Any) -> Any:
    return value.isoformat() if isinstance(value, datetime) else value


def _serialize_session(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["diagnose_result"] = _json_loads(result.pop("diagnose_result_json", None), {})
    result["training_context"] = _json_loads(result.pop("training_context_json", None), {})
    result["created_at"] = _serialize_time(result.get("created_at"))
    return result


def _serialize_question(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["question_id"] = result.get("generated_question_id")
    result["options"] = _json_loads(result.pop("options_json", None), [])
    result["scoring_rubric"] = _json_loads(result.pop("scoring_rubric_json", None), [])
    result["raw_ai"] = _json_loads(result.pop("raw_ai_json", None), {})
    result["created_at"] = _serialize_time(result.get("created_at"))
    return result


def _serialize_attempt(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["answer"] = _json_loads(result.pop("answer_json", None), None)
    result["score"] = _to_float(result.get("score"))
    if result.get("is_correct") is not None:
        result["is_correct"] = bool(result["is_correct"])
    result["submitted_at"] = _serialize_time(result.get("submitted_at"))
    return result


def get_knowledge_mappings(
    *,
    module_id: Optional[int] = None,
    task_id: Optional[int] = None,
    question_id: Optional[Any] = None,
) -> list[dict[str, Any]]:
    ensure_training_schema()
    params: dict[str, Any] = {}
    union_sql: list[str] = []

    if question_id is not None:
        question_uid = str(question_id)
        numeric_id = question_numeric_id(question_id)
        params.update({"question_uid": question_uid, "question_numeric_id": numeric_id})
        union_sql.append(
            """
            SELECT kp.*, qkp.question_id, qkp.question_uid, qkp.generated_question_id,
                   NULL AS module_id, NULL AS task_id, qkp.relevance_weight, 'question' AS mapping_source
            FROM question_knowledge_point qkp
            JOIN knowledge_point kp ON kp.knowledge_point_id = qkp.knowledge_point_id
            WHERE kp.is_active = 1
              AND (qkp.question_uid = %(question_uid)s OR qkp.question_id = %(question_numeric_id)s)
            """
        )

    if task_id is not None:
        params["task_id"] = task_id
        params["module_id"] = module_id
        union_sql.append(
            """
            SELECT kp.*, NULL AS question_id, NULL AS question_uid, NULL AS generated_question_id,
                   tkp.module_id, tkp.task_id, tkp.relevance_weight, 'task' AS mapping_source
            FROM task_knowledge_point tkp
            JOIN knowledge_point kp ON kp.knowledge_point_id = tkp.knowledge_point_id
            WHERE kp.is_active = 1
              AND tkp.task_id = %(task_id)s
              AND (%(module_id)s IS NULL OR tkp.module_id = %(module_id)s)
            """
        )

    if module_id is not None:
        params["module_id"] = module_id
        union_sql.append(
            """
            SELECT kp.*, NULL AS question_id, NULL AS question_uid, NULL AS generated_question_id,
                   mkp.module_id, NULL AS task_id, mkp.relevance_weight, 'module' AS mapping_source
            FROM module_knowledge_point mkp
            JOIN knowledge_point kp ON kp.knowledge_point_id = mkp.knowledge_point_id
            WHERE kp.is_active = 1 AND mkp.module_id = %(module_id)s
            """
        )

    if not union_sql:
        union_sql.append(
            """
            SELECT kp.*, NULL AS question_id, NULL AS question_uid, NULL AS generated_question_id,
                   NULL AS module_id, NULL AS task_id, 0.50 AS relevance_weight, 'fallback' AS mapping_source
            FROM knowledge_point kp
            WHERE kp.is_active = 1
            """
        )

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(" UNION ALL ".join(union_sql), params)
            rows = list(cursor.fetchall() or [])
    return rows


def list_active_knowledge_points(limit: int = 20) -> list[dict[str, Any]]:
    ensure_training_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM knowledge_point
                WHERE is_active = 1
                ORDER BY knowledge_point_id ASC
                LIMIT %(limit)s
                """,
                {"limit": max(1, min(limit, 100))},
            )
            return list(cursor.fetchall() or [])


def fetch_recent_training_evidence(user_id: int, course_id: Optional[int] = None, limit: int = 50) -> dict[str, Any]:
    ensure_training_schema()
    params: dict[str, Any] = {"user_id": user_id, "limit": max(1, min(limit, 200))}
    course_filter = ""
    if course_id is not None:
        params["course_id"] = course_id
        course_filter = "AND (course_id = %(course_id)s OR course_id IS NULL)"

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT submission_id, question_id, question_uid, question_source,
                       training_session_id, knowledge_point_id, class_id, course_id,
                       module_id, task_id, question_type, is_correct, score, cost_time, created_at
                FROM question_submission
                WHERE user_id = %(user_id)s {course_filter}
                ORDER BY created_at DESC
                LIMIT %(limit)s
                """,
                params,
            )
            submissions = list(cursor.fetchall() or [])

            cursor.execute(
                f"""
                SELECT id, event_id, event_type, module_id, task_id, question_id,
                       event_time, payload_json, source, request_id
                FROM learning_event
                WHERE user_id = %(user_id)s {course_filter}
                ORDER BY event_time DESC, id DESC
                LIMIT %(limit)s
                """,
                params,
            )
            events = list(cursor.fetchall() or [])

            ai_topics: list[str] = []
            try:
                cursor.execute(
                    f"""
                    SELECT m.content
                    FROM ai_message m
                    JOIN ai_conversation c ON c.conversation_id = m.conversation_id
                    WHERE c.user_id = %(user_id)s {course_filter.replace("course_id", "c.course_id")}
                      AND m.role = 'user'
                    ORDER BY m.created_at DESC
                    LIMIT 10
                    """,
                    params,
                )
                ai_topics = [str(row.get("content") or "")[:120] for row in cursor.fetchall() or [] if row.get("content")]
            except Exception:
                ai_topics = []

    for row in submissions:
        row["score"] = _to_float(row.get("score"))
        row["created_at"] = _serialize_time(row.get("created_at"))
    for row in events:
        row["event_time"] = _serialize_time(row.get("event_time"))
        row["payload_json"] = _json_loads(row.get("payload_json"), {})

    return {
        "recent_submissions": submissions,
        "recent_events": events,
        "recent_ai_topics": ai_topics,
    }


def create_training_session(
    *,
    user_id: int,
    class_id: Optional[int],
    course_id: Optional[int],
    profile_snapshot_id: Optional[str],
    diagnose_result: dict[str, Any],
    training_context: Optional[dict[str, Any]] = None,
    training_session_id: Optional[str] = None,
) -> dict[str, Any]:
    ensure_training_schema()
    training_session_id = training_session_id or f"train-{uuid4()}"
    row = {
        "training_session_id": training_session_id,
        "user_id": user_id,
        "class_id": class_id,
        "course_id": course_id,
        "profile_snapshot_id": profile_snapshot_id,
        "source_type": "personalized_training",
        "diagnose_result_json": _json_dumps(diagnose_result),
        "training_context_json": _json_dumps(training_context or {}),
    }
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO training_session (
                    training_session_id, user_id, class_id, course_id, profile_snapshot_id,
                    source_type, diagnose_result_json, training_context_json
                ) VALUES (
                    %(training_session_id)s, %(user_id)s, %(class_id)s, %(course_id)s,
                    %(profile_snapshot_id)s, %(source_type)s, %(diagnose_result_json)s,
                    %(training_context_json)s
                )
                """,
                row,
            )
        conn.commit()
    return get_training_session(training_session_id) or {"training_session_id": training_session_id}


def save_generated_questions(
    *,
    training_session_id: str,
    questions: list[dict[str, Any]],
    source_model: str,
) -> list[dict[str, Any]]:
    ensure_training_schema()
    saved_ids: list[str] = []
    with get_connection() as conn:
        with conn.cursor() as cursor:
            for question in questions:
                generated_question_id = str(question.get("question_id") or question.get("generated_question_id") or f"gq-{uuid4()}")
                numeric_id = question_numeric_id(generated_question_id)
                kp_id = _to_int(question.get("knowledge_point_id"))
                row = {
                    "generated_question_id": generated_question_id,
                    "question_numeric_id": numeric_id,
                    "training_session_id": training_session_id,
                    "question_type": str(question.get("question_type") or "single_choice"),
                    "knowledge_point_id": kp_id,
                    "module_id": _to_int(question.get("module_id")),
                    "task_id": _to_int(question.get("task_id")),
                    "difficulty": question.get("difficulty") or None,
                    "title": str(question.get("title") or "个性化训练题"),
                    "stem": str(question.get("stem") or ""),
                    "options_json": _json_dumps(question.get("options")) if question.get("options") is not None else None,
                    "standard_answer": None if question.get("answer") is None else str(question.get("answer")),
                    "reference_answer": None if question.get("reference_answer") is None else str(question.get("reference_answer")),
                    "explanation": question.get("explanation") or None,
                    "scoring_rubric_json": _json_dumps(question.get("scoring_rubric")) if question.get("scoring_rubric") is not None else None,
                    "source_model": source_model,
                    "raw_ai_json": _json_dumps(question),
                }
                cursor.execute(
                    """
                    INSERT INTO generated_question (
                        generated_question_id, question_numeric_id, training_session_id,
                        question_type, knowledge_point_id, module_id, task_id, difficulty,
                        title, stem, options_json, standard_answer, reference_answer,
                        explanation, scoring_rubric_json, source_model, raw_ai_json
                    ) VALUES (
                        %(generated_question_id)s, %(question_numeric_id)s, %(training_session_id)s,
                        %(question_type)s, %(knowledge_point_id)s, %(module_id)s, %(task_id)s,
                        %(difficulty)s, %(title)s, %(stem)s, %(options_json)s, %(standard_answer)s,
                        %(reference_answer)s, %(explanation)s, %(scoring_rubric_json)s,
                        %(source_model)s, %(raw_ai_json)s
                    )
                    """,
                    row,
                )
                if kp_id is not None:
                    cursor.execute(
                        """
                        INSERT INTO question_knowledge_point (
                            question_id, question_uid, generated_question_id, knowledge_point_id, relevance_weight
                        ) VALUES (
                            %(question_id)s, %(question_uid)s, %(generated_question_id)s, %(knowledge_point_id)s, 1.00
                        )
                        """,
                        {
                            "question_id": numeric_id,
                            "question_uid": generated_question_id,
                            "generated_question_id": generated_question_id,
                            "knowledge_point_id": kp_id,
                        },
                    )
                saved_ids.append(generated_question_id)
        conn.commit()
    return [item for item in list_generated_questions(training_session_id) if item["generated_question_id"] in saved_ids]


def get_training_session(training_session_id: str) -> Optional[dict[str, Any]]:
    ensure_training_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM training_session WHERE training_session_id = %(training_session_id)s",
                {"training_session_id": training_session_id},
            )
            row = cursor.fetchone()
    return _serialize_session(row) if row else None


def list_generated_questions(training_session_id: str) -> list[dict[str, Any]]:
    ensure_training_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM generated_question
                WHERE training_session_id = %(training_session_id)s
                ORDER BY created_at ASC, generated_question_id ASC
                """,
                {"training_session_id": training_session_id},
            )
            rows = list(cursor.fetchall() or [])
    return [_serialize_question(row) for row in rows]


def get_generated_question(generated_question_id: str) -> Optional[dict[str, Any]]:
    ensure_training_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM generated_question WHERE generated_question_id = %(generated_question_id)s",
                {"generated_question_id": generated_question_id},
            )
            row = cursor.fetchone()
    return _serialize_question(row) if row else None


def list_user_training_sessions(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    ensure_training_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT ts.*,
                       (
                           SELECT COUNT(*)
                           FROM generated_question gq
                           WHERE gq.training_session_id = ts.training_session_id
                       ) AS question_count,
                       (
                           SELECT COUNT(*)
                           FROM generated_question_attempt gqa
                           WHERE gqa.training_session_id = ts.training_session_id
                       ) AS attempt_count
                FROM training_session ts
                WHERE ts.user_id = %(user_id)s
                ORDER BY ts.created_at DESC
                LIMIT %(limit)s
                """,
                {"user_id": user_id, "limit": max(1, min(limit, 100))},
            )
            rows = list(cursor.fetchall() or [])
    result = []
    for row in rows:
        item = _serialize_session(row)
        item["question_count"] = int(row.get("question_count") or 0)
        item["attempt_count"] = int(row.get("attempt_count") or 0)
        result.append(item)
    return result


def save_generated_question_attempt(
    *,
    training_session_id: str,
    generated_question_id: str,
    user_id: int,
    answer: Any,
    is_correct: Optional[bool],
    score: float,
    cost_time: Optional[int],
    submission_id: Optional[str],
    profile_rebuild_snapshot_id: Optional[str] = None,
) -> dict[str, Any]:
    ensure_training_schema()
    attempt_id = f"attempt-{uuid4()}"
    row = {
        "attempt_id": attempt_id,
        "training_session_id": training_session_id,
        "generated_question_id": generated_question_id,
        "user_id": user_id,
        "answer_json": _json_dumps(answer),
        "is_correct": None if is_correct is None else (1 if is_correct else 0),
        "score": score,
        "cost_time": cost_time,
        "submission_id": submission_id,
        "profile_rebuild_snapshot_id": profile_rebuild_snapshot_id,
    }
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO generated_question_attempt (
                    attempt_id, training_session_id, generated_question_id, user_id,
                    answer_json, is_correct, score, cost_time, submission_id,
                    profile_rebuild_snapshot_id
                ) VALUES (
                    %(attempt_id)s, %(training_session_id)s, %(generated_question_id)s,
                    %(user_id)s, %(answer_json)s, %(is_correct)s, %(score)s,
                    %(cost_time)s, %(submission_id)s, %(profile_rebuild_snapshot_id)s
                )
                """,
                row,
            )
        conn.commit()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM generated_question_attempt WHERE attempt_id = %(attempt_id)s",
                {"attempt_id": attempt_id},
            )
            saved = cursor.fetchone()
    return _serialize_attempt(saved or row)


def list_generated_question_attempts(
    training_session_id: str,
    user_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    ensure_training_schema()
    params: dict[str, Any] = {"training_session_id": training_session_id}
    user_filter = ""
    if user_id is not None:
        params["user_id"] = user_id
        user_filter = "AND user_id = %(user_id)s"
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *
                FROM generated_question_attempt
                WHERE training_session_id = %(training_session_id)s
                  {user_filter}
                ORDER BY submitted_at ASC, attempt_id ASC
                """,
                params,
            )
            rows = list(cursor.fetchall() or [])
    return [_serialize_attempt(row) for row in rows]


def list_generated_question_attempts_for_sessions(
    training_session_ids: Sequence[str],
    user_id: Optional[int] = None,
) -> dict[str, list[dict[str, Any]]]:
    """一次取回多个会话的作答记录，按 training_session_id 分组返回。

    教师端「本实验全部做题情况」原先是按会话逐个调
    list_generated_question_attempts()，每个会话都要新建一次连接。班里题目一多就退化成
    N+1：242 班一门实验有 139 个会话，139 次往返要 1.7 秒，而同样的数据一条 IN 查询
    只要 23 毫秒。
    """
    ensure_training_schema()
    session_ids = [str(item) for item in training_session_ids if item]
    if not session_ids:
        return {}
    params: list[Any] = list(session_ids)
    user_filter = ""
    if user_id is not None:
        params.append(user_id)
        user_filter = "AND user_id = %s"
    placeholders = ", ".join(["%s"] * len(session_ids))
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *
                FROM generated_question_attempt
                WHERE training_session_id IN ({placeholders})
                  {user_filter}
                ORDER BY submitted_at ASC, attempt_id ASC
                """,
                params,
            )
            rows = list(cursor.fetchall() or [])
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("training_session_id"))].append(_serialize_attempt(row))
    return grouped
