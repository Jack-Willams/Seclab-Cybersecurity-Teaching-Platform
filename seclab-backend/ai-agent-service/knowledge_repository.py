from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from database import ensure_database, get_connection


def _fetch_all(cursor, sql: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    cursor.execute(sql, params or {})
    return list(cursor.fetchall() or [])


def _fetch_one(cursor, sql: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cursor.execute(sql, params or {})
    return cursor.fetchone() or {}


def _table_exists(cursor, schema: str, table: str) -> bool:
    row = _fetch_one(
        cursor,
        """
        SELECT COUNT(*) AS total
        FROM information_schema.tables
        WHERE table_schema = %(schema)s AND table_name = %(table)s
        """,
        {"schema": schema, "table": table},
    )
    return bool(int(row.get("total") or 0))


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _text_blob(*values: Any) -> str:
    return " ".join(str(value or "").strip().lower() for value in values if value is not None)


def _parse_csv_tags(raw: Any) -> list[str]:
    if raw is None:
        return []
    text = str(raw).strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return _unique([item.strip().strip('"').strip("'") for item in text.split(",") if item.strip()])


def _normalize_difficulty(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return max(1, min(5, value))
    text = str(value).strip().lower()
    if not text:
        return None
    if text.isdigit():
        return max(1, min(5, int(text)))
    mapping = {
        "easy": 1,
        "medium": 3,
        "hard": 5,
    }
    return mapping.get(text)


def _isoformat(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    return None if value is None else str(value)


def build_knowledge_tags(title: str = "", content: str = "", explicit_tags: Optional[list[str]] = None) -> list[str]:
    tags = list(explicit_tags or [])
    haystack = _text_blob(title, content, *(explicit_tags or []))
    rules = [
        (["sql注入", "sql", "注入"], ["SQL注入", "Web安全"]),
        (["xss", "跨站脚本"], ["XSS", "Web安全"]),
        (["文件上传"], ["文件上传", "Web安全"]),
        (["中间件", "tomcat", "weblogic", "jboss"], ["中间件漏洞", "系统安全"]),
        (["代码审计"], ["代码审计", "漏洞挖掘"]),
        (["ctf"], ["CTF综合实战"]),
    ]
    for keywords, mapped_tags in rules:
        if any(keyword in haystack for keyword in keywords):
            tags.extend(mapped_tags)
    return _unique(tags)


def build_dimension_tags(
    title: str = "",
    content: str = "",
    knowledge_tags: Optional[list[str]] = None,
    task_point: str = "",
) -> list[str]:
    haystack = _text_blob(title, content, task_point, *(knowledge_tags or []))
    tags = ["knowledge_mastery"]
    if any(keyword in haystack for keyword in ["防御", "修复", "排查", "实战", "分析", "复盘"]):
        tags.append("troubleshooting")
    if any(keyword in haystack for keyword in ["基础", "入门", "实践", "实操", "实验"]):
        tags.append("autonomy")
    if any(keyword in haystack for keyword in ["代码审计", "漏洞分析", "错误分析", "防御方案", "分析"]):
        tags.append("ai_collaboration")
    if any(keyword in haystack for keyword in ["基础", "入门", "短周期", "实验"]):
        tags.append("engagement")
    return _unique(tags)


def _load_courses(cursor) -> list[dict[str, Any]]:
    if not _table_exists(cursor, "userservice", "course"):
        return []
    return _fetch_all(
        cursor,
        """
        SELECT
            id,
            course_name,
            course_description,
            difficulty,
            tags,
            type
        FROM userservice.course
        WHERE COALESCE(course_status, 1) <> 0
        ORDER BY id ASC
        """,
    )


def _load_modules(cursor) -> list[dict[str, Any]]:
    if not _table_exists(cursor, "userservice", "module"):
        return []
    return _fetch_all(
        cursor,
        """
        SELECT
            module_id,
            module_name,
            introduction,
            difficulty,
            type
        FROM userservice.module
        ORDER BY module_id ASC
        """,
    )


def _load_module_knowledge_points(cursor) -> tuple[dict[int, list[dict[str, Any]]], dict[int, list[int]]]:
    if not _table_exists(cursor, "seclab_profile", "module_knowledge_point") or not _table_exists(cursor, "seclab_profile", "knowledge_point"):
        return {}, {}
    rows = _fetch_all(
        cursor,
        """
        SELECT
            mkp.module_id,
            kp.knowledge_point_id,
            kp.name,
            kp.category,
            kp.description,
            kp.difficulty_level
        FROM seclab_profile.module_knowledge_point mkp
        JOIN seclab_profile.knowledge_point kp ON kp.knowledge_point_id = mkp.knowledge_point_id
        ORDER BY mkp.module_id ASC, mkp.relevance_weight DESC, kp.knowledge_point_id ASC
        """,
    )
    by_module: dict[int, list[dict[str, Any]]] = {}
    by_knowledge_point: dict[int, list[int]] = {}
    for row in rows:
        module_id = int(row["module_id"])
        kp_id = int(row["knowledge_point_id"])
        by_module.setdefault(module_id, []).append(row)
        by_knowledge_point.setdefault(kp_id, [])
        if module_id not in by_knowledge_point[kp_id]:
            by_knowledge_point[kp_id].append(module_id)
    return by_module, by_knowledge_point


def _load_generated_questions(cursor) -> list[dict[str, Any]]:
    if not _table_exists(cursor, "seclab_profile", "generated_question"):
        return []
    return _fetch_all(
        cursor,
        """
        SELECT
            gq.generated_question_id,
            gq.question_numeric_id,
            gq.knowledge_point_id,
            gq.module_id,
            gq.task_id,
            gq.difficulty,
            gq.title,
            gq.stem,
            gq.standard_answer,
            gq.reference_answer,
            gq.explanation,
            gq.created_at,
            kp.name AS knowledge_point_name,
            kp.category AS knowledge_point_category,
            kp.description AS knowledge_point_description
        FROM seclab_profile.generated_question gq
        LEFT JOIN seclab_profile.knowledge_point kp ON kp.knowledge_point_id = gq.knowledge_point_id
        ORDER BY gq.created_at DESC, gq.generated_question_id DESC
        """,
    )


def _course_units(courses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for row in courses:
        explicit_tags = _parse_csv_tags(row.get("tags"))
        if row.get("type"):
            explicit_tags.append(str(row["type"]))
        knowledge_tags = build_knowledge_tags(
            str(row.get("course_name") or ""),
            str(row.get("course_description") or ""),
            explicit_tags,
        )
        units.append(
            {
                "knowledgeUnitId": f"course-{row['id']}",
                "courseId": int(row["id"]),
                "courseTitle": row.get("course_name"),
                "moduleId": None,
                "moduleTitle": None,
                "labId": None,
                "questionId": None,
                "knowledgeTags": knowledge_tags,
                "dimensionTags": build_dimension_tags(
                    str(row.get("course_name") or ""),
                    str(row.get("course_description") or ""),
                    knowledge_tags,
                ),
                "difficulty": _normalize_difficulty(row.get("difficulty")),
                "taskPoint": None,
                "content": row.get("course_description"),
                "question": None,
                "answer": None,
                "explanation": None,
                "sourceType": "COURSE",
                "sourceDocument": "userservice.course",
                "updatedAt": None,
            }
        )
    return units


def _module_units(modules: list[dict[str, Any]], module_knowledge_points: dict[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for row in modules:
        module_id = int(row["module_id"])
        related_points = module_knowledge_points.get(module_id, [])
        explicit_tags = [str(row.get("type") or "")]
        explicit_tags.extend([str(point.get("category") or "") for point in related_points])
        explicit_tags.extend([str(point.get("name") or "") for point in related_points[:3]])
        task_point = "；".join([str(point.get("name") or "") for point in related_points[:3] if point.get("name")]) or None
        knowledge_tags = build_knowledge_tags(
            str(row.get("module_name") or ""),
            str(row.get("introduction") or ""),
            explicit_tags,
        )
        units.append(
            {
                "knowledgeUnitId": f"module-{module_id}",
                "courseId": None,
                "courseTitle": None,
                "moduleId": module_id,
                "moduleTitle": row.get("module_name"),
                "labId": None,
                "questionId": None,
                "knowledgeTags": knowledge_tags,
                "dimensionTags": build_dimension_tags(
                    str(row.get("module_name") or ""),
                    str(row.get("introduction") or ""),
                    knowledge_tags,
                    task_point or "",
                ),
                "difficulty": _normalize_difficulty(row.get("difficulty")),
                "taskPoint": task_point,
                "content": row.get("introduction"),
                "question": None,
                "answer": None,
                "explanation": None,
                "sourceType": "MODULE",
                "sourceDocument": "userservice.module",
                "updatedAt": None,
            }
        )
    return units


def _question_units(
    generated_questions: list[dict[str, Any]],
    modules_by_id: dict[int, dict[str, Any]],
    module_ids_by_knowledge_point: dict[int, list[int]],
) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for row in generated_questions:
        module_id: Optional[int] = None
        if row.get("module_id") is not None:
            module_id = int(row["module_id"])
        elif row.get("knowledge_point_id") is not None:
            candidates = module_ids_by_knowledge_point.get(int(row["knowledge_point_id"])) or []
            module_id = candidates[0] if candidates else None
        module_row = modules_by_id.get(module_id) if module_id is not None else None
        explicit_tags = [
            str(row.get("knowledge_point_category") or ""),
            str(row.get("knowledge_point_name") or ""),
            str(module_row.get("type") or "") if module_row else "",
        ]
        knowledge_tags = build_knowledge_tags(
            str(row.get("title") or ""),
            " ".join(
                [
                    str(row.get("stem") or ""),
                    str(row.get("explanation") or ""),
                    str(row.get("knowledge_point_description") or ""),
                ]
            ),
            explicit_tags,
        )
        task_point = str(row.get("knowledge_point_name") or "") or None
        units.append(
            {
                "knowledgeUnitId": f"question-{row['generated_question_id']}",
                "courseId": None,
                "courseTitle": None,
                "moduleId": module_id,
                "moduleTitle": module_row.get("module_name") if module_row else None,
                "labId": None,
                "questionId": int(row["question_numeric_id"]) if row.get("question_numeric_id") is not None else None,
                "knowledgeTags": knowledge_tags,
                "dimensionTags": build_dimension_tags(
                    str(row.get("title") or ""),
                    " ".join(
                        [
                            str(row.get("stem") or ""),
                            str(row.get("explanation") or ""),
                        ]
                    ),
                    knowledge_tags,
                    task_point or "",
                ),
                "difficulty": _normalize_difficulty(row.get("difficulty")),
                "taskPoint": task_point,
                "content": row.get("stem"),
                "question": row.get("stem"),
                "answer": row.get("standard_answer") or row.get("reference_answer"),
                "explanation": row.get("explanation"),
                "sourceType": "QUESTION",
                "sourceDocument": "seclab_profile.generated_question",
                "updatedAt": _isoformat(row.get("created_at")),
            }
        )
    return units


def _matches_tag(unit: dict[str, Any], tag: str) -> bool:
    normalized = tag.strip().lower()
    if not normalized:
        return True
    values = list(unit.get("knowledgeTags") or []) + list(unit.get("dimensionTags") or [])
    return any(normalized in str(value).lower() for value in values)


def list_knowledge_units(
    module_id: Optional[int] = None,
    course_id: Optional[int] = None,
    tag: Optional[str] = None,
) -> dict[str, Any]:
    ensure_database()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            courses = _load_courses(cursor)
            modules = _load_modules(cursor)
            module_knowledge_points, module_ids_by_knowledge_point = _load_module_knowledge_points(cursor)
            generated_questions = _load_generated_questions(cursor)

    modules_by_id = {int(row["module_id"]): row for row in modules}
    items = (
        _course_units(courses)
        + _module_units(modules, module_knowledge_points)
        + _question_units(generated_questions, modules_by_id, module_ids_by_knowledge_point)
    )
    if module_id is not None:
        items = [item for item in items if item.get("moduleId") == module_id]
    if course_id is not None:
        items = [item for item in items if item.get("courseId") == course_id]
    if tag:
        items = [item for item in items if _matches_tag(item, tag)]

    return {
        "items": items,
        "total": len(items),
        "filters": {
            "moduleId": module_id,
            "courseId": course_id,
            "tag": tag,
        },
    }
