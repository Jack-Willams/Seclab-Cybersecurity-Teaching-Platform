import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from database import get_connection
from event_repository import ensure_schema as ensure_learning_event_schema
from profile_dashboard_repository import get_profile_dashboard
from profile_repository import ensure_profile_schema, get_latest_student_profile
from training_repository import ensure_training_schema


USER_SERVICE_SCHEMA = "userservice"
CLASS_NAME_ALIASES = {
    "Cyber Security 231": "网络安全231班",
    "Cyber Security 232": "网络安全232班",
    "Cyber Security 233": "网络安全233班",
    "SecLab Demo Class": "SecLab演示班",
    "SecLab Teacher Scope Class A": "SecLab教师权限A班",
    "SecLab Teacher Scope Class B": "SecLab教师权限B班",
}
DIMENSION_TEACHER_GUIDANCE = {
    "knowledge_mastery": {
        "focus": "知识点理解、关键概念复述、实验原理迁移",
        "action": "建议教师安排一次个人口头追问或错题讲解，要求学生用自己的话解释最近一次训练题涉及的原理和适用边界。",
    },
    "troubleshooting": {
        "focus": "错误定位、排查路径记录、修复依据说明",
        "action": "建议教师安排一次个人复盘，要求学生说明最近一次失败题目的排查步骤、尝试依据和下一步验证方式。",
    },
    "autonomy": {
        "focus": "独立尝试、提示使用克制、过程记录完整度",
        "action": "建议教师布置一次限提示的个人练习，观察学生是否能先写出自己的判断、尝试路径和卡点说明。",
    },
    "ai_collaboration": {
        "focus": "AI 提问质量、回答校验、关键结论复述",
        "action": "建议教师抽查一次学生与 AI 的交互记录，要求学生标出哪些建议被验证、哪些建议被放弃以及原因。",
    },
    "engagement": {
        "focus": "练习持续性、提交频率、复盘完成度",
        "action": "建议教师设置短周期个人跟进目标，优先确认学生是否按时完成训练、提交复盘并记录下一次改进点。",
    },
}

DIMENSION_FIELDS = [
    ("knowledge_mastery", "知识掌握", "knowledge_mastery_score"),
    ("troubleshooting", "排障能力", "troubleshooting_score"),
    ("autonomy", "自主探索", "autonomy_score"),
    ("ai_collaboration", "AI 协同", "ai_collaboration_score"),
    ("engagement", "学习投入", "engagement_score"),
]


def _ensure_teacher_source_schemas() -> None:
    ensure_profile_schema()
    ensure_training_schema()
    ensure_learning_event_schema()


def _json_loads(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _json_field(source: Any, *keys: str, default: Any = None) -> Any:
    data = _json_loads(source, {})
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _round(value: Any) -> float:
    return round(_to_float(value), 2)


def _display_class_name(raw_name: Any, class_id: int) -> str:
    name = str(raw_name or "").strip()
    if not name or set(name) <= {"?"}:
        return f"未命名班级 {class_id}"
    return CLASS_NAME_ALIASES.get(name, name)


def build_rule_based_student_recommendations(
    profile: dict[str, Any],
    attempts: list[dict[str, Any]],
    last_active_at: Optional[str],
) -> list[dict[str, Any]]:
    scored_dimensions = [
        {
            "dimension": dimension,
            "label": label,
            "score": _round(profile.get(field)),
        }
        for dimension, label, field in DIMENSION_FIELDS
    ]
    weak_dimensions = sorted(
        [item for item in scored_dimensions if item["score"] < 70],
        key=lambda item: item["score"],
    )[:3]
    if not weak_dimensions:
        weak_dimensions = sorted(scored_dimensions, key=lambda item: item["score"])[:1]

    attempt_count = len(attempts)
    incorrect_count = sum(1 for item in attempts if item.get("isCorrect") is False)
    average_score = (
        sum(_to_float(item.get("score")) for item in attempts) / attempt_count
        if attempt_count else None
    )
    attempt_text = (
        f"最近 {attempt_count} 次训练作答，平均得分 {average_score:.1f} 分，需复盘 {incorrect_count} 次"
        if average_score is not None
        else "暂无最近训练作答"
    )
    active_text = f"最近活跃时间 {last_active_at}" if last_active_at else "暂无最近活跃记录"

    recommendations: list[dict[str, Any]] = []
    for item in weak_dimensions:
        guidance = DIMENSION_TEACHER_GUIDANCE[item["dimension"]]
        score = item["score"]
        priority = "high" if score < 40 else "medium" if score < 60 else "low"
        recommendations.append(
            {
                "dimension": item["dimension"],
                "label": item["label"],
                "score": score,
                "scope": "student",
                "priority": priority,
                "summary": (
                    f"{item['label']} {score:.1f} 分：该学生在{guidance['focus']}上需要重点关注。"
                ),
                "evidence": f"个人五维得分显示{item['label']}为 {score:.1f} 分；{attempt_text}；{active_text}。",
                "teacherAction": guidance["action"],
            }
        )
    return recommendations


_build_student_recommendations = build_rule_based_student_recommendations


def _table_exists(cursor, schema: str, table: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM information_schema.tables
        WHERE table_schema = %(schema)s AND table_name = %(table)s
        """,
        {"schema": schema, "table": table},
    )
    return _to_int((cursor.fetchone() or {}).get("count")) > 0


def _scope_class_ids(current_user: Optional[dict[str, Any]]) -> Optional[list[int]]:
    if not current_user or current_user.get("role") == "admin":
        return None
    return [
        int(class_id)
        for class_id in current_user.get("scope_class_ids") or []
        if class_id is not None
    ]


def _current_user_id(current_user: Optional[dict[str, Any]], fallback: Optional[int] = None) -> Optional[int]:
    if current_user and current_user.get("user_id") is not None:
        return int(current_user["user_id"])
    return fallback


def require_owned_teaching_class(teacher_id: int, teaching_class_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT teaching_class_id, teacher_id, class_name, status
                FROM `{USER_SERVICE_SCHEMA}`.`teaching_class`
                WHERE teaching_class_id = %(teaching_class_id)s
                LIMIT 1
                """,
                {"teaching_class_id": teaching_class_id},
            )
            row = cursor.fetchone()
    if not row:
        raise KeyError(f"teaching class does not exist: {teaching_class_id}")
    if int(row.get("teacher_id") or 0) != int(teacher_id):
        raise PermissionError("teaching class is outside current teacher scope")
    return row


def require_student_in_owned_teaching_class(
    teacher_id: int,
    teaching_class_id: int,
    student_id: int,
) -> None:
    require_owned_teaching_class(teacher_id, teaching_class_id)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT 1
                FROM `{USER_SERVICE_SCHEMA}`.`teaching_class_student`
                WHERE teaching_class_id = %(teaching_class_id)s
                  AND student_id = %(student_id)s
                LIMIT 1
                """,
                {"teaching_class_id": teaching_class_id, "student_id": student_id},
            )
            membership = cursor.fetchone()
    if not membership:
        raise PermissionError("student is outside the selected teaching class")


def _sql_in_condition(column: str, values: Optional[list[int]], params: dict[str, Any], prefix: str) -> str:
    if values is None:
        return ""
    if not values:
        return " AND 1 = 0"
    placeholders: list[str] = []
    for index, value in enumerate(values):
        key = f"{prefix}_{index}"
        params[key] = value
        placeholders.append(f"%({key})s")
    return f" AND {column} IN ({', '.join(placeholders)})"


def _user_id_scope_condition(column: str, user_ids: Optional[set[int]], params: dict[str, Any], prefix: str) -> str:
    if user_ids is None:
        return ""
    return _sql_in_condition(column, sorted(user_ids), params, prefix)


def _profile_schema_name(cursor) -> str:
    cursor.execute("SELECT DATABASE() AS db_name")
    return str((cursor.fetchone() or {}).get("db_name") or "")


def _fetch_users(cursor, class_ids: Optional[list[int]] = None) -> dict[int, dict[str, Any]]:
    if not _table_exists(cursor, USER_SERVICE_SCHEMA, "user"):
        return {}
    params: dict[str, Any] = {}
    class_condition = _sql_in_condition("u.class_id_class_id", class_ids, params, "user_class")
    cursor.execute(
        f"""
        SELECT
            u.user_id,
            u.user_student_number,
            u.user_name,
            u.user_image,
            u.user_academy,
            u.user_email,
            u.user_tel,
            u.user_gender,
            u.class_id_class_id AS class_id,
            c.class_name,
            u.create_time,
            u.is_deleted
        FROM `{USER_SERVICE_SCHEMA}`.`user` u
        LEFT JOIN `{USER_SERVICE_SCHEMA}`.`class` c
          ON c.class_id = u.class_id_class_id
        WHERE (u.is_admin IS NULL OR u.is_admin = b'0' OR u.is_admin = 0)
          AND COALESCE(u.is_deleted, 0) = 0
          AND NOT EXISTS (
              SELECT 1
              FROM `{USER_SERVICE_SCHEMA}`.`class` managed_class
              WHERE managed_class.admin_id = u.user_id
                AND COALESCE(managed_class.is_end, 0) = 0
          )
          {class_condition}
        """,
        params,
    )
    return {
        _to_int(row.get("user_id")): row
        for row in cursor.fetchall() or []
        if row.get("user_id") is not None
    }


def _fetch_classes(cursor, class_ids: Optional[list[int]] = None) -> dict[int, dict[str, Any]]:
    if not _table_exists(cursor, USER_SERVICE_SCHEMA, "class"):
        return {}
    params: dict[str, Any] = {}
    class_condition = _sql_in_condition("class_id", class_ids, params, "class_id")
    cursor.execute(
        f"""
        SELECT class_id, class_name, class_detail, admin_id
        FROM `{USER_SERVICE_SCHEMA}`.`class`
        WHERE COALESCE(is_end, 0) = 0
          {class_condition}
        ORDER BY class_id ASC
        """,
        params,
    )
    return {
        _to_int(row.get("class_id")): row
        for row in cursor.fetchall() or []
        if row.get("class_id") is not None
    }


def _fetch_latest_profiles(
    cursor,
    class_id: Optional[int] = None,
    class_ids: Optional[list[int]] = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {}
    class_filter = ""
    if class_id is not None:
        params["class_id"] = class_id
        class_filter = "AND s.class_id = %(class_id)s"
    elif class_ids is not None:
        class_filter = _sql_in_condition("s.class_id", class_ids, params, "profile_class").replace(" AND ", "AND ", 1)
    cursor.execute(
        f"""
        SELECT s.*
        FROM student_profile_snapshot s
        JOIN (
            SELECT user_id, MAX(computed_at) AS computed_at
            FROM student_profile_snapshot
            GROUP BY user_id
        ) latest
          ON latest.user_id = s.user_id AND latest.computed_at = s.computed_at
        WHERE 1 = 1 {class_filter}
        ORDER BY s.computed_at DESC, s.created_at DESC
        """,
        params,
    )
    return list(cursor.fetchall() or [])


def _group_profiles_by_current_class(
    profiles: list[dict[str, Any]],
    users: dict[int, dict[str, Any]],
) -> dict[int, list[dict[str, Any]]]:
    profiles_by_user = {
        _to_int(profile.get("user_id")): profile
        for profile in profiles
        if _to_int(profile.get("user_id")) in users
    }
    grouped: dict[int, list[dict[str, Any]]] = {}
    for user_id, user in users.items():
        class_id = _to_int(user.get("class_id"))
        profile = profiles_by_user.get(user_id)
        if not class_id or not profile:
            continue
        grouped.setdefault(class_id, []).append({**profile, "class_id": class_id})
    return grouped


def _profiles_for_current_users(
    profiles: list[dict[str, Any]],
    users: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    current_profiles: list[dict[str, Any]] = []
    for profile in profiles:
        user_id = _to_int(profile.get("user_id"))
        user = users.get(user_id)
        if not user:
            continue
        current_profiles.append({**profile, "class_id": _to_int(user.get("class_id"))})
    return current_profiles


def _profiles_for_current_class(
    profiles: list[dict[str, Any]],
    users: dict[int, dict[str, Any]],
    class_id: int,
) -> list[dict[str, Any]]:
    profiles_by_user = {
        _to_int(profile.get("user_id")): profile
        for profile in profiles
        if _to_int(profile.get("user_id")) in users
    }
    current_user_ids = sorted(
        user_id
        for user_id, user in users.items()
        if _to_int(user.get("class_id")) == class_id
    )
    return [
        {**profiles_by_user[user_id], "class_id": class_id}
        if user_id in profiles_by_user
        else {"user_id": user_id, "class_id": class_id}
        for user_id in current_user_ids
    ]


def _fetch_attempt_stats(cursor, user_ids: Optional[set[int]] = None) -> dict[int, dict[str, Any]]:
    params: dict[str, Any] = {}
    user_condition = _user_id_scope_condition("gqa.user_id", user_ids, params, "attempt_user")
    cursor.execute(
        f"""
        SELECT
            gqa.user_id,
            COUNT(*) AS attempt_count,
            AVG(gqa.score) AS average_score,
            MAX(gqa.submitted_at) AS last_attempt_at
        FROM generated_question_attempt gqa
        WHERE 1 = 1
          {user_condition}
        GROUP BY gqa.user_id
        """,
        params,
    )
    return {_to_int(row.get("user_id")): row for row in cursor.fetchall() or []}


def _fetch_training_submit_counts(cursor, user_ids: Optional[set[int]] = None) -> dict[int, int]:
    profile_schema = _profile_schema_name(cursor)
    if not _table_exists(cursor, profile_schema, "question_submission"):
        return {}
    params: dict[str, Any] = {}
    user_condition = _user_id_scope_condition("user_id", user_ids, params, "submit_user")
    cursor.execute(
        f"""
        SELECT user_id, COUNT(*) AS submit_count
        FROM question_submission
        WHERE question_source = 'personalized_training'
          {user_condition}
        GROUP BY user_id
        """,
        params,
    )
    return {_to_int(row.get("user_id")): _to_int(row.get("submit_count")) for row in cursor.fetchall() or []}


def _fetch_last_active(cursor, user_ids: Optional[set[int]] = None) -> dict[int, str]:
    params: dict[str, Any] = {}
    user_condition = _user_id_scope_condition("user_id", user_ids, params, "active_user")
    cursor.execute(
        f"""
        SELECT user_id, MAX(ts) AS last_active_at
        FROM (
            SELECT user_id, event_time AS ts FROM learning_event
            UNION ALL
            SELECT user_id, submitted_at AS ts FROM generated_question_attempt
            UNION ALL
            SELECT user_id, created_at AS ts FROM training_session
        ) activity
        WHERE user_id IS NOT NULL
          {user_condition}
        GROUP BY user_id
        """,
        params,
    )
    return {
        _to_int(row.get("user_id")): _iso(row.get("last_active_at")) or ""
        for row in cursor.fetchall() or []
    }


def _student_name(user: Optional[dict[str, Any]], user_id: int) -> str:
    if user:
        return str(user.get("user_name") or user.get("user_student_number") or f"用户 {user_id}")
    return f"用户 {user_id}"


def _student_item(
    profile: dict[str, Any],
    users: dict[int, dict[str, Any]],
    attempt_stats: dict[int, dict[str, Any]],
    submit_counts: dict[int, int],
    last_active: dict[int, str],
) -> dict[str, Any]:
    user_id = _to_int(profile.get("user_id"))
    user = users.get(user_id)
    attempts = attempt_stats.get(user_id, {})
    return {
        "userId": user_id,
        "username": str((user or {}).get("user_student_number") or user_id),
        "nickname": _student_name(user, user_id),
        "avatarUrl": (user or {}).get("user_image"),
        "classId": _to_int(profile.get("class_id")) if profile.get("class_id") is not None else (user or {}).get("class_id"),
        "className": _display_class_name(
            (user or {}).get("class_name"),
            _to_int(profile.get("class_id")) if profile.get("class_id") is not None else _to_int((user or {}).get("class_id")),
        ),
        "overallScore": _round(profile.get("overall_score")),
        "knowledgeMasteryScore": _round(profile.get("knowledge_mastery_score")),
        "troubleshootingScore": _round(profile.get("troubleshooting_score")),
        "autonomyScore": _round(profile.get("autonomy_score")),
        "aiCollaborationScore": _round(profile.get("ai_collaboration_score")),
        "engagementScore": _round(profile.get("engagement_score")),
        "trainingQuestionSubmitCount": submit_counts.get(user_id, 0),
        "generatedQuestionAttemptCount": _to_int(attempts.get("attempt_count")),
        "averageTrainingScore": _round(attempts.get("average_score")),
        "lastActiveAt": last_active.get(user_id) or _iso(profile.get("computed_at")),
    }


def _weak_dimensions(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if not profiles:
        return result
    for dimension, label, field in DIMENSION_FIELDS:
        scores = [_to_float(row.get(field)) for row in profiles if row.get(field) is not None]
        if not scores:
            continue
        average = sum(scores) / len(scores)
        result.append(
            {
                "dimension": dimension,
                "label": label,
                "averageScore": round(average, 2),
                "studentCount": sum(1 for score in scores if score < 70),
            }
        )
    return sorted(result, key=lambda item: item["averageScore"])


def _recent_activities(
    cursor,
    users: dict[int, dict[str, Any]],
    limit: int = 8,
    user_ids: Optional[set[int]] = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"limit": max(1, min(limit, 20))}
    user_condition = _user_id_scope_condition("user_id", user_ids, params, "event_user")
    cursor.execute(
        f"""
        SELECT user_id, event_type, event_time, module_id, task_id, question_id, source, payload_json
        FROM learning_event
        WHERE 1 = 1
          {user_condition}
        ORDER BY event_time DESC, id DESC
        LIMIT %(limit)s
        """,
        params,
    )
    activities: list[dict[str, Any]] = []
    for row in cursor.fetchall() or []:
        user_id = _to_int(row.get("user_id"))
        payload = _json_loads(row.get("payload_json"), {})
        summary = payload.get("summary") if isinstance(payload, dict) else None
        if not summary:
            summary = "完成学习事件记录"
        activities.append(
            {
                "userId": user_id,
                "username": _student_name(users.get(user_id), user_id),
                "eventType": str(row.get("event_type") or ""),
                "createdAt": _iso(row.get("event_time")),
                "summary": str(summary),
            }
        )
    return activities


def _fetch_student_personal_signals(cursor, user_id: int, limit: int = 8) -> list[dict[str, Any]]:
    params = {"user_id": user_id, "limit": max(1, min(limit, 20))}
    cursor.execute(
        """
        SELECT event_type, event_time, module_id, task_id, question_id, payload_json
        FROM learning_event
        WHERE user_id = %(user_id)s
          AND event_type IN ('ERROR_EVENT', 'HINT_REQUEST', 'AI_INTERACTION')
        ORDER BY event_time DESC, id DESC
        LIMIT %(limit)s
        """,
        params,
    )
    signals: list[dict[str, Any]] = []
    for row in cursor.fetchall() or []:
        payload = _json_loads(row.get("payload_json"), {})
        payload = payload if isinstance(payload, dict) else {}
        event_type = str(row.get("event_type") or "")
        summary = str(payload.get("summary") or "").strip()
        if not summary and event_type == "ERROR_EVENT":
            category = payload.get("error_category") or "未分类错误"
            signature = payload.get("error_signature") or "未识别错误"
            summary = f"出现{category}类错误，错误特征为{signature}"
        elif not summary and event_type == "HINT_REQUEST":
            summary = "学生请求过学习提示"
        elif not summary and event_type == "AI_INTERACTION":
            summary = "学生使用过 AI 辅助"
        if not summary:
            summary = "记录到个人学习过程信号"
        signals.append(
            {
                "eventType": event_type,
                "eventTime": _iso(row.get("event_time")),
                "moduleId": _to_int(row.get("module_id")) if row.get("module_id") is not None else None,
                "taskId": _to_int(row.get("task_id")) if row.get("task_id") is not None else None,
                "questionId": _to_int(row.get("question_id")) if row.get("question_id") is not None else None,
                "summary": summary[:180],
                "severity": payload.get("severity"),
                "errorCategory": payload.get("error_category"),
            }
        )
    return signals


def _question_tags(raw_ai: Any, fallback: Optional[str] = None) -> list[str]:
    data = _json_loads(raw_ai, {})
    for key in ("knowledgeTags", "knowledge_tags", "tags"):
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, list):
            return [str(item) for item in value if item]
        if isinstance(value, str) and value.strip():
            return [item.strip() for item in value.split(",") if item.strip()]
    return [fallback] if fallback else []


def _first_json_value(source: Any, keys: tuple[str, ...], default: Any = None) -> Any:
    data = _json_loads(source, {})
    if not isinstance(data, dict):
        return default
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return default


def read_teacher_dashboard(
    teacher_id: Optional[int] = None,
    current_user: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    _ensure_teacher_source_schemas()
    scope_class_ids = _scope_class_ids(current_user)
    actor_id = _current_user_id(current_user, teacher_id)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            users = _fetch_users(cursor, class_ids=scope_class_ids)
            scoped_user_ids = set(users.keys())
            classes = _fetch_classes(cursor, class_ids=scope_class_ids)
            profiles = _profiles_for_current_users(
                _fetch_latest_profiles(cursor, class_ids=scope_class_ids),
                users,
            )
            attempt_stats = _fetch_attempt_stats(cursor, user_ids=scoped_user_ids)
            submit_counts = _fetch_training_submit_counts(cursor, user_ids=scoped_user_ids)
            last_active = _fetch_last_active(cursor, user_ids=scoped_user_ids)

            active_users = {
                user_id
                for user_id, active_at in last_active.items()
                if active_at
            }

            params: dict[str, Any] = {}
            question_scope = _user_id_scope_condition("u.user_id", scoped_user_ids, params, "gq_user")
            cursor.execute(
                f"""
                SELECT COUNT(DISTINCT gq.generated_question_id) AS count
                FROM generated_question gq
                LEFT JOIN training_session ts
                  ON ts.training_session_id = gq.training_session_id
                LEFT JOIN `{USER_SERVICE_SCHEMA}`.`user` u
                  ON u.user_id = ts.user_id
                WHERE 1 = 1
                  {question_scope}
                """,
                params,
            )
            generated_question_count = _to_int((cursor.fetchone() or {}).get("count"))
            attempt_params: dict[str, Any] = {}
            attempt_scope = _user_id_scope_condition("u.user_id", scoped_user_ids, attempt_params, "gqa_user")
            cursor.execute(
                f"""
                SELECT COUNT(gqa.attempt_id) AS count, AVG(gqa.score) AS avg_score
                FROM generated_question_attempt gqa
                LEFT JOIN `{USER_SERVICE_SCHEMA}`.`user` u
                  ON u.user_id = gqa.user_id
                WHERE 1 = 1
                  {attempt_scope}
                """,
                attempt_params,
            )
            attempt_row = cursor.fetchone() or {}

            average_profile_score = (
                sum(_to_float(row.get("overall_score")) for row in profiles) / len(profiles)
                if profiles else 0
            )

            students = [
                _student_item(row, users, attempt_stats, submit_counts, last_active)
                for row in profiles
            ]
            top_students = sorted(students, key=lambda item: item["overallScore"], reverse=True)[:5]

            return {
                "success": True,
                "teacherId": actor_id,
                "updatedAt": datetime.utcnow().isoformat() + "Z",
                "summary": {
                    "classCount": len(classes),
                    "studentCount": len(users),
                    "activeStudentCount": len(active_users),
                    "generatedQuestionCount": generated_question_count,
                    "attemptCount": _to_int(attempt_row.get("count")),
                    "averageProfileScore": round(average_profile_score, 2),
                    "averageTrainingScore": _round(attempt_row.get("avg_score")),
                },
                "weakDimensions": _weak_dimensions(profiles),
                "recentActivities": _recent_activities(
                    cursor,
                    users,
                    user_ids=scoped_user_ids,
                ),
                "topStudents": [
                    {
                        "userId": item["userId"],
                        "username": item["nickname"] or item["username"],
                        "overallScore": item["overallScore"],
                        "attemptCount": item["generatedQuestionAttemptCount"],
                    }
                    for item in top_students
                ],
            }


def list_teacher_classes(
    teacher_id: Optional[int] = None,
    current_user: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    _ensure_teacher_source_schemas()
    class_ids = _scope_class_ids(current_user)
    actor_id = _current_user_id(current_user, teacher_id)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            users = _fetch_users(cursor, class_ids=class_ids)
            scoped_user_ids = set(users.keys())
            classes = _fetch_classes(cursor, class_ids=class_ids)
            profiles = _fetch_latest_profiles(cursor)
            attempt_stats = _fetch_attempt_stats(cursor, user_ids=scoped_user_ids if class_ids is not None else None)
            last_active = _fetch_last_active(cursor, user_ids=scoped_user_ids if class_ids is not None else None)

    by_class = _group_profiles_by_current_class(profiles, users)

    user_count_by_class: dict[int, int] = {}
    active_count_by_class: dict[int, int] = {}
    training_sum_by_class: dict[int, list[float]] = {}
    last_active_by_class: dict[int, str] = {}
    for user_id, user in users.items():
        class_id = _to_int(user.get("class_id"))
        if class_id:
            user_count_by_class[class_id] = user_count_by_class.get(class_id, 0) + 1
            if last_active.get(user_id):
                active_count_by_class[class_id] = active_count_by_class.get(class_id, 0) + 1
                last_active_by_class[class_id] = max(last_active_by_class.get(class_id, ""), last_active[user_id])
            score = _to_float((attempt_stats.get(user_id) or {}).get("average_score"))
            if score:
                training_sum_by_class.setdefault(class_id, []).append(score)

    class_ids = set(classes.keys())
    items = []
    for class_id in sorted(class_ids):
        class_profiles = by_class.get(class_id, [])
        average_profile = (
            sum(_to_float(row.get("overall_score")) for row in class_profiles) / len(class_profiles)
            if class_profiles else 0
        )
        training_scores = training_sum_by_class.get(class_id, [])
        class_info = classes.get(class_id, {})
        items.append(
            {
                "classId": class_id,
                "className": _display_class_name(class_info.get("class_name"), class_id),
                "studentCount": user_count_by_class.get(class_id, len(class_profiles)),
                "activeStudentCount": active_count_by_class.get(class_id, 0),
                "averageProfileScore": round(average_profile, 2),
                "averageTrainingScore": round(sum(training_scores) / len(training_scores), 2) if training_scores else 0,
                "lastActiveAt": last_active_by_class.get(class_id) or max((_iso(row.get("computed_at")) or "" for row in class_profiles), default=None),
            }
        )
    return {"success": True, "teacherId": actor_id, "items": items}


def list_class_students(class_id: int, current_user: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    _ensure_teacher_source_schemas()
    class_ids = _scope_class_ids(current_user)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            all_class_map = _fetch_classes(cursor, class_ids=None)
            if class_id not in all_class_map:
                raise KeyError(f"classId does not exist: {class_id}")
            if class_ids is not None and class_id not in class_ids:
                raise PermissionError("classId is outside current teacher scope")
            users = _fetch_users(cursor, class_ids=class_ids)
            scoped_user_ids = set(users.keys())
            profiles = _fetch_latest_profiles(cursor)
            attempt_stats = _fetch_attempt_stats(cursor, user_ids=scoped_user_ids if class_ids is not None else None)
            submit_counts = _fetch_training_submit_counts(cursor, user_ids=scoped_user_ids if class_ids is not None else None)
            last_active = _fetch_last_active(cursor, user_ids=scoped_user_ids if class_ids is not None else None)

    profiles = _profiles_for_current_class(profiles, users, class_id)

    items = [
        _student_item(profile, users, attempt_stats, submit_counts, last_active)
        for profile in profiles
    ]
    items.sort(key=lambda item: item["overallScore"], reverse=True)
    return {"success": True, "classId": class_id, "items": items}


def get_student_profile_for_teacher(
    user_id: int,
    current_user: Optional[dict[str, Any]] = None,
    teaching_class_id: Optional[int] = None,
) -> dict[str, Any]:
    _ensure_teacher_source_schemas()
    actor_id = _current_user_id(current_user)
    if actor_id is None:
        raise PermissionError("teacher identity is required")
    if teaching_class_id is not None:
        require_student_in_owned_teaching_class(actor_id, teaching_class_id, user_id)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT u.user_id
                FROM `{USER_SERVICE_SCHEMA}`.`user` u
                INNER JOIN `{USER_SERVICE_SCHEMA}`.`teaching_class_student` tcs
                  ON tcs.student_id = u.user_id
                INNER JOIN `{USER_SERVICE_SCHEMA}`.`teaching_class` tc
                  ON tc.teaching_class_id = tcs.teaching_class_id
                WHERE u.user_id = %(user_id)s
                  AND tc.teacher_id = %(teacher_id)s
                  AND COALESCE(u.is_deleted, 0) = 0
                LIMIT 1
                """,
                {"user_id": user_id, "teacher_id": actor_id},
            )
            student_row = cursor.fetchone()
            if not student_row:
                raise PermissionError("studentId is outside current teacher scope")
    latest_profile = get_latest_student_profile(user_id)
    dashboard = get_profile_dashboard(user_id)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    gqa.attempt_id,
                    gqa.generated_question_id,
                    gq.title,
                    gq.question_type,
                    gq.difficulty,
                    gqa.score,
                    gqa.is_correct,
                    gqa.submitted_at
                FROM generated_question_attempt gqa
                LEFT JOIN generated_question gq
                  ON gq.generated_question_id = gqa.generated_question_id
                WHERE gqa.user_id = %(user_id)s
                ORDER BY gqa.submitted_at DESC
                LIMIT 10
                """,
                {"user_id": user_id},
            )
            attempts = []
            for row in cursor.fetchall() or []:
                attempts.append(
                    {
                        "attemptId": row.get("attempt_id"),
                        "generatedQuestionId": row.get("generated_question_id"),
                        "title": row.get("title") or "个性化训练题",
                        "questionType": row.get("question_type"),
                        "difficulty": row.get("difficulty"),
                        "score": _round(row.get("score")),
                        "isCorrect": None if row.get("is_correct") is None else bool(row.get("is_correct")),
                        "submittedAt": _iso(row.get("submitted_at")),
                    }
                )
            personal_signals = _fetch_student_personal_signals(cursor, user_id)

    recommendations = []
    if latest_profile:
        recommendations = _build_student_recommendations(
            latest_profile,
            attempts,
            _iso(latest_profile.get("computed_at")),
        )

    return {
        "success": True,
        "userId": user_id,
        "latestProfile": latest_profile,
        "dashboard": dashboard,
        "recentAttempts": attempts,
        "personalSignals": personal_signals,
        "recommendations": recommendations,
    }


VALID_ANSWER_RESULTS = {"correct", "incorrect", "attempted", "unanswered"}


def _normalize_answer_result(value: Optional[str]) -> Optional[str]:
    normalized = str(value or "").strip().lower() or None
    if normalized and normalized not in VALID_ANSWER_RESULTS:
        raise ValueError("answerResult only supports correct, incorrect, attempted, or unanswered")
    return normalized


def map_generated_question_record(row: dict[str, Any]) -> dict[str, Any]:
    raw_ai = _json_loads(row.get("raw_ai_json"), {})
    latest_attempt = None
    if row.get("latest_attempt_id"):
        correct_value = row.get("latest_is_correct")
        latest_attempt = {
            "attemptId": row.get("latest_attempt_id"),
            "answer": _json_loads(row.get("latest_answer_json"), row.get("latest_answer_json")),
            "isCorrect": None if correct_value is None else bool(_to_int(correct_value)),
            "score": _round(row.get("latest_score")),
            "costTime": row.get("latest_cost_time"),
            "submittedAt": _iso(row.get("latest_submitted_at")),
        }
    generation_reason = _first_json_value(
        raw_ai,
        ("generationReason", "generation_reason", "reason", "diagnosisReason", "diagnosis_reason"),
    )
    return {
        "generatedQuestionId": row.get("generated_question_id"),
        "trainingSessionId": row.get("training_session_id"),
        "student": {
            "studentId": _to_int(row.get("user_id")),
            "studentNumber": row.get("user_student_number"),
            "studentName": row.get("user_name") or row.get("user_student_number") or "未知学生",
        },
        "teachingClassId": _to_int(row.get("teaching_class_id")),
        "teachingClassName": row.get("teaching_class_name"),
        "courseId": _to_int(row.get("course_id")) if row.get("course_id") is not None else None,
        "courseName": row.get("course_name"),
        "knowledgePointId": _to_int(row.get("knowledge_point_id")) if row.get("knowledge_point_id") is not None else None,
        "knowledgePointName": row.get("knowledge_point_name"),
        "questionType": row.get("question_type"),
        "difficulty": row.get("difficulty"),
        "title": row.get("title") or "个性化训练题",
        "stem": row.get("stem") or "",
        "options": _json_loads(row.get("options_json"), []),
        "generationReason": generation_reason,
        "standardAnswer": row.get("standard_answer"),
        "referenceAnswer": row.get("reference_answer"),
        "explanation": row.get("explanation"),
        "latestAttempt": latest_attempt,
        "attemptCount": _to_int(row.get("attempt_count")),
        "generatedAt": _iso(row.get("created_at")),
        "isTypical": bool(_to_int(row.get("is_typical"))),
    }


def _generated_question_filters(
    *,
    teaching_class_id: Optional[int],
    course_id: Optional[int],
    knowledge_point_id: Optional[int],
    student_id: Optional[int],
    answer_result: Optional[str],
    typical_only: bool,
    date_from: Optional[date],
    date_to: Optional[date],
    generated_question_id: Optional[str] = None,
) -> tuple[str, dict[str, Any]]:
    params: dict[str, Any] = {}
    conditions: list[str] = []
    values = {
        "teaching_class_id": (teaching_class_id, "tcs.teaching_class_id"),
        "course_id": (course_id, "ts.course_id"),
        "knowledge_point_id": (knowledge_point_id, "gq.knowledge_point_id"),
        "student_id": (student_id, "ts.user_id"),
        "generated_question_id": (generated_question_id, "gq.generated_question_id"),
    }
    for key, (value, column) in values.items():
        if value is not None:
            params[key] = value
            conditions.append(f"AND {column} = %({key})s")
    normalized_answer = _normalize_answer_result(answer_result)
    if normalized_answer == "correct":
        conditions.append("AND latest.is_correct = 1")
    elif normalized_answer == "incorrect":
        conditions.append("AND latest.is_correct = 0")
    elif normalized_answer == "attempted":
        conditions.append("AND latest.attempt_id IS NOT NULL")
    elif normalized_answer == "unanswered":
        conditions.append("AND latest.attempt_id IS NULL")
    if typical_only:
        conditions.append("AND typical.teacher_id IS NOT NULL")
    if date_from is not None:
        params["date_from"] = date_from
        conditions.append("AND gq.created_at >= %(date_from)s")
    if date_to is not None:
        params["date_to"] = date_to
        conditions.append("AND gq.created_at < DATE_ADD(%(date_to)s, INTERVAL 1 DAY)")
    return "\n".join(conditions), params


def _generated_question_from_sql(actor_id: int, conditions: str) -> str:
    return f"""
        FROM generated_question gq
        INNER JOIN training_session ts ON ts.training_session_id = gq.training_session_id
        INNER JOIN `{USER_SERVICE_SCHEMA}`.`user` u ON u.user_id = ts.user_id
        INNER JOIN `{USER_SERVICE_SCHEMA}`.`teaching_class_student` tcs ON tcs.student_id = ts.user_id
        INNER JOIN `{USER_SERVICE_SCHEMA}`.`teaching_class` tc
          ON tc.teaching_class_id = tcs.teaching_class_id
        LEFT JOIN `{USER_SERVICE_SCHEMA}`.`course` c ON c.id = ts.course_id
        LEFT JOIN knowledge_point kp ON kp.knowledge_point_id = gq.knowledge_point_id
        LEFT JOIN (
            SELECT attempt.generated_question_id, COUNT(*) AS attempt_count
            FROM generated_question_attempt attempt
            GROUP BY attempt.generated_question_id
        ) attempt_stats ON attempt_stats.generated_question_id = gq.generated_question_id
        LEFT JOIN generated_question_attempt latest
          ON latest.attempt_id = (
              SELECT newest.attempt_id
              FROM generated_question_attempt newest
              WHERE newest.generated_question_id = gq.generated_question_id
              ORDER BY newest.submitted_at DESC, newest.attempt_id DESC
              LIMIT 1
          )
        LEFT JOIN teacher_typical_question typical
          ON typical.generated_question_id = gq.generated_question_id
         AND typical.teacher_id = {int(actor_id)}
        WHERE COALESCE(u.is_deleted, 0) = 0
          AND tc.teacher_id = {int(actor_id)}
          {conditions}
    """


def _generated_question_select_sql() -> str:
    return """
        SELECT
            gq.*,
            ts.user_id,
            ts.course_id,
            u.user_student_number,
            u.user_name,
            tc.teaching_class_id,
            tc.class_name AS teaching_class_name,
            c.course_name,
            kp.name AS knowledge_point_name,
            COALESCE(attempt_stats.attempt_count, 0) AS attempt_count,
            latest.attempt_id AS latest_attempt_id,
            latest.answer_json AS latest_answer_json,
            latest.is_correct AS latest_is_correct,
            latest.score AS latest_score,
            latest.cost_time AS latest_cost_time,
            latest.submitted_at AS latest_submitted_at,
            CASE WHEN typical.teacher_id IS NULL THEN 0 ELSE 1 END AS is_typical
    """


def list_generated_questions_for_teacher(
    *,
    teacher_id: Optional[int] = None,
    current_user: Optional[dict[str, Any]] = None,
    teaching_class_id: Optional[int] = None,
    course_id: Optional[int] = None,
    knowledge_point_id: Optional[int] = None,
    student_id: Optional[int] = None,
    answer_result: Optional[str] = None,
    typical_only: bool = False,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    _ensure_teacher_source_schemas()
    actor_id = _current_user_id(current_user, teacher_id)
    if actor_id is None:
        raise PermissionError("teacher identity is required")
    page = max(1, page)
    size = max(1, min(size, 100))
    conditions, params = _generated_question_filters(
        teaching_class_id=teaching_class_id,
        course_id=course_id,
        knowledge_point_id=knowledge_point_id,
        student_id=student_id,
        answer_result=answer_result,
        typical_only=typical_only,
        date_from=date_from,
        date_to=date_to,
    )
    base_from = _generated_question_from_sql(actor_id, conditions)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM ("
                "SELECT gq.generated_question_id, tc.teaching_class_id "
                f"{base_from} GROUP BY gq.generated_question_id, tc.teaching_class_id"
                ") records",
                params,
            )
            total = _to_int((cursor.fetchone() or {}).get("total"))
            query_params = {**params, "limit": size, "offset": (page - 1) * size}
            cursor.execute(
                f"""
                {_generated_question_select_sql()}
                {base_from}
                ORDER BY gq.created_at DESC, gq.generated_question_id, tc.teaching_class_id
                LIMIT %(limit)s OFFSET %(offset)s
                """,
                query_params,
            )
            rows = list(cursor.fetchall() or [])
    return {
        "success": True,
        "teacherId": actor_id,
        "items": [map_generated_question_record(row) for row in rows],
        "total": total,
        "page": page,
        "size": size,
    }


def get_generated_question_for_teacher(
    generated_question_id: str,
    *,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    actor_id = _current_user_id(current_user)
    if actor_id is None:
        raise PermissionError("teacher identity is required")
    conditions, params = _generated_question_filters(
        teaching_class_id=None,
        course_id=None,
        knowledge_point_id=None,
        student_id=None,
        answer_result=None,
        typical_only=False,
        date_from=None,
        date_to=None,
        generated_question_id=generated_question_id,
    )
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"{_generated_question_select_sql()} {_generated_question_from_sql(actor_id, conditions)} "
                "ORDER BY tc.updated_at DESC LIMIT 1",
                params,
            )
            row = cursor.fetchone()
    if not row:
        raise KeyError(f"generated question does not exist: {generated_question_id}")
    return map_generated_question_record(row)


def mark_generated_question_typical(teacher_id: int, generated_question_id: str) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM generated_question WHERE generated_question_id = %(question_id)s LIMIT 1",
                {"question_id": generated_question_id},
            )
            if not cursor.fetchone():
                raise KeyError(f"generated question does not exist: {generated_question_id}")
            cursor.execute(
                """
                INSERT IGNORE INTO teacher_typical_question (teacher_id, generated_question_id, created_at)
                VALUES (%(teacher_id)s, %(question_id)s, NOW(6))
                """,
                {"teacher_id": teacher_id, "question_id": generated_question_id},
            )
        conn.commit()
    return {"generatedQuestionId": generated_question_id, "isTypical": True}


def unmark_generated_question_typical(teacher_id: int, generated_question_id: str) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM teacher_typical_question
                WHERE teacher_id = %(teacher_id)s AND generated_question_id = %(question_id)s
                """,
                {"teacher_id": teacher_id, "question_id": generated_question_id},
            )
        conn.commit()
    return {"generatedQuestionId": generated_question_id, "isTypical": False}


def summarize_generated_questions_for_class(
    teaching_class_id: int,
    current_user: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    actor_id = _current_user_id(current_user)
    if actor_id is not None:
        require_owned_teaching_class(actor_id, teaching_class_id)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    gq.knowledge_point_id,
                    COALESCE(kp.name, '未标注知识点') AS knowledge_point_name,
                    COUNT(DISTINCT ts.user_id) AS student_count,
                    COUNT(DISTINCT gq.generated_question_id) AS generated_question_count,
                    COUNT(gqa.attempt_id) AS attempted_count,
                    SUM(CASE WHEN gqa.is_correct = 0 THEN 1 ELSE 0 END) AS incorrect_count,
                    GROUP_CONCAT(DISTINCT gq.generated_question_id ORDER BY gq.created_at DESC SEPARATOR ',') AS question_ids
                FROM generated_question gq
                INNER JOIN training_session ts ON ts.training_session_id = gq.training_session_id
                INNER JOIN `{USER_SERVICE_SCHEMA}`.`teaching_class_student` tcs ON tcs.student_id = ts.user_id
                LEFT JOIN knowledge_point kp ON kp.knowledge_point_id = gq.knowledge_point_id
                LEFT JOIN generated_question_attempt gqa ON gqa.generated_question_id = gq.generated_question_id
                WHERE tcs.teaching_class_id = %(teaching_class_id)s
                GROUP BY gq.knowledge_point_id, kp.name
                ORDER BY incorrect_count DESC, generated_question_count DESC
                """,
                {"teaching_class_id": teaching_class_id},
            )
            rows = list(cursor.fetchall() or [])
    items = []
    for row in rows:
        attempted_count = _to_int(row.get("attempted_count"))
        incorrect_count = _to_int(row.get("incorrect_count"))
        items.append(
            {
                "knowledgePointId": row.get("knowledge_point_id"),
                "knowledgePointName": row.get("knowledge_point_name"),
                "studentCount": _to_int(row.get("student_count")),
                "generatedQuestionCount": _to_int(row.get("generated_question_count")),
                "attemptedCount": attempted_count,
                "incorrectCount": incorrect_count,
                "incorrectRate": round(incorrect_count / attempted_count, 4) if attempted_count else 0.0,
                "representativeQuestionIds": str(row.get("question_ids") or "").split(",")[:3],
            }
        )
    return {"teachingClassId": teaching_class_id, "items": items}
