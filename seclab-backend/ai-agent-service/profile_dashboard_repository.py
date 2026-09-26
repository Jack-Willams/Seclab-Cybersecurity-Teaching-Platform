import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from class_profile_repository import ensure_class_profile_schema
from database import get_connection
from lab_repository import ensure_lab_schema
from profile_repository import ensure_profile_schema
from question_repository import ensure_question_schema


DIMENSION_VIEW = [
    ("knowledge_mastery_score", "知识掌握", "text-primary"),
    ("troubleshooting_score", "排障能力", "text-secondary"),
    ("autonomy_score", "自主探索", "text-accent"),
    ("ai_collaboration_score", "AI协同", "text-info"),
    ("engagement_score", "学习投入", "text-success"),
]

DEFAULT_DASHBOARD = {
    "userStats": {
        "completedCourses": 0,
        "totalScore": 0,
        "ranking": 0,
        "activeStreak": 0,
    },
    "learningProfile": {
        "skills": [
            {"name": "知识掌握", "score": 0, "color": "text-primary"},
            {"name": "排障能力", "score": 0, "color": "text-secondary"},
            {"name": "自主探索", "score": 0, "color": "text-accent"},
            {"name": "AI协同", "score": 0, "color": "text-info"},
            {"name": "学习投入", "score": 0, "color": "text-success"},
        ],
        "tags": [],
        "recentFocus": "",
        "comprehensiveScore": 0,
        "evaluation": "暂无可用画像快照。完成题目、靶机和 AI 交互后，可重新生成学生画像。",
    },
    "solveRecords": [],
}


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return int(value)
    return int(value)


def _serialize_time(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value or "")


def _json_loads(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}


def _json_value(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list, int, float, bool)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def _is_correct(value: Any) -> Optional[bool]:
    if value is None:
        return None
    return bool(value)


def _result_label(value: Any) -> str:
    correct = _is_correct(value)
    if correct is True:
        return "正确"
    if correct is False:
        return "错误"
    return "已提交"


def _answer_display(value: Any, options: list[Any]) -> Any:
    parsed = _json_value(value, value)
    if isinstance(parsed, dict):
        for key in ("answerText", "answer", "selectedOptions", "value"):
            if parsed.get(key) is not None:
                return _answer_display(parsed[key], options)
        return parsed
    if isinstance(parsed, list):
        return [_answer_display(item, options) for item in parsed]
    if isinstance(parsed, int) and 0 <= parsed < len(options):
        return str(options[parsed])
    return parsed


def _module_label(module_id: Any) -> str:
    return f"模块 #{module_id}" if module_id not in (None, "") else "未关联模块"


def _course_question_record(row: dict[str, Any]) -> dict[str, Any]:
    snapshot = _json_value(row.get("question_snapshot_json"), {})
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    options = snapshot.get("options") if isinstance(snapshot.get("options"), list) else []
    question_uid = str(row.get("question_uid") or row.get("question_id") or "-")
    stem = str(
        snapshot.get("content")
        or snapshot.get("stem")
        or snapshot.get("question")
        or ""
    ).strip()
    title = str(snapshot.get("title") or stem or f"历史题目 {question_uid}").strip()
    correct = _is_correct(row.get("is_correct"))
    return {
        "id": f"course:{row.get('submission_id')}",
        "sort_time": row.get("created_at"),
        "sourceType": str(row.get("question_source") or "course_question"),
        "questionId": question_uid,
        "title": title,
        "experiment": title,
        "stem": stem,
        "questionType": str(row.get("question_type") or ""),
        "module": _module_label(row.get("module_id")),
        "taskId": row.get("task_id"),
        "result": _result_label(row.get("is_correct")),
        "isCorrect": correct,
        "score": _to_float(row.get("score")),
        "costTime": _to_int(row.get("cost_time")) if row.get("cost_time") is not None else None,
        "studentAnswer": _answer_display(row.get("answer_json"), options),
        "standardAnswer": _answer_display(row.get("standard_answer_json"), options),
        "options": [str(option) for option in options],
        "explanation": str(snapshot.get("explanation") or snapshot.get("analysis") or "").strip(),
        "contentAvailable": bool(stem),
    }


def _generated_question_record(row: dict[str, Any]) -> dict[str, Any]:
    options_value = _json_value(row.get("options_json"), [])
    options = options_value if isinstance(options_value, list) else []
    title = str(row.get("title") or row.get("stem") or "专项训练题").strip()
    return {
        "id": f"generated:{row.get('attempt_id')}",
        "sort_time": row.get("submitted_at"),
        "sourceType": "generated_training",
        "questionId": str(row.get("generated_question_id") or ""),
        "trainingSessionId": str(row.get("training_session_id") or ""),
        "title": title,
        "experiment": title,
        "stem": str(row.get("stem") or "").strip(),
        "questionType": str(row.get("question_type") or ""),
        "module": _module_label(row.get("module_id")),
        "taskId": row.get("task_id"),
        "result": _result_label(row.get("is_correct")),
        "isCorrect": _is_correct(row.get("is_correct")),
        "score": _to_float(row.get("score")),
        "costTime": _to_int(row.get("cost_time")) if row.get("cost_time") is not None else None,
        "studentAnswer": _answer_display(row.get("answer_json"), options),
        "standardAnswer": _answer_display(row.get("standard_answer"), options),
        "options": [str(option) for option in options],
        "explanation": str(row.get("explanation") or "").strip(),
        "contentAvailable": bool(row.get("stem")),
    }


def _fetch_one(cursor, sql: str, params: dict[str, Any]) -> dict[str, Any]:
    cursor.execute(sql, params)
    return cursor.fetchone() or {}


def _fetch_all(cursor, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    cursor.execute(sql, params)
    return list(cursor.fetchall() or [])


def _latest_profile(cursor, user_id: int) -> dict[str, Any]:
    return _fetch_one(
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


def _completed_courses(cursor, user_id: int) -> int:
    row = _fetch_one(
        cursor,
        """
        SELECT COUNT(*) AS total
        FROM lab_session
        WHERE user_id = %(user_id)s AND status = 'completed'
        """,
        {"user_id": user_id},
    )
    return _to_int(row.get("total"))


def _total_score(cursor, user_id: int) -> int:
    row = _fetch_one(
        cursor,
        """
        SELECT
            COALESCE((SELECT SUM(score) FROM question_submission WHERE user_id = %(user_id)s), 0)
            + COALESCE((SELECT SUM(score) FROM flag_submission WHERE user_id = %(user_id)s), 0)
            AS total
        """,
        {"user_id": user_id},
    )
    return round(_to_float(row.get("total")))


def _active_streak(cursor, user_id: int) -> int:
    rows = _fetch_all(
        cursor,
        """
        SELECT stat_date
        FROM student_profile_feature_daily
        WHERE user_id = %(user_id)s
          AND (
              question_submit_count > 0 OR flag_submit_count > 0 OR lab_session_count > 0
              OR completed_lab_count > 0 OR ai_user_message_count > 0
              OR command_count > 0 OR file_change_count > 0 OR error_count > 0
          )
        ORDER BY stat_date DESC
        """,
        {"user_id": user_id},
    )
    active_dates = {row["stat_date"] for row in rows if row.get("stat_date")}
    if not active_dates:
        return 0
    current = max(active_dates)
    streak = 0
    while current in active_dates:
        streak += 1
        current = current - timedelta(days=1)
    return streak


def _ranking_from_class_metrics(cursor, class_id: Optional[int], user_id: int) -> int:
    if not class_id:
        return 0
    latest_class = _fetch_one(
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
    if latest_class:
        rows = _fetch_all(
            cursor,
            """
            SELECT user_id, overall_score
            FROM class_profile_student_metric
            WHERE class_id = %(class_id)s AND snapshot_id = %(snapshot_id)s
            ORDER BY overall_score DESC, user_id ASC
            """,
            {"class_id": class_id, "snapshot_id": latest_class["snapshot_id"]},
        )
        for index, row in enumerate(rows, start=1):
            if int(row["user_id"]) == user_id:
                return index

    rows = _fetch_all(
        cursor,
        """
        SELECT s.user_id, s.overall_score
        FROM student_profile_snapshot s
        WHERE s.class_id = %(class_id)s
          AND NOT EXISTS (
              SELECT 1
              FROM student_profile_snapshot newer
              WHERE newer.class_id = s.class_id
                AND newer.user_id = s.user_id
                AND (
                    newer.computed_at > s.computed_at
                    OR (newer.computed_at = s.computed_at AND newer.created_at > s.created_at)
                )
          )
        ORDER BY s.overall_score DESC, s.user_id ASC
        """,
        {"class_id": class_id},
    )
    seen: set[int] = set()
    rank = 0
    for row in rows:
        row_user_id = int(row["user_id"])
        if row_user_id in seen:
            continue
        seen.add(row_user_id)
        rank += 1
        if row_user_id == user_id:
            return rank
    return 0


def _dimension_scores(profile: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"name": name, "score": round(_to_float(profile.get(key))), "color": color}
        for key, name, color in DIMENSION_VIEW
    ]


def _tags(skills: list[dict[str, Any]]) -> list[dict[str, str]]:
    high_types = ["badge-primary", "badge-secondary", "badge-accent", "badge-info"]
    low_types = ["badge-warning", "badge-error"]
    tags: list[dict[str, str]] = []
    for skill in sorted(skills, key=lambda item: item["score"], reverse=True):
        if skill["score"] >= 80 and len(tags) < 2:
            tags.append({"text": f"{skill['name']}优势", "type": high_types[len(tags) % len(high_types)]})
    for skill in sorted(skills, key=lambda item: item["score"]):
        if skill["score"] < 50 and len(tags) < 4:
            tags.append({"text": f"{skill['name']}待提升", "type": low_types[len(tags) % len(low_types)]})
    return tags


def _recent_focus(skills: list[dict[str, Any]]) -> str:
    if not skills:
        return ""
    weakest = min(skills, key=lambda item: item["score"])
    return weakest["name"] if weakest["score"] < 60 else "保持综合能力稳定提升"


def _evaluation(profile: dict[str, Any], skills: list[dict[str, Any]]) -> str:
    summary = _json_loads(profile.get("profile_summary_json"))
    strengths = summary.get("strengths") or []
    weaknesses = summary.get("weaknesses") or []
    strongest = max(skills, key=lambda item: item["score"]) if skills else {"name": "综合能力", "score": 0}
    weakest = min(skills, key=lambda item: item["score"]) if skills else {"name": "综合能力", "score": 0}
    parts = [
        f"当前综合得分 {round(_to_float(profile.get('overall_score')))} 分。",
        f"优势维度为{strongest['name']}（{strongest['score']} 分），薄弱维度为{weakest['name']}（{weakest['score']} 分）。",
    ]
    if strengths:
        parts.append(f"画像识别出的优势：{'、'.join(str(item) for item in strengths)}。")
    if weaknesses:
        parts.append(f"建议重点关注：{'、'.join(str(item) for item in weaknesses)}。")
    return "".join(parts)


def _learning_profile(profile: dict[str, Any]) -> dict[str, Any]:
    if not profile:
        return dict(DEFAULT_DASHBOARD["learningProfile"])
    skills = _dimension_scores(profile)
    return {
        "skills": skills,
        "tags": _tags(skills),
        "recentFocus": _recent_focus(skills),
        "comprehensiveScore": round(_to_float(profile.get("overall_score"))),
        "evaluation": _evaluation(profile, skills),
    }


def _question_records(cursor, user_id: int) -> list[dict[str, Any]]:
    rows = _fetch_all(
        cursor,
        """
        SELECT submission_id, question_id, question_uid, module_id, task_id,
               question_type, question_source, question_snapshot_json,
               answer_json, standard_answer_json, is_correct, score, cost_time, created_at
        FROM question_submission
        WHERE user_id = %(user_id)s
        ORDER BY created_at DESC
        LIMIT 30
        """,
        {"user_id": user_id},
    )
    return [_course_question_record(row) for row in rows]


def _generated_question_records(cursor, user_id: int) -> list[dict[str, Any]]:
    rows = _fetch_all(
        cursor,
        """
        SELECT a.attempt_id, a.generated_question_id, a.training_session_id,
               a.answer_json, a.is_correct, a.score, a.cost_time, a.submitted_at,
               q.module_id, q.task_id, q.question_type, q.title, q.stem,
               q.options_json, q.standard_answer, q.explanation
        FROM generated_question_attempt a
        JOIN generated_question q
          ON q.generated_question_id = a.generated_question_id
        WHERE a.user_id = %(user_id)s
        ORDER BY a.submitted_at DESC
        LIMIT 30
        """,
        {"user_id": user_id},
    )
    return [_generated_question_record(row) for row in rows]


def _flag_records(cursor, user_id: int) -> list[dict[str, Any]]:
    rows = _fetch_all(
        cursor,
        """
        SELECT submission_id, module_id, task_id, is_correct, score, created_at
        FROM flag_submission
        WHERE user_id = %(user_id)s
        ORDER BY created_at DESC
        LIMIT 8
        """,
        {"user_id": user_id},
    )
    return [
        {
            "id": f"flag:{row.get('submission_id')}",
            "sort_time": row.get("created_at"),
            "sourceType": "flag",
            "questionId": str(row.get("task_id") or row.get("submission_id") or ""),
            "title": f"Flag 提交 #{row.get('task_id') or row.get('submission_id')}",
            "experiment": f"Flag 提交 #{row.get('task_id') or row.get('submission_id')}",
            "stem": "",
            "questionType": "FLAG",
            "module": _module_label(row.get("module_id")),
            "taskId": row.get("task_id"),
            "result": _result_label(row.get("is_correct")),
            "isCorrect": _is_correct(row.get("is_correct")),
            "score": _to_float(row.get("score")),
            "costTime": None,
            "studentAnswer": None,
            "standardAnswer": None,
            "options": [],
            "explanation": "",
            "contentAvailable": False,
        }
        for row in rows
    ]


def _solve_records(cursor, user_id: int) -> list[dict[str, Any]]:
    records = (
        _question_records(cursor, user_id)
        + _generated_question_records(cursor, user_id)
        + _flag_records(cursor, user_id)
    )
    records.sort(key=lambda item: item.get("sort_time") or datetime.min, reverse=True)
    return [
        {
            **{key: value for key, value in item.items() if key != "sort_time"},
            "time": _serialize_time(item.get("sort_time")),
        }
        for item in records[:50]
    ]


def get_profile_dashboard(user_id: int) -> dict[str, Any]:
    """Build the student Profile page dashboard from persisted learning evidence."""
    ensure_question_schema()
    ensure_lab_schema()
    ensure_profile_schema()
    ensure_class_profile_schema()

    with get_connection() as conn:
        with conn.cursor() as cursor:
            profile = _latest_profile(cursor, user_id)
            class_id = int(profile["class_id"]) if profile.get("class_id") is not None else None
            user_stats = {
                "completedCourses": _completed_courses(cursor, user_id),
                "totalScore": _total_score(cursor, user_id),
                "ranking": _ranking_from_class_metrics(cursor, class_id, user_id),
                "activeStreak": _active_streak(cursor, user_id),
            }
            return {
                "userStats": user_stats,
                "learningProfile": _learning_profile(profile),
                "solveRecords": _solve_records(cursor, user_id),
            }
