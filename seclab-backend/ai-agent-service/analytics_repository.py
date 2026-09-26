from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from database import get_connection


RANKING_TYPES = {"overall", "experiment", "course"}


def _table_exists(cursor, table_name: str) -> bool:
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


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
        LIMIT 1
        """,
        (table_name, column_name),
    )
    return cursor.fetchone() is not None


def _scalar(cursor, sql: str, params: tuple[Any, ...] = ()) -> Any:
    cursor.execute(sql, params)
    row = cursor.fetchone()
    if not row:
        return None
    return next(iter(row.values()))


def _serialize_datetime(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return None
    return str(value)


def _count_table_rows(cursor, table_name: str, *, include_only_active: bool = False) -> int:
    if not _table_exists(cursor, table_name):
        return 0

    where_clauses: list[str] = []
    if include_only_active:
        if _column_exists(cursor, table_name, "is_deleted"):
            where_clauses.append("COALESCE(is_deleted, 0) = 0")
        elif _column_exists(cursor, table_name, "deleted"):
            where_clauses.append("COALESCE(deleted, 0) = 0")

    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    total = _scalar(cursor, f"SELECT COUNT(*) AS total FROM `{table_name}`{where_sql}")
    return int(total or 0)


def _count_users_by_role(cursor, admin_flag: bool) -> int:
    if not _table_exists(cursor, "user"):
        return 0

    where_clauses = ["COALESCE(is_deleted, 0) = 0"]
    if _column_exists(cursor, "user", "is_admin"):
        where_clauses.append("COALESCE(is_admin + 0, 0) = 1" if admin_flag else "COALESCE(is_admin + 0, 0) = 0")

    total = _scalar(
        cursor,
        f"SELECT COUNT(*) AS total FROM `user` WHERE {' AND '.join(where_clauses)}",
    )
    return int(total or 0)


def _avg_latest_class_score(cursor) -> Optional[float]:
    if not _table_exists(cursor, "class_profile_snapshot"):
        return None

    avg_score = _scalar(
        cursor,
        """
        SELECT ROUND(AVG(latest.class_overall_score), 2) AS avg_score
        FROM class_profile_snapshot latest
        WHERE NOT EXISTS (
            SELECT 1
            FROM class_profile_snapshot newer
            WHERE newer.class_id = latest.class_id
              AND (
                    newer.computed_at > latest.computed_at
                    OR (
                        newer.computed_at = latest.computed_at
                        AND newer.created_at > latest.created_at
                    )
                  )
        )
        """,
    )
    return float(avg_score) if avg_score is not None else None


def _active_student_count(cursor) -> int:
    if not _table_exists(cursor, "learning_event"):
        return 0

    total = _scalar(
        cursor,
        """
        SELECT COUNT(DISTINCT user_id) AS total
        FROM learning_event
        WHERE user_id IS NOT NULL
          AND event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """,
    )
    return int(total or 0)


def _completion_rate(cursor) -> Optional[float]:
    if not _table_exists(cursor, "challenge_completion_event"):
        return None

    rate = _scalar(
        cursor,
        """
        SELECT ROUND(
            AVG(
                CASE
                    WHEN LOWER(COALESCE(completion_status, '')) IN ('completed', 'success', 'passed')
                    THEN 100
                    ELSE 0
                END
            ),
            2
        ) AS completion_rate
        FROM challenge_completion_event
        """,
    )
    return float(rate) if rate is not None else None


def get_dashboard_summary() -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            user_count = _count_table_rows(cursor, "user", include_only_active=True)
            student_count = _count_users_by_role(cursor, admin_flag=False)
            teacher_count = _count_users_by_role(cursor, admin_flag=True)
            course_count = _count_table_rows(cursor, "course", include_only_active=True)
            module_count = _count_table_rows(cursor, "module", include_only_active=True)
            class_count = _count_table_rows(cursor, "class", include_only_active=False)
            avg_class_score = _avg_latest_class_score(cursor)
            active_student_count = _active_student_count(cursor)
            completion_rate = _completion_rate(cursor)

    # 当前库里教师端“实验”与“模块”都来自 module 维度，先保持同口径返回。
    return {
        "userCount": user_count,
        "studentCount": student_count,
        "teacherCount": teacher_count,
        "courseCount": course_count,
        "moduleCount": module_count,
        "experimentCount": module_count,
        "classCount": class_count,
        "avgClassScore": avg_class_score,
        "activeStudentCount": active_student_count,
        "completionRate": completion_rate,
    }


def _load_user_map(cursor, user_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not user_ids or not _table_exists(cursor, "user"):
        return {}

    placeholders = ",".join(["%s"] * len(user_ids))
    cursor.execute(
        f"""
        SELECT user_id, user_student_number, user_name
        FROM `user`
        WHERE user_id IN ({placeholders})
          AND COALESCE(is_deleted, 0) = 0
        """,
        tuple(user_ids),
    )
    return {int(row["user_id"]): row for row in cursor.fetchall()}


def _load_class_map(cursor, class_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not class_ids or not _table_exists(cursor, "class"):
        return {}

    placeholders = ",".join(["%s"] * len(class_ids))
    cursor.execute(
        f"""
        SELECT class_id, class_name
        FROM `class`
        WHERE class_id IN ({placeholders})
        """,
        tuple(class_ids),
    )
    return {int(row["class_id"]): row for row in cursor.fetchall()}


def _overall_ranking_rows(cursor, class_id: Optional[int]) -> list[dict[str, Any]]:
    if not _table_exists(cursor, "student_profile_snapshot"):
        return []

    if class_id is None:
        cursor.execute(
            """
            SELECT s.user_id, s.class_id, s.overall_score AS score, s.computed_at AS updated_at
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
            LIMIT 100
            """
        )
    else:
        cursor.execute(
            """
            SELECT s.user_id, s.class_id, s.overall_score AS score, s.computed_at AS updated_at
            FROM student_profile_snapshot s
            WHERE s.class_id = %s
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
            ORDER BY s.overall_score DESC, s.computed_at DESC, s.user_id ASC
            LIMIT 100
            """,
            (class_id,),
        )

    return cursor.fetchall()


def _experiment_ranking_rows(cursor, class_id: Optional[int]) -> list[dict[str, Any]]:
    if _table_exists(cursor, "flag_submission"):
        if class_id is None:
            cursor.execute(
                """
                SELECT
                    user_id,
                    class_id,
                    COALESCE(SUM(score), 0) AS score,
                    COUNT(DISTINCT CASE WHEN COALESCE(is_correct, 0) = 1 THEN task_id END) AS completed_experiment_count,
                    MAX(created_at) AS updated_at
                FROM flag_submission
                WHERE user_id IS NOT NULL
                GROUP BY user_id, class_id
                HAVING score > 0 OR completed_experiment_count > 0
                ORDER BY score DESC, completed_experiment_count DESC, updated_at DESC, user_id ASC
                LIMIT 100
                """
            )
        else:
            cursor.execute(
                """
                SELECT
                    user_id,
                    class_id,
                    COALESCE(SUM(score), 0) AS score,
                    COUNT(DISTINCT CASE WHEN COALESCE(is_correct, 0) = 1 THEN task_id END) AS completed_experiment_count,
                    MAX(created_at) AS updated_at
                FROM flag_submission
                WHERE user_id IS NOT NULL
                  AND class_id = %s
                GROUP BY user_id, class_id
                HAVING score > 0 OR completed_experiment_count > 0
                ORDER BY score DESC, completed_experiment_count DESC, updated_at DESC, user_id ASC
                LIMIT 100
                """,
                (class_id,),
            )
        return cursor.fetchall()

    if not _table_exists(cursor, "challenge_completion_event"):
        return []

    if class_id is None:
        cursor.execute(
            """
            SELECT
                user_id,
                class_id,
                COUNT(DISTINCT CASE WHEN LOWER(COALESCE(completion_status, '')) IN ('completed', 'success', 'passed') THEN task_id END) AS score,
                COUNT(DISTINCT CASE WHEN LOWER(COALESCE(completion_status, '')) IN ('completed', 'success', 'passed') THEN task_id END) AS completed_experiment_count,
                MAX(created_at) AS updated_at
            FROM challenge_completion_event
            WHERE user_id IS NOT NULL
            GROUP BY user_id, class_id
            HAVING score > 0
            ORDER BY score DESC, updated_at DESC, user_id ASC
            LIMIT 100
            """
        )
    else:
        cursor.execute(
            """
            SELECT
                user_id,
                class_id,
                COUNT(DISTINCT CASE WHEN LOWER(COALESCE(completion_status, '')) IN ('completed', 'success', 'passed') THEN task_id END) AS score,
                COUNT(DISTINCT CASE WHEN LOWER(COALESCE(completion_status, '')) IN ('completed', 'success', 'passed') THEN task_id END) AS completed_experiment_count,
                MAX(created_at) AS updated_at
            FROM challenge_completion_event
            WHERE user_id IS NOT NULL
              AND class_id = %s
            GROUP BY user_id, class_id
            HAVING score > 0
            ORDER BY score DESC, updated_at DESC, user_id ASC
            LIMIT 100
            """,
            (class_id,),
        )
    return cursor.fetchall()


def _course_ranking_rows(cursor, class_id: Optional[int]) -> list[dict[str, Any]]:
    if not _table_exists(cursor, "learning_event"):
        return []

    if class_id is None:
        cursor.execute(
            """
            SELECT
                user_id,
                class_id,
                COUNT(DISTINCT course_id) AS score,
                COUNT(DISTINCT course_id) AS completed_experiment_count,
                MAX(event_time) AS updated_at
            FROM learning_event
            WHERE user_id IS NOT NULL
              AND course_id IS NOT NULL
            GROUP BY user_id, class_id
            HAVING score > 0
            ORDER BY score DESC, updated_at DESC, user_id ASC
            LIMIT 100
            """
        )
    else:
        cursor.execute(
            """
            SELECT
                user_id,
                class_id,
                COUNT(DISTINCT course_id) AS score,
                COUNT(DISTINCT course_id) AS completed_experiment_count,
                MAX(event_time) AS updated_at
            FROM learning_event
            WHERE user_id IS NOT NULL
              AND course_id IS NOT NULL
              AND class_id = %s
            GROUP BY user_id, class_id
            HAVING score > 0
            ORDER BY score DESC, updated_at DESC, user_id ASC
            LIMIT 100
            """,
            (class_id,),
        )
    return cursor.fetchall()


def get_rankings(rank_type: str = "overall", class_id: Optional[int] = None) -> dict[str, Any]:
    normalized_type = str(rank_type or "overall").strip().lower()
    if normalized_type not in RANKING_TYPES:
        raise ValueError(f"unsupported ranking type: {rank_type}")

    with get_connection() as conn:
        with conn.cursor() as cursor:
            if normalized_type == "overall":
                rows = _overall_ranking_rows(cursor, class_id)
            elif normalized_type == "experiment":
                rows = _experiment_ranking_rows(cursor, class_id)
            else:
                rows = _course_ranking_rows(cursor, class_id)

            user_ids = [int(row["user_id"]) for row in rows if row.get("user_id") is not None]
            class_ids = [int(row["class_id"]) for row in rows if row.get("class_id") is not None]
            user_map = _load_user_map(cursor, sorted(set(user_ids)))
            class_map = _load_class_map(cursor, sorted(set(class_ids)))

    items: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        user_id = int(row.get("user_id") or 0)
        snapshot_class_id = int(row["class_id"]) if row.get("class_id") is not None else None
        user_info = user_map.get(user_id, {})
        class_info = class_map.get(snapshot_class_id or -1, {})
        score = float(row.get("score") or 0)
        completed = int(row.get("completed_experiment_count") or 0)

        items.append(
            {
                "rank": index,
                "userId": user_id,
                "classId": snapshot_class_id,
                "studentNumber": str(user_info.get("user_student_number") or "").strip(),
                "name": str(user_info.get("user_name") or "").strip() or f"用户 {user_id}",
                "className": str(class_info.get("class_name") or "").strip(),
                "score": round(score, 2),
                "completedExperimentCount": completed,
                "updatedAt": _serialize_datetime(row.get("updated_at")),
            }
        )

    return {
        "type": normalized_type,
        "classId": class_id,
        "items": items,
    }
