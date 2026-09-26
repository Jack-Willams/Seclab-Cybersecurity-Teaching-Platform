from typing import Any, Optional

from profile_dashboard_repository import get_profile_dashboard
from profile_repository import get_latest_student_profile, rebuild_student_profile
from training_repository import (
    fetch_recent_training_evidence,
    get_knowledge_mappings,
    list_active_knowledge_points,
)


DIMENSION_LABELS = {
    "knowledge_mastery_score": "知识掌握",
    "troubleshooting_score": "排障能力",
    "autonomy_score": "自主探索",
    "ai_collaboration_score": "AI协同",
    "engagement_score": "学习投入",
    "overall_score": "综合表现",
}


def _to_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _dimension_scores(profile: dict[str, Any]) -> dict[str, float]:
    return {
        key: _to_float(profile.get(key))
        for key in (
            "knowledge_mastery_score",
            "troubleshooting_score",
            "autonomy_score",
            "ai_collaboration_score",
            "engagement_score",
            "overall_score",
        )
    }


def _weak_dimensions(scores: dict[str, float]) -> list[str]:
    ranked = sorted(
        (
            (key, value)
            for key, value in scores.items()
            if key != "overall_score"
        ),
        key=lambda item: item[1],
    )
    weak = [DIMENSION_LABELS[key] for key, value in ranked if value < 60]
    return weak or [DIMENSION_LABELS[key] for key, _ in ranked[:2]]


def _dashboard_profile(user_id: int) -> dict[str, Any]:
    try:
        dashboard = get_profile_dashboard(user_id)
        return dashboard.get("learningProfile") or {}
    except Exception:
        return {}


def _tag_texts(tags: Any) -> list[str]:
    result: list[str] = []
    for item in tags or []:
        if isinstance(item, dict):
            text = item.get("text")
        else:
            text = item
        if text:
            result.append(str(text))
    return result


def _difficulty_from_scores(scores: dict[str, float]) -> str:
    knowledge = scores.get("knowledge_mastery_score", 0)
    overall = scores.get("overall_score", 0)
    if knowledge < 35 or overall < 35:
        return "easy"
    if knowledge < 75 or overall < 70:
        return "medium"
    return "hard"


def _kp_catalog() -> dict[int, dict[str, Any]]:
    return {
        int(row["knowledge_point_id"]): row
        for row in list_active_knowledge_points(limit=100)
        if row.get("knowledge_point_id") is not None
    }


def _mapped_kps(
    *,
    knowledge_point_id: Optional[int],
    module_id: Optional[int],
    task_id: Optional[int],
    question_id: Optional[Any],
    catalog: dict[int, dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    if knowledge_point_id and knowledge_point_id in catalog:
        return [{**catalog[knowledge_point_id], "mapping_source": "question_submission"}], False

    mappings = get_knowledge_mappings(module_id=module_id, task_id=task_id, question_id=question_id)
    if mappings:
        approximate = not any(row.get("mapping_source") == "question" for row in mappings)
        return mappings, approximate
    return [], True


def _append_candidate(
    candidates: dict[int, dict[str, Any]],
    kp: dict[str, Any],
    *,
    confidence_delta: float,
    module_id: Optional[int],
    task_id: Optional[int],
    reason: str,
    approximate: bool = False,
) -> None:
    kp_id = int(kp["knowledge_point_id"])
    current = candidates.setdefault(
        kp_id,
        {
            "knowledge_point_id": kp_id,
            "name": kp.get("name"),
            "category": kp.get("category"),
            "description": kp.get("description"),
            "difficulty_level": kp.get("difficulty_level"),
            "module_id": module_id,
            "task_id": task_id,
            "confidence": 0.0,
            "reasons": [],
            "evidence_level": "approximate" if approximate else "direct",
        },
    )
    current["confidence"] += confidence_delta
    current["module_id"] = current.get("module_id") or module_id
    current["task_id"] = current.get("task_id") or task_id
    if approximate and current["evidence_level"] != "direct":
        current["evidence_level"] = "approximate"
    if reason not in current["reasons"]:
        current["reasons"].append(reason)


def _recent_errors(events: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for event in events:
        payload = event.get("payload_json") if isinstance(event.get("payload_json"), dict) else {}
        if event.get("event_type") == "ERROR_EVENT":
            marker = payload.get("error_category") or payload.get("error_signature") or "ERROR_EVENT"
            if marker and marker not in errors:
                errors.append(str(marker))
        if payload.get("is_correct") is False and "answer_incorrect" not in errors:
            errors.append("answer_incorrect")
    return errors[:8]


def _failed_tasks(submissions: list[dict[str, Any]]) -> list[int]:
    tasks: list[int] = []
    for row in submissions:
        if row.get("is_correct") == 0 and row.get("task_id") is not None:
            task_id = int(row["task_id"])
            if task_id not in tasks:
                tasks.append(task_id)
    return tasks[:8]


def _score_candidates(
    *,
    evidence: dict[str, Any],
    scores: dict[str, float],
    recent_focus: str,
    tags: list[str],
) -> list[dict[str, Any]]:
    catalog = _kp_catalog()
    candidates: dict[int, dict[str, Any]] = {}

    knowledge_gap = max(0.0, (70 - scores.get("knowledge_mastery_score", 0)) / 70)
    engagement_gap = max(0.0, (60 - scores.get("engagement_score", 0)) / 60)
    autonomy_gap = max(0.0, (60 - scores.get("autonomy_score", 0)) / 60)
    dashboard_signal = 0.06 if recent_focus or tags else 0.0

    for row in evidence.get("recent_submissions") or []:
        module_id = row.get("module_id")
        task_id = row.get("task_id")
        is_wrong = row.get("is_correct") == 0
        if not is_wrong and row.get("knowledge_point_id") is None:
            continue
        mappings, approximate = _mapped_kps(
            knowledge_point_id=row.get("knowledge_point_id"),
            module_id=module_id,
            task_id=task_id,
            question_id=row.get("question_uid") or row.get("question_id"),
            catalog=catalog,
        )
        for kp in mappings:
            delta = 0.38 if is_wrong else 0.12
            delta += knowledge_gap * 0.25 + dashboard_signal
            reason = (
                f"近期题目 {row.get('question_uid') or row.get('question_id')} 作答错误，"
                f"映射到知识点 {kp.get('name')}"
                if is_wrong
                else f"近期训练题已关联知识点 {kp.get('name')}，用于延续巩固"
            )
            if approximate:
                reason += "；当前缺少题目级稳定标签，按 module/task 粒度近似推断"
            _append_candidate(
                candidates,
                kp,
                confidence_delta=delta,
                module_id=module_id,
                task_id=task_id,
                reason=reason,
                approximate=approximate,
            )

    for event in evidence.get("recent_events") or []:
        if event.get("event_type") not in {"ERROR_EVENT", "FLAG_SUBMIT", "QUESTION_SUBMIT", "HINT_REQUEST", "AI_INTERACTION"}:
            continue
        module_id = event.get("module_id")
        task_id = event.get("task_id")
        mappings, approximate = _mapped_kps(
            knowledge_point_id=None,
            module_id=module_id,
            task_id=task_id,
            question_id=event.get("question_id"),
            catalog=catalog,
        )
        for kp in mappings:
            if event.get("event_type") == "ERROR_EVENT":
                delta = 0.28 + knowledge_gap * 0.15
                reason = f"近期实验错误事件集中在 module={module_id}, task={task_id}"
            elif event.get("event_type") in {"HINT_REQUEST", "AI_INTERACTION"}:
                delta = 0.16 + autonomy_gap * 0.12
                reason = f"近期 AI 求助或提示请求涉及 module={module_id}, task={task_id}"
            else:
                payload = event.get("payload_json") if isinstance(event.get("payload_json"), dict) else {}
                if payload.get("is_correct") is not False:
                    continue
                delta = 0.22 + engagement_gap * 0.10
                reason = f"近期提交失败事件涉及 module={module_id}, task={task_id}"
            if approximate:
                reason += "；当前缺少题目级稳定标签，按 module/task 粒度近似推断"
            _append_candidate(
                candidates,
                kp,
                confidence_delta=delta,
                module_id=module_id,
                task_id=task_id,
                reason=reason,
                approximate=approximate,
            )

    ai_topics = " ".join(evidence.get("recent_ai_topics") or [])
    for kp in catalog.values():
        name = str(kp.get("name") or "")
        category = str(kp.get("category") or "")
        if (name and name[:4] in ai_topics) or (category and category in ai_topics):
            _append_candidate(
                candidates,
                kp,
                confidence_delta=0.18 + autonomy_gap * 0.10,
                module_id=None,
                task_id=None,
                reason=f"近期 AI 提问内容与 {name} 相关",
                approximate=False,
            )

    if not candidates:
        base_delta = 0.42 + knowledge_gap * 0.25 + dashboard_signal
        for kp in list(catalog.values())[:5]:
            _append_candidate(
                candidates,
                kp,
                confidence_delta=base_delta,
                module_id=None,
                task_id=None,
                reason="暂无明确知识点证据，基于当前画像短板选择基础知识点做近似训练",
                approximate=True,
            )

    result = []
    for item in candidates.values():
        confidence = min(0.95, round(item["confidence"], 2))
        reasons = item.pop("reasons")
        item["confidence"] = confidence
        item["reason"] = "；".join(reasons[:3])
        result.append(item)
    result.sort(key=lambda item: item["confidence"], reverse=True)
    return result


def diagnose_training_need(request: dict[str, Any]) -> dict[str, Any]:
    user_id = int(request.get("user_id") or 0)
    if user_id <= 0:
        raise ValueError("user_id is required")
    class_id = request.get("class_id")
    course_id = request.get("course_id")
    top_k = int(request.get("top_k") or 3)
    top_k = max(1, min(top_k, 10))

    profile = get_latest_student_profile(user_id)
    if not profile:
        profile = rebuild_student_profile(user_id)

    scores = _dimension_scores(profile)
    learning_profile = _dashboard_profile(user_id)
    tags = _tag_texts(learning_profile.get("tags"))
    recent_focus = str(learning_profile.get("recentFocus") or "")
    evidence = fetch_recent_training_evidence(user_id, int(course_id) if course_id is not None else None)
    weak_kps = _score_candidates(evidence=evidence, scores=scores, recent_focus=recent_focus, tags=tags)[:top_k]

    constraints = {
        "difficulty": _difficulty_from_scores(scores),
        "question_types": ["single_choice", "fill_blank", "short_answer"],
        "question_count": int(request.get("question_count") or 5),
    }

    return {
        "profile_snapshot_id": profile.get("snapshot_id"),
        "user_id": user_id,
        "class_id": int(class_id) if class_id is not None else profile.get("class_id"),
        "course_id": int(course_id) if course_id is not None else profile.get("course_id"),
        "dimension_scores": scores,
        "weak_dimensions": _weak_dimensions(scores),
        "tags": tags,
        "recent_focus": recent_focus,
        "weak_knowledge_points": weak_kps,
        "generation_constraints": constraints,
        "recent_evidence": {
            "recent_errors": _recent_errors(evidence.get("recent_events") or []),
            "recent_failed_tasks": _failed_tasks(evidence.get("recent_submissions") or []),
            "recent_ai_topics": evidence.get("recent_ai_topics") or [],
        },
    }
