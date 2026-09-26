import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

from database import ensure_database, get_connection
from profile_repository import OVERALL_WEIGHTS as STUDENT_OVERALL_WEIGHTS


CLASS_PROFILE_SNAPSHOT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS class_profile_snapshot (
    snapshot_id VARCHAR(64) NOT NULL,
    class_id BIGINT NOT NULL,
    course_id BIGINT NULL,
    computed_at DATETIME(6) NOT NULL,
    student_count INT NOT NULL DEFAULT 0,
    class_avg_knowledge_mastery DECIMAL(5,2) NOT NULL DEFAULT 0,
    class_avg_troubleshooting DECIMAL(5,2) NOT NULL DEFAULT 0,
    class_avg_autonomy DECIMAL(5,2) NOT NULL DEFAULT 0,
    class_avg_ai_collaboration DECIMAL(5,2) NOT NULL DEFAULT 0,
    class_avg_engagement DECIMAL(5,2) NOT NULL DEFAULT 0,
    class_overall_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    weak_dimensions_json JSON NOT NULL,
    strengths_json JSON NOT NULL,
    risk_students_json JSON NOT NULL,
    summary_json JSON NOT NULL,
    source_range_start DATETIME(6) NULL,
    source_range_end DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (snapshot_id),
    KEY idx_class_profile_class_time (class_id, computed_at),
    KEY idx_class_profile_course_time (course_id, computed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

CLASS_PROFILE_STUDENT_METRIC_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS class_profile_student_metric (
    id BIGINT NOT NULL AUTO_INCREMENT,
    class_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    snapshot_id VARCHAR(64) NOT NULL,
    overall_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    knowledge_mastery_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    troubleshooting_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    autonomy_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    ai_collaboration_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    engagement_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    risk_level VARCHAR(16) NOT NULL DEFAULT 'low',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uk_class_profile_metric_snapshot_user (snapshot_id, user_id),
    KEY idx_class_profile_metric_class_user (class_id, user_id),
    KEY idx_class_profile_metric_snapshot (snapshot_id),
    KEY idx_class_profile_metric_risk (class_id, risk_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()

DIMENSIONS = [
    ("knowledge_mastery_score", "class_avg_knowledge_mastery", "知识掌握"),
    ("troubleshooting_score", "class_avg_troubleshooting", "排障能力"),
    ("autonomy_score", "class_avg_autonomy", "自主探索"),
    ("ai_collaboration_score", "class_avg_ai_collaboration", "AI 协同"),
    ("engagement_score", "class_avg_engagement", "学习投入"),
]

OVERALL_WEIGHTS = {
    "class_avg_knowledge_mastery": STUDENT_OVERALL_WEIGHTS["knowledge_mastery_score"],
    "class_avg_troubleshooting": STUDENT_OVERALL_WEIGHTS["troubleshooting_score"],
    "class_avg_autonomy": STUDENT_OVERALL_WEIGHTS["autonomy_score"],
    "class_avg_ai_collaboration": STUDENT_OVERALL_WEIGHTS["ai_collaboration_score"],
    "class_avg_engagement": STUDENT_OVERALL_WEIGHTS["engagement_score"],
}

_schema_ready = False


def ensure_class_profile_schema() -> None:
    """Create class profile tables once per process."""
    global _schema_ready
    if _schema_ready:
        return
    ensure_database()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(CLASS_PROFILE_SNAPSHOT_TABLE_SQL)
            cursor.execute(CLASS_PROFILE_STUDENT_METRIC_TABLE_SQL)
        conn.commit()
    _schema_ready = True


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=_json_default)


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _clamp(value: float, low: float = 0, high: float = 100) -> float:
    return round(max(low, min(high, value)), 2)


def _fetch_one(cursor, sql: str, params: dict[str, Any]) -> dict[str, Any]:
    cursor.execute(sql, params)
    return cursor.fetchone() or {}


def _fetch_all(cursor, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    cursor.execute(sql, params)
    return list(cursor.fetchall() or [])


def _latest_student_snapshots(cursor, class_id: int) -> list[dict[str, Any]]:
    # MySQL 5.x compatible latest-row query: one latest profile snapshot per student.
    rows = _fetch_all(
        cursor,
        """
        SELECT s.*
        FROM student_profile_snapshot s
        WHERE s.class_id = %(class_id)s
          AND NOT EXISTS (
              SELECT 1
              FROM student_profile_snapshot newer
              WHERE newer.class_id = s.class_id
                AND newer.user_id = s.user_id
                AND (
                    newer.computed_at > s.computed_at
                    OR (
                        newer.computed_at = s.computed_at
                        AND newer.created_at > s.created_at
                    )
                )
          )
        ORDER BY s.user_id ASC
        """,
        {"class_id": class_id},
    )
    # Extremely rare ties on computed_at and created_at are collapsed here to keep one row per student.
    latest_by_user: dict[int, dict[str, Any]] = {}
    for row in rows:
        latest_by_user[int(row["user_id"])] = row
    return list(latest_by_user.values())


def _pick_course_id(students: list[dict[str, Any]]) -> Optional[int]:
    counts: dict[int, int] = {}
    for row in students:
        course_id = row.get("course_id")
        if course_id is not None:
            counts[int(course_id)] = counts.get(int(course_id), 0) + 1
    if not counts:
        return None
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _average(students: list[dict[str, Any]], key: str) -> float:
    if not students:
        return 0.0
    return _clamp(sum(_to_float(row.get(key)) for row in students) / len(students))


def _score_class(students: list[dict[str, Any]]) -> dict[str, float]:
    scores = {
        avg_key: _average(students, student_key)
        for student_key, avg_key, _ in DIMENSIONS
    }
    scores["class_overall_score"] = _clamp(
        sum(scores[key] * weight for key, weight in OVERALL_WEIGHTS.items())
    )
    return scores


def _dimension_rank(scores: dict[str, float], reverse: bool = False) -> list[dict[str, Any]]:
    ranked = sorted(
        (
            {
                "dimension": avg_key,
                "dimension_name": label,
                "average_score": scores[avg_key],
                "description": f"班级在「{label}」维度的平均分为 {scores[avg_key]}。",
            }
            for _, avg_key, label in DIMENSIONS
        ),
        key=lambda item: item["average_score"],
        reverse=reverse,
    )
    return ranked


def _risk_for_student(row: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    reasons: list[str] = []
    weak_dimensions: list[str] = []
    overall = _to_float(row.get("overall_score"))
    troubleshooting = _to_float(row.get("troubleshooting_score"))
    engagement = _to_float(row.get("engagement_score"))

    if overall < 50:
        reasons.append("综合分低于 50")
    if troubleshooting < 40:
        reasons.append("排障能力低于 40")
    if engagement < 40:
        reasons.append("学习投入低于 40")

    for student_key, _, label in DIMENSIONS:
        if _to_float(row.get(student_key)) < 50:
            weak_dimensions.append(label)

    if overall < 50 or troubleshooting < 40 or engagement < 40:
        return "high", reasons or ["存在高风险画像信号"], weak_dimensions
    if overall < 65 or weak_dimensions:
        return "medium", reasons or ["存在需要关注的薄弱维度"], weak_dimensions
    return "low", ["当前画像风险较低"], weak_dimensions


def _risk_students(students: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_metrics: list[dict[str, Any]] = []
    risky: list[dict[str, Any]] = []
    for row in students:
        risk_level, reasons, weak_dimensions = _risk_for_student(row)
        item = {
            "user_id": row["user_id"],
            "overall_score": _to_float(row.get("overall_score")),
            "knowledge_mastery_score": _to_float(row.get("knowledge_mastery_score")),
            "troubleshooting_score": _to_float(row.get("troubleshooting_score")),
            "autonomy_score": _to_float(row.get("autonomy_score")),
            "ai_collaboration_score": _to_float(row.get("ai_collaboration_score")),
            "engagement_score": _to_float(row.get("engagement_score")),
            "risk_level": risk_level,
            "risk_reasons": reasons,
            "weak_dimensions": weak_dimensions,
        }
        all_metrics.append(item)
        if risk_level in ("high", "medium"):
            risky.append(item)
    risky.sort(key=lambda item: ({"high": 0, "medium": 1}.get(item["risk_level"], 2), item["overall_score"]))
    return risky, all_metrics


def _source_range(students: list[dict[str, Any]]) -> tuple[Optional[datetime], Optional[datetime]]:
    starts = [row.get("source_range_start") for row in students if row.get("source_range_start")]
    ends = [row.get("source_range_end") for row in students if row.get("source_range_end")]
    return (min(starts) if starts else None, max(ends) if ends else None)


def _serialize_class_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key in ("weak_dimensions_json", "strengths_json", "risk_students_json", "summary_json"):
        if isinstance(result.get(key), str):
            result[key] = json.loads(result[key])
    for key in ("computed_at", "source_range_start", "source_range_end", "created_at"):
        if isinstance(result.get(key), datetime):
            result[key] = result[key].isoformat()
    for key in (
        "class_avg_knowledge_mastery",
        "class_avg_troubleshooting",
        "class_avg_autonomy",
        "class_avg_ai_collaboration",
        "class_avg_engagement",
        "class_overall_score",
    ):
        if result.get(key) is not None:
            result[key] = _to_float(result[key])
    return result


def _serialize_student_metric(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    if isinstance(result.get("created_at"), datetime):
        result["created_at"] = result["created_at"].isoformat()
    for key in (
        "overall_score",
        "knowledge_mastery_score",
        "troubleshooting_score",
        "autonomy_score",
        "ai_collaboration_score",
        "engagement_score",
    ):
        if result.get(key) is not None:
            result[key] = _to_float(result[key])
    return result


def rebuild_class_profile(class_id: int) -> dict[str, Any]:
    """Aggregate latest student profile snapshots into one class profile snapshot."""
    ensure_class_profile_schema()
    now = datetime.utcnow()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            students = _latest_student_snapshots(cursor, class_id)
            if not students:
                raise ValueError("no student profile snapshots found for this class_id")

            scores = _score_class(students)
            weak_dimensions = _dimension_rank(scores, reverse=False)
            strengths = _dimension_rank(scores, reverse=True)[:2]
            risk_students, all_metrics = _risk_students(students)
            source_start, source_end = _source_range(students)
            course_id = _pick_course_id(students)
            snapshot_id = f"class-profile-{uuid4()}"
            summary = {
                "aggregation_strategy": "基于 student_profile_snapshot 中班级内每个学生的最新一条画像快照聚合，不绕开学生画像重算事件。",
                "student_count": len(students),
                "overall_weights": OVERALL_WEIGHTS,
                "main_strengths": strengths,
                "main_weak_dimensions": weak_dimensions[:2],
                "risk_student_count": len(risk_students),
                "risk_student_overview": risk_students[:10],
                "data_limitations": [
                    "class_id 为空的学生画像不会进入本次班级聚合。",
                    "course_id 如存在多个值，快照中记录出现次数最多的 course_id。",
                ],
            }
            row = {
                "snapshot_id": snapshot_id,
                "class_id": class_id,
                "course_id": course_id,
                "computed_at": now,
                "student_count": len(students),
                **scores,
                "weak_dimensions_json": _json_dumps(weak_dimensions),
                "strengths_json": _json_dumps(strengths),
                "risk_students_json": _json_dumps(risk_students),
                "summary_json": _json_dumps(summary),
                "source_range_start": source_start,
                "source_range_end": source_end,
            }
            cursor.execute(
                """
                INSERT INTO class_profile_snapshot (
                    snapshot_id, class_id, course_id, computed_at, student_count,
                    class_avg_knowledge_mastery, class_avg_troubleshooting,
                    class_avg_autonomy, class_avg_ai_collaboration,
                    class_avg_engagement, class_overall_score,
                    weak_dimensions_json, strengths_json, risk_students_json,
                    summary_json, source_range_start, source_range_end
                ) VALUES (
                    %(snapshot_id)s, %(class_id)s, %(course_id)s, %(computed_at)s, %(student_count)s,
                    %(class_avg_knowledge_mastery)s, %(class_avg_troubleshooting)s,
                    %(class_avg_autonomy)s, %(class_avg_ai_collaboration)s,
                    %(class_avg_engagement)s, %(class_overall_score)s,
                    %(weak_dimensions_json)s, %(strengths_json)s, %(risk_students_json)s,
                    %(summary_json)s, %(source_range_start)s, %(source_range_end)s
                )
                """,
                row,
            )
            for item in all_metrics:
                cursor.execute(
                    """
                    INSERT INTO class_profile_student_metric (
                        class_id, user_id, snapshot_id, overall_score,
                        knowledge_mastery_score, troubleshooting_score, autonomy_score,
                        ai_collaboration_score, engagement_score, risk_level
                    ) VALUES (
                        %(class_id)s, %(user_id)s, %(snapshot_id)s, %(overall_score)s,
                        %(knowledge_mastery_score)s, %(troubleshooting_score)s, %(autonomy_score)s,
                        %(ai_collaboration_score)s, %(engagement_score)s, %(risk_level)s
                    )
                    """,
                    {
                        "class_id": class_id,
                        "user_id": item["user_id"],
                        "snapshot_id": snapshot_id,
                        "overall_score": item["overall_score"],
                        "knowledge_mastery_score": item["knowledge_mastery_score"],
                        "troubleshooting_score": item["troubleshooting_score"],
                        "autonomy_score": item["autonomy_score"],
                        "ai_collaboration_score": item["ai_collaboration_score"],
                        "engagement_score": item["engagement_score"],
                        "risk_level": item["risk_level"],
                    },
                )
        conn.commit()
    return _serialize_class_snapshot(
        {
            **row,
            "weak_dimensions_json": weak_dimensions,
            "strengths_json": strengths,
            "risk_students_json": risk_students,
            "summary_json": summary,
        }
    )


def get_latest_class_profile(class_id: int) -> Optional[dict[str, Any]]:
    ensure_class_profile_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            row = _fetch_one(
                cursor,
                """
                SELECT *
                FROM class_profile_snapshot
                WHERE class_id = %(class_id)s
                ORDER BY computed_at DESC, created_at DESC
                LIMIT 1
                """,
                {"class_id": class_id},
            )
    return _serialize_class_snapshot(row) if row else None


def list_class_profile_students(class_id: int) -> dict[str, Any]:
    """Return latest class-snapshot student metrics; fallback to latest student snapshots before rebuild."""
    ensure_class_profile_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            latest = _fetch_one(
                cursor,
                """
                SELECT snapshot_id
                FROM class_profile_snapshot
                WHERE class_id = %(class_id)s
                ORDER BY computed_at DESC, created_at DESC
                LIMIT 1
                """,
                {"class_id": class_id},
            )
            if latest:
                rows = _fetch_all(
                    cursor,
                    """
                    SELECT user_id, overall_score, knowledge_mastery_score,
                           troubleshooting_score, autonomy_score, ai_collaboration_score,
                           engagement_score, risk_level, created_at
                    FROM class_profile_student_metric
                    WHERE class_id = %(class_id)s AND snapshot_id = %(snapshot_id)s
                    ORDER BY
                      CASE risk_level WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                      overall_score ASC,
                      user_id ASC
                    """,
                    {"class_id": class_id, "snapshot_id": latest["snapshot_id"]},
                )
                return {
                    "class_id": class_id,
                    "snapshot_id": latest["snapshot_id"],
                    "student_count": len(rows),
                    "source": "class_profile_student_metric",
                    "students": [_serialize_student_metric(row) for row in rows],
                }

            students = _latest_student_snapshots(cursor, class_id)
            if not students:
                raise ValueError("no student profile snapshots found for this class_id")
            _, all_metrics = _risk_students(students)
            all_metrics.sort(key=lambda item: ({"high": 0, "medium": 1, "low": 2}.get(item["risk_level"], 3), item["overall_score"], item["user_id"]))
            return {
                "class_id": class_id,
                "snapshot_id": None,
                "student_count": len(all_metrics),
                "source": "student_profile_snapshot",
                "students": all_metrics,
            }
