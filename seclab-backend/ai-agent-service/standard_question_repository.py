import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional


STANDARD_QUESTION_PATH = Path(__file__).with_name("standard_questions.json")
ALLOWED_QUESTION_TYPES = {"SHORT_ANSWER", "MCQ", "CASE"}
QUALITY_LEVEL_SCORE = {"HIGH": 30, "MEDIUM": 15, "LOW": 0}
SOURCE_SCORE = {
    "teacher_defined": 35,
    "standard_question_bank": 35,
    "seed_sql": 25,
    "doc": 20,
    "module": 12,
    "course": 10,
}


def _to_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_question_type(value: Any) -> str:
    question_type = str(value or "").strip().upper()
    return question_type if question_type in ALLOWED_QUESTION_TYPES else ""


def _normalize_quality_level(value: Any) -> str:
    level = str(value or "").strip().upper()
    return level if level in QUALITY_LEVEL_SCORE else "LOW"


def _normalize_rubric(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rubric: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        point = str(item.get("point") or "").strip()
        score = _to_int(item.get("score"))
        if point and score is not None:
            rubric.append({"point": point, "score": score})
    return rubric


def _normalize_standard_question(item: dict[str, Any]) -> Optional[dict[str, Any]]:
    example_id = str(item.get("exampleQuestionId") or "").strip()
    stem = str(item.get("stem") or "").strip()
    standard_answer = str(item.get("standardAnswer") or "").strip()
    question_type = _normalize_question_type(item.get("questionType"))
    knowledge_tags = _as_string_list(item.get("knowledgeTags"))
    difficulty = _to_int(item.get("difficulty"))
    if not example_id or not stem or not standard_answer or not question_type or not knowledge_tags:
        return None
    difficulty = difficulty if difficulty is not None and 1 <= difficulty <= 5 else 3
    return {
        "exampleQuestionId": example_id,
        "title": str(item.get("title") or "").strip() or stem[:40],
        "stem": stem,
        "questionType": question_type,
        "difficulty": difficulty,
        "knowledgeTags": knowledge_tags,
        "dimensionTags": _as_string_list(item.get("dimensionTags")),
        "standardAnswer": standard_answer,
        "explanation": str(item.get("explanation") or "").strip(),
        "gradingRubric": _normalize_rubric(item.get("gradingRubric")),
        "source": str(item.get("source") or "module").strip(),
        "sourceDocument": str(item.get("sourceDocument") or "").strip(),
        "qualityLevel": _normalize_quality_level(item.get("qualityLevel")),
        "reviewed": bool(item.get("reviewed")),
        "moduleId": _to_int(item.get("moduleId")),
        "courseId": _to_int(item.get("courseId")),
        "updatedAt": str(item.get("updatedAt") or "").strip(),
    }


def _load_standard_questions() -> list[dict[str, Any]]:
    if not STANDARD_QUESTION_PATH.exists():
        return []
    try:
        raw = json.loads(STANDARD_QUESTION_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    questions: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_standard_question(item)
        if not normalized or normalized["exampleQuestionId"] in seen_ids:
            continue
        seen_ids.add(normalized["exampleQuestionId"])
        questions.append(normalized)
    return questions


def list_standard_questions(
    *,
    tag: str | None = None,
    module_id: int | None = None,
    course_id: int | None = None,
    question_type: str | None = None,
    difficulty: int | None = None,
    reviewed_only: bool = False,
) -> list[dict[str, Any]]:
    normalized_tag = str(tag or "").strip().lower()
    normalized_type = _normalize_question_type(question_type) if question_type else ""
    normalized_difficulty = _to_int(difficulty)
    questions = _load_standard_questions()
    results: list[dict[str, Any]] = []
    for item in questions:
        if reviewed_only and not item["reviewed"]:
            continue
        if normalized_tag and normalized_tag not in {tag.lower() for tag in item["knowledgeTags"]}:
            continue
        if module_id is not None and item["moduleId"] != module_id:
            continue
        if course_id is not None and item["courseId"] != course_id:
            continue
        if normalized_type and item["questionType"] != normalized_type:
            continue
        if normalized_difficulty is not None and item["difficulty"] != normalized_difficulty:
            continue
        results.append(dict(item))
    return results


def _score_question(
    item: dict[str, Any],
    *,
    knowledge_tags: list[str],
    dimension: str,
    question_type: str,
    difficulty: int,
    module_id: int | None,
    course_id: int | None,
) -> int:
    score = 0
    item_tags = {tag.lower() for tag in item["knowledgeTags"]}
    request_tags = {tag.lower() for tag in knowledge_tags}
    overlap = item_tags & request_tags
    has_anchor_match = bool(overlap)
    if module_id is not None and item["moduleId"] == module_id:
        has_anchor_match = True
    if course_id is not None and item["courseId"] == course_id:
        has_anchor_match = True
    if not has_anchor_match:
        return 0
    score += len(overlap) * 40
    if item["questionType"] == question_type:
        score += 45
    score += max(0, 35 - abs(item["difficulty"] - difficulty) * 10)
    if dimension and dimension in item["dimensionTags"]:
        score += 25
    if module_id is not None and item["moduleId"] == module_id:
        score += 30
    if course_id is not None and item["courseId"] == course_id:
        score += 20
    if item["reviewed"]:
        score += 25
    score += QUALITY_LEVEL_SCORE.get(item["qualityLevel"], 0)
    score += SOURCE_SCORE.get(item["source"], 0)
    return score


def retrieve_example_questions(
    *,
    knowledge_tags: list[str],
    dimension: str,
    question_type: str,
    difficulty: int,
    module_id: int | None = None,
    course_id: int | None = None,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    normalized_type = _normalize_question_type(question_type)
    normalized_difficulty = _to_int(difficulty) or 3
    ranked: list[tuple[int, dict[str, Any]]] = []
    for item in _load_standard_questions():
        score = _score_question(
            item,
            knowledge_tags=knowledge_tags,
            dimension=dimension,
            question_type=normalized_type,
            difficulty=normalized_difficulty,
            module_id=module_id,
            course_id=course_id,
        )
        if score <= 0:
            continue
        candidate = dict(item)
        candidate["retrievalScore"] = score
        ranked.append((score, candidate))
    ranked.sort(
        key=lambda pair: (
            pair[0],
            pair[1]["reviewed"],
            QUALITY_LEVEL_SCORE.get(pair[1]["qualityLevel"], 0),
            pair[1]["updatedAt"],
            pair[1]["exampleQuestionId"],
        ),
        reverse=True,
    )
    return [item for _, item in ranked[: max(0, min(top_k, 10))]]


def to_jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=_json_default))
