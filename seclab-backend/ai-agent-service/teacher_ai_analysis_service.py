from __future__ import annotations

import json
import logging
import math
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from config import DIFY_API_KEY, DIFY_API_URL
from llm_provider import complete_text, direct_llm_enabled
from teacher_ai_prompts import (
    build_class_ai_analysis_prompt,
    build_student_ai_analysis_prompt,
    build_teaching_class_analysis_prompt,
)
from teacher_analysis_repository import (
    InsufficientAnalysisDataError,
    TeacherAnalysisProviderError,
    TeacherAnalysisRepository,
    TeacherStudentAnalysisRepository,
    collect_teaching_class_analysis_evidence,
    require_teaching_class_owner,
)
from teacher_repository import (
    DIMENSION_FIELDS,
    build_rule_based_student_recommendations,
    get_student_profile_for_teacher,
    list_class_students,
    require_student_in_owned_teaching_class,
)


logger = logging.getLogger(__name__)


ALLOWED_PRIORITIES = {"high", "medium", "low"}
STUDENT_TONE_PATTERNS = (
    "你应该",
    "你需要",
    "你可以",
    "开始训练",
    "点击",
    "继续完成",
    "推荐你",
    "推荐补强训练",
    "建议补强训练",
)
VAGUE_ADVICE_PATTERNS = (
    "建议加强训练",
    "建议重点关注",
    "建议补强",
    "提升相关能力",
)
STREAM_END_EVENTS = {"message_end", "agent_message_end", "workflow_finished"}


def provider_failure_message(exc: Exception) -> str:
    """Return a safe, teacher-facing reason without leaking provider details."""
    chain: list[BaseException] = []
    current: Optional[BaseException] = exc
    while current is not None and current not in chain:
        chain.append(current)
        current = current.__cause__ or current.__context__

    for item in chain:
        if isinstance(item, httpx.HTTPStatusError):
            status_code = item.response.status_code
            if status_code in {401, 403}:
                return "Dify 鉴权失败，请检查应用 API Key 是否仍然有效。"
            if status_code == 429:
                return "Dify 模型额度或调用频率已受限，请检查模型供应商余额和限流设置。"
            if status_code >= 500:
                return "Dify 已连接，但上游模型服务暂时异常，请稍后重试。"

    combined = " ".join(str(item).lower() for item in chain)
    if any(isinstance(item, (TimeoutError, httpx.TimeoutException)) for item in chain):
        return "Dify 应用已连接，但模型生成超时；请检查 Dify Agent 的模型供应商、额度和工具配置。"
    if any(keyword in combined for keyword in ("quota", "rate limit", "rate_limit", "insufficient balance")):
        return "Dify 模型额度或调用频率已受限，请检查模型供应商余额和限流设置。"
    if any(keyword in combined for keyword in ("not valid structured", "不是有效结构化", "不能为空", "必须为")):
        return "Dify 已返回内容，但结果格式不符合教学分析要求，请检查 Agent 提示词和输出格式。"
    return "Dify 已连接，但本次模型生成失败；请检查 Dify Agent 的模型供应商和运行日志。"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _score_snapshot(latest_profile: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "dimension": dimension,
            "label": label,
            "score": round(_to_float(latest_profile.get(field)), 1),
        }
        for dimension, label, field in DIMENSION_FIELDS
    ]


def _compact_attempts(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "title": str(item.get("title") or "个性化训练题"),
            "questionType": item.get("questionType") or "未知",
            "score": _to_float(item.get("score")),
            "isCorrect": item.get("isCorrect"),
            "submittedAt": item.get("submittedAt"),
        }
        for item in attempts[:10]
    ]


def _compact_personal_signals(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    for item in signals[:8]:
        event_type = str(item.get("eventType") or "UNKNOWN")
        error_category = item.get("errorCategory")
        if event_type == "ERROR_EVENT":
            summary = f"个人错误类型：{error_category or '未分类'}"
        elif event_type == "HINT_REQUEST":
            summary = "记录到个人学习提示请求"
        elif event_type == "AI_INTERACTION":
            summary = "记录到个人 AI 求助"
        else:
            summary = "记录到个人学习过程信号"
        compacted.append(
            {
                "eventType": event_type,
                "eventTime": item.get("eventTime"),
                "summary": summary,
                "severity": item.get("severity"),
                "errorCategory": error_category,
            }
        )
    return compacted


def _dimension_snapshot_from_students(students: list[dict[str, Any]]) -> list[dict[str, Any]]:
    field_by_dimension = {
        "knowledge_mastery": "knowledgeMasteryScore",
        "troubleshooting": "troubleshootingScore",
        "autonomy": "autonomyScore",
        "ai_collaboration": "aiCollaborationScore",
        "engagement": "engagementScore",
    }
    snapshots: list[dict[str, Any]] = []
    for dimension, label, _ in DIMENSION_FIELDS:
        field = field_by_dimension[dimension]
        scores = [_to_float(student.get(field)) for student in students]
        average_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        low_count = sum(1 for score in scores if score < 70)
        critical_count = sum(1 for score in scores if score < 40)
        snapshots.append(
            {
                "dimension": dimension,
                "label": label,
                "averageScore": average_score,
                "affectedStudentCount": low_count,
                "criticalStudentCount": critical_count,
            }
        )
    return sorted(snapshots, key=lambda item: item["averageScore"])


def build_student_ai_input(profile_data: dict[str, Any]) -> dict[str, Any]:
    latest_profile = profile_data.get("latestProfile") or {}
    dashboard = profile_data.get("dashboard") or {}
    user_stats = dashboard.get("userStats") or {}
    attempts = profile_data.get("recentAttempts") or []
    personal_signals = profile_data.get("personalSignals") or []
    return {
        "scope": "student",
        "userId": profile_data.get("userId"),
        "computedAt": latest_profile.get("computed_at"),
        "dimensionScores": _score_snapshot(latest_profile),
        "overallScore": _to_float(latest_profile.get("overall_score")),
        "userStats": {
            "completedCourses": user_stats.get("completedCourses", 0),
            "totalScore": user_stats.get("totalScore", 0),
            "activeStreak": user_stats.get("activeStreak", 0),
        },
        "recentAttempts": _compact_attempts(attempts),
        "recentAttemptCount": len(attempts),
        "personalSignals": _compact_personal_signals(personal_signals),
        "personalSignalCount": len(personal_signals),
        "sourceLimit": "仅包含该学生个人画像、个人最近训练作答、个人活跃统计、个人错误或求助信号，不包含班级平均分或其他学生数据。",
    }


def build_class_ai_input(class_data: dict[str, Any]) -> dict[str, Any]:
    students = class_data.get("items") or []
    dimension_snapshots = _dimension_snapshot_from_students(students)
    average_profile = (
        round(sum(_to_float(student.get("overallScore")) for student in students) / len(students), 1)
        if students else 0.0
    )
    training_scores = [
        _to_float(student.get("averageTrainingScore"))
        for student in students
        if _to_float(student.get("averageTrainingScore")) > 0
    ]
    average_training = round(sum(training_scores) / len(training_scores), 1) if training_scores else 0.0
    active_count = sum(1 for student in students if student.get("lastActiveAt"))
    return {
        "scope": "class",
        "classId": class_data.get("classId"),
        "className": next((student.get("className") for student in students if student.get("className")), None),
        "studentCount": len(students),
        "activeStudentCount": active_count,
        "averageProfileScore": average_profile,
        "averageTrainingScore": average_training,
        "dimensionSnapshots": dimension_snapshots,
        "weakDimensions": [item for item in dimension_snapshots if item["affectedStudentCount"] > 0][:3],
        "trainingSummary": {
            "attemptCount": sum(_to_float(student.get("generatedQuestionAttemptCount")) for student in students),
            "submitCount": sum(_to_float(student.get("trainingQuestionSubmitCount")) for student in students),
        },
        "sourceLimit": "仅包含该班级学生最新画像与训练聚合数据，不包含单个学生干预建议或其他班级数据。",
    }


def build_rule_fallback_analysis(
    profile_data: dict[str, Any],
    *,
    generated_at: Optional[str] = None,
) -> dict[str, Any]:
    latest_profile = profile_data.get("latestProfile") or {}
    attempts = profile_data.get("recentAttempts") or []
    focus_areas = build_rule_based_student_recommendations(
        latest_profile,
        attempts,
        latest_profile.get("computed_at"),
    )
    return {
        "scope": "student",
        "generatedBy": "rule_fallback",
        "fallbackUsed": True,
        "generatedAt": generated_at or _now_iso(),
        "overallComment": "当前 AI 分析暂不可用，以下为基于画像分数和近期学习行为生成的系统规则建议。",
        "focusAreas": focus_areas,
    }


def build_class_rule_fallback_analysis(
    class_data: dict[str, Any],
    *,
    generated_at: Optional[str] = None,
) -> dict[str, Any]:
    class_input = build_class_ai_input(class_data)
    weak_dimensions = class_input["weakDimensions"] or class_input["dimensionSnapshots"][:1]
    suggestions: list[dict[str, Any]] = []
    for item in weak_dimensions[:3]:
        average_score = _to_float(item.get("averageScore"))
        affected_count = int(_to_float(item.get("affectedStudentCount")))
        priority = "high" if average_score < 50 or affected_count >= 3 else "medium" if affected_count else "low"
        suggestions.append(
            {
                "dimension": item["dimension"],
                "label": item["label"],
                "averageScore": average_score,
                "affectedStudentCount": affected_count,
                "evidence": f"{item['label']}班级均分 {average_score:.1f} 分，{affected_count} 名学生低于 70 分。",
                "inClassAction": f"建议教师在下一次课堂安排 {item['label']} 专项讲评，先展示标准解题或排查流程，再用随堂练习检查全班掌握情况。",
                "afterClassFollowUp": f"建议课后筛选{item['label']}低于 70 分的学生布置一次短复盘，要求提交关键步骤、错误原因和下一次改进点。",
                "priority": priority,
            }
        )
    return {
        "scope": "class",
        "generatedBy": "rule_fallback",
        "fallbackUsed": True,
        "generatedAt": generated_at or _now_iso(),
        "overallComment": "当前 AI 班级分析暂不可用，以下为基于班级画像聚合数据生成的系统规则建议。",
        "suggestions": suggestions,
    }


def _extract_json_object(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass

    # Reasoning models may emit a <think> block containing a draft JSON object
    # before the final answer. Decode every complete object and select the one
    # that finishes latest in the response instead of greedily spanning from
    # the first opening brace to the last closing brace.
    decoder = json.JSONDecoder()
    candidates: list[tuple[int, int, dict[str, Any]]] = []
    for match in re.finditer(r"\{", text):
        try:
            value, relative_end = decoder.raw_decode(text[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append((match.start() + relative_end, match.start(), value))
    if not candidates:
        return None
    _, _, value = max(candidates, key=lambda item: (item[0], -item[1]))
    return value


async def _parse_dify_streaming_answer(response: httpx.Response, *, max_seconds: float = 45.0) -> str:
    chunks: list[str] = []
    deadline = time.monotonic() + max_seconds
    async for raw_line in response.aiter_lines():
        if time.monotonic() > deadline:
            raise TimeoutError("Dify streaming response timed out")
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue
        data_text = line.removeprefix("data:").strip()
        if not data_text:
            continue
        if data_text == "[DONE]":
            break
        try:
            event_payload = json.loads(data_text)
        except json.JSONDecodeError:
            continue
        event = event_payload.get("event")
        if event == "error":
            raise ValueError(str(event_payload.get("message") or "Dify streaming error"))
        answer_chunk = event_payload.get("answer")
        if answer_chunk:
            chunks.append(str(answer_chunk))
        if event in STREAM_END_EVENTS:
            break
    answer = "".join(chunks).strip()
    if not answer:
        raise RuntimeError("Dify streaming response has no answer")
    return answer


def _has_student_tone(value: str) -> bool:
    return any(pattern in value for pattern in STUDENT_TONE_PATTERNS)


def _has_vague_advice(value: str) -> bool:
    return any(pattern in value for pattern in VAGUE_ADVICE_PATTERNS)


def _require_text(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} 不能为空")
    if _has_student_tone(value):
        raise ValueError(f"{key} 包含学生端口吻")
    text = value.strip()
    if key == "teacherAction" and _has_vague_advice(text):
        raise ValueError(f"{key} 内容过于空泛")
    return text


def _require_score(record: dict[str, Any]) -> float:
    if record.get("score") is None:
        raise ValueError("score 不能为空")
    score = _to_float(record.get("score"), default=float("nan"))
    if not math.isfinite(score):
        raise ValueError("score 必须为数字")
    return round(score, 1)


def validate_ai_analysis_payload(payload: dict[str, Any]) -> dict[str, Any]:
    overall_comment = _require_text(payload, "overallComment")
    focus_areas = payload.get("focusAreas")
    if not isinstance(focus_areas, list) or not focus_areas:
        raise ValueError("focusAreas 不能为空")

    normalized: list[dict[str, Any]] = []
    allowed_dimensions = {dimension for dimension, _, _ in DIMENSION_FIELDS}
    for raw_item in focus_areas[:3]:
        if not isinstance(raw_item, dict):
            raise ValueError("focusAreas 必须为对象数组")
        dimension = str(raw_item.get("dimension") or "").strip()
        if dimension not in allowed_dimensions:
            raise ValueError("dimension 不在学生画像维度范围内")
        label = _require_text(raw_item, "label")
        evidence = _require_text(raw_item, "evidence")
        teacher_action = _require_text(raw_item, "teacherAction")
        priority = str(raw_item.get("priority") or "medium").strip().lower()
        if priority not in ALLOWED_PRIORITIES:
            raise ValueError("priority 只能为 high、medium 或 low")
        normalized.append(
            {
                "dimension": dimension,
                "label": label,
                "score": _require_score(raw_item),
                "evidence": evidence,
                "teacherAction": teacher_action,
                "priority": priority,
            }
        )

    return {
        "scope": "student",
        "generatedBy": "llm",
        "fallbackUsed": False,
        "generatedAt": _now_iso(),
        "overallComment": overall_comment,
        "focusAreas": normalized,
    }


def validate_class_ai_analysis_payload(payload: dict[str, Any]) -> dict[str, Any]:
    overall_comment = _require_text(payload, "overallComment")
    suggestions = payload.get("suggestions")
    if not isinstance(suggestions, list) or not suggestions:
        raise ValueError("suggestions 不能为空")

    normalized: list[dict[str, Any]] = []
    allowed_dimensions = {dimension for dimension, _, _ in DIMENSION_FIELDS}
    for raw_item in suggestions[:3]:
        if not isinstance(raw_item, dict):
            raise ValueError("suggestions 必须为对象数组")
        dimension = str(raw_item.get("dimension") or "").strip()
        if dimension not in allowed_dimensions:
            raise ValueError("dimension 不在班级画像维度范围内")
        label = _require_text(raw_item, "label")
        evidence = _require_text(raw_item, "evidence")
        in_class_action = _require_text(raw_item, "inClassAction")
        after_class_follow_up = _require_text(raw_item, "afterClassFollowUp")
        priority = str(raw_item.get("priority") or "medium").strip().lower()
        if priority not in ALLOWED_PRIORITIES:
            raise ValueError("priority 只能为 high、medium 或 low")
        normalized.append(
            {
                "dimension": dimension,
                "label": label,
                "averageScore": _require_score({"score": raw_item.get("averageScore")}),
                "affectedStudentCount": int(_to_float(raw_item.get("affectedStudentCount"))),
                "evidence": evidence,
                "inClassAction": in_class_action,
                "afterClassFollowUp": after_class_follow_up,
                "priority": priority,
            }
        )

    return {
        "scope": "class",
        "generatedBy": "llm",
        "fallbackUsed": False,
        "generatedAt": _now_iso(),
        "overallComment": overall_comment,
        "suggestions": normalized,
    }


def validate_teaching_class_analysis_payload(
    payload: dict[str, Any],
    evidence_question_ids: set[str],
) -> dict[str, Any]:
    overall_comment = _require_text(payload, "overallComment")
    common_problems = payload.get("commonProblems")
    if not isinstance(common_problems, list) or not common_problems:
        raise ValueError("commonProblems 不能为空")
    normalized = []
    for raw_item in common_problems[:5]:
        if not isinstance(raw_item, dict):
            raise ValueError("commonProblems 必须为对象数组")
        title = _require_text(raw_item, "title")
        evidence = _require_text(raw_item, "evidence")
        teacher_action = _require_text(raw_item, "teacherAction")
        student_count = int(_to_float(raw_item.get("studentCount")))
        if student_count < 1:
            raise ValueError("studentCount 必须大于0")
        question_ids = raw_item.get("questionIds")
        if not isinstance(question_ids, list) or not question_ids:
            raise ValueError("questionIds 不能为空")
        normalized_ids = [str(value).strip() for value in question_ids if str(value).strip()]
        if not normalized_ids or any(value not in evidence_question_ids for value in normalized_ids):
            raise ValueError("questionIds 包含证据范围外的题目")
        normalized.append(
            {
                "title": title,
                "evidence": evidence,
                "studentCount": student_count,
                "questionIds": normalized_ids,
                "teacherAction": teacher_action,
            }
        )
    return {
        "overallComment": overall_comment,
        "commonProblems": normalized,
    }


async def _call_dify_for_student_analysis(prompt: str, user_id: Any) -> dict[str, Any]:
    if not DIFY_API_URL or not DIFY_API_KEY:
        raise RuntimeError("Dify API is not configured")
    timeout = httpx.Timeout(30.0, connect=10.0, read=15.0, write=10.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        request_url = f"{DIFY_API_URL.rstrip('/')}/chat-messages"
        headers = {
            "Authorization": f"Bearer {DIFY_API_KEY}",
            "Content-Type": "application/json",
        }
        request_body = {
            "inputs": {},
            "query": prompt,
            "response_mode": "streaming",
            "conversation_id": "",
            "user": f"teacher-student-profile-{user_id or 'anonymous'}",
        }
        async with client.stream(
            "POST",
            request_url,
            headers=headers,
            json=request_body,
        ) as streaming_response:
            streaming_response.raise_for_status()
            text = await _parse_dify_streaming_answer(streaming_response)
    parsed = _extract_json_object(text)
    if not parsed:
        raise ValueError("AI 返回内容不是有效结构化结果")
    return parsed


ANALYSIS_SYSTEM_PROMPT = (
    "你是网络安全实验教学平台的教学分析引擎。"
    "严格按用户消息中给定的 JSON 结构输出，不要输出 Markdown 代码块，不要输出解释性前后缀。"
)


async def _call_direct_llm_for_student_analysis(prompt: str) -> dict[str, Any]:
    text = await complete_text(prompt, system=ANALYSIS_SYSTEM_PROMPT)
    parsed = _extract_json_object(text)
    if not parsed:
        raise ValueError("AI 返回内容不是有效结构化结果")
    return parsed


async def _call_ai_for_student_analysis(prompt: str, user_id: Any) -> dict[str, Any]:
    """按配置分发：配置了 LLM_API_KEY 走直连模型，否则走 Dify，返回结构一致。"""
    if direct_llm_enabled():
        return await _call_direct_llm_for_student_analysis(prompt)
    return await _call_dify_for_student_analysis(prompt, user_id)


async def generate_teacher_student_ai_analysis(
    user_id: int,
    current_user: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    profile_data = get_student_profile_for_teacher(user_id, current_user=current_user)
    generated_at = _now_iso()
    try:
        ai_input = build_student_ai_input(profile_data)
        prompt = build_student_ai_analysis_prompt(json.dumps(ai_input, ensure_ascii=False))
        payload = await _call_ai_for_student_analysis(prompt, user_id)
        result = validate_ai_analysis_payload(payload)
        result["generatedAt"] = generated_at
        return result
    except Exception:
        return build_rule_fallback_analysis(profile_data, generated_at=generated_at)


async def generate_teacher_class_ai_analysis(
    class_id: int,
    current_user: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    class_data = list_class_students(class_id, current_user=current_user)
    generated_at = _now_iso()
    try:
        ai_input = build_class_ai_input(class_data)
        prompt = build_class_ai_analysis_prompt(json.dumps(ai_input, ensure_ascii=False))
        payload = await _call_ai_for_student_analysis(prompt, f"class-{class_id}")
        result = validate_class_ai_analysis_payload(payload)
        result["generatedAt"] = generated_at
        return result
    except Exception:
        return build_class_rule_fallback_analysis(class_data, generated_at=generated_at)


TEACHER_ANALYSIS_REPOSITORY = TeacherAnalysisRepository()
STUDENT_ANALYSIS_REPOSITORY = TeacherStudentAnalysisRepository()


def get_latest_teaching_class_analysis(
    teaching_class_id: int,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    require_teaching_class_owner(
        teaching_class_id,
        int(current_user.get("user_id") or 0),
    )
    return TEACHER_ANALYSIS_REPOSITORY.get_latest(teaching_class_id)


async def run_manual_teaching_class_analysis(
    teaching_class_id: int,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    teacher_id = int(current_user.get("user_id") or 0)
    require_teaching_class_owner(teaching_class_id, teacher_id)
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None)
    TEACHER_ANALYSIS_REPOSITORY.begin(teaching_class_id, teacher_id, cutoff)
    try:
        evidence = collect_teaching_class_analysis_evidence(teaching_class_id)
        prompt = build_teaching_class_analysis_prompt(json.dumps(evidence, ensure_ascii=False))
        payload = await _call_ai_for_student_analysis(prompt, f"teaching-class-{teaching_class_id}")
        result = validate_teaching_class_analysis_payload(
            payload,
            set(evidence.get("evidenceQuestionIds") or []),
        )
        TEACHER_ANALYSIS_REPOSITORY.save_success(
            teaching_class_id,
            teacher_id,
            cutoff,
            result,
            evidence,
        )
        return TEACHER_ANALYSIS_REPOSITORY.get_latest(teaching_class_id)
    except InsufficientAnalysisDataError as exc:
        TEACHER_ANALYSIS_REPOSITORY.save_failure(teaching_class_id, str(exc))
        raise
    except Exception as exc:
        TEACHER_ANALYSIS_REPOSITORY.save_failure(teaching_class_id, "AI 服务暂不可用")
        logger.warning(
            "teacher=%s class analysis failed teaching_class=%s reason=%s",
            teacher_id,
            teaching_class_id,
            type(exc).__name__,
            exc_info=True,
        )
        raise TeacherAnalysisProviderError(provider_failure_message(exc)) from exc


def get_latest_student_analysis(
    teaching_class_id: int,
    student_id: int,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    teacher_id = int(current_user.get("user_id") or 0)
    require_student_in_owned_teaching_class(teacher_id, teaching_class_id, student_id)
    return STUDENT_ANALYSIS_REPOSITORY.get_latest(teacher_id, teaching_class_id, student_id)


async def run_manual_student_analysis(
    teaching_class_id: int,
    student_id: int,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    teacher_id = int(current_user.get("user_id") or 0)
    require_student_in_owned_teaching_class(teacher_id, teaching_class_id, student_id)
    logger.info(
        "teacher=%s started student analysis teaching_class=%s student=%s",
        teacher_id,
        teaching_class_id,
        student_id,
    )
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None)
    STUDENT_ANALYSIS_REPOSITORY.begin(teacher_id, teaching_class_id, student_id, cutoff)
    try:
        profile_data = get_student_profile_for_teacher(
            student_id,
            current_user=current_user,
            teaching_class_id=teaching_class_id,
        )
        if not (
            profile_data.get("latestProfile")
            or profile_data.get("recentAttempts")
            or profile_data.get("personalSignals")
        ):
            raise InsufficientAnalysisDataError("该学生暂无可用于分析的学习记录")
        evidence = build_student_ai_input(profile_data)
        prompt = build_student_ai_analysis_prompt(json.dumps(evidence, ensure_ascii=False))
        payload = await _call_ai_for_student_analysis(
            prompt,
            f"teaching-class-{teaching_class_id}-student-{student_id}",
        )
        result = validate_ai_analysis_payload(payload)
        STUDENT_ANALYSIS_REPOSITORY.save_success(
            teacher_id,
            teaching_class_id,
            student_id,
            cutoff,
            result,
            evidence,
        )
        logger.info(
            "teacher=%s completed student analysis teaching_class=%s student=%s",
            teacher_id,
            teaching_class_id,
            student_id,
        )
        return STUDENT_ANALYSIS_REPOSITORY.get_latest(
            teacher_id,
            teaching_class_id,
            student_id,
        )
    except InsufficientAnalysisDataError as exc:
        STUDENT_ANALYSIS_REPOSITORY.save_failure(
            teacher_id,
            teaching_class_id,
            student_id,
            str(exc),
        )
        logger.info(
            "teacher=%s student analysis lacked evidence teaching_class=%s student=%s",
            teacher_id,
            teaching_class_id,
            student_id,
        )
        raise
    except Exception as exc:
        STUDENT_ANALYSIS_REPOSITORY.save_failure(
            teacher_id,
            teaching_class_id,
            student_id,
            "AI 服务暂不可用",
        )
        logger.warning(
            "teacher=%s student analysis failed teaching_class=%s student=%s reason=%s",
            teacher_id,
            teaching_class_id,
            student_id,
            type(exc).__name__,
            exc_info=True,
        )
        raise TeacherAnalysisProviderError(provider_failure_message(exc)) from exc
