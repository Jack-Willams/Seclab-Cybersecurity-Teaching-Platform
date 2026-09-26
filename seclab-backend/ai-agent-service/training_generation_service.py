import json
import re
from typing import Any, Optional
from uuid import uuid4

import httpx

from config import DIFY_API_KEY, DIFY_API_URL, LLM_MODEL
from llm_provider import complete_text, direct_llm_enabled
from training_diagnosis_service import diagnose_training_need
from training_repository import create_training_session, save_generated_questions


SUPPORTED_QUESTION_TYPES = ["single_choice", "fill_blank", "short_answer"]
QUESTION_SYSTEM_PROMPT = (
    "你是网络安全实训平台的出题引擎。"
    "只输出用户消息里要求的 JSON 结构，不要输出 Markdown 代码块或解释性文字。"
)


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_question_types(value: Any) -> list[str]:
    raw = value if isinstance(value, list) else []
    result = [str(item).strip() for item in raw if str(item).strip() in SUPPORTED_QUESTION_TYPES]
    return result or list(SUPPORTED_QUESTION_TYPES)


def build_training_context_package(request: dict[str, Any], diagnose_result: dict[str, Any]) -> dict[str, Any]:
    constraints = dict(diagnose_result.get("generation_constraints") or {})
    if request.get("question_types"):
        constraints["question_types"] = _normalize_question_types(request.get("question_types"))
    if request.get("difficulty"):
        constraints["difficulty"] = str(request.get("difficulty"))
    if request.get("question_count"):
        constraints["question_count"] = max(1, min(_safe_int(request.get("question_count"), 5), 10))

    course_context = request.get("course_context")
    if not isinstance(course_context, list) or not course_context:
        course_context = []
        for kp in diagnose_result.get("weak_knowledge_points") or []:
            course_context.append(
                {
                    "module_id": kp.get("module_id"),
                    "module_name": kp.get("category") or "个性化训练模块",
                    "knowledge_snippets": [
                        kp.get("name"),
                        kp.get("description"),
                        kp.get("reason"),
                    ],
                }
            )

    return {
        "user_id": diagnose_result.get("user_id") or request.get("user_id"),
        "profile_snapshot_id": request.get("profile_snapshot_id") or diagnose_result.get("profile_snapshot_id"),
        "dimension_scores": diagnose_result.get("dimension_scores") or {},
        "weak_dimensions": diagnose_result.get("weak_dimensions") or [],
        "recent_focus": diagnose_result.get("recent_focus") or "",
        "tags": diagnose_result.get("tags") or [],
        "weak_knowledge_points": [
            {
                "knowledge_point_id": item.get("knowledge_point_id"),
                "name": item.get("name"),
                "category": item.get("category"),
                "module_id": item.get("module_id"),
                "task_id": item.get("task_id"),
                "confidence": item.get("confidence"),
                "reason": item.get("reason"),
            }
            for item in diagnose_result.get("weak_knowledge_points") or []
        ],
        "recent_evidence": diagnose_result.get("recent_evidence") or {},
        "course_context": course_context,
        "generation_constraints": constraints,
    }


def build_question_generation_prompt(training_context: dict[str, Any]) -> str:
    context_json = json.dumps(training_context, ensure_ascii=False)
    return f"""
你是 SecLab 个性化训练出题服务。请只基于给定训练上下文包出题，不要编造画像以外的学生隐私。

输出必须是一个 JSON 对象，不能包含 Markdown，结构如下：
{{
  "questions": [
    {{
      "question_type": "single_choice | fill_blank | short_answer",
      "knowledge_point_id": 101,
      "module_id": 4,
      "task_id": 1,
      "difficulty": "medium",
      "title": "题目标题",
      "stem": "题干",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "answer": "B",
      "reference_answer": "简答题参考答案",
      "explanation": "解析",
      "scoring_rubric": ["评分点1", "评分点2"]
    }}
  ]
}}

约束：
1. 必须覆盖 single_choice、fill_blank、short_answer 三类题型，除非 question_count 小于 3。
2. single_choice 必须有 4 个 options，answer 必须是 A/B/C/D。
3. fill_blank 必须有 answer 和 explanation。
4. short_answer 必须有 reference_answer 和 scoring_rubric，scoring_rubric 至少 2 条。
5. 不要输出自然语言说明，只输出 JSON。

训练上下文包：
{context_json}
""".strip()


def _extract_json_object(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        return None


async def _call_dify_for_questions(prompt: str, user_id: Any) -> tuple[Optional[list[dict[str, Any]]], str, Optional[str]]:
    if not DIFY_API_URL or not DIFY_API_KEY:
        return None, "dify-unconfigured", "Dify API is not configured"
    try:
        # 12s 上限：Dify 不可达/慢响应时快速失败走 _fallback_questions，
        # 防止前端 button 在 await 上挂死（之前 80s 会让按钮长时间 disabled）
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(
                f"{DIFY_API_URL.rstrip('/')}/chat-messages",
                headers={
                    "Authorization": f"Bearer {DIFY_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": prompt,
                    "response_mode": "blocking",
                    "conversation_id": "",
                    "user": f"training-{user_id or 'anonymous'}",
                    "inputs": {"scenario": "personalized_training_question_generation"},
                },
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        return None, "dify-error", str(exc)

    answer = payload.get("answer") or payload.get("data", {}).get("answer") or ""
    parsed = _extract_json_object(answer)
    questions = parsed.get("questions") if isinstance(parsed, dict) else None
    if isinstance(questions, list) and questions:
        return [q for q in questions if isinstance(q, dict)], "dify-chat-messages", None
    return None, "dify-invalid-json", "Dify response did not contain structured questions"


async def _call_direct_llm_for_questions(prompt: str) -> tuple[Optional[list[dict[str, Any]]], str, Optional[str]]:
    try:
        # 12s 上限同 Dify 路径：慢响应时快速失败走 _fallback_questions，不让前端按钮挂死
        answer = await complete_text(prompt, system=QUESTION_SYSTEM_PROMPT, timeout=12.0)
    except Exception as exc:
        return None, "llm-error", str(exc)

    parsed = _extract_json_object(answer)
    questions = parsed.get("questions") if isinstance(parsed, dict) else None
    if isinstance(questions, list) and questions:
        return [q for q in questions if isinstance(q, dict)], f"llm-{LLM_MODEL}", None
    return None, "llm-invalid-json", "LLM response did not contain structured questions"


async def _call_llm_for_questions(prompt: str, user_id: Any) -> tuple[Optional[list[dict[str, Any]]], str, Optional[str]]:
    """按配置分发到直连模型或 Dify，返回 (题目列表, 来源标识, 错误信息)。"""
    if direct_llm_enabled():
        return await _call_direct_llm_for_questions(prompt)
    return await _call_dify_for_questions(prompt, user_id)


def _fallback_question(
    *,
    qtype: str,
    kp: dict[str, Any],
    difficulty: str,
    index: int,
) -> dict[str, Any]:
    kp_name = str(kp.get("name") or "目标知识点")
    kp_id = kp.get("knowledge_point_id")
    module_id = kp.get("module_id")
    task_id = kp.get("task_id")
    if qtype == "single_choice":
        return {
            "question_type": "single_choice",
            "knowledge_point_id": kp_id,
            "module_id": module_id,
            "task_id": task_id,
            "difficulty": difficulty,
            "title": f"{kp_name} 选择题",
            "stem": f"围绕「{kp_name}」，下列哪一项最符合安全实验中的正确处理思路？",
            "options": [
                "A. 直接重复失败 payload，不分析过滤条件",
                "B. 先识别输入限制和上下文，再选择对应绕过方式",
                "C. 只依赖提示，不记录实验现象",
                "D. 跳过验证，直接提交答案",
            ],
            "answer": "B",
            "explanation": f"针对 {kp_name}，应先定位限制条件和上下文，再选择匹配的验证与绕过方式。",
        }
    if qtype == "fill_blank":
        return {
            "question_type": "fill_blank",
            "knowledge_point_id": kp_id,
            "module_id": module_id,
            "task_id": task_id,
            "difficulty": difficulty,
            "title": f"{kp_name} 填空题",
            "stem": f"当题目暴露出「{kp_name}」相关弱点时，应先记录失败现象，再定位输入过滤规则和____。",
            "answer": "执行上下文",
            "explanation": "多数 Web 安全题需要同时判断过滤规则与执行/解析上下文，才能选择稳定 payload。",
        }
    return {
        "question_type": "short_answer",
        "knowledge_point_id": kp_id,
        "module_id": module_id,
        "task_id": task_id,
        "difficulty": difficulty,
        "title": f"{kp_name} 简答题",
        "stem": f"请说明你会如何验证并改进「{kp_name}」相关实验中的一次失败尝试。",
        "reference_answer": f"先复盘失败输入、响应和报错，确认 {kp_name} 的限制点；再提出最小变更 payload 验证假设；最后记录成功条件、失败原因和可复用的防御建议。",
        "answer": f"先复盘失败输入、响应和报错，确认 {kp_name} 的限制点；再提出最小变更 payload 验证假设；最后记录成功条件、失败原因和可复用的防御建议。",
        "explanation": "简答题重点考察是否能把失败证据转化为下一步验证，而不是只背 payload。",
        "scoring_rubric": [
            "能指出失败证据和限制条件",
            "能提出下一步可验证的 payload 或实验步骤",
            "能总结防御或复盘要点",
        ],
    }


def _fallback_questions(training_context: dict[str, Any]) -> list[dict[str, Any]]:
    constraints = training_context.get("generation_constraints") or {}
    question_types = _normalize_question_types(constraints.get("question_types"))
    question_count = max(1, min(_safe_int(constraints.get("question_count"), 5), 10))
    difficulty = str(constraints.get("difficulty") or "medium")
    weak_kps = training_context.get("weak_knowledge_points") or [{"name": "综合基础知识", "knowledge_point_id": None}]

    questions = []
    for index in range(question_count):
        qtype = question_types[index % len(question_types)]
        kp = weak_kps[index % len(weak_kps)]
        questions.append(_fallback_question(qtype=qtype, kp=kp, difficulty=difficulty, index=index))
    return questions


def _normalize_questions(
    questions: Optional[list[dict[str, Any]]],
    training_context: dict[str, Any],
    *,
    force_fallback: bool = False,
) -> list[dict[str, Any]]:
    constraints = training_context.get("generation_constraints") or {}
    question_types = _normalize_question_types(constraints.get("question_types"))
    question_count = max(1, min(_safe_int(constraints.get("question_count"), 5), 10))
    difficulty = str(constraints.get("difficulty") or "medium")
    weak_kps = training_context.get("weak_knowledge_points") or [{"knowledge_point_id": None, "name": "综合基础知识"}]

    if force_fallback or not questions:
        questions = _fallback_questions(training_context)

    normalized: list[dict[str, Any]] = []
    for index in range(question_count):
        raw = questions[index] if index < len(questions) else {}
        if not isinstance(raw, dict) or not raw:
            raw = _fallback_question(
                qtype=question_types[index % len(question_types)],
                kp=weak_kps[index % len(weak_kps)],
                difficulty=difficulty,
                index=index,
            )
        qtype = str(raw.get("question_type") or question_types[index % len(question_types)])
        if qtype not in SUPPORTED_QUESTION_TYPES:
            qtype = question_types[index % len(question_types)]
        kp = weak_kps[index % len(weak_kps)]
        item = {
            **raw,
            "question_id": f"gq-{uuid4()}",
            "question_type": qtype,
            "knowledge_point_id": raw.get("knowledge_point_id") or kp.get("knowledge_point_id"),
            "module_id": raw.get("module_id") or kp.get("module_id"),
            "task_id": raw.get("task_id") or kp.get("task_id"),
            "difficulty": raw.get("difficulty") or difficulty,
            "title": raw.get("title") or f"个性化训练题 {index + 1}",
            "stem": raw.get("stem") or _fallback_question(qtype=qtype, kp=kp, difficulty=difficulty, index=index)["stem"],
        }
        if qtype == "single_choice":
            fallback = _fallback_question(qtype=qtype, kp=kp, difficulty=difficulty, index=index)
            options = item.get("options")
            item["options"] = options if isinstance(options, list) and len(options) >= 2 else fallback["options"]
            item["answer"] = str(item.get("answer") or fallback["answer"]).strip()[:1].upper()
            item["explanation"] = item.get("explanation") or fallback["explanation"]
        elif qtype == "fill_blank":
            fallback = _fallback_question(qtype=qtype, kp=kp, difficulty=difficulty, index=index)
            item["answer"] = item.get("answer") or fallback["answer"]
            item["explanation"] = item.get("explanation") or fallback["explanation"]
        else:
            fallback = _fallback_question(qtype=qtype, kp=kp, difficulty=difficulty, index=index)
            item["reference_answer"] = item.get("reference_answer") or item.get("answer") or fallback["reference_answer"]
            item["answer"] = item.get("answer") or item["reference_answer"]
            rubric = item.get("scoring_rubric")
            item["scoring_rubric"] = rubric if isinstance(rubric, list) and len(rubric) >= 2 else fallback["scoring_rubric"]
            item["explanation"] = item.get("explanation") or fallback["explanation"]
        normalized.append(item)
    return normalized


async def generate_personalized_questions(request: dict[str, Any]) -> dict[str, Any]:
    diagnose_result = {
        "profile_snapshot_id": request.get("profile_snapshot_id"),
        "user_id": request.get("user_id"),
        "class_id": request.get("class_id"),
        "course_id": request.get("course_id"),
        "dimension_scores": request.get("dimension_scores") or {},
        "weak_dimensions": request.get("weak_dimensions") or [],
        "weak_knowledge_points": request.get("weak_knowledge_points") or [],
        "recent_focus": request.get("recent_focus") or "",
        "tags": request.get("tags") or [],
        "recent_evidence": request.get("recent_evidence") or {},
        "generation_constraints": {
            "difficulty": request.get("difficulty") or "medium",
            "question_types": _normalize_question_types(request.get("question_types")),
            "question_count": max(1, min(_safe_int(request.get("question_count"), 5), 10)),
        },
    }
    if not diagnose_result["weak_knowledge_points"]:
        diagnose_result = diagnose_training_need(request)

    training_context = build_training_context_package(request, diagnose_result)
    session = create_training_session(
        user_id=int(training_context.get("user_id") or request.get("user_id")),
        class_id=request.get("class_id") or diagnose_result.get("class_id"),
        course_id=request.get("course_id") or diagnose_result.get("course_id"),
        profile_snapshot_id=training_context.get("profile_snapshot_id"),
        diagnose_result=diagnose_result,
        training_context=training_context,
    )

    prompt = build_question_generation_prompt(training_context)
    ai_questions, source_model, error = await _call_llm_for_questions(prompt, training_context.get("user_id"))
    questions = _normalize_questions(ai_questions, training_context, force_fallback=ai_questions is None)
    if ai_questions is None:
        source_model = "local-structured-fallback"

    saved_questions = save_generated_questions(
        training_session_id=session["training_session_id"],
        questions=questions,
        source_model=source_model,
    )

    return {
        "training_session_id": session["training_session_id"],
        "profile_snapshot_id": training_context.get("profile_snapshot_id"),
        "source_model": source_model,
        "generation_status": "ok" if error is None else "fallback",
        "generation_error": error,
        "training_context": training_context,
        "questions": saved_questions,
    }
