from __future__ import annotations

import json
import re
from datetime import datetime
from difflib import SequenceMatcher
from math import ceil
from typing import Any, Optional

from event_repository import save_learning_event
from question_repository import question_numeric_id
from training_repository import get_generated_question, get_training_session, save_generated_question_attempt


class GeneratedQuestionSubmissionError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400, details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

    def to_detail(self) -> dict[str, Any]:
        detail = {"code": self.code, "message": self.message}
        if self.details:
            detail["details"] = self.details
        return detail


def _json_loads(value: Any, default: Any) -> Any:
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


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _cjk_ngrams(text: str) -> set[str]:
    terms: set[str] = set()
    for block in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        if len(block) <= 4:
            terms.add(block)
        for size in (2, 3, 4):
            for index in range(0, max(0, len(block) - size + 1)):
                terms.add(block[index : index + size])
    return terms


def _extract_terms(value: Any) -> set[str]:
    text = str(value or "").lower()
    terms = {term for term in re.findall(r"[a-z0-9_+#.-]{2,}", text) if len(term) >= 2}
    terms.update(_cjk_ngrams(text))
    return {term for term in terms if term not in {"the", "and", "with", "this", "that"}}


def _normalize_rubric(value: Any) -> list[dict[str, Any]]:
    raw = value if isinstance(value, list) else []
    rubric: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        point = str(item.get("point") or "").strip()
        if not point:
            continue
        try:
            score = float(item.get("score") or 0)
        except (TypeError, ValueError):
            score = 0
        rubric.append({"point": point, "score": max(0, score)})
    total = sum(item["score"] for item in rubric)
    if total > 0 and total != 100:
        for item in rubric:
            item["score"] = round(item["score"] / total * 100, 2)
    return rubric


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _keyword_hits(answer: str, keywords: list[str]) -> tuple[list[str], list[str]]:
    normalized_answer = _normalize_text(answer)
    hits: list[str] = []
    misses: list[str] = []
    for keyword in keywords:
        candidates = _keyword_candidates(keyword)
        matched = False
        for candidate in candidates:
            normalized_keyword = _normalize_text(candidate)
            if normalized_keyword and normalized_keyword in normalized_answer:
                matched = True
                break
            candidate_terms = _extract_terms(candidate)
            answer_terms = _extract_terms(answer)
            if candidate_terms and len(candidate_terms & answer_terms) >= max(1, ceil(len(candidate_terms) * 0.35)):
                matched = True
                break
        if matched:
            hits.append(keyword)
        else:
            misses.append(keyword)
    return hits, misses


def _keyword_candidates(value: str) -> list[str]:
    text = str(value or "").strip()
    candidates = [text] if text else []
    candidates.extend(match.strip() for match in re.findall(r"['\"]([^'\"]{2,})['\"]", text))
    for part in re.split(r"[、,，/或和\s]+", text):
        part = part.strip("。；;：:（）()[]【】")
        if len(part) >= 2:
            candidates.append(part)
    seen: set[str] = set()
    result: list[str] = []
    for item in candidates:
        key = _normalize_text(item)
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _rubric_match(answer_terms: set[str], answer_text: str, point: str) -> bool:
    point_terms = _extract_terms(point)
    if not point_terms:
        return False
    normalized_answer = _normalize_text(answer_text)
    normalized_point = _normalize_text(point)
    if normalized_point and normalized_point in normalized_answer:
        return True
    overlap = point_terms & answer_terms
    required = max(1, ceil(len(point_terms) * 0.18))
    return len(overlap) >= required


def _level(score: int) -> str:
    if score >= 85:
        return "EXCELLENT"
    if score >= 70:
        return "GOOD"
    if score >= 50:
        return "PARTIAL"
    return "NEEDS_REVIEW"


def _safe_similarity(left: Any, right: Any) -> float:
    normalized_left = _normalize_text(left)
    normalized_right = _normalize_text(right)
    if not normalized_left or not normalized_right:
        return 0.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio() * 100


def _build_feedback(hit_items: list[dict[str, Any]], missed_items: list[dict[str, Any]], score: int) -> tuple[str, str]:
    if score >= 85:
        feedback = "回答覆盖了主要评分点，表达较完整。"
    elif score >= 70:
        feedback = "回答覆盖了主要知识点，但仍有少量评分点可以补充。"
    elif score >= 50:
        feedback = "回答有部分有效内容，但关键评分点覆盖不够完整。"
    else:
        feedback = "回答目前覆盖的评分点较少，建议回到题目要求逐项补充。"

    if missed_items:
        missed_points = "；".join(item["point"] for item in missed_items[:2])
        suggestion = f"建议补充：{missed_points}。"
    else:
        suggestion = "建议保持当前答题思路，并继续补充依据和边界说明。"
    return feedback, suggestion


def _score_answer(question: dict[str, Any], answer: str) -> dict[str, Any]:
    raw_ai = question.get("raw_ai") or {}
    validation_hints = raw_ai.get("validationHints") or raw_ai.get("validation_hints") or {}
    if not isinstance(validation_hints, dict):
        validation_hints = {}
    keywords = _as_string_list(validation_hints.get("keywords"))
    min_length = _to_int(validation_hints.get("minLength")) or 10
    rubric = _normalize_rubric(raw_ai.get("gradingRubric") or question.get("scoring_rubric"))
    answer_terms = _extract_terms(answer)

    hit_items: list[dict[str, Any]] = []
    missed_items: list[dict[str, Any]] = []
    rubric_score = 0.0
    for item in rubric:
        matched = _rubric_match(answer_terms, answer, item["point"])
        view_item = {"point": item["point"], "score": item["score"], "matched": matched}
        if matched:
            rubric_score += item["score"]
            hit_items.append(view_item)
        else:
            missed_items.append(view_item)

    keyword_hits, keyword_misses = _keyword_hits(answer, keywords)
    keyword_score = (len(keyword_hits) / len(keywords) * 100) if keywords else 50.0
    length_score = 100.0 if len(answer.strip()) >= min_length else max(0.0, len(answer.strip()) / max(min_length, 1) * 50)
    standard_similarity = _safe_similarity(answer, question.get("standard_answer") or question.get("reference_answer") or "")

    if rubric:
        score = round(rubric_score * 0.7 + keyword_score * 0.2 + length_score * 0.1)
    else:
        score = round(keyword_score * 0.5 + standard_similarity * 0.4 + length_score * 0.1)
    score = max(0, min(100, int(score)))
    feedback, suggestion = _build_feedback(hit_items, missed_items, score)
    if keyword_misses and not missed_items:
        suggestion = f"建议补充关键词方向：{'、'.join(keyword_misses[:3])}。"

    return {
        "correctnessScore": score,
        "level": _level(score),
        "feedback": feedback,
        "hitRubricItems": hit_items,
        "missedRubricItems": missed_items,
        "keywordHits": keyword_hits,
        "keywordMisses": keyword_misses,
        "suggestion": suggestion,
        "standardAnswerSimilarity": round(standard_similarity, 2),
        "minLength": min_length,
    }


def submit_generated_question_answer(
    *,
    generated_question_id: str,
    user_id: int,
    answer: str,
    source: str = "user_profile_recommendation",
) -> dict[str, Any]:
    normalized_answer = str(answer or "").strip()
    if not normalized_answer:
        raise GeneratedQuestionSubmissionError("EMPTY_ANSWER", "answer is required", status_code=400)
    if len(normalized_answer) < 3:
        raise GeneratedQuestionSubmissionError("ANSWER_TOO_SHORT", "answer is too short", status_code=400)

    question = get_generated_question(generated_question_id)
    if not question:
        raise GeneratedQuestionSubmissionError("GENERATED_QUESTION_NOT_FOUND", "generated question not found", status_code=404)
    if str(question.get("question_type") or "").upper() != "SHORT_ANSWER":
        raise GeneratedQuestionSubmissionError("UNSUPPORTED_QUESTION_TYPE", "only SHORT_ANSWER is supported", status_code=400)

    result = _score_answer(question, normalized_answer)
    submitted_at = datetime.utcnow()
    training_session = get_training_session(str(question["training_session_id"])) or {}
    attempt_payload = {
        "answerText": normalized_answer,
        "feedback": result,
        "source": source,
        "submittedAt": submitted_at.isoformat(),
    }
    attempt = save_generated_question_attempt(
        training_session_id=str(question["training_session_id"]),
        generated_question_id=str(question["generated_question_id"]),
        user_id=int(user_id),
        answer=attempt_payload,
        is_correct=result["correctnessScore"] >= 70,
        score=float(result["correctnessScore"]),
        cost_time=None,
        submission_id=None,
        profile_rebuild_snapshot_id=None,
    )

    raw_ai = question.get("raw_ai") or {}
    event_payload = {
        "event_type": "GENERATED_QUESTION_SUBMIT",
        "user_id": user_id,
        "class_id": training_session.get("class_id"),
        "course_id": training_session.get("course_id"),
        "module_id": question.get("module_id"),
        "task_id": question.get("task_id"),
        "question_id": question_numeric_id(question.get("generated_question_id")),
        "event_time": submitted_at,
        "source": source or "user_profile_recommendation",
        "generatedQuestionId": question.get("generated_question_id"),
        "attemptId": attempt["attempt_id"],
        "questionType": question.get("question_type"),
        "dimension": raw_ai.get("dimension"),
        "difficulty": question.get("difficulty"),
        "correctnessScore": result["correctnessScore"],
        "level": result["level"],
        "knowledgeTags": raw_ai.get("knowledgeTags") or raw_ai.get("knowledge_tags") or [],
        "answerLength": len(normalized_answer),
        "request_id": attempt["attempt_id"],
    }
    learning_event = save_learning_event(event_payload)

    return {
        "success": True,
        "generatedQuestionId": question["generated_question_id"],
        "trainingSessionId": str(question["training_session_id"]),
        "attemptId": attempt["attempt_id"],
        "correctnessScore": result["correctnessScore"],
        "level": result["level"],
        "feedback": result["feedback"],
        "hitRubricItems": result["hitRubricItems"],
        "missedRubricItems": result["missedRubricItems"],
        "keywordHits": result["keywordHits"],
        "keywordMisses": result["keywordMisses"],
        "suggestion": result["suggestion"],
        "submittedAt": attempt["submitted_at"],
        "learningEventId": learning_event.get("event_id"),
    }
