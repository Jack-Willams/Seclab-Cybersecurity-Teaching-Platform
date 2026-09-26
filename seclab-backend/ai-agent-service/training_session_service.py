from __future__ import annotations

import asyncio
from statistics import mean
from typing import Any, Optional
from uuid import uuid4

from profile_repository import get_latest_student_profile
from single_question_generation_service import (
    QuestionGenerationError,
    _build_rag_context,
    _extract_recommendation_context,
    _normalize_request,
    _pick_knowledge_point_id,
    _pick_module_id,
    _retrieve_standard_examples,
    generate_question_with_llm,
    retrieve_knowledge_units,
    validate_generated_question,
)
from training_repository import (
    create_training_session,
    get_training_session,
    list_generated_question_attempts,
    list_generated_questions,
    save_generated_questions,
)


QUESTION_SET_DEFAULT_COUNT = 7
QUESTION_SET_MIN_COUNT = 4
QUESTION_SET_MAX_COUNT = 8
QUESTION_SET_RETRY_LIMIT = 2
QUESTION_SET_TIMEOUT_SECONDS = 12.0

# 画像诊断的 weak_dimensions 可能以中文标签回传（前端 analysisDimensions 直接用 label 发起训练），
# 这里统一归一到内部英文维度键，否则知识检索会拿不到匹配维度。
DIMENSION_ALIASES = {
    "知识掌握": "knowledge_mastery",
    "知识掌握度": "knowledge_mastery",
    "排障能力": "troubleshooting",
    "自主探索": "autonomy",
    "自主探索能力": "autonomy",
    "AI协同": "ai_collaboration",
    "AI 协作能力": "ai_collaboration",
    "学习投入": "engagement",
    "学习投入度": "engagement",
}

QUESTION_ANGLES = [
    "基础概念理解",
    "关键术语辨析",
    "场景判断",
    "错误排查",
    "响应差异分析",
    "防御与修复思路",
    "综合分析题",
    "边界条件分析",
    "证据链组织",
    "迁移应用题",
]


class TrainingSessionServiceError(Exception):
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


def _to_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_question_set_input(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    dimension = str(normalized.get("dimension") or "").strip()
    if dimension in DIMENSION_ALIASES:
        normalized["dimension"] = DIMENSION_ALIASES[dimension]
    return normalized


def _normalize_question_set_request(data: dict[str, Any]) -> dict[str, Any]:
    data = _normalize_question_set_input(data)
    count = QUESTION_SET_DEFAULT_COUNT if data.get("count") in (None, "") else _to_int(data.get("count"))
    if count is None or count < QUESTION_SET_MIN_COUNT or count > QUESTION_SET_MAX_COUNT:
        raise TrainingSessionServiceError(
            "INVALID_COUNT",
            f"count must be between {QUESTION_SET_MIN_COUNT} and {QUESTION_SET_MAX_COUNT}",
            status_code=400,
            details={"count": data.get("count")},
        )
    if str(data.get("question_type") or data.get("questionType") or "").strip().upper() != "SHORT_ANSWER":
        raise TrainingSessionServiceError(
            "UNSUPPORTED_QUESTION_TYPE",
            "question set currently supports SHORT_ANSWER only",
            status_code=400,
            details={"questionType": data.get("question_type") or data.get("questionType")},
        )
    normalized = _normalize_request({**data, "count": 1, "question_type": "SHORT_ANSWER"})
    normalized["count"] = count
    return normalized


def _build_set_context(
    req: dict[str, Any],
    *,
    training_session_id: str,
    question_index: Optional[int] = None,
    question_angle: Optional[str] = None,
    actual_count: Optional[int] = None,
) -> dict[str, Any]:
    context = {
        "trainingSessionId": training_session_id,
        "questionSetCount": actual_count or req["count"],
        "targetCount": req["count"],
        "recommendationId": req["recommendation_id"],
        "dimension": req["dimension"],
        "moduleId": req["module_id"],
        "courseId": req["course_id"],
        "knowledgeTags": req["knowledge_tags"],
        "source": req["source"],
        "generationMode": "question_set_batch",
    }
    if question_index is not None:
        context["questionSetIndex"] = question_index
    if question_angle:
        context["questionAngle"] = question_angle
    return context


def _build_session_records(
    req: dict[str, Any],
    *,
    training_session_id: str,
    profile: Optional[dict[str, Any]],
    knowledge_units: list[dict[str, Any]],
    rag_context: dict[str, Any],
    generator: str,
    actual_count: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    training_context = _build_set_context(
        req,
        training_session_id=training_session_id,
        actual_count=actual_count,
    )
    training_context.update(
        {
            "actualCount": actual_count,
            "minUsableCount": QUESTION_SET_MIN_COUNT,
            "maxCount": QUESTION_SET_MAX_COUNT,
            "partial": actual_count < req["count"],
            "status": "READY",
            "difficulty": req["difficulty"],
            "questionType": req["question_type"],
            "knowledgeUnitIds": [unit["knowledgeUnitId"] for unit in knowledge_units],
            "knowledgeUnitCount": len(knowledge_units),
            "ragMode": rag_context["ragMode"],
            "retrievalQuery": rag_context["retrievalQuery"],
            "retrievalMetadata": rag_context["retrievalMetadata"],
            "sourceValidationMode": rag_context.get("sourceValidationMode") or "warning_only",
            "generator": generator,
            "sourceSnapshotId": (profile or {}).get("snapshot_id"),
        }
    )
    diagnose_result = {
        "user_id": req["user_id"],
        "profile_snapshot_id": training_context["sourceSnapshotId"],
        "weak_dimensions": [req["dimension"]],
        "weak_knowledge_points": [],
        "generation_constraints": {
            "difficulty": req["difficulty"],
            "question_type": req["question_type"],
            "question_count": req["count"],
            "actual_question_count": actual_count,
        },
    }
    return diagnose_result, training_context


def _question_response(row: dict[str, Any]) -> dict[str, Any]:
    raw_ai = row.get("raw_ai") or {}
    return {
        "generatedQuestionId": row["generated_question_id"],
        "title": row["title"],
        "stem": row["stem"],
        "questionType": row["question_type"],
        "difficulty": _to_int(row.get("difficulty")),
        "knowledgeTags": raw_ai.get("knowledgeTags") or raw_ai.get("knowledge_tags") or [],
    }


async def generate_training_question_set(data: dict[str, Any]) -> dict[str, Any]:
    return await generate_training_question_set_batch(data)


async def _generate_question_rows(
    req: dict[str, Any],
    *,
    knowledge_units: list[dict[str, Any]],
    recommendation: dict[str, Any],
    example_questions: list[dict[str, Any]],
    rag_context: dict[str, Any],
    training_session_id: str,
) -> tuple[list[dict[str, Any]], str]:
    async def generate_slot(index: int) -> tuple[int, Optional[dict[str, Any]], str]:
        angle = QUESTION_ANGLES[index - 1] if index <= len(QUESTION_ANGLES) else f"差异化训练 {index}"
        item_req = {
            **req,
            "count": 1,
            "question_index": index,
            "question_set_count": req["count"],
            "question_angle": angle,
            "previous_question_stems": [],
            "avoid_duplicate_instruction": (
                f"本题是训练组第 {index}/{req['count']} 题，请只围绕“{angle}”出题，"
                "题目场景、题干结构、答案结构和评分点必须与其他角度明显不同。"
            ),
        }
        for _attempt in range(QUESTION_SET_RETRY_LIMIT):
            try:
                llm_result = await generate_question_with_llm(
                    item_req,
                    knowledge_units,
                    recommendation,
                    example_questions,
                    rag_context,
                )
                question = validate_generated_question(
                    llm_result["payload"],
                    item_req,
                    knowledge_units,
                    example_questions,
                    rag_context,
                    llm_result.get("difyMetadata") or {},
                )
                question_context = _build_set_context(
                    req,
                    training_session_id=training_session_id,
                    question_index=index,
                    question_angle=angle,
                )
                return (
                    index,
                    {
                        "question_id": f"gq-{uuid4()}",
                        "question_type": question["questionType"],
                        "knowledge_point_id": _pick_knowledge_point_id(knowledge_units),
                        "module_id": _pick_module_id(req, knowledge_units),
                        "task_id": None,
                        "difficulty": str(question["difficulty"]),
                        "title": question["title"],
                        "stem": question["stem"],
                        "options": question.get("options"),
                        "answer": question["standardAnswer"],
                        "reference_answer": question["standardAnswer"],
                        "explanation": question["explanation"],
                        "scoring_rubric": question["gradingRubric"],
                        "dimension": question["dimension"],
                        "knowledgeTags": question["knowledgeTags"],
                        "sourceKnowledgeUnitIds": question["sourceKnowledgeUnitIds"],
                        "sourceExampleQuestionIds": question["sourceExampleQuestionIds"],
                        "ragMode": rag_context["ragMode"],
                        "sourceValidationMode": rag_context.get("sourceValidationMode"),
                        "difySourceExampleQuestionIds": rag_context.get("difySourceExampleQuestionIds") or [],
                        "validationHints": question["validationHints"],
                        "teachingObjective": question["teachingObjective"],
                        "expectedSkill": question["expectedSkill"],
                        "difficultyReason": question["difficultyReason"],
                        "commonMistakes": question["commonMistakes"],
                        "gradingRubric": question["gradingRubric"],
                        "qualityScore": question["qualityScore"],
                        "qualitySummary": question["qualitySummary"],
                        "qualityFlags": question["qualityFlags"],
                        "generator": llm_result["generator"],
                        "recommendationId": req["recommendation_id"],
                        "source": req["source"],
                        "trainingContext": question_context,
                    },
                    str(llm_result["generator"]),
                )
            except Exception:
                continue
        return index, None, ""

    results = await asyncio.gather(*(generate_slot(index) for index in range(1, req["count"] + 1)))
    successful = sorted((item for item in results if item[1] is not None), key=lambda item: item[0])
    rows = [item[1] for item in successful if item[1] is not None]
    generator = next((item[2] for item in successful if item[2]), "unknown")
    return rows, generator


def _build_grounded_fallback_rows(
    req: dict[str, Any],
    *,
    knowledge_units: list[dict[str, Any]],
    example_questions: list[dict[str, Any]],
    training_session_id: str,
) -> tuple[list[dict[str, Any]], str]:
    candidates: list[dict[str, Any]] = []
    for unit in knowledge_units:
        stem = str(unit.get("question") or "").strip()
        answer = str(unit.get("answer") or "").strip()
        if not stem or not answer:
            continue
        candidates.append(
            {
                "sourceKnowledgeUnitIds": [str(unit["knowledgeUnitId"])],
                "sourceExampleQuestionIds": [],
                "title": str(unit.get("moduleTitle") or "知识库训练题").strip(),
                "stem": stem,
                "answer": answer,
                "explanation": str(unit.get("explanation") or "本题来自平台已持久化知识题。").strip(),
                "knowledgeTags": list(unit.get("knowledgeTags") or req["knowledge_tags"]),
                "difficulty": _to_int(unit.get("difficulty")) or req["difficulty"],
                "gradingRubric": [
                    {"point": "准确说明题目要求的核心概念", "score": 60},
                    {"point": "给出清晰依据或安全边界", "score": 40},
                ],
            }
        )
    for example in example_questions:
        stem = str(example.get("stem") or "").strip()
        answer = str(example.get("standardAnswer") or "").strip()
        if not stem or not answer:
            continue
        candidates.append(
            {
                "sourceKnowledgeUnitIds": [],
                "sourceExampleQuestionIds": [str(example["exampleQuestionId"])],
                "title": str(example.get("title") or "平台标准训练题").strip(),
                "stem": stem,
                "answer": answer,
                "explanation": str(example.get("explanation") or "本题来自平台标准题库。").strip(),
                "knowledgeTags": list(example.get("knowledgeTags") or req["knowledge_tags"]),
                "difficulty": _to_int(example.get("difficulty")) or req["difficulty"],
                "gradingRubric": list(example.get("gradingRubric") or [
                    {"point": "准确说明题目要求的核心概念", "score": 100}
                ]),
            }
        )

    rows: list[dict[str, Any]] = []
    seen_stems: set[str] = set()
    for candidate in candidates:
        if candidate["stem"] in seen_stems:
            continue
        seen_stems.add(candidate["stem"])
        index = len(rows) + 1
        context = _build_set_context(
            req,
            training_session_id=training_session_id,
            question_index=index,
            question_angle="平台持久化知识题",
        )
        rows.append(
            {
                "question_id": f"gq-{uuid4()}",
                "question_type": "SHORT_ANSWER",
                "knowledge_point_id": _pick_knowledge_point_id(knowledge_units),
                "module_id": _pick_module_id(req, knowledge_units),
                "task_id": None,
                "difficulty": str(candidate["difficulty"]),
                "title": candidate["title"],
                "stem": candidate["stem"],
                "options": None,
                "answer": candidate["answer"],
                "reference_answer": candidate["answer"],
                "explanation": candidate["explanation"],
                "scoring_rubric": candidate["gradingRubric"],
                "dimension": req["dimension"],
                "knowledgeTags": candidate["knowledgeTags"],
                "sourceKnowledgeUnitIds": candidate["sourceKnowledgeUnitIds"],
                "sourceExampleQuestionIds": candidate["sourceExampleQuestionIds"],
                "ragMode": "persisted_knowledge",
                "sourceValidationMode": "persisted_source",
                "difySourceExampleQuestionIds": [],
                "validationHints": {"keywords": candidate["knowledgeTags"][:3], "minLength": 10},
                "teachingObjective": "基于平台已持久化知识题检验当前推荐维度。",
                "expectedSkill": f"{req['dimension']}相关的概念理解与解释能力。",
                "difficultyReason": f"沿用平台题库中难度 {candidate['difficulty']} 的真实题目。",
                "commonMistakes": ["只给出结论，未说明判断依据。"],
                "gradingRubric": candidate["gradingRubric"],
                "qualityScore": 85,
                "qualitySummary": "题干、答案和解析均复用平台已持久化知识来源。",
                "qualityFlags": [],
                "generator": "persisted_knowledge",
                "recommendationId": req["recommendation_id"],
                "source": req["source"],
                "trainingContext": context,
            }
        )
        if len(rows) >= req["count"]:
            break
    return rows, "persisted_knowledge"


async def generate_training_question_set_batch(data: dict[str, Any]) -> dict[str, Any]:
    req = _normalize_question_set_request(data)
    profile = get_latest_student_profile(req["user_id"])
    recommendation = _extract_recommendation_context(profile, req)
    knowledge_units = retrieve_knowledge_units(req, top_k=5)
    example_questions = _retrieve_standard_examples(req)
    rag_context = _build_rag_context(req, example_questions)
    training_session_id = f"train-{uuid4()}"
    provider_timed_out = False
    try:
        generated_rows, generator = await asyncio.wait_for(
            _generate_question_rows(
                req,
                knowledge_units=knowledge_units,
                recommendation=recommendation,
                example_questions=example_questions,
                rag_context=rag_context,
                training_session_id=training_session_id,
            ),
            timeout=QUESTION_SET_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        provider_timed_out = True
        generated_rows, generator = [], "unknown"

    if len(generated_rows) < QUESTION_SET_MIN_COUNT:
        grounded_rows, grounded_generator = _build_grounded_fallback_rows(
            req,
            knowledge_units=knowledge_units,
            example_questions=example_questions,
            training_session_id=training_session_id,
        )
        if len(grounded_rows) >= QUESTION_SET_MIN_COUNT:
            generated_rows, generator = grounded_rows, grounded_generator
        elif provider_timed_out:
            raise TrainingSessionServiceError(
                "QUESTION_SET_GENERATION_TIMEOUT",
                "训练题准备超时，请稍后重试。",
                status_code=504,
                details={"timeoutSeconds": int(QUESTION_SET_TIMEOUT_SECONDS)},
            )

    actual_count = len(generated_rows)
    if actual_count < QUESTION_SET_MIN_COUNT:
        raise TrainingSessionServiceError(
            "QUESTION_SET_GENERATION_FAILED",
            "训练题准备失败，请稍后重试。",
            status_code=502,
        )
    for index, row in enumerate(generated_rows, start=1):
        training_context = row.get("trainingContext") or {}
        training_context.update(
            {
                "questionSetIndex": index,
                "questionSetCount": actual_count,
                "targetCount": req["count"],
            }
        )
        row["trainingContext"] = training_context

    diagnose_result, training_context = _build_session_records(
        req,
        training_session_id=training_session_id,
        profile=profile,
        knowledge_units=knowledge_units,
        rag_context=rag_context,
        generator=generator,
        actual_count=actual_count,
    )
    session = create_training_session(
        user_id=req["user_id"],
        class_id=None,
        course_id=req["course_id"],
        profile_snapshot_id=training_context.get("sourceSnapshotId"),
        diagnose_result=diagnose_result,
        training_context=training_context,
        training_session_id=training_session_id,
    )
    saved_questions = save_generated_questions(
        training_session_id=session["training_session_id"],
        questions=generated_rows,
        source_model=generator,
    )
    return {
        "success": True,
        "trainingSessionId": session["training_session_id"],
        "count": len(saved_questions),
        "targetCount": req["count"],
        "actualCount": len(saved_questions),
        "partial": len(saved_questions) < req["count"],
        "questions": [_question_response(row) for row in saved_questions],
        "metadata": {
            "generator": generator,
            "mode": "question_set_batch",
            "targetCount": req["count"],
            "actualCount": len(saved_questions),
            "partial": len(saved_questions) < req["count"],
        },
    }

    req = _normalize_question_set_request(data)
    profile = get_latest_student_profile(req["user_id"])
    recommendation = _extract_recommendation_context(profile, req)
    knowledge_units = retrieve_knowledge_units(req, top_k=5)
    example_questions = _retrieve_standard_examples(req)
    rag_context = _build_rag_context(req, example_questions)
    training_session_id = f"train-{uuid4()}"
    generated_rows: list[dict[str, Any]] = []
    previous_stems: list[str] = []
    generator = "unknown"

    for index in range(1, req["count"] + 1):
        angle = QUESTION_ANGLES[index - 1] if index <= len(QUESTION_ANGLES) else f"差异化训练 {index}"
        item_req = {
            **req,
            "count": 1,
            "question_index": index,
            "question_set_count": req["count"],
            "question_angle": angle,
            "previous_question_stems": previous_stems[-6:],
            "avoid_duplicate_instruction": (
                f"本题是训练组第 {index}/{req['count']} 题，请围绕“{angle}”出题，"
                "不要复用前面题目的场景、题干结构、答案结构或评分点。"
            ),
        }
        llm_result = await generate_question_with_llm(
            item_req,
            knowledge_units,
            recommendation,
            example_questions,
            rag_context,
        )
        generator = llm_result["generator"]
        question = validate_generated_question(
            llm_result["payload"],
            item_req,
            knowledge_units,
            example_questions,
            rag_context,
            llm_result.get("difyMetadata") or {},
        )
        previous_stems.append(question["stem"])
        question_context = _build_set_context(
            req,
            training_session_id=training_session_id,
            question_index=index,
            question_angle=angle,
        )
        generated_id = f"gq-{uuid4()}"
        generated_rows.append(
            {
                "question_id": generated_id,
                "question_type": question["questionType"],
                "knowledge_point_id": _pick_knowledge_point_id(knowledge_units),
                "module_id": _pick_module_id(req, knowledge_units),
                "task_id": None,
                "difficulty": str(question["difficulty"]),
                "title": question["title"],
                "stem": question["stem"],
                "options": question.get("options"),
                "answer": question["standardAnswer"],
                "reference_answer": question["standardAnswer"],
                "explanation": question["explanation"],
                "scoring_rubric": question["gradingRubric"],
                "dimension": question["dimension"],
                "knowledgeTags": question["knowledgeTags"],
                "sourceKnowledgeUnitIds": question["sourceKnowledgeUnitIds"],
                "sourceExampleQuestionIds": question["sourceExampleQuestionIds"],
                "ragMode": rag_context["ragMode"],
                "sourceValidationMode": rag_context.get("sourceValidationMode"),
                "difySourceExampleQuestionIds": rag_context.get("difySourceExampleQuestionIds") or [],
                "validationHints": question["validationHints"],
                "teachingObjective": question["teachingObjective"],
                "expectedSkill": question["expectedSkill"],
                "difficultyReason": question["difficultyReason"],
                "commonMistakes": question["commonMistakes"],
                "gradingRubric": question["gradingRubric"],
                "qualityScore": question["qualityScore"],
                "qualitySummary": question["qualitySummary"],
                "qualityFlags": question["qualityFlags"],
                "generator": generator,
                "recommendationId": req["recommendation_id"],
                "source": req["source"],
                "trainingContext": question_context,
            }
        )

    diagnose_result, training_context = _build_session_records(
        req,
        training_session_id=training_session_id,
        profile=profile,
        knowledge_units=knowledge_units,
        rag_context=rag_context,
        generator=generator,
    )
    session = create_training_session(
        user_id=req["user_id"],
        class_id=None,
        course_id=req["course_id"],
        profile_snapshot_id=training_context.get("sourceSnapshotId"),
        diagnose_result=diagnose_result,
        training_context=training_context,
        training_session_id=training_session_id,
    )
    saved_questions = save_generated_questions(
        training_session_id=session["training_session_id"],
        questions=generated_rows,
        source_model=generator,
    )
    return {
        "success": True,
        "trainingSessionId": session["training_session_id"],
        "count": len(saved_questions),
        "questions": [_question_response(row) for row in saved_questions],
        "metadata": {
            "generator": generator,
            "mode": "question_set",
            "count": req["count"],
            "partial": False,
        },
    }


def _level(score: float) -> str:
    if score >= 85:
        return "EXCELLENT"
    if score >= 70:
        return "GOOD"
    if score >= 50:
        return "PARTIAL"
    return "NEEDS_REVIEW"


def _latest_attempt_by_question(attempts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for attempt in attempts:
        result[str(attempt.get("generated_question_id"))] = attempt
    return result


def _feedback_from_attempt(attempt: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not attempt:
        return {}
    answer_payload = attempt.get("answer") if isinstance(attempt.get("answer"), dict) else {}
    feedback = answer_payload.get("feedback") if isinstance(answer_payload.get("feedback"), dict) else {}
    return feedback


def _attempt_answer(attempt: Optional[dict[str, Any]]) -> str:
    if not attempt:
        return ""
    answer_payload = attempt.get("answer") if isinstance(attempt.get("answer"), dict) else {}
    return str(answer_payload.get("answerText") or "")


def _summary_feedback(questions: list[dict[str, Any]], average_score: float) -> str:
    missed: list[str] = []
    suggestions: list[str] = []
    for item in questions:
        for rubric in item.get("missedRubricItems") or []:
            point = str(rubric.get("point") or "").strip()
            if point and point not in missed:
                missed.append(point)
        suggestion = str(item.get("suggestion") or "").strip()
        if suggestion and suggestion not in suggestions:
            suggestions.append(suggestion)
    if average_score >= 85:
        prefix = "本轮训练整体完成度较高，主要评分点覆盖较完整。"
    elif average_score >= 70:
        prefix = "本轮训练基本达标，但仍有少量关键点需要补强。"
    elif average_score >= 50:
        prefix = "本轮训练有一定基础，建议围绕遗漏评分点继续巩固。"
    else:
        prefix = "本轮训练暴露出较明显薄弱点，建议先回到题目要求和基础概念逐项补齐。"
    if missed:
        return f"{prefix} 重点遗漏项包括：{'；'.join(missed[:3])}。"
    if suggestions:
        return f"{prefix} {'；'.join(suggestions[:2])}"
    return prefix


def _next_actions(questions: list[dict[str, Any]]) -> list[str]:
    actions: list[str] = []
    for item in questions:
        for rubric in item.get("missedRubricItems") or []:
            point = str(rubric.get("point") or "").strip()
            if point:
                actions.append(f"补充练习：{point}")
        for keyword in item.get("keywordMisses") or []:
            text = str(keyword).strip()
            if text:
                actions.append(f"复习关键词：{text}")
        suggestion = str(item.get("suggestion") or "").strip()
        if suggestion:
            actions.append(suggestion)
    deduped: list[str] = []
    for action in actions:
        if action not in deduped:
            deduped.append(action)
        if len(deduped) >= 4:
            break
    return deduped or ["复盘本轮题目要求，按评分点补充答案依据。"]


def get_training_session_summary(training_session_id: str, user_id: Optional[int]) -> dict[str, Any]:
    if user_id is None:
        raise TrainingSessionServiceError("MISSING_USER_ID", "userId is required", status_code=400)
    session = get_training_session(training_session_id)
    if not session:
        raise TrainingSessionServiceError(
            "TRAINING_SESSION_NOT_FOUND",
            "training session not found",
            status_code=404,
        )
    if int(session.get("user_id") or 0) != int(user_id):
        raise TrainingSessionServiceError(
            "TRAINING_SESSION_NOT_FOUND",
            "training session not found",
            status_code=404,
        )
    questions = list_generated_questions(training_session_id)
    attempts = list_generated_question_attempts(training_session_id, user_id=int(user_id))
    latest_attempts = _latest_attempt_by_question(attempts)
    submitted_count = len(latest_attempts)
    total_questions = len(questions)
    completed = total_questions > 0 and submitted_count >= total_questions
    scores = [float(attempt.get("score") or 0) for attempt in latest_attempts.values()]
    average_score = round(mean(scores), 1) if scores else 0.0
    context = session.get("training_context") or {}

    question_items: list[dict[str, Any]] = []
    for row in questions:
        raw_ai = row.get("raw_ai") or {}
        attempt = latest_attempts.get(str(row["generated_question_id"]))
        feedback = _feedback_from_attempt(attempt)
        item = {
            "generatedQuestionId": row["generated_question_id"],
            "title": row["title"],
            "stem": row["stem"],
            "submitted": bool(attempt),
            "studentAnswer": _attempt_answer(attempt),
            "correctnessScore": int(feedback.get("correctnessScore") or attempt.get("score") or 0) if attempt else None,
            "level": feedback.get("level") if attempt else None,
            "feedback": feedback.get("feedback") if attempt else None,
            "hitRubricItems": feedback.get("hitRubricItems") or [],
            "missedRubricItems": feedback.get("missedRubricItems") or [],
            "keywordHits": feedback.get("keywordHits") or [],
            "keywordMisses": feedback.get("keywordMisses") or [],
            "suggestion": feedback.get("suggestion") if attempt else None,
        }
        if completed:
            item.update(
                {
                    "standardAnswer": row.get("standard_answer") or row.get("reference_answer"),
                    "explanation": row.get("explanation"),
                    "teachingObjective": raw_ai.get("teachingObjective"),
                    "expectedSkill": raw_ai.get("expectedSkill"),
                    "difficultyReason": raw_ai.get("difficultyReason"),
                    "commonMistakes": raw_ai.get("commonMistakes") or [],
                    "gradingRubric": raw_ai.get("gradingRubric") or row.get("scoring_rubric") or [],
                }
            )
        question_items.append(item)

    response = {
        "success": True,
        "trainingSessionId": training_session_id,
        "userId": int(user_id),
        "totalQuestions": total_questions,
        "submittedCount": submitted_count,
        "completed": completed,
        "averageScore": average_score,
        "level": _level(average_score),
        "dimension": context.get("dimension"),
        "knowledgeTags": context.get("knowledgeTags") or [],
        "questions": question_items,
    }
    if completed:
        response["summaryFeedback"] = _summary_feedback(question_items, average_score)
        response["nextActions"] = _next_actions(question_items)
    return response
