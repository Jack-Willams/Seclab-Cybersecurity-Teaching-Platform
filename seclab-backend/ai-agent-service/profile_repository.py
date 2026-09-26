import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from database import ensure_database, get_connection
from knowledge_repository import build_knowledge_tags


STUDENT_PROFILE_SNAPSHOT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS student_profile_snapshot (
    snapshot_id VARCHAR(64) NOT NULL,
    user_id BIGINT NOT NULL,
    class_id BIGINT NULL,
    course_id BIGINT NULL,
    computed_at DATETIME(6) NOT NULL,
    knowledge_mastery_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    troubleshooting_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    autonomy_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    ai_collaboration_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    engagement_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    overall_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    profile_summary_json JSON NOT NULL,
    source_range_start DATETIME(6) NULL,
    source_range_end DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (snapshot_id),
    KEY idx_student_profile_user_time (user_id, computed_at),
    KEY idx_student_profile_class_time (class_id, computed_at),
    KEY idx_student_profile_course_time (course_id, computed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

STUDENT_PROFILE_FEATURE_DAILY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS student_profile_feature_daily (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    stat_date DATE NOT NULL,
    question_submit_count INT NOT NULL DEFAULT 0,
    question_correct_count INT NOT NULL DEFAULT 0,
    flag_submit_count INT NOT NULL DEFAULT 0,
    flag_correct_count INT NOT NULL DEFAULT 0,
    lab_session_count INT NOT NULL DEFAULT 0,
    completed_lab_count INT NOT NULL DEFAULT 0,
    ai_message_count INT NOT NULL DEFAULT 0,
    ai_user_message_count INT NOT NULL DEFAULT 0,
    ai_assistant_message_count INT NOT NULL DEFAULT 0,
    command_count INT NOT NULL DEFAULT 0,
    unique_command_count INT NOT NULL DEFAULT 0,
    file_change_count INT NOT NULL DEFAULT 0,
    error_count INT NOT NULL DEFAULT 0,
    high_severity_error_count INT NOT NULL DEFAULT 0,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uk_profile_feature_user_date (user_id, stat_date),
    KEY idx_profile_feature_user_date (user_id, stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

_schema_ready = False

CALCULATION_VERSION = "capability-growth-v1"
NON_PRODUCTION_SOURCE_TOKENS = (
    "showcase-seed",
    "static-fallback",
    "mock",
    "demo",
    "test",
    "seed",
)

OVERALL_WEIGHTS = {
    "knowledge_mastery_score": 0.30,
    "troubleshooting_score": 0.20,
    "autonomy_score": 0.20,
    "ai_collaboration_score": 0.15,
    "engagement_score": 0.15,
}

DIMENSION_LABELS = {
    "knowledge_mastery_score": "知识掌握",
    "troubleshooting_score": "排障能力",
    "autonomy_score": "自主探索能力",
    "ai_collaboration_score": "AI 协作能力",
    "engagement_score": "学习投入度",
}

DIMENSION_CODES = {
    "knowledge_mastery_score": "knowledge_mastery",
    "troubleshooting_score": "troubleshooting",
    "autonomy_score": "autonomy",
    "ai_collaboration_score": "ai_collaboration",
    "engagement_score": "engagement",
}


def is_production_source(value: Any) -> bool:
    normalized = str(value or "").strip().lower()
    return bool(normalized) and not any(
        token in normalized for token in NON_PRODUCTION_SOURCE_TOKENS
    )


def build_data_provenance(
    source_counts: dict[str, int],
    eligible_record_count: int,
    excluded_record_count: int,
    unverifiable_record_count: int,
) -> dict[str, Any]:
    clean_source_counts = {
        str(source): max(0, int(count or 0))
        for source, count in source_counts.items()
        if str(source or "").strip() and int(count or 0) > 0
    }
    production_sources = sorted(
        source for source in clean_source_counts if is_production_source(source)
    )
    excluded_sources = sorted(
        source for source in clean_source_counts if not is_production_source(source)
    )
    eligible_count = max(0, int(eligible_record_count or 0))
    excluded_count = max(0, int(excluded_record_count or 0))
    unverifiable_count = max(0, int(unverifiable_record_count or 0))
    is_clean = (
        eligible_count > 0
        and excluded_count == 0
        and unverifiable_count == 0
    )
    return {
        "mode": "production_events" if is_clean else "mixed_or_insufficient_data",
        "calculationVersion": CALCULATION_VERSION,
        "eligibleRecordCount": eligible_count,
        "excludedRecordCount": excluded_count,
        "unverifiableRecordCount": unverifiable_count,
        "excludedReasons": excluded_sources,
        "sourceTypes": production_sources,
        "sourceCounts": clean_source_counts,
    }


def summarize_source_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts: dict[str, int] = defaultdict(int)
    eligible_count = 0
    excluded_count = 0
    unverifiable_count = 0
    for row in rows:
        count = max(0, int(row.get("record_count") or 0))
        source = str(row.get("source") or "").strip()
        if not source:
            unverifiable_count += count
            continue
        source_counts[source] += count
        if is_production_source(source):
            eligible_count += count
        else:
            excluded_count += count
    return build_data_provenance(
        dict(source_counts),
        eligible_count,
        excluded_count,
        unverifiable_count,
    )


def is_growth_eligible_snapshot(snapshot: dict[str, Any]) -> bool:
    summary = snapshot.get("profile_summary_json")
    if isinstance(summary, str):
        try:
            summary = json.loads(summary)
        except (TypeError, json.JSONDecodeError):
            return False
    if not isinstance(summary, dict):
        return False
    provenance = summary.get("data_provenance")
    if not isinstance(provenance, dict):
        return False
    return (
        provenance.get("mode") == "production_events"
        and provenance.get("calculationVersion") == CALCULATION_VERSION
        and int(provenance.get("eligibleRecordCount") or 0) > 0
        and int(provenance.get("excludedRecordCount") or 0) == 0
        and int(provenance.get("unverifiableRecordCount") or 0) == 0
    )

DIMENSION_BREAKDOWN = {
    "knowledge_mastery_score": {
        "label": "知识掌握",
        "weight": OVERALL_WEIGHTS["knowledge_mastery_score"],
        "components": [
            {"key": "course_question_accuracy", "label": "课程先导题正确率", "weight": 0.35},
            {"key": "lab_task_mastery", "label": "实验 Flag / 关键任务达成", "weight": 0.40},
            {"key": "training_question_accuracy", "label": "动态题库掌握度", "weight": 0.25},
        ],
    },
    "troubleshooting_score": {
        "label": "排障能力",
        "weight": OVERALL_WEIGHTS["troubleshooting_score"],
        "components": [
            {"key": "step_completion", "label": "当前步骤完成度", "weight": 0.30},
            {"key": "recovery_after_error", "label": "引导后恢复能力", "weight": 0.45},
            {"key": "verification_after_fix", "label": "修复验证能力", "weight": 0.25},
        ],
    },
    "autonomy_score": {
        "label": "自主探索",
        "weight": OVERALL_WEIGHTS["autonomy_score"],
        "components": [
            {"key": "path_diversity", "label": "有效探索路径多样性", "weight": 0.40},
            {"key": "effective_operations", "label": "有效操作行为", "weight": 0.30},
            {"key": "independent_attempt", "label": "独立尝试程度", "weight": 0.30},
        ],
    },
    "ai_collaboration_score": {
        "label": "AI协同",
        "weight": OVERALL_WEIGHTS["ai_collaboration_score"],
        "components": [
            {"key": "contextual_help_quality", "label": "上下文化求助质量", "weight": 0.35},
            {"key": "post_ai_action_conversion", "label": "AI 交互后行动转化", "weight": 0.40},
            {"key": "ai_usage_moderation", "label": "适度使用与依赖控制", "weight": 0.25},
        ],
    },
    "engagement_score": {
        "label": "学习投入",
        "weight": OVERALL_WEIGHTS["engagement_score"],
        "components": [
            {"key": "active_days", "label": "活跃天数", "weight": 0.30},
            {"key": "lab_participation", "label": "实验参与与完成", "weight": 0.35},
            {"key": "sustained_practice", "label": "持续练习行为", "weight": 0.35},
        ],
    },
}


def ensure_profile_schema() -> None:
    """Create profile snapshot and daily-feature tables once per process."""
    global _schema_ready
    if _schema_ready:
        return
    ensure_database()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(STUDENT_PROFILE_SNAPSHOT_TABLE_SQL)
            cursor.execute(STUDENT_PROFILE_FEATURE_DAILY_TABLE_SQL)
        conn.commit()
    _schema_ready = True


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=_json_default)


def _clamp(value: float, low: float = 0, high: float = 100) -> float:
    return round(max(low, min(high, value)), 2)


def _ratio(numerator: int | float, denominator: int | float) -> float:
    return 0.0 if not denominator else float(numerator) / float(denominator)


def _scalar(row: Optional[dict[str, Any]], key: str = "value", default: Any = 0) -> Any:
    return (row or {}).get(key, default) or default


def _fetch_one(cursor, sql: str, params: dict[str, Any]) -> dict[str, Any]:
    cursor.execute(sql, params)
    return cursor.fetchone() or {}


def _fetch_all(cursor, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    cursor.execute(sql, params)
    return list(cursor.fetchall() or [])


def _collect_data_provenance(cursor, user_id: int) -> dict[str, Any]:
    rows = _fetch_all(
        cursor,
        """
        SELECT source, COUNT(*) AS record_count
        FROM (
            SELECT NULLIF(TRIM(question_source), '') AS source
            FROM question_submission
            WHERE user_id = %(user_id)s

            UNION ALL
            SELECT NULLIF(TRIM(ts.source_type), '') AS source
            FROM generated_question_attempt gqa
            LEFT JOIN training_session ts
              ON ts.training_session_id = gqa.training_session_id
            WHERE gqa.user_id = %(user_id)s
              AND gqa.submission_id IS NULL

            UNION ALL
            SELECT COALESCE(
                (
                    SELECT NULLIF(TRIM(le.source), '')
                    FROM learning_event le
                    WHERE le.lab_session_id = fs.lab_session_id
                    ORDER BY le.event_time ASC
                    LIMIT 1
                ),
                (
                    SELECT NULLIF(TRIM(cce.source), '')
                    FROM container_command_event cce
                    WHERE cce.lab_session_id = fs.lab_session_id
                    ORDER BY cce.executed_at ASC
                    LIMIT 1
                )
            ) AS source
            FROM flag_submission fs
            WHERE fs.user_id = %(user_id)s

            UNION ALL
            SELECT COALESCE(
                (
                    SELECT NULLIF(TRIM(le.source), '')
                    FROM learning_event le
                    WHERE le.lab_session_id = ls.session_id
                    ORDER BY le.event_time ASC
                    LIMIT 1
                ),
                (
                    SELECT NULLIF(TRIM(cce.source), '')
                    FROM container_command_event cce
                    WHERE cce.lab_session_id = ls.session_id
                    ORDER BY cce.executed_at ASC
                    LIMIT 1
                )
            ) AS source
            FROM lab_session ls
            WHERE ls.user_id = %(user_id)s

            UNION ALL
            SELECT NULLIF(TRIM(c.source), '') AS source
            FROM ai_message m
            JOIN ai_conversation c ON c.conversation_id = m.conversation_id
            WHERE c.user_id = %(user_id)s

            UNION ALL
            SELECT NULLIF(TRIM(c.source), '') AS source
            FROM ai_context_injection ci
            JOIN ai_conversation c ON c.conversation_id = ci.conversation_id
            WHERE c.user_id = %(user_id)s

            UNION ALL
            SELECT NULLIF(TRIM(source), '') AS source
            FROM learning_event
            WHERE user_id = %(user_id)s

            UNION ALL
            SELECT NULLIF(TRIM(source), '') AS source
            FROM container_command_event
            WHERE user_id = %(user_id)s

            UNION ALL
            SELECT NULLIF(TRIM(source), '') AS source
            FROM container_file_event
            WHERE user_id = %(user_id)s

            UNION ALL
            SELECT NULLIF(TRIM(source), '') AS source
            FROM error_event
            WHERE user_id = %(user_id)s
        ) provenance_sources
        GROUP BY source
        """,
        {"user_id": user_id},
    )
    return summarize_source_rows(rows)


def _collect_source_range(cursor, user_id: int) -> tuple[Optional[datetime], Optional[datetime]]:
    rows = _fetch_all(
        cursor,
        """
        SELECT MIN(ts) AS min_ts, MAX(ts) AS max_ts
        FROM (
            SELECT created_at AS ts FROM question_submission WHERE user_id = %(user_id)s
            UNION ALL SELECT created_at AS ts FROM flag_submission WHERE user_id = %(user_id)s
            UNION ALL SELECT start_time AS ts FROM lab_session WHERE user_id = %(user_id)s
            UNION ALL SELECT m.created_at AS ts FROM ai_message m JOIN ai_conversation c ON c.conversation_id = m.conversation_id WHERE c.user_id = %(user_id)s
            UNION ALL SELECT event_time AS ts FROM learning_event WHERE user_id = %(user_id)s
            UNION ALL SELECT executed_at AS ts FROM container_command_event WHERE user_id = %(user_id)s
            UNION ALL SELECT changed_at AS ts FROM container_file_event WHERE user_id = %(user_id)s
            UNION ALL SELECT occurred_at AS ts FROM error_event WHERE user_id = %(user_id)s
        ) source_times
        """,
        {"user_id": user_id},
    )
    row = rows[0] if rows else {}
    return row.get("min_ts"), row.get("max_ts")


def _latest_context(cursor, user_id: int) -> dict[str, Any]:
    row = _fetch_one(
        cursor,
        """
        SELECT class_id, course_id
        FROM (
            SELECT class_id, course_id, created_at AS ts FROM question_submission WHERE user_id = %(user_id)s
            UNION ALL SELECT class_id, course_id, created_at AS ts FROM flag_submission WHERE user_id = %(user_id)s
            UNION ALL SELECT class_id, course_id, start_time AS ts FROM lab_session WHERE user_id = %(user_id)s
            UNION ALL SELECT class_id, course_id, last_message_at AS ts FROM ai_conversation WHERE user_id = %(user_id)s
            UNION ALL SELECT class_id, course_id, executed_at AS ts FROM container_command_event WHERE user_id = %(user_id)s
            UNION ALL SELECT class_id, course_id, changed_at AS ts FROM container_file_event WHERE user_id = %(user_id)s
            UNION ALL SELECT class_id, course_id, occurred_at AS ts FROM error_event WHERE user_id = %(user_id)s
        ) ctx
        WHERE class_id IS NOT NULL OR course_id IS NOT NULL
        ORDER BY ts DESC
        LIMIT 1
        """,
        {"user_id": user_id},
    )
    return {"class_id": row.get("class_id"), "course_id": row.get("course_id")}


def _collect_stats(cursor, user_id: int) -> dict[str, Any]:
    question = _fetch_one(
        cursor,
        """
        SELECT COUNT(*) AS submit_count, SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct_count
        FROM question_submission
        WHERE user_id = %(user_id)s
        """,
        {"user_id": user_id},
    )
    course_question = _fetch_one(
        cursor,
        """
        SELECT COUNT(*) AS submit_count, SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct_count
        FROM question_submission
        WHERE user_id = %(user_id)s
          AND COALESCE(question_source, 'course_question') = 'course_question'
        """,
        {"user_id": user_id},
    )
    training_question = _fetch_one(
        cursor,
        """
        SELECT COUNT(*) AS submit_count, SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct_count
        FROM question_submission
        WHERE user_id = %(user_id)s
          AND question_source = 'personalized_training'
        """,
        {"user_id": user_id},
    )
    generated_attempt = _fetch_one(
        cursor,
        """
        SELECT
            COUNT(*) AS submit_count,
            SUM(CASE WHEN is_correct = 1 OR (is_correct IS NULL AND score >= 70) THEN 1 ELSE 0 END) AS correct_count
        FROM generated_question_attempt
        WHERE user_id = %(user_id)s
          AND submission_id IS NULL
        """,
        {"user_id": user_id},
    )
    flag = _fetch_one(
        cursor,
        """
        SELECT COUNT(*) AS submit_count, SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct_count
        FROM flag_submission
        WHERE user_id = %(user_id)s
        """,
        {"user_id": user_id},
    )
    lab = _fetch_one(
        cursor,
        """
        SELECT COUNT(*) AS session_count, SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_count
        FROM lab_session
        WHERE user_id = %(user_id)s
        """,
        {"user_id": user_id},
    )
    ai = _fetch_one(
        cursor,
        """
        SELECT
            COUNT(*) AS message_count,
            SUM(CASE WHEN m.role = 'user' THEN 1 ELSE 0 END) AS user_message_count,
            SUM(CASE WHEN m.role = 'assistant' THEN 1 ELSE 0 END) AS assistant_message_count,
            SUM(CASE WHEN m.contains_context = 1 THEN 1 ELSE 0 END) AS context_message_count
        FROM ai_message m
        JOIN ai_conversation c ON c.conversation_id = m.conversation_id
        WHERE c.user_id = %(user_id)s
        """,
        {"user_id": user_id},
    )
    ai_context = _fetch_one(
        cursor,
        """
        SELECT COUNT(*) AS context_injection_count
        FROM ai_context_injection ci
        JOIN ai_conversation c ON c.conversation_id = ci.conversation_id
        WHERE c.user_id = %(user_id)s
        """,
        {"user_id": user_id},
    )
    command = _fetch_one(
        cursor,
        """
        SELECT COUNT(*) AS command_count, COUNT(DISTINCT normalized_command) AS unique_command_count
        FROM container_command_event
        WHERE user_id = %(user_id)s
        """,
        {"user_id": user_id},
    )
    file_change = _fetch_one(
        cursor,
        """
        SELECT COUNT(*) AS file_change_count
        FROM container_file_event
        WHERE user_id = %(user_id)s
        """,
        {"user_id": user_id},
    )
    error = _fetch_one(
        cursor,
        """
        SELECT
            COUNT(*) AS error_count,
            SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) AS high_severity_error_count,
            SUM(CASE WHEN severity = 'medium' THEN 1 ELSE 0 END) AS medium_severity_error_count,
            SUM(CASE WHEN severity = 'low' THEN 1 ELSE 0 END) AS low_severity_error_count
        FROM error_event
        WHERE user_id = %(user_id)s
        """,
        {"user_id": user_id},
    )
    learning_event = _fetch_one(
        cursor,
        """
        SELECT
            COUNT(*) AS event_count,
            SUM(CASE WHEN event_type = 'AI_INTERACTION' THEN 1 ELSE 0 END) AS ai_interaction_count,
            SUM(CASE WHEN event_type = 'AI_ASK' THEN 1 ELSE 0 END) AS ai_ask_count
        FROM learning_event
        WHERE user_id = %(user_id)s
        """,
        {"user_id": user_id},
    )
    active_days = _fetch_one(
        cursor,
        """
        SELECT COUNT(DISTINCT DATE(ts)) AS active_day_count
        FROM (
            SELECT created_at AS ts FROM question_submission WHERE user_id = %(user_id)s
            UNION ALL SELECT created_at AS ts FROM flag_submission WHERE user_id = %(user_id)s
            UNION ALL SELECT start_time AS ts FROM lab_session WHERE user_id = %(user_id)s
            UNION ALL SELECT m.created_at AS ts FROM ai_message m JOIN ai_conversation c ON c.conversation_id = m.conversation_id WHERE c.user_id = %(user_id)s
            UNION ALL SELECT event_time AS ts FROM learning_event WHERE user_id = %(user_id)s
            UNION ALL SELECT executed_at AS ts FROM container_command_event WHERE user_id = %(user_id)s
            UNION ALL SELECT changed_at AS ts FROM container_file_event WHERE user_id = %(user_id)s
            UNION ALL SELECT occurred_at AS ts FROM error_event WHERE user_id = %(user_id)s
        ) activity
        """,
        {"user_id": user_id},
    )

    ai_interaction_count = int(_scalar(learning_event, "ai_interaction_count"))
    ai_ask_count = int(_scalar(learning_event, "ai_ask_count"))
    ai_help_count = ai_interaction_count + ai_ask_count
    legacy_ai_message_count = int(_scalar(ai, "message_count"))
    legacy_ai_user_message_count = int(_scalar(ai, "user_message_count"))
    legacy_ai_assistant_message_count = int(_scalar(ai, "assistant_message_count"))

    generated_attempt_submit_count = int(_scalar(generated_attempt, "submit_count"))
    generated_attempt_correct_count = int(_scalar(generated_attempt, "correct_count"))
    question_submit_count = int(_scalar(question, "submit_count")) + generated_attempt_submit_count
    question_correct_count = int(_scalar(question, "correct_count")) + generated_attempt_correct_count
    training_submit_count = int(_scalar(training_question, "submit_count")) + generated_attempt_submit_count
    training_correct_count = int(_scalar(training_question, "correct_count")) + generated_attempt_correct_count

    return {
        "question_submit_count": question_submit_count,
        "question_correct_count": question_correct_count,
        "course_question_submit_count": int(_scalar(course_question, "submit_count")),
        "course_question_correct_count": int(_scalar(course_question, "correct_count")),
        "training_question_submit_count": training_submit_count,
        "training_question_correct_count": training_correct_count,
        "generated_question_attempt_count": generated_attempt_submit_count,
        "generated_question_attempt_correct_count": generated_attempt_correct_count,
        "flag_submit_count": int(_scalar(flag, "submit_count")),
        "flag_correct_count": int(_scalar(flag, "correct_count")),
        "lab_session_count": int(_scalar(lab, "session_count")),
        "completed_lab_count": int(_scalar(lab, "completed_count")),
        "event_count": int(_scalar(learning_event, "event_count")),
        "ai_interaction_count": ai_interaction_count,
        "ai_ask_count": ai_ask_count,
        "ai_message_count": legacy_ai_message_count + ai_help_count,
        "ai_user_message_count": legacy_ai_user_message_count + ai_help_count,
        "ai_assistant_message_count": legacy_ai_assistant_message_count + ai_interaction_count,
        "ai_context_message_count": int(_scalar(ai, "context_message_count")),
        "ai_context_injection_count": int(_scalar(ai_context, "context_injection_count")),
        "command_count": int(_scalar(command, "command_count")),
        "unique_command_count": int(_scalar(command, "unique_command_count")),
        "file_change_count": int(_scalar(file_change, "file_change_count")),
        "error_count": int(_scalar(error, "error_count")),
        "high_severity_error_count": int(_scalar(error, "high_severity_error_count")),
        "medium_severity_error_count": int(_scalar(error, "medium_severity_error_count")),
        "low_severity_error_count": int(_scalar(error, "low_severity_error_count")),
        "active_day_count": int(_scalar(active_days, "active_day_count")),
    }


def _score_profile(stats: dict[str, int]) -> tuple[dict[str, float], dict[str, Any]]:
    q_rate = _ratio(stats["question_correct_count"], stats["question_submit_count"])
    course_q_rate = _ratio(stats["course_question_correct_count"], stats["course_question_submit_count"])
    training_q_rate = _ratio(stats["training_question_correct_count"], stats["training_question_submit_count"])
    flag_rate = _ratio(stats["flag_correct_count"], stats["flag_submit_count"])
    completion_rate = _ratio(stats["completed_lab_count"], stats["lab_session_count"])

    course_question_score = _clamp(course_q_rate * 100)
    lab_task_mastery_score = _clamp(flag_rate * 70 + completion_rate * 30)
    training_question_score = _clamp(training_q_rate * 100)
    knowledge = _clamp(
        course_question_score * 0.35
        + lab_task_mastery_score * 0.40
        + training_question_score * 0.25
    )

    high_errors = stats["high_severity_error_count"]
    medium_errors = stats["medium_severity_error_count"]
    low_errors = stats["low_severity_error_count"]
    step_completion_score = _clamp(completion_rate * 100)
    if stats["error_count"] == 0:
        recovery_after_error_score = 60.0 if stats["completed_lab_count"] > 0 else 0.0
    else:
        recovery_after_error_score = _clamp(20 + _ratio(stats["completed_lab_count"], stats["error_count"]) * 80)
    verification_after_fix_score = _clamp(flag_rate * 60 + completion_rate * 40)
    troubleshooting = _clamp(
        step_completion_score * 0.30
        + recovery_after_error_score * 0.45
        + verification_after_fix_score * 0.25
    )

    operation_count = stats["command_count"] + stats["file_change_count"] + stats["question_submit_count"] + stats["flag_submit_count"]
    ai_user = stats["ai_user_message_count"]
    independence_ratio = _ratio(operation_count, operation_count + ai_user)
    path_diversity_ratio = _ratio(stats["unique_command_count"], stats["command_count"])
    path_diversity_score = _clamp(min(60, stats["unique_command_count"] * 10) + path_diversity_ratio * 40)
    effective_operations_score = _clamp(min(100, stats["command_count"] * 2.5 + stats["file_change_count"] * 8))
    independent_attempt_score = _clamp(independence_ratio * 100)
    autonomy = _clamp(
        path_diversity_score * 0.40
        + effective_operations_score * 0.30
        + independent_attempt_score * 0.30
    )

    context_signal = 1 if stats["ai_context_injection_count"] > 0 or stats["ai_context_message_count"] > 0 else 0
    ai_followup_activity = stats["command_count"] + stats["file_change_count"] + stats["question_submit_count"] + stats["flag_submit_count"]
    if ai_user == 0 and context_signal == 0:
        contextual_help_quality_score = 60.0
        post_ai_action_conversion_score = 60.0
        ai_usage_moderation_score = 60.0
    else:
        contextual_help_quality_score = _clamp(
            min(100, stats["ai_context_injection_count"] * 30 + stats["ai_context_message_count"] * 12)
        )
        post_ai_action_conversion_score = _clamp(
            min(100, _ratio(ai_followup_activity, ai_user or 1) * 35 + min(40, (stats["flag_correct_count"] + stats["question_correct_count"]) * 5))
        )
        moderation_penalty = max(0, ai_user - 6) * 8 + (20 if ai_followup_activity == 0 else 0)
        ai_usage_moderation_score = _clamp(100 - moderation_penalty)
    ai_collaboration = _clamp(
        contextual_help_quality_score * 0.35
        + post_ai_action_conversion_score * 0.40
        + ai_usage_moderation_score * 0.25
    )

    active_count = (
        stats["lab_session_count"]
        + stats["question_submit_count"]
        + stats["flag_submit_count"]
        + stats["command_count"]
        + stats["file_change_count"]
        + stats["ai_user_message_count"]
    )
    active_days_score = _clamp(min(100, stats["active_day_count"] * 12))
    lab_participation_score = _clamp(min(100, stats["lab_session_count"] * 15 + stats["completed_lab_count"] * 10))
    sustained_practice_score = _clamp(
        min(100, (stats["question_submit_count"] + stats["flag_submit_count"]) * 5 + (stats["command_count"] + stats["file_change_count"]) * 2)
    )
    engagement = _clamp(
        active_days_score * 0.30
        + lab_participation_score * 0.35
        + sustained_practice_score * 0.35
    )

    scores = {
        "knowledge_mastery_score": knowledge,
        "troubleshooting_score": troubleshooting,
        "autonomy_score": autonomy,
        "ai_collaboration_score": ai_collaboration,
        "engagement_score": engagement,
    }
    overall = _clamp(sum(scores[key] * weight for key, weight in OVERALL_WEIGHTS.items()))
    scores["overall_score"] = overall

    explanations = {
        "knowledge_mastery_score": {
            "stats": {
                "question_correct_rate": round(q_rate, 4),
                "course_question_correct_rate": round(course_q_rate, 4),
                "training_question_correct_rate": round(training_q_rate, 4),
                "flag_correct_rate": round(flag_rate, 4),
                "lab_completion_rate": round(completion_rate, 4),
                "component_scores": {
                    "course_question_accuracy": course_question_score,
                    "lab_task_mastery": lab_task_mastery_score,
                    "training_question_accuracy": training_question_score,
                },
            },
            "weights": DIMENSION_BREAKDOWN["knowledge_mastery_score"]["components"],
            "explanation": "知识掌握强调结果性证据，占综合分 30%。内部采用课程先导题 35%、实验 Flag/关键任务 40%、动态题库 25%，兼顾基础理解、实操达成和迁移掌握。",
        },
        "troubleshooting_score": {
            "stats": {
                "error_count": stats["error_count"],
                "high_severity_error_count": high_errors,
                "medium_severity_error_count": medium_errors,
                "low_severity_error_count": low_errors,
                "component_scores": {
                    "step_completion": step_completion_score,
                    "recovery_after_error": recovery_after_error_score,
                    "verification_after_fix": verification_after_fix_score,
                },
            },
            "weights": DIMENSION_BREAKDOWN["troubleshooting_score"]["components"],
            "explanation": "排障能力强调卡住后的恢复过程，占综合分 20%。内部采用步骤完成度 30%、引导后恢复能力 45%、修复验证能力 25%。",
        },
        "autonomy_score": {
            "stats": {
                "command_count": stats["command_count"],
                "unique_command_count": stats["unique_command_count"],
                "file_change_count": stats["file_change_count"],
                "operation_count": operation_count,
                "ai_user_message_count": ai_user,
                "independence_ratio": round(independence_ratio, 4),
                "path_diversity_ratio": round(path_diversity_ratio, 4),
                "component_scores": {
                    "path_diversity": path_diversity_score,
                    "effective_operations": effective_operations_score,
                    "independent_attempt": independent_attempt_score,
                },
            },
            "weights": DIMENSION_BREAKDOWN["autonomy_score"]["components"],
            "explanation": "自主探索占综合分 20%。内部采用探索路径多样性 40%、有效操作行为 30%、独立尝试程度 30%，避免只看命令次数。",
        },
        "ai_collaboration_score": {
            "stats": {
                "ai_user_message_count": ai_user,
                "ai_context_injection_count": stats["ai_context_injection_count"],
                "ai_context_message_count": stats["ai_context_message_count"],
                "followup_activity_count": ai_followup_activity,
                "component_scores": {
                    "contextual_help_quality": contextual_help_quality_score,
                    "post_ai_action_conversion": post_ai_action_conversion_score,
                    "ai_usage_moderation": ai_usage_moderation_score,
                },
            },
            "weights": DIMENSION_BREAKDOWN["ai_collaboration_score"]["components"],
            "explanation": "AI 协同占综合分 15%。它与自主探索不是对立维度：不使用 AI 记中性分，过度依赖才扣分；真正加分点在于上下文化求助和求助后的行动转化。",
        },
        "engagement_score": {
            "stats": {
                "active_day_count": stats["active_day_count"],
                "lab_session_count": stats["lab_session_count"],
                "completed_lab_count": stats["completed_lab_count"],
                "active_behavior_count": active_count,
                "component_scores": {
                    "active_days": active_days_score,
                    "lab_participation": lab_participation_score,
                    "sustained_practice": sustained_practice_score,
                },
            },
            "weights": DIMENSION_BREAKDOWN["engagement_score"]["components"],
            "explanation": "学习投入占综合分 15%。当前先用活跃天数 30%、实验参与与完成 35%、持续练习行为 35% 作为可落地代理指标。",
        },
        "overall_score": {
            "weights": OVERALL_WEIGHTS,
            "dimension_breakdown": DIMENSION_BREAKDOWN,
            "explanation": "一级维度采用结果与过程并重的固定权重：知识掌握 30%，排障能力 20%，自主探索 20%，AI 协同 15%，学习投入 15%。",
        },
    }
    return scores, explanations


def _strengths_and_weaknesses(scores: dict[str, float]) -> tuple[list[str], list[str]]:
    strengths = [DIMENSION_LABELS[key] for key, value in scores.items() if key in DIMENSION_LABELS and value >= 75]
    weaknesses = [DIMENSION_LABELS[key] for key, value in scores.items() if key in DIMENSION_LABELS and value < 50]
    return strengths or ["暂无明显优势，建议继续积累学习证据"], weaknesses or ["暂无明显短板"]


def _text_blob(*values: Any) -> str:
    return " ".join(str(value or "").strip().lower() for value in values if value is not None)


def _table_exists(cursor, schema: str, table: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM information_schema.tables
        WHERE table_schema = %(schema)s AND table_name = %(table)s
        """,
        {"schema": schema, "table": table},
    )
    return bool(int(_scalar(cursor.fetchone(), "total")))


def _load_catalog_resources(cursor) -> dict[str, list[dict[str, Any]]]:
    resources: dict[str, list[dict[str, Any]]] = {"courses": [], "modules": []}
    if _table_exists(cursor, "userservice", "course"):
        resources["courses"] = _fetch_all(
            cursor,
            """
            SELECT
                id,
                course_name,
                course_description,
                difficulty,
                type
            FROM userservice.course
            WHERE COALESCE(course_status, 1) <> 0
            ORDER BY difficulty ASC, id ASC
            """,
            {},
        )
    if _table_exists(cursor, "userservice", "module"):
        resources["modules"] = _fetch_all(
            cursor,
            """
            SELECT
                module_id,
                module_name,
                introduction,
                difficulty,
                type
            FROM userservice.module
            ORDER BY difficulty ASC, module_id ASC
            """,
            {},
        )
    return resources


def _pick_first_match(
    rows: list[dict[str, Any]],
    keywords: list[str],
    predicate=None,
) -> Optional[dict[str, Any]]:
    normalized_keywords = [keyword.strip().lower() for keyword in keywords if keyword.strip()]
    best_row: Optional[dict[str, Any]] = None
    best_score = -1
    for row in rows:
        if predicate and not predicate(row):
            continue
        haystack = _text_blob(*row.values())
        hit_score = 0
        for index, keyword in enumerate(normalized_keywords):
            if keyword in haystack:
                hit_score += len(normalized_keywords) - index
        if hit_score <= 0:
            continue
        difficulty_penalty = int(row.get("difficulty") or 0)
        ranking_score = hit_score * 100 - difficulty_penalty
        if ranking_score > best_score:
            best_score = ranking_score
            best_row = row
    return best_row


def _build_recommendations(scores: dict[str, float], catalog: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    courses = catalog.get("courses", [])
    modules = catalog.get("modules", [])
    rules = {
        "knowledge_mastery_score": {
            "title": "基础题目复习与课程回补",
            "reason_template": "知识掌握度偏低，优先回补基础理论和题目复习模块。",
            "action": "开始训练",
            "module_keywords": ["sql注入基础", "sql 注入基础", "xss", "文件上传", "中间件", "基础实验"],
            "course_keywords": ["sql注入", "xss", "文件上传", "中间件"],
        },
        "troubleshooting_score": {
            "title": "排障实验与错误复盘",
            "reason_template": "排障能力偏低，建议围绕排查、修复与实战复盘类资源补强。",
            "action": "开始训练",
            "module_keywords": ["实战", "综合", "突破", "排查", "修复", "漏洞"],
            "course_keywords": ["防御", "分析", "网络安全"],
        },
        "autonomy_score": {
            "title": "低提示依赖的自主实验",
            "reason_template": "自主探索能力偏低，建议先完成基础到中等难度的独立实操实验。",
            "action": "开始训练",
            "module_keywords": ["基础", "入门", "实践", "实验"],
            "course_keywords": ["概述", "基础"],
        },
        "ai_collaboration_score": {
            "title": "AI 协作式训练任务",
            "reason_template": "AI 协作能力偏低，建议选择适合分析、审计与防御方案讨论的任务。",
            "action": "开始训练",
            "module_keywords": ["漏洞分析", "代码审计", "错误分析", "防御", "方法论", "框架漏洞", "代码审计进阶"],
            "course_keywords": ["分析", "防御", "网络安全"],
        },
        "engagement_score": {
            "title": "短周期入门实验",
            "reason_template": "学习投入度偏低，建议先完成低难度、短周期、容易完成的模块。",
            "action": "开始训练",
            "module_keywords": ["基础", "xss", "命令注入", "实验"],
            "course_keywords": ["xss", "概述"],
            "module_predicate": lambda row: int(row.get("difficulty") or 0) in (1, 2),
            "course_predicate": lambda row: int(row.get("difficulty") or 0) in (1, 2),
        },
    }
    recommendations: list[dict[str, Any]] = []
    for key, rule in rules.items():
        score = float(scores.get(key) or 0)
        if score >= 60:
            continue
        matched_module = _pick_first_match(
            modules,
            rule.get("module_keywords", []),
            predicate=rule.get("module_predicate"),
        )
        matched_course = _pick_first_match(
            courses,
            rule.get("course_keywords", []),
            predicate=rule.get("course_predicate"),
        )
        priority = "high" if score < 40 else "medium"
        recommendation_type = "GENERAL"
        course_id = None
        module_id = None
        difficulty = None
        knowledge_tags = build_knowledge_tags(rule["title"], rule["reason_template"], [DIMENSION_LABELS[key]])
        reason_suffix = "当前没有匹配到可直接跳转的真实课程或模块资源。"
        title = rule["title"]
        if matched_module:
            recommendation_type = "MODULE"
            module_id = int(matched_module.get("module_id"))
            difficulty = int(matched_module.get("difficulty") or 0) or None
            title = str(matched_module.get("module_name") or title)
            knowledge_tags = build_knowledge_tags(
                title,
                str(matched_module.get("introduction") or ""),
                [str(matched_module.get("type") or ""), DIMENSION_LABELS[key]],
            )
            reason_suffix = f"已匹配真实模块「{title}」。"
        elif matched_course:
            recommendation_type = "COURSE"
            course_id = int(matched_course.get("id"))
            difficulty = int(matched_course.get("difficulty") or 0) or None
            title = str(matched_course.get("course_name") or title)
            knowledge_tags = build_knowledge_tags(
                title,
                str(matched_course.get("course_description") or ""),
                [str(matched_course.get("type") or ""), str(matched_course.get("tags") or ""), DIMENSION_LABELS[key]],
            )
            reason_suffix = f"已匹配真实课程「{title}」。"
        recommendations.append(
            {
                "id": f"{DIMENSION_CODES[key]}-{module_id or course_id or 'general'}",
                "dimension": DIMENSION_CODES[key],
                "dimension_name": DIMENSION_LABELS[key],
                "score": score,
                "type": recommendation_type,
                "title": title,
                "reason": f"{DIMENSION_LABELS[key]}当前得分 {score:.2f}，{rule['reason_template']} {reason_suffix}",
                "courseId": course_id,
                "moduleId": module_id,
                "labId": None,
                "questionId": None,
                "difficulty": difficulty,
                "actionText": rule["action"],
                "source": "student_profile_snapshot",
                "knowledgeTags": knowledge_tags,
                "priority": priority,
                "threshold": 60,
                "action": rule["action"],
                "tags": [
                    DIMENSION_LABELS[key],
                    "画像推荐",
                    recommendation_type,
                    "高优先级" if priority == "high" else "建议跟进",
                ],
            }
        )
    return recommendations


def _date_key(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _rebuild_daily_features(cursor, user_id: int, source_start: Optional[datetime], source_end: Optional[datetime]) -> None:
    if not source_start or not source_end:
        return
    start_date = source_start.date()
    end_date = source_end.date()
    daily: dict[date, dict[str, int | set[str]]] = defaultdict(lambda: {
        "question_submit_count": 0,
        "question_correct_count": 0,
        "flag_submit_count": 0,
        "flag_correct_count": 0,
        "lab_session_count": 0,
        "completed_lab_count": 0,
        "ai_message_count": 0,
        "ai_user_message_count": 0,
        "ai_assistant_message_count": 0,
        "command_count": 0,
        "unique_commands": set(),
        "file_change_count": 0,
        "error_count": 0,
        "high_severity_error_count": 0,
    })

    for row in _fetch_all(cursor, "SELECT created_at, is_correct FROM question_submission WHERE user_id = %(user_id)s", {"user_id": user_id}):
        key = _date_key(row.get("created_at"))
        if key:
            daily[key]["question_submit_count"] += 1
            daily[key]["question_correct_count"] += 1 if row.get("is_correct") == 1 else 0
    for row in _fetch_all(
        cursor,
        """
        SELECT submitted_at, is_correct, score
        FROM generated_question_attempt
        WHERE user_id = %(user_id)s
          AND submission_id IS NULL
        """,
        {"user_id": user_id},
    ):
        key = _date_key(row.get("submitted_at"))
        if key:
            daily[key]["question_submit_count"] += 1
            daily[key]["question_correct_count"] += 1 if row.get("is_correct") == 1 or (row.get("is_correct") is None and float(row.get("score") or 0) >= 70) else 0
    for row in _fetch_all(cursor, "SELECT created_at, is_correct FROM flag_submission WHERE user_id = %(user_id)s", {"user_id": user_id}):
        key = _date_key(row.get("created_at"))
        if key:
            daily[key]["flag_submit_count"] += 1
            daily[key]["flag_correct_count"] += 1 if row.get("is_correct") == 1 else 0
    for row in _fetch_all(cursor, "SELECT start_time, status FROM lab_session WHERE user_id = %(user_id)s", {"user_id": user_id}):
        key = _date_key(row.get("start_time"))
        if key:
            daily[key]["lab_session_count"] += 1
            daily[key]["completed_lab_count"] += 1 if row.get("status") == "completed" else 0
    for row in _fetch_all(
        cursor,
        """
        SELECT m.created_at, m.role
        FROM ai_message m
        JOIN ai_conversation c ON c.conversation_id = m.conversation_id
        WHERE c.user_id = %(user_id)s
        """,
        {"user_id": user_id},
    ):
        key = _date_key(row.get("created_at"))
        if key:
            daily[key]["ai_message_count"] += 1
            daily[key]["ai_user_message_count"] += 1 if row.get("role") == "user" else 0
            daily[key]["ai_assistant_message_count"] += 1 if row.get("role") == "assistant" else 0
    for row in _fetch_all(cursor, "SELECT executed_at, normalized_command FROM container_command_event WHERE user_id = %(user_id)s", {"user_id": user_id}):
        key = _date_key(row.get("executed_at"))
        if key:
            daily[key]["command_count"] += 1
            if row.get("normalized_command"):
                daily[key]["unique_commands"].add(row["normalized_command"])
    for row in _fetch_all(cursor, "SELECT changed_at FROM container_file_event WHERE user_id = %(user_id)s", {"user_id": user_id}):
        key = _date_key(row.get("changed_at"))
        if key:
            daily[key]["file_change_count"] += 1
    for row in _fetch_all(cursor, "SELECT occurred_at, severity FROM error_event WHERE user_id = %(user_id)s", {"user_id": user_id}):
        key = _date_key(row.get("occurred_at"))
        if key:
            daily[key]["error_count"] += 1
            daily[key]["high_severity_error_count"] += 1 if row.get("severity") == "high" else 0

    cursor.execute(
        "DELETE FROM student_profile_feature_daily WHERE user_id = %(user_id)s AND stat_date BETWEEN %(start)s AND %(end)s",
        {"user_id": user_id, "start": start_date, "end": end_date},
    )
    current = start_date
    while current <= end_date:
        item = daily[current]
        cursor.execute(
            """
            INSERT INTO student_profile_feature_daily (
                user_id, stat_date, question_submit_count, question_correct_count,
                flag_submit_count, flag_correct_count, lab_session_count,
                completed_lab_count, ai_message_count, ai_user_message_count,
                ai_assistant_message_count, command_count, unique_command_count,
                file_change_count, error_count, high_severity_error_count
            ) VALUES (
                %(user_id)s, %(stat_date)s, %(question_submit_count)s, %(question_correct_count)s,
                %(flag_submit_count)s, %(flag_correct_count)s, %(lab_session_count)s,
                %(completed_lab_count)s, %(ai_message_count)s, %(ai_user_message_count)s,
                %(ai_assistant_message_count)s, %(command_count)s, %(unique_command_count)s,
                %(file_change_count)s, %(error_count)s, %(high_severity_error_count)s
            )
            """,
            {
                "user_id": user_id,
                "stat_date": current,
                "question_submit_count": item["question_submit_count"],
                "question_correct_count": item["question_correct_count"],
                "flag_submit_count": item["flag_submit_count"],
                "flag_correct_count": item["flag_correct_count"],
                "lab_session_count": item["lab_session_count"],
                "completed_lab_count": item["completed_lab_count"],
                "ai_message_count": item["ai_message_count"],
                "ai_user_message_count": item["ai_user_message_count"],
                "ai_assistant_message_count": item["ai_assistant_message_count"],
                "command_count": item["command_count"],
                "unique_command_count": len(item["unique_commands"]),
                "file_change_count": item["file_change_count"],
                "error_count": item["error_count"],
                "high_severity_error_count": item["high_severity_error_count"],
            },
        )
        current += timedelta(days=1)


def rebuild_student_profile(user_id: int) -> dict[str, Any]:
    """Recompute a reproducible rule-based profile snapshot for one student."""
    ensure_profile_schema()
    now = datetime.utcnow()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            source_start, source_end = _collect_source_range(cursor, user_id)
            stats = _collect_stats(cursor, user_id)
            data_provenance = _collect_data_provenance(cursor, user_id)
            scores, explanations = _score_profile(stats)
            strengths, weaknesses = _strengths_and_weaknesses(scores)
            catalog = _load_catalog_resources(cursor)
            recommendations = _build_recommendations(scores, catalog)
            context = _latest_context(cursor, user_id)
            summary = {
                "source_strategy": "当前没有稳定知识标签表，知识掌握按 module_id/task_id 粒度的题目、Flag、实验完成证据替代。",
                "score_model": {
                    "overall_weights": OVERALL_WEIGHTS,
                    "dimension_breakdown": DIMENSION_BREAKDOWN,
                    "rationale": {
                        "knowledge_mastery_score": "结果性学习证据，权重最高，用于衡量知识理解、实验达成和迁移掌握。",
                        "troubleshooting_score": "安全实验高度依赖排错与恢复，因此单列 20%。",
                        "autonomy_score": "强调独立探索与主动尝试，是过程能力核心维度之一。",
                        "ai_collaboration_score": "衡量是否合理借助 AI，而非把 AI 当答案生成器。",
                        "engagement_score": "衡量持续投入与练习稳定性，避免只看一次性结果。",
                    },
                },
                "evidence": {
                    "eventCount": stats["event_count"],
                    "aiInteractionCount": stats["ai_interaction_count"],
                    "aiAskCount": stats["ai_ask_count"],
                    "questionSubmitCount": stats["question_submit_count"],
                    "flagSubmitCount": stats["flag_submit_count"],
                    "labStartCount": stats["lab_session_count"],
                    "activeDayCount": stats["active_day_count"],
                },
                "raw_stats": stats,
                "dimension_explanations": explanations,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "recommendations": recommendations,
                "data_provenance": data_provenance,
            }
            snapshot_id = f"profile-{uuid4()}"
            row = {
                "snapshot_id": snapshot_id,
                "user_id": user_id,
                "class_id": context.get("class_id"),
                "course_id": context.get("course_id"),
                "computed_at": now,
                **scores,
                "profile_summary_json": _json_dumps(summary),
                "source_range_start": source_start,
                "source_range_end": source_end,
            }
            _rebuild_daily_features(cursor, user_id, source_start, source_end)
            cursor.execute(
                """
                INSERT INTO student_profile_snapshot (
                    snapshot_id, user_id, class_id, course_id, computed_at,
                    knowledge_mastery_score, troubleshooting_score, autonomy_score,
                    ai_collaboration_score, engagement_score, overall_score,
                    profile_summary_json, source_range_start, source_range_end
                ) VALUES (
                    %(snapshot_id)s, %(user_id)s, %(class_id)s, %(course_id)s, %(computed_at)s,
                    %(knowledge_mastery_score)s, %(troubleshooting_score)s, %(autonomy_score)s,
                    %(ai_collaboration_score)s, %(engagement_score)s, %(overall_score)s,
                    %(profile_summary_json)s, %(source_range_start)s, %(source_range_end)s
                )
                """,
                row,
            )
        conn.commit()
    return _serialize_snapshot({**row, "profile_summary_json": summary})


def _serialize_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    if isinstance(result.get("profile_summary_json"), str):
        result["profile_summary_json"] = json.loads(result["profile_summary_json"])
    for key in (
        "computed_at",
        "source_range_start",
        "source_range_end",
        "created_at",
    ):
        if isinstance(result.get(key), datetime):
            result[key] = result[key].isoformat()
    for key in (
        "knowledge_mastery_score",
        "troubleshooting_score",
        "autonomy_score",
        "ai_collaboration_score",
        "engagement_score",
        "overall_score",
    ):
        if result.get(key) is not None:
            result[key] = float(result[key])
    return result


def get_latest_student_profile(user_id: int) -> Optional[dict[str, Any]]:
    ensure_profile_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            row = _fetch_one(
                cursor,
                """
                SELECT *
                FROM student_profile_snapshot
                WHERE user_id = %(user_id)s
                ORDER BY computed_at DESC, created_at DESC
                LIMIT 1
                """,
                {"user_id": user_id},
            )
    return _serialize_snapshot(row) if row else None
