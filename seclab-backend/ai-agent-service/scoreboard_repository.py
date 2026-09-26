from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from database import get_connection


SCOREBOARD_SOURCE = "student_profile_snapshot+generated_question_attempt"
DIMENSION_KEYS = (
    ("knowledge_mastery_score", "knowledge_mastery", "知识掌握"),
    ("troubleshooting_score", "troubleshooting", "排障能力"),
    ("autonomy_score", "autonomy", "自主探索"),
    ("ai_collaboration_score", "ai_collaboration", "AI 协作"),
    ("engagement_score", "engagement", "学习投入"),
)


def _table_exists(cursor, schema_name: Optional[str], table_name: str) -> bool:
    if schema_name:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_name = %s
            LIMIT 1
            """,
            (schema_name, table_name),
        )
    else:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = %s
            LIMIT 1
            """,
            (table_name,),
        )
    return cursor.fetchone() is not None


def _serialize_datetime(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return None
    return str(value)


def _parse_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="ignore")
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _latest_snapshot_rows(cursor, limit: int) -> list[dict[str, Any]]:
    if not _table_exists(cursor, None, "student_profile_snapshot"):
        return []

    cursor.execute(
        """
        SELECT
            s.snapshot_id,
            s.user_id,
            s.class_id,
            s.course_id,
            s.computed_at,
            s.knowledge_mastery_score,
            s.troubleshooting_score,
            s.autonomy_score,
            s.ai_collaboration_score,
            s.engagement_score,
            s.overall_score,
            s.profile_summary_json,
            s.created_at
        FROM student_profile_snapshot s
        WHERE NOT EXISTS (
            SELECT 1
            FROM student_profile_snapshot newer
            WHERE newer.user_id = s.user_id
              AND (
                    newer.computed_at > s.computed_at
                    OR (
                        newer.computed_at = s.computed_at
                        AND newer.created_at > s.created_at
                    )
                  )
        )
        ORDER BY s.overall_score DESC, s.computed_at DESC, s.user_id ASC
        LIMIT %s
        """,
        (limit,),
    )
    return list(cursor.fetchall() or [])


def _load_teaching_class_roster(cursor) -> list[dict[str, Any]]:
    """
    排行榜名单以教师端教学班名单为准：教师看到多少人，学生端就能看到多少人。

    早期实现是从 student_profile_snapshot 出发的，只有做过实验、算过画像的学生才进榜，
    刚导入还没开始做的学生整批消失，学生端筛自己班只看得到零星几个人。
    """
    for schema in ("userservice", None):
        if not _table_exists(cursor, schema, "teaching_class_student"):
            continue
        if not _table_exists(cursor, schema, "teaching_class"):
            continue
        prefix = f"`{schema}`." if schema else ""
        cursor.execute(
            f"""
            SELECT
                u.user_id,
                u.user_student_number,
                u.user_name,
                u.user_image,
                u.class_id_class_id AS class_id,
                c.class_name
            FROM {prefix}`teaching_class_student` tcs
            INNER JOIN {prefix}`teaching_class` tc
                ON tc.teaching_class_id = tcs.teaching_class_id
               AND tc.status = 'ACTIVE'
            INNER JOIN {prefix}`user` u
                ON u.user_id = tcs.student_id
            LEFT JOIN {prefix}`class` c
                ON c.class_id = u.class_id_class_id
            WHERE COALESCE(u.is_deleted, 0) = 0
              AND u.user_role = 'STUDENT'
            GROUP BY u.user_id, u.user_student_number, u.user_name, u.user_image,
                     u.class_id_class_id, c.class_name
            ORDER BY u.user_student_number
            """
        )
        return list(cursor.fetchall() or [])
    return []


def _latest_snapshot_map(cursor, user_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not user_ids or not _table_exists(cursor, None, "student_profile_snapshot"):
        return {}

    placeholders = ",".join(["%s"] * len(user_ids))
    cursor.execute(
        f"""
        SELECT
            s.snapshot_id,
            s.user_id,
            s.class_id,
            s.course_id,
            s.computed_at,
            s.knowledge_mastery_score,
            s.troubleshooting_score,
            s.autonomy_score,
            s.ai_collaboration_score,
            s.engagement_score,
            s.overall_score,
            s.profile_summary_json,
            s.created_at
        FROM student_profile_snapshot s
        WHERE s.user_id IN ({placeholders})
          AND NOT EXISTS (
            SELECT 1
            FROM student_profile_snapshot newer
            WHERE newer.user_id = s.user_id
              AND (
                    newer.computed_at > s.computed_at
                    OR (
                        newer.computed_at = s.computed_at
                        AND newer.created_at > s.created_at
                    )
                  )
        )
        """,
        tuple(user_ids),
    )
    return {int(row["user_id"]): row for row in cursor.fetchall() or []}


def _load_generated_attempt_stats(cursor, user_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not user_ids or not _table_exists(cursor, None, "generated_question_attempt"):
        return {}

    placeholders = ",".join(["%s"] * len(user_ids))
    cursor.execute(
        f"""
        SELECT
            user_id,
            COUNT(*) AS generated_question_attempt_count,
            ROUND(AVG(score), 2) AS generated_average_score,
            MAX(submitted_at) AS last_generated_attempt_at
        FROM generated_question_attempt
        WHERE user_id IN ({placeholders})
        GROUP BY user_id
        """,
        tuple(user_ids),
    )
    return {int(row["user_id"]): row for row in cursor.fetchall() or []}


def _load_training_submission_stats(cursor, user_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not user_ids or not _table_exists(cursor, None, "question_submission"):
        return {}

    placeholders = ",".join(["%s"] * len(user_ids))
    cursor.execute(
        f"""
        SELECT
            user_id,
            COUNT(*) AS training_question_submit_count,
            ROUND(AVG(score), 2) AS training_average_score,
            MAX(created_at) AS last_training_submit_at
        FROM question_submission
        WHERE user_id IN ({placeholders})
          AND question_source = 'personalized_training'
        GROUP BY user_id
        """,
        tuple(user_ids),
    )
    return {int(row["user_id"]): row for row in cursor.fetchall() or []}


def _load_learning_event_stats(cursor, user_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not user_ids or not _table_exists(cursor, None, "learning_event"):
        return {}

    placeholders = ",".join(["%s"] * len(user_ids))
    cursor.execute(
        f"""
        SELECT
            user_id,
            COUNT(*) AS event_count,
            MAX(event_time) AS last_event_at
        FROM learning_event
        WHERE user_id IN ({placeholders})
        GROUP BY user_id
        """,
        tuple(user_ids),
    )
    return {int(row["user_id"]): row for row in cursor.fetchall() or []}


def _load_user_map(cursor, user_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not user_ids:
        return {}

    user_table: Optional[str] = None
    if _table_exists(cursor, "userservice", "user"):
        user_table = "`userservice`.`user`"
    elif _table_exists(cursor, None, "user"):
        user_table = "`user`"

    if not user_table:
        return {}

    placeholders = ",".join(["%s"] * len(user_ids))
    cursor.execute(
        f"""
        SELECT
            user_id,
            user_student_number,
            user_name,
            user_image,
            class_id_class_id
        FROM {user_table}
        WHERE user_id IN ({placeholders})
          AND COALESCE(is_deleted, 0) = 0
        """,
        tuple(user_ids),
    )
    return {int(row["user_id"]): row for row in cursor.fetchall() or []}


def _load_class_map(cursor, class_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not class_ids:
        return {}

    class_table: Optional[str] = None
    if _table_exists(cursor, "userservice", "class"):
        class_table = "`userservice`.`class`"
    elif _table_exists(cursor, None, "class"):
        class_table = "`class`"

    if not class_table:
        return {}

    placeholders = ",".join(["%s"] * len(class_ids))
    cursor.execute(
        f"""
        SELECT class_id, class_name
        FROM {class_table}
        WHERE class_id IN ({placeholders})
        """,
        tuple(class_ids),
    )
    return {int(row["class_id"]): row for row in cursor.fetchall() or []}


def _dimension_extreme(row: dict[str, Any], *, best: bool) -> Optional[str]:
    scored: list[tuple[float, str]] = []
    for field_name, _code, label in DIMENSION_KEYS:
        value = _float_or_none(row.get(field_name))
        if value is not None:
            scored.append((value, label))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=best)
    return scored[0][1]


def _latest_time(*values: Any) -> Optional[datetime]:
    datetimes = [value for value in values if isinstance(value, datetime)]
    return max(datetimes) if datetimes else None


def _average_training_score(generated_stats: dict[str, Any], training_stats: dict[str, Any]) -> Optional[float]:
    generated_count = _int_or_zero(generated_stats.get("generated_question_attempt_count"))
    training_count = _int_or_zero(training_stats.get("training_question_submit_count"))
    generated_average = _float_or_none(generated_stats.get("generated_average_score"))
    training_average = _float_or_none(training_stats.get("training_average_score"))

    weighted_total = 0.0
    weighted_count = 0
    if generated_count and generated_average is not None:
        weighted_total += generated_average * generated_count
        weighted_count += generated_count
    if training_count and training_average is not None:
        weighted_total += training_average * training_count
        weighted_count += training_count

    if not weighted_count:
        return None
    return round(weighted_total / weighted_count, 2)


def get_scoreboard(limit: int = 50) -> dict[str, Any]:
    safe_limit = max(1, min(int(limit or 50), 500))
    with get_connection() as conn:
        with conn.cursor() as cursor:
            roster_rows = _load_teaching_class_roster(cursor)
            if roster_rows:
                # 名单驱动：教学班里的每个学生都占一行，没有画像数据的也在
                base_rows = [
                    {
                        "user": row,
                        "snapshot": None,
                    }
                    for row in roster_rows
                ]
                user_ids = [int(row["user_id"]) for row in roster_rows if row.get("user_id") is not None]
                snapshot_map = _latest_snapshot_map(cursor, user_ids)
                for entry in base_rows:
                    entry["snapshot"] = snapshot_map.get(int(entry["user"]["user_id"]))
                class_map = {}
            else:
                # 老库还没有教学班表时退回旧行为：只列有画像快照的学生
                snapshot_rows = _latest_snapshot_rows(cursor, safe_limit)
                user_ids = [int(row["user_id"]) for row in snapshot_rows if row.get("user_id") is not None]
                user_map = _load_user_map(cursor, sorted(set(user_ids)))
                base_rows = [
                    {
                        "user": user_map.get(int(row["user_id"]), {"user_id": row["user_id"]}),
                        "snapshot": row,
                    }
                    for row in snapshot_rows
                    if row.get("user_id") is not None
                ]
                class_ids = sorted(
                    {
                        int(value)
                        for row in snapshot_rows
                        for value in (
                            row.get("class_id"),
                            (user_map.get(int(row.get("user_id") or 0), {}) or {}).get("class_id_class_id"),
                        )
                        if value is not None
                    }
                )
                class_map = _load_class_map(cursor, class_ids)

            generated_stats = _load_generated_attempt_stats(cursor, user_ids)
            training_stats = _load_training_submission_stats(cursor, user_ids)
            learning_stats = _load_learning_event_stats(cursor, user_ids)

    items: list[dict[str, Any]] = []
    for entry in base_rows:
        user_info = entry["user"] or {}
        row = entry["snapshot"] or {}
        user_id = int(user_info.get("user_id") or row.get("user_id") or 0)
        class_id = user_info.get("class_id") or user_info.get("class_id_class_id") or row.get("class_id")
        class_id_int = int(class_id) if class_id is not None else None
        class_name = user_info.get("class_name")
        if class_name is None:
            class_name = class_map.get(class_id_int or -1, {}).get("class_name")
        class_info = {"class_name": class_name}
        summary = _parse_json(row.get("profile_summary_json"))
        evidence = summary.get("evidence") if isinstance(summary.get("evidence"), dict) else {}
        raw_stats = summary.get("raw_stats") if isinstance(summary.get("raw_stats"), dict) else {}
        generated = generated_stats.get(user_id, {})
        training = training_stats.get(user_id, {})
        events = learning_stats.get(user_id, {})
        last_active = _latest_time(
            row.get("computed_at"),
            generated.get("last_generated_attempt_at"),
            training.get("last_training_submit_at"),
            events.get("last_event_at"),
        )
        generated_attempt_count = _int_or_zero(
            generated.get("generated_question_attempt_count")
            or raw_stats.get("generated_question_attempt_count")
        )
        db_training_submit_count = _int_or_zero(training.get("training_question_submit_count"))
        raw_training_total = _int_or_zero(
            raw_stats.get("training_question_submit_count") or evidence.get("questionSubmitCount")
        )
        training_count = max(raw_training_total, generated_attempt_count + db_training_submit_count)

        # 还没做过实验的学生没有画像快照：综合分留空，前端渲染成 --，排在有分的人后面
        overall_score = (
            round(float(row.get("overall_score") or 0), 2) if row.get("overall_score") is not None else None
        )
        has_activity = overall_score is not None or training_count > 0 or last_active is not None

        items.append(
            {
                "rank": 0,
                "userId": user_id,
                "studentNumber": str(user_info.get("user_student_number") or "").strip(),
                "username": str(user_info.get("user_name") or "").strip() or f"用户 {user_id}",
                "nickname": str(user_info.get("user_name") or "").strip() or f"用户 {user_id}",
                "classId": class_id_int,
                "className": str(class_info.get("class_name") or "").strip(),
                "avatarUrl": str(user_info.get("user_image") or "").strip() or None,
                "overallScore": overall_score,
                "trainingCount": training_count,
                "generatedQuestionAttemptCount": generated_attempt_count,
                "averageTrainingScore": _average_training_score(generated, training),
                "lastActiveAt": _serialize_datetime(last_active or row.get("computed_at")),
                "hasActivity": has_activity,
                "_lastActiveSort": (last_active or row.get("computed_at")).timestamp()
                if isinstance(last_active or row.get("computed_at"), datetime)
                else 0,
                "trend": "stable",
                "weakDimension": _dimension_extreme(row, best=False),
                "bestDimension": _dimension_extreme(row, best=True),
            }
        )

    items.sort(
        key=lambda item: (
            0 if item["overallScore"] is not None else 1,
            -float(item["overallScore"] or 0),
            -float(item.get("_lastActiveSort") or 0),
            str(item.get("studentNumber") or ""),
            int(item["userId"] or 0),
        )
    )
    items = items[:safe_limit]
    for index, item in enumerate(items, start=1):
        item["rank"] = index
        item.pop("_lastActiveSort", None)

    updated_at = max((item["lastActiveAt"] for item in items if item.get("lastActiveAt")), default=None)
    return {
        "success": True,
        "updatedAt": updated_at or _serialize_datetime(datetime.utcnow()),
        "source": SCOREBOARD_SOURCE,
        "items": items,
    }
