from __future__ import annotations

import json
import os
import re
from difflib import SequenceMatcher
from typing import Any, Optional
from uuid import uuid4

import httpx

from config import LLM_MODEL
from knowledge_repository import list_knowledge_units
from llm_provider import LLMError, complete_text, direct_llm_enabled
from profile_repository import get_latest_student_profile
from standard_question_repository import list_standard_questions, retrieve_example_questions
from training_repository import create_training_session, get_generated_question, save_generated_questions


SINGLE_QUESTION_SYSTEM_PROMPT = (
    "你是网络安全实训平台的个性化出题引擎。"
    "只输出用户消息里要求的 JSON 结构，不要输出 Markdown 代码块或解释性文字。"
)

ALLOWED_DIMENSIONS = {
    "knowledge_mastery",
    "troubleshooting",
    "autonomy",
    "ai_collaboration",
    "engagement",
}

ALLOWED_QUESTION_TYPES = {
    "SHORT_ANSWER",
    "MCQ",
    "CASE",
}

HARD_BLOCK_PATTERNS = [
    ("script_tag", r"</?\s*script\b"),
    ("api_key", r"\bapi[_-]?key\b"),
    ("bearer_token", r"authorization\s*:\s*bearer"),
    ("secret_assignment", r"\b(?:token|password|passwd|secret|credential)s?\s*[:=]\s*['\"]?[a-z0-9_./+\-=]{8,}"),
    ("prompt_injection", r"\bsystem prompt\b|\bignore previous instructions\b"),
    ("public_url", r"https?://[^\s'\"<>]+|\bwww\.[a-z0-9.-]+\.[a-z]{2,}\b"),
    ("public_ip", r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"),
    ("public_domain", r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:com|net|org|cn|io|xyz|top|site|gov|edu|mil|co|info|biz|ru)\b"),
    ("av_evasion", r"免杀|绕过杀软|绕过检测|\bav\s*evasion\b|\bbypass\s+(?:antivirus|av|edr|detection)\b"),
    ("backdoor", r"后门|木马|\bbackdoor\b|\btrojan\b"),
    ("persistence", r"持久化|开机自启|注册表自启动|\bpersistence\b"),
    ("credential_theft", r"凭证窃取|窃取凭证|偷取密码|盗取密码|cookie\s*窃取|\bcredential\s+theft\b|\bsteal\s+(?:password|cookie|token|credential)s?\b"),
    ("data_exfiltration", r"数据窃取|拖库|导出用户数据|\bdata\s+exfiltration\b|\bexfiltrate\b"),
    ("privilege_escalation_steps", r"提权(?:实操|步骤|命令|利用|操作)|\bprivilege\s+escalation\b.*\b(?:steps?|commands?|exploit)\b"),
    ("public_mass_scan", r"批量扫描公网|公网扫描|批量探测公网|\bmass\s+scan(?:ning)?\b|\bscan\s+the\s+internet\b"),
    ("real_exploit_chain", r"真实漏洞利用链|完整攻击链|完整利用链|\bfull\s+exploit\s+chain\b|\bkill\s+chain\b"),
    ("reverse_shell", r"反弹\s*shell|\breverse\s+shell\b"),
]

SOFT_RISK_TERMS = [
    "SQL注入",
    "XSS",
    "文件上传",
    "命令执行",
    "联合查询",
    "UNION",
    "payload",
    "SQL injection",
    "file upload",
    "command execution",
]

EDUCATIONAL_CONTEXT_TERMS = [
    "授权实验",
    "靶场",
    "教学",
    "教学环境",
    "受控",
    "受控实验",
    "防御",
    "识别",
    "原理",
    "修复",
    "参数化",
    "参数化查询",
    "输入校验",
    "安全实验",
    "练习",
    "课程",
    "学习",
    "分析",
    "排查",
    "复盘",
    "controlled lab",
    "training",
    "education",
    "defense",
    "mitigation",
    "identify",
    "principle",
]

ORIGINAL_KNOWLEDGE_SOURCE_TYPES = {
    "COURSE",
    "MODULE",
    "KNOWLEDGE_POINT",
    "DOC",
}

SUPPLEMENTAL_KNOWLEDGE_SOURCE_TYPES = {
    "QUESTION",
    "GENERATED_QUESTION",
}

SOURCE_TYPE_PRIORITY = {
    "MODULE": 50,
    "COURSE": 45,
    "KNOWLEDGE_POINT": 40,
    "DOC": 35,
    "QUESTION": 5,
    "GENERATED_QUESTION": 5,
}

ALLOWED_RAG_MODES = {"local", "hybrid", "dify"}


class QuestionGenerationError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

    def to_detail(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


def _to_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _normalize_dimension(value: Any) -> str:
    dimension = str(value or "").strip()
    if dimension not in ALLOWED_DIMENSIONS:
        raise QuestionGenerationError(
            "INVALID_DIMENSION",
            f"dimension must be one of: {', '.join(sorted(ALLOWED_DIMENSIONS))}",
            details={"dimension": dimension},
        )
    return dimension


def _normalize_question_type(value: Any) -> str:
    question_type = str(value or "").strip().upper()
    if question_type not in ALLOWED_QUESTION_TYPES:
        raise QuestionGenerationError(
            "INVALID_QUESTION_TYPE",
            f"questionType must be one of: {', '.join(sorted(ALLOWED_QUESTION_TYPES))}",
            details={"questionType": question_type},
        )
    return question_type


def _normalize_difficulty(value: Any) -> int:
    difficulty = _to_int(value)
    if difficulty is None or difficulty < 1 or difficulty > 5:
        raise QuestionGenerationError(
            "INVALID_DIFFICULTY",
            "difficulty must be an integer between 1 and 5",
            details={"difficulty": value},
        )
    return difficulty


def _normalize_request(data: dict[str, Any]) -> dict[str, Any]:
    count = _to_int(data.get("count")) or 1
    if count != 1:
        raise QuestionGenerationError(
            "COUNT_NOT_SUPPORTED",
            "this endpoint only supports count = 1",
            details={"count": count},
        )

    user_id = _to_int(data.get("user_id"))
    if user_id is None:
        raise QuestionGenerationError("INVALID_USER_ID", "userId is required")

    module_id = _to_int(data.get("module_id"))
    course_id = _to_int(data.get("course_id"))
    raw_tags = data.get("knowledge_tags") or []
    knowledge_tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]
    if module_id is None and not knowledge_tags:
        raise QuestionGenerationError(
            "MISSING_KNOWLEDGE_TARGET",
            "moduleId or knowledgeTags is required",
        )

    return {
        "user_id": user_id,
        "dimension": _normalize_dimension(data.get("dimension")),
        "recommendation_id": str(data.get("recommendation_id") or "").strip() or None,
        "module_id": module_id,
        "course_id": course_id,
        "knowledge_tags": knowledge_tags,
        "difficulty": _normalize_difficulty(data.get("difficulty")),
        "question_type": _normalize_question_type(data.get("question_type")),
        "count": count,
        "source": str(data.get("source") or "student_profile_snapshot"),
    }


def _difficulty_distance_score(item_difficulty: Any, requested_difficulty: int) -> int:
    item_value = _to_int(item_difficulty)
    if item_value is None:
        return 10
    delta = abs(item_value - requested_difficulty)
    return max(0, 60 - delta * 15)


def _source_type(unit: dict[str, Any]) -> str:
    return str(unit.get("sourceType") or "").upper()


def _source_type_priority(unit: dict[str, Any]) -> int:
    return SOURCE_TYPE_PRIORITY.get(_source_type(unit), 20)


def _score_knowledge_unit(unit: dict[str, Any], req: dict[str, Any]) -> int:
    score = 0
    if req["module_id"] is not None and unit.get("moduleId") == req["module_id"]:
        score += 500
    if req["course_id"] is not None and unit.get("courseId") == req["course_id"]:
        score += 350

    requested_tags = {tag.lower() for tag in req["knowledge_tags"]}
    unit_tags = {str(tag).lower() for tag in unit.get("knowledgeTags") or []}
    for tag in requested_tags:
        if tag in unit_tags:
            score += 100

    dimension_tags = {str(tag).lower() for tag in unit.get("dimensionTags") or []}
    if req["dimension"].lower() in dimension_tags:
        score += 120

    source_type = _source_type(unit)
    if source_type in ORIGINAL_KNOWLEDGE_SOURCE_TYPES:
        score += _source_type_priority(unit)
    elif source_type in SUPPLEMENTAL_KNOWLEDGE_SOURCE_TYPES:
        score += 5

    score += _difficulty_distance_score(unit.get("difficulty"), req["difficulty"])
    return score


def _rank_key(pair: tuple[int, dict[str, Any]]) -> tuple[int, int, int]:
    score, unit = pair
    return (
        score,
        _source_type_priority(unit),
        -(_to_int(unit.get("difficulty")) or 99),
    )


def _select_generation_knowledge_units(
    ranked: list[tuple[int, dict[str, Any]]],
    limit: int,
) -> list[dict[str, Any]]:
    original = [
        pair for pair in ranked
        if _source_type(pair[1]) in ORIGINAL_KNOWLEDGE_SOURCE_TYPES
    ]
    supplemental = [
        pair for pair in ranked
        if _source_type(pair[1]) in SUPPLEMENTAL_KNOWLEDGE_SOURCE_TYPES
    ]
    other = [
        pair for pair in ranked
        if _source_type(pair[1]) not in ORIGINAL_KNOWLEDGE_SOURCE_TYPES
        and _source_type(pair[1]) not in SUPPLEMENTAL_KNOWLEDGE_SOURCE_TYPES
    ]

    minimum_context = min(3, limit)
    selected = [item for _, item in original[:limit]]
    if len(selected) >= minimum_context:
        return selected

    for _, item in other:
        if len(selected) >= minimum_context:
            break
        selected.append(item)

    for _, item in supplemental:
        if len(selected) >= minimum_context:
            break
        selected.append(item)

    return selected


def retrieve_knowledge_units(req: dict[str, Any], top_k: int = 5) -> list[dict[str, Any]]:
    items = list_knowledge_units(
        module_id=req["module_id"],
        course_id=req["course_id"],
    ).get("items", [])

    if req["module_id"] is not None and not any(
        unit.get("moduleId") == req["module_id"]
        and str(unit.get("sourceType") or "").upper() == "MODULE"
        for unit in items
    ):
        raise QuestionGenerationError(
            "KNOWLEDGE_CONTEXT_NOT_FOUND",
            "knowledge units are insufficient for this request",
            status_code=404,
            details={
                "moduleId": req["module_id"],
                "courseId": req["course_id"],
                "knowledgeTags": req["knowledge_tags"],
                "dimension": req["dimension"],
            },
        )

    lowered_tags = {tag.lower() for tag in req["knowledge_tags"]}
    if lowered_tags:
        items = [
            item for item in items
            if (
                lowered_tags.intersection({str(tag).lower() for tag in item.get("knowledgeTags") or []})
                or req["dimension"].lower() in {str(tag).lower() for tag in item.get("dimensionTags") or []}
            )
        ]

    ranked = []
    for item in items:
        score = _score_knowledge_unit(item, req)
        if score <= 0:
            continue
        ranked.append((score, item))

    ranked.sort(key=_rank_key, reverse=True)

    results = _select_generation_knowledge_units(ranked, max(3, min(top_k, 5)))
    if not results:
        raise QuestionGenerationError(
            "KNOWLEDGE_CONTEXT_NOT_FOUND",
            "knowledge units are insufficient for this request",
            status_code=404,
            details={
                "moduleId": req["module_id"],
                "courseId": req["course_id"],
                "knowledgeTags": req["knowledge_tags"],
                "dimension": req["dimension"],
            },
        )
    return results


def _extract_recommendation_context(profile: Optional[dict[str, Any]], req: dict[str, Any]) -> dict[str, Any]:
    summary = (profile or {}).get("profile_summary_json") or {}
    recommendations = summary.get("recommendations") or []
    for item in recommendations:
        if not isinstance(item, dict):
            continue
        if req["recommendation_id"] and item.get("id") == req["recommendation_id"]:
            return item
        if item.get("dimension") == req["dimension"] and item.get("moduleId") == req["module_id"]:
            return item
    return {}


def _json_block(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _get_dify_rag_mode() -> str:
    configured = str(os.getenv("DIFY_RAG_MODE") or "").strip().lower()
    if configured in ALLOWED_RAG_MODES:
        return configured
    if _to_bool(os.getenv("ENABLE_DIFY_KNOWLEDGE_RAG")):
        return "dify"
    return "local"


def _build_retrieval_metadata(req: dict[str, Any]) -> dict[str, Any]:
    return {
        "moduleId": req["module_id"],
        "courseId": req["course_id"],
        "difficulty": req["difficulty"],
        "questionType": req["question_type"],
        "dimension": req["dimension"],
        "knowledgeTags": req["knowledge_tags"],
    }


def _build_retrieval_query(req: dict[str, Any]) -> str:
    tags = " ".join(req["knowledge_tags"]) or "当前推荐知识点"
    return (
        f"生成一题 {tags} 难度{req['difficulty']} "
        f"{req['question_type']} {req['dimension']} 训练题"
    )


def _build_rag_context(req: dict[str, Any], example_questions: list[dict[str, Any]]) -> dict[str, Any]:
    mode = _get_dify_rag_mode()
    return {
        "ragMode": mode,
        "retrievalQuery": _build_retrieval_query(req),
        "retrievalMetadata": _build_retrieval_metadata(req),
        "localExampleQuestionIds": [item["exampleQuestionId"] for item in example_questions],
        "difySourceExampleQuestionIds": [],
        "difyRetrievedExampleSnippets": [],
        "sourceValidationMode": "local_strict" if mode == "local" else "warning_only",
        "exampleQuestionSimilarityChecked": bool(example_questions),
    }


def build_generation_prompt(
    req: dict[str, Any],
    knowledge_units: list[dict[str, Any]],
    recommendation: dict[str, Any],
    example_questions: list[dict[str, Any]],
    rag_context: Optional[dict[str, Any]] = None,
) -> str:
    recommendation_reason = recommendation.get("reason")
    rag_context = rag_context or _build_rag_context(req, example_questions)
    example_question_ids = [item["exampleQuestionId"] for item in example_questions]
    prompt = {
        "system": (
            "你是一名网络安全教学出题助手。请基于提供的知识单元生成一题训练题。"
            "题目必须严格依据输入知识，不得编造超出知识范围的背景设定。"
            "输出必须是合法 JSON，不要输出 markdown。"
            "题目用于授权教学实验平台，不得包含真实攻击目标、真实恶意载荷、绕过现实系统的操作指令。"
        ),
        "task": {
            "dimension": req["dimension"],
            "difficulty": req["difficulty"],
            "questionType": req["question_type"],
            "recommendationReason": recommendation_reason,
            "moduleId": req["module_id"],
            "courseId": req["course_id"],
            "knowledgeTags": req["knowledge_tags"],
            "ragMode": rag_context["ragMode"],
            "retrievalQuery": rag_context["retrievalQuery"],
            "retrievalMetadata": rag_context["retrievalMetadata"],
            "questionIndex": req.get("question_index"),
            "questionSetCount": req.get("question_set_count"),
            "questionAngle": req.get("question_angle"),
            "avoidDuplicateInstruction": req.get("avoid_duplicate_instruction"),
            "previousQuestionStems": req.get("previous_question_stems") or [],
        },
        "requirements": {
            "mustInclude": [
                "title",
                "stem",
                "questionType",
                "difficulty",
                "dimension",
                "knowledgeTags",
                "standardAnswer",
                "explanation",
                "sourceKnowledgeUnitIds",
                "validationHints",
                "sourceExampleQuestionIds",
                "teachingObjective",
                "expectedSkill",
                "difficultyReason",
                "commonMistakes",
                "gradingRubric",
                "qualityScore",
                "qualitySummary",
                "qualityFlags",
            ],
            "optionalForMCQ": ["options", "correctOption"],
            "sourceKnowledgeUnitIdsMustComeFrom": [unit["knowledgeUnitId"] for unit in knowledge_units],
            "sourceExampleQuestionIdsMustComeFrom": example_question_ids,
            "exampleQuestionRules": [
                "exampleQuestionsJson is only a style and structure reference for question type, difficulty, answer organization, and grading rubric.",
                "Do not copy the example question stem.",
                "Do not copy the example standardAnswer.",
                "Do not copy the example explanation.",
                "Generate a new question grounded in knowledgeUnitsJson.",
                "If exampleQuestionsJson is not empty, return sourceExampleQuestionIds using only IDs from exampleQuestionsJson.",
                "If ragMode is dify and the workflow retrieves standard examples, return sourceExampleQuestionIds using only IDs from retrieved example metadata.",
                "If no standard examples are available from either exampleQuestionsJson or Dify retrieval metadata, return sourceExampleQuestionIds as an empty array.",
            ],
            "teachingQualityRules": [
                "Return JSON only. Do not return markdown.",
                "teachingObjective must state the learning goal based only on the retrieved knowledge units.",
                "expectedSkill must name the target capability for the requested dimension.",
                "difficultyReason must explain why the requested difficulty fits the knowledge units.",
                "commonMistakes must be an array of likely misconceptions, not exploit instructions.",
                "gradingRubric must contain at least two items. Each item is {point, score}; scores should sum to 100.",
                "qualityScore must be an integer from 0 to 100.",
                "qualitySummary must explain whether the question is grounded, clear, and assessable.",
                "qualityFlags must be an array. Use [] when no quality concern is found.",
                "Do not include real attack targets, real malicious payloads, or instructions for bypassing real systems.",
            ],
            "questionSetRules": [
                "If questionIndex and questionAngle are provided, generate this single question for that angle.",
                "Avoid repeating previousQuestionStems in title, stem, answer structure, and grading rubric.",
                "Keep the question grounded in the same knowledge units but change the reasoning perspective.",
            ],
        },
        "knowledgeUnits": knowledge_units,
        "knowledgeUnitsJson": _json_block(knowledge_units),
        "exampleQuestions": example_questions,
        "exampleQuestionsJson": _json_block(example_questions),
        "ragMode": rag_context["ragMode"],
        "retrievalQuery": rag_context["retrievalQuery"],
        "retrievalMetadata": rag_context["retrievalMetadata"],
        "questionSet": {
            "questionIndex": req.get("question_index"),
            "questionSetCount": req.get("question_set_count"),
            "questionAngle": req.get("question_angle"),
            "avoidDuplicateInstruction": req.get("avoid_duplicate_instruction"),
            "previousQuestionStems": req.get("previous_question_stems") or [],
        },
    }
    return _json_block(prompt)


def _extract_json_object(payload: str) -> Optional[dict[str, Any]]:
    if not payload:
        return None
    try:
        value = json.loads(payload)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", payload, flags=re.S)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        return None


def _keyword_hints(knowledge_units: list[dict[str, Any]], requested_tags: list[str]) -> list[str]:
    hints = list(requested_tags)
    for unit in knowledge_units:
        for tag in unit.get("knowledgeTags") or []:
            text = str(tag).strip()
            if text and text not in hints:
                hints.append(text)
        if len(hints) >= 4:
            break
    return hints[:4]


def _fake_generate_question(req: dict[str, Any], knowledge_units: list[dict[str, Any]]) -> dict[str, Any]:
    primary = knowledge_units[0]
    source_ids = [unit["knowledgeUnitId"] for unit in knowledge_units[:2]]
    hints = _keyword_hints(knowledge_units, req["knowledge_tags"])
    title = str(primary.get("moduleTitle") or primary.get("courseTitle") or "个性化训练题")
    source_type = str(primary.get("sourceType") or "GENERAL")
    content_hint = str(primary.get("taskPoint") or primary.get("content") or "").strip()
    angle = str(req.get("question_angle") or "单题训练").strip()

    if req["question_type"] == "MCQ":
        return {
            "title": f"{title} 选择题",
            "stem": f"围绕“{title}”相关知识，下面哪一项最符合受控教学实验中的安全分析思路？",
            "questionType": "MCQ",
            "difficulty": req["difficulty"],
            "dimension": req["dimension"],
            "knowledgeTags": hints,
            "standardAnswer": "B",
            "explanation": "先识别实验场景中的输入限制、上下文和防护点，再选择对应的分析或验证方法。",
            "sourceKnowledgeUnitIds": source_ids,
            "validationHints": {
                "keywords": hints[:2] or ["安全分析"],
                "minLength": 1,
            },
            "options": [
                f"A. 直接复用与 {title} 无关的历史答案",
                "B. 先识别受控实验上下文，再选择对应的分析与验证步骤",
                "C. 跳过分析，直接对现实网站执行验证",
                "D. 输出真实攻击目标和恶意载荷",
            ],
            "correctOption": "B",
        }

    stem_suffix = f" 当前知识来源类型为 {source_type}。"
    if content_hint:
        stem_suffix += f" 可参考要点：{content_hint[:120]}。"

    return {
        "title": f"{title} {angle}",
        "stem": f"请结合“{title}”，从“{angle}”角度说明你会如何在受控教学实验中识别关键风险点，并给出一条安全、可解释的验证思路。{stem_suffix}",
        "questionType": req["question_type"],
        "difficulty": req["difficulty"],
        "dimension": req["dimension"],
        "knowledgeTags": hints,
        "standardAnswer": "应先说明风险点、受控实验边界、验证步骤以及为何该思路适合当前模块。",
        "explanation": "本题用于检验学生是否能基于当前推荐资源给出受控、可解释的训练性回答，而不是输出现实攻击指令。",
        "sourceKnowledgeUnitIds": source_ids,
        "validationHints": {
            "keywords": hints[:2] or ["风险点", "验证步骤"],
            "minLength": 10,
        },
    }


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_grading_rubric(value: Any) -> list[dict[str, Any]]:
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


def _default_quality_fields(question: dict[str, Any], req: dict[str, Any], knowledge_units: list[dict[str, Any]]) -> dict[str, Any]:
    tags = question.get("knowledgeTags") or req["knowledge_tags"]
    focus = "、".join(tags[:2]) if tags else "当前推荐知识点"
    source_count = len(question.get("sourceKnowledgeUnitIds") or [])
    rubric = [
        {"point": "回答准确覆盖题目要求的核心概念", "score": 40},
        {"point": "结合检索到的知识单元说明分析依据", "score": 35},
        {"point": "表达清晰，并保持在受控教学实验边界内", "score": 25},
    ]
    return {
        "teachingObjective": f"检验学生能否围绕{focus}完成受控教学场景下的安全分析。",
        "expectedSkill": f"{req['dimension']} 相关的概念理解、证据提取与解释能力。",
        "difficultyReason": f"题目难度为 {req['difficulty']}，依据 {source_count or len(knowledge_units)} 个检索知识单元设置。",
        "commonMistakes": [
            "只给出结论，缺少来自知识单元的依据。",
            "忽略受控教学实验边界，写成现实攻击操作。",
        ],
        "gradingRubric": rubric,
        "qualityScore": 80,
        "qualitySummary": "题目包含明确题干、参考答案、解析和可评分要点，适合作为画像推荐后的单题训练。",
        "qualityFlags": [],
    }


async def _read_dify_streaming_answer(
    client: httpx.AsyncClient,
    api_url: str,
    headers: dict[str, str],
    user_token: str,
    prompt: str,
    dify_inputs: dict[str, Any],
) -> str:
    answer_parts: list[str] = []
    async with client.stream(
        "POST",
        f"{api_url.rstrip('/')}/chat-messages",
        headers=headers,
        json={
            "query": prompt,
            "response_mode": "streaming",
            "conversation_id": "",
            "user": user_token,
            "inputs": {
                "scenario": "profile_single_question_generation",
                **dify_inputs,
            },
        },
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            text = line.strip()
            if not text.startswith("data:"):
                continue
            data = text.removeprefix("data:").strip()
            if not data or data == "[DONE]":
                continue
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                continue
            if payload.get("event") == "error":
                raise QuestionGenerationError(
                    "LLM_REQUEST_FAILED",
                    "Dify request failed",
                    status_code=502,
                    details={
                        "statusCode": payload.get("status"),
                        "responseText": str(payload.get("message") or "")[:500],
                    },
                )
            answer = payload.get("answer")
            if answer:
                answer_parts.append(str(answer))
    return "".join(answer_parts)


def _extract_dify_output_text(payload: dict[str, Any]) -> str:
    outputs = payload.get("data", {}).get("outputs")
    if isinstance(outputs, dict):
        for key in ("result", "answer", "text", "output"):
            value = outputs.get(key)
            if isinstance(value, (dict, list)):
                return _json_block(value)
            if value:
                return str(value)
        for value in outputs.values():
            if isinstance(value, (dict, list)):
                return _json_block(value)
            if isinstance(value, str) and value.strip():
                return value
    for key in ("answer", "text", "result"):
        value = payload.get(key)
        if isinstance(value, (dict, list)):
            return _json_block(value)
        if value:
            return str(value)
    return ""


def _extract_dify_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = {
        "metadata": payload.get("metadata") or {},
        "dataMetadata": payload.get("data", {}).get("metadata") or {},
    }
    outputs = payload.get("data", {}).get("outputs")
    if isinstance(outputs, dict):
        metadata["outputsMetadata"] = outputs.get("metadata") or outputs.get("retrieval_metadata") or {}
        metadata["outputsRetrieval"] = (
            outputs.get("retrieval")
            or outputs.get("retrievalResults")
            or outputs.get("retrieval_results")
            or outputs.get("source_documents")
            or []
        )
    return metadata


def _build_dify_inputs(
    prompt: str,
    req: dict[str, Any],
    knowledge_units: list[dict[str, Any]],
    recommendation: dict[str, Any],
    example_questions: list[dict[str, Any]],
    rag_context: dict[str, Any],
) -> dict[str, Any]:
    dify_inputs = {
        "prompt": prompt,
        "dimension": req["dimension"],
        "difficulty": req["difficulty"],
        "questionType": req["question_type"],
        "question_type": req["question_type"],
        "knowledgeTags": req["knowledge_tags"],
        "knowledge_tags": req["knowledge_tags"],
        "recommendationReason": recommendation.get("reason"),
        "moduleId": req["module_id"],
        "courseId": req["course_id"],
        "ragMode": rag_context["ragMode"],
        "retrievalQuery": rag_context["retrievalQuery"],
        "retrievalMetadata": rag_context["retrievalMetadata"],
        "knowledgeUnitsJson": _json_block(knowledge_units),
        "questionIndex": req.get("question_index"),
        "questionSetCount": req.get("question_set_count"),
        "questionAngle": req.get("question_angle"),
        "avoidDuplicateInstruction": req.get("avoid_duplicate_instruction"),
        "previousQuestionStems": req.get("previous_question_stems") or [],
    }
    if rag_context["ragMode"] in {"local", "hybrid"}:
        dify_inputs["exampleQuestionsJson"] = _json_block(example_questions)
    return dify_inputs


async def _call_dify_chat(
    prompt: str,
    req: dict[str, Any],
    knowledge_units: list[dict[str, Any]],
    recommendation: dict[str, Any],
    example_questions: list[dict[str, Any]],
    rag_context: dict[str, Any],
) -> dict[str, Any]:
    api_url = str(os.getenv("DIFY_API_URL") or "").strip()
    api_key = str(os.getenv("DIFY_API_KEY") or "").strip()
    if not api_url or not api_key:
        raise QuestionGenerationError(
            "LLM_NOT_CONFIGURED",
            "Dify API is not configured",
            status_code=503,
        )

    workflow_id = str(os.getenv("DIFY_WORKFLOW_ID") or os.getenv("DIFY_APP_ID") or "").strip() or None
    user_token = f"profile-training-{req['user_id']}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    dify_inputs = _build_dify_inputs(prompt, req, knowledge_units, recommendation, example_questions, rag_context)
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            if workflow_id:
                response = await client.post(
                    f"{api_url.rstrip('/')}/workflows/run",
                    headers=headers,
                    json={
                        "inputs": dify_inputs,
                        "response_mode": "blocking",
                        "user": user_token,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                raw_text = _extract_dify_output_text(payload)
                generator = "dify_workflow"
            else:
                try:
                    response = await client.post(
                        f"{api_url.rstrip('/')}/chat-messages",
                        headers=headers,
                        json={
                            "query": prompt,
                            "response_mode": "blocking",
                            "conversation_id": "",
                            "user": user_token,
                            "inputs": {
                                "scenario": "profile_single_question_generation",
                                **dify_inputs,
                            },
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                    raw_text = _extract_dify_output_text(payload)
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code != 400 or "does not support blocking mode" not in exc.response.text.lower():
                        raise
                    raw_text = await _read_dify_streaming_answer(
                        client,
                        api_url,
                        headers,
                        user_token,
                        prompt,
                        dify_inputs,
                    )
                    payload = {}
                generator = "dify_chat"
    except httpx.HTTPStatusError as exc:
        raise QuestionGenerationError(
            "LLM_REQUEST_FAILED",
            "Dify request failed",
            status_code=502,
            details={"statusCode": exc.response.status_code, "responseText": exc.response.text[:500]},
        ) from exc
    except httpx.HTTPError as exc:
        raise QuestionGenerationError(
            "LLM_REQUEST_FAILED",
            "Dify request failed",
            status_code=502,
            details={"error": str(exc)},
        ) from exc

    parsed = _extract_json_object(raw_text)
    if not parsed:
        raise QuestionGenerationError(
            "INVALID_LLM_OUTPUT",
            "LLM output is not valid JSON",
            status_code=502,
        )
    return {
        "generator": generator,
        "payload": parsed,
        "difyMetadata": _extract_dify_metadata(payload),
        "difyInputs": dify_inputs,
    }


async def _call_direct_llm(
    prompt: str,
    req: dict[str, Any],
    knowledge_units: list[dict[str, Any]],
    recommendation: dict[str, Any],
    example_questions: list[dict[str, Any]],
    rag_context: dict[str, Any],
) -> dict[str, Any]:
    # 直连模型没有 Dify 的 inputs 变量机制，把同一份上下文附在提示词后面
    dify_inputs = _build_dify_inputs(prompt, req, knowledge_units, recommendation, example_questions, rag_context)
    context = {key: value for key, value in dify_inputs.items() if key != "prompt"}
    full_prompt = f"{prompt}\n\n【生成上下文】\n{json.dumps(context, ensure_ascii=False)}"
    try:
        raw_text = await complete_text(full_prompt, system=SINGLE_QUESTION_SYSTEM_PROMPT, timeout=90.0)
    except LLMError as exc:
        raise QuestionGenerationError(
            "LLM_REQUEST_FAILED",
            "LLM request failed",
            status_code=502,
            details={"error": str(exc)},
        ) from exc
    except httpx.HTTPError as exc:
        raise QuestionGenerationError(
            "LLM_REQUEST_FAILED",
            "LLM request failed",
            status_code=502,
            details={"error": str(exc)},
        ) from exc

    parsed = _extract_json_object(raw_text)
    if not parsed:
        raise QuestionGenerationError(
            "INVALID_LLM_OUTPUT",
            "LLM output is not valid JSON",
            status_code=502,
        )
    return {
        "generator": f"llm_{LLM_MODEL}",
        "payload": parsed,
        "difyMetadata": {},
        "difyInputs": dify_inputs,
    }


async def generate_question_with_llm(
    req: dict[str, Any],
    knowledge_units: list[dict[str, Any]],
    recommendation: dict[str, Any],
    example_questions: list[dict[str, Any]],
    rag_context: dict[str, Any],
) -> dict[str, Any]:
    if _to_bool(os.getenv("ENABLE_FAKE_LLM_FOR_TEST")):
        payload = _fake_generate_question(req, knowledge_units)
        payload["sourceExampleQuestionIds"] = [item["exampleQuestionId"] for item in example_questions[:1]]
        return {
            "generator": "fake_test_generator",
            "payload": payload,
            "difyMetadata": {},
            "difyInputs": {},
        }
    prompt = build_generation_prompt(req, knowledge_units, recommendation, example_questions, rag_context)
    if direct_llm_enabled():
        return await _call_direct_llm(prompt, req, knowledge_units, recommendation, example_questions, rag_context)
    return await _call_dify_chat(prompt, req, knowledge_units, recommendation, example_questions, rag_context)


def _find_hard_block_matches(value: str) -> list[str]:
    text = str(value or "")
    matches: list[str] = []
    for label, pattern in HARD_BLOCK_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            matches.append(label)
    return matches


def _find_soft_risk_terms(value: str) -> list[str]:
    lowered = str(value or "").lower()
    matches: list[str] = []
    for term in SOFT_RISK_TERMS:
        if term.lower() in lowered:
            matches.append(term)
    return matches


def _has_educational_context(value: str) -> bool:
    lowered = str(value or "").lower()
    return any(term.lower() in lowered for term in EDUCATIONAL_CONTEXT_TERMS)


def _append_quality_flag(question: dict[str, Any], flag: str) -> None:
    flags = question.setdefault("qualityFlags", [])
    if flag not in flags:
        flags.append(flag)


def _validate_training_safety(question: dict[str, Any], safe_texts: list[str]) -> None:
    combined_text = "\n".join(str(text or "") for text in safe_texts)
    hard_matches = sorted(set(_find_hard_block_matches(combined_text)))
    if hard_matches:
        raise QuestionGenerationError(
            "UNSAFE_GENERATED_CONTENT",
            "generated question contains hard-blocked unsafe content",
            status_code=502,
            details={"hardBlockMatches": hard_matches},
        )

    soft_matches = sorted(set(_find_soft_risk_terms(combined_text)), key=str.lower)
    if not soft_matches:
        return

    if not _has_educational_context(combined_text):
        raise QuestionGenerationError(
            "UNSAFE_GENERATED_CONTENT",
            "security training terms require controlled teaching context",
            status_code=502,
            details={"softRiskTerms": soft_matches},
        )

    _append_quality_flag(question, "包含安全训练关键词，已按受控教学语境放行")


def _normalize_similarity_text(value: Any) -> str:
    text = str(value or "").lower()
    return re.sub(r"[\s，。！？、；：,.!?;:'\"`~@#$%^&*()_\-+=\[\]{}<>/\\|]", "", text)


def check_question_similarity(new_stem: str, example_questions: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    normalized_new = _normalize_similarity_text(new_stem)
    if not normalized_new:
        return None
    for item in example_questions:
        normalized_example = _normalize_similarity_text(item.get("stem"))
        if not normalized_example:
            continue
        ratio = SequenceMatcher(None, normalized_new, normalized_example).ratio()
        if ratio > 0.85:
            return {"exampleQuestionId": item.get("exampleQuestionId"), "similarity": round(ratio, 4)}
    return None


def _check_answer_similarity(question: dict[str, Any], example_questions: list[dict[str, Any]]) -> None:
    normalized_answer = _normalize_similarity_text(question.get("standardAnswer"))
    if not normalized_answer:
        return
    for item in example_questions:
        normalized_example = _normalize_similarity_text(item.get("standardAnswer"))
        if not normalized_example:
            continue
        ratio = SequenceMatcher(None, normalized_answer, normalized_example).ratio()
        if ratio > 0.9:
            _append_quality_flag(question, "参考答案与规范题目较相似，已保留来源标识供复核")
            return


def _walk_values(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_values(child)


def _extract_dify_example_sources(metadata: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    ids: list[str] = []
    snippets: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in _walk_values(metadata):
        if not isinstance(item, dict):
            continue
        candidate_ids: list[str] = []
        for key in ("exampleQuestionId", "example_question_id"):
            value = item.get(key)
            if value:
                candidate_ids.append(str(value).strip())
        for key in ("sourceExampleQuestionIds", "source_example_question_ids"):
            value = item.get(key)
            if isinstance(value, list):
                candidate_ids.extend(str(part).strip() for part in value if str(part).strip())
        nested_metadata = item.get("metadata")
        if isinstance(nested_metadata, dict):
            for key in ("exampleQuestionId", "example_question_id"):
                value = nested_metadata.get(key)
                if value:
                    candidate_ids.append(str(value).strip())
        snippet = (
            item.get("content")
            or item.get("text")
            or item.get("snippet")
            or item.get("segment")
            or item.get("document_content")
            or item.get("page_content")
        )
        for example_id in candidate_ids:
            if not example_id:
                continue
            if example_id not in seen_ids:
                seen_ids.add(example_id)
                ids.append(example_id)
            if snippet:
                snippets.append({"exampleQuestionId": example_id, "snippet": str(snippet)[:1000]})
    return ids, snippets[:10]


def _check_snippet_similarity(new_stem: str, snippets: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    normalized_new = _normalize_similarity_text(new_stem)
    if not normalized_new:
        return None
    for item in snippets:
        normalized_snippet = _normalize_similarity_text(item.get("snippet"))
        if not normalized_snippet:
            continue
        ratio = SequenceMatcher(None, normalized_new, normalized_snippet).ratio()
        if ratio > 0.85:
            return {"exampleQuestionId": item.get("exampleQuestionId"), "similarity": round(ratio, 4)}
    return None


def _normalize_llm_payload(raw: dict[str, Any]) -> dict[str, Any]:
    validation_hints = raw.get("validationHints") or raw.get("validation_hints") or {}
    if isinstance(validation_hints, list):
        validation_hints = {
            "keywords": [str(item).strip() for item in validation_hints if str(item).strip()],
            "minLength": 10,
        }
    rubric = _normalize_grading_rubric(raw.get("gradingRubric") or raw.get("grading_rubric"))
    quality_score_raw = raw.get("qualityScore") if "qualityScore" in raw else raw.get("quality_score")
    return {
        "title": str(raw.get("title") or "").strip(),
        "stem": str(raw.get("stem") or "").strip(),
        "questionType": str(raw.get("questionType") or raw.get("question_type") or "").strip().upper(),
        "difficulty": _to_int(raw.get("difficulty")),
        "dimension": str(raw.get("dimension") or "").strip(),
        "knowledgeTags": [str(tag).strip() for tag in (raw.get("knowledgeTags") or raw.get("knowledge_tags") or []) if str(tag).strip()],
        "standardAnswer": str(raw.get("standardAnswer") or raw.get("standard_answer") or "").strip(),
        "explanation": str(raw.get("explanation") or "").strip(),
        "sourceKnowledgeUnitIds": [
            str(item).strip()
            for item in (raw.get("sourceKnowledgeUnitIds") or raw.get("source_knowledge_unit_ids") or [])
            if str(item).strip()
        ],
        "sourceExampleQuestionIds": [
            str(item).strip()
            for item in (raw.get("sourceExampleQuestionIds") or raw.get("source_example_question_ids") or [])
            if str(item).strip()
        ],
        "validationHints": validation_hints,
        "options": raw.get("options"),
        "correctOption": str(raw.get("correctOption") or raw.get("correct_option") or "").strip().upper() or None,
        "teachingObjective": str(raw.get("teachingObjective") or raw.get("teaching_objective") or "").strip(),
        "expectedSkill": str(raw.get("expectedSkill") or raw.get("expected_skill") or "").strip(),
        "difficultyReason": str(raw.get("difficultyReason") or raw.get("difficulty_reason") or "").strip(),
        "commonMistakes": _normalize_string_list(raw.get("commonMistakes") or raw.get("common_mistakes")),
        "gradingRubric": rubric,
        "qualityScore": _to_int(quality_score_raw),
        "qualitySummary": str(raw.get("qualitySummary") or raw.get("quality_summary") or "").strip(),
        "qualityFlags": _normalize_string_list(raw.get("qualityFlags") or raw.get("quality_flags")),
    }


def validate_generated_question(
    raw: dict[str, Any],
    req: dict[str, Any],
    knowledge_units: list[dict[str, Any]],
    example_questions: Optional[list[dict[str, Any]]] = None,
    rag_context: Optional[dict[str, Any]] = None,
    dify_metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    example_questions = example_questions or []
    rag_context = rag_context or _build_rag_context(req, example_questions)
    dify_source_ids, dify_snippets = _extract_dify_example_sources(dify_metadata or {})
    if dify_source_ids:
        rag_context["difySourceExampleQuestionIds"] = dify_source_ids
    if dify_snippets:
        rag_context["difyRetrievedExampleSnippets"] = dify_snippets
    raw_quality_flags = raw.get("qualityFlags") if "qualityFlags" in raw else raw.get("quality_flags")
    if raw_quality_flags is not None and not isinstance(raw_quality_flags, list):
        raise QuestionGenerationError("INVALID_GENERATED_QUESTION", "qualityFlags must be an array", status_code=502)
    raw_source_examples = raw.get("sourceExampleQuestionIds") if "sourceExampleQuestionIds" in raw else raw.get("source_example_question_ids")
    if raw_source_examples is not None and not isinstance(raw_source_examples, list):
        raise QuestionGenerationError("INVALID_GENERATED_QUESTION", "sourceExampleQuestionIds must be an array", status_code=502)

    question = _normalize_llm_payload(raw)

    for field in (
        "title",
        "stem",
        "questionType",
        "difficulty",
        "dimension",
        "knowledgeTags",
        "standardAnswer",
        "explanation",
        "sourceKnowledgeUnitIds",
    ):
        if not question.get(field):
            raise QuestionGenerationError(
                "INVALID_GENERATED_QUESTION",
                f"missing required field: {field}",
                status_code=502,
            )

    default_quality = _default_quality_fields(question, req, knowledge_units)
    for field in ("teachingObjective", "expectedSkill", "difficultyReason", "qualitySummary"):
        if not question.get(field):
            question[field] = default_quality[field]
    if not question.get("commonMistakes"):
        question["commonMistakes"] = default_quality["commonMistakes"]
    if not question.get("gradingRubric"):
        question["gradingRubric"] = default_quality["gradingRubric"]
    if question.get("qualityScore") is None:
        question["qualityScore"] = default_quality["qualityScore"]
    if question.get("qualityFlags") is None:
        question["qualityFlags"] = default_quality["qualityFlags"]

    for field in ("teachingObjective", "expectedSkill"):
        if not question.get(field):
            raise QuestionGenerationError("INVALID_GENERATED_QUESTION", f"{field} is required", status_code=502)
    if not isinstance(question["commonMistakes"], list):
        raise QuestionGenerationError("INVALID_GENERATED_QUESTION", "commonMistakes must be an array", status_code=502)
    if not isinstance(question["gradingRubric"], list) or len(question["gradingRubric"]) < 2:
        raise QuestionGenerationError("INVALID_GENERATED_QUESTION", "gradingRubric requires at least 2 items", status_code=502)
    rubric_total = sum(int(item.get("score") or 0) for item in question["gradingRubric"])
    if rubric_total <= 0:
        raise QuestionGenerationError("INVALID_GENERATED_QUESTION", "gradingRubric score total must be greater than 0", status_code=502)
    if rubric_total != 100:
        normalized: list[dict[str, Any]] = []
        running_total = 0
        for index, item in enumerate(question["gradingRubric"]):
            if index == len(question["gradingRubric"]) - 1:
                score = max(0, 100 - running_total)
            else:
                score = max(0, round((int(item.get("score") or 0) / rubric_total) * 100))
                running_total += score
            normalized.append({"point": item["point"], "score": score})
        score_delta = 100 - sum(item["score"] for item in normalized)
        if normalized:
            normalized[-1]["score"] = max(0, normalized[-1]["score"] + score_delta)
        question["gradingRubric"] = normalized
    if question["qualityScore"] < 0 or question["qualityScore"] > 100:
        raise QuestionGenerationError("INVALID_GENERATED_QUESTION", "qualityScore must be between 0 and 100", status_code=502)
    if not isinstance(question["qualityFlags"], list):
        raise QuestionGenerationError("INVALID_GENERATED_QUESTION", "qualityFlags must be an array", status_code=502)

    if len(question["title"]) > 255:
        raise QuestionGenerationError("INVALID_GENERATED_QUESTION", "title is too long", status_code=502)
    if question["questionType"] not in ALLOWED_QUESTION_TYPES:
        raise QuestionGenerationError("INVALID_GENERATED_QUESTION", "questionType is invalid", status_code=502)
    if question["dimension"] not in ALLOWED_DIMENSIONS:
        raise QuestionGenerationError("INVALID_GENERATED_QUESTION", "dimension is invalid", status_code=502)
    if question["difficulty"] is None or question["difficulty"] < 1 or question["difficulty"] > 5:
        raise QuestionGenerationError("INVALID_GENERATED_QUESTION", "difficulty is invalid", status_code=502)

    valid_ids = {unit["knowledgeUnitId"] for unit in knowledge_units}
    unknown_ids = [item for item in question["sourceKnowledgeUnitIds"] if item not in valid_ids]
    if unknown_ids:
        raise QuestionGenerationError(
            "INVALID_GENERATED_QUESTION",
            "sourceKnowledgeUnitIds must come from retrieved knowledge units",
            status_code=502,
            details={"unknownSourceKnowledgeUnitIds": unknown_ids},
        )

    valid_example_ids = {item["exampleQuestionId"] for item in example_questions}
    local_standard_ids = {item["exampleQuestionId"] for item in list_standard_questions()}
    unknown_example_ids = [item for item in question["sourceExampleQuestionIds"] if item not in valid_example_ids]
    if unknown_example_ids:
        strict_validation = _to_bool(os.getenv("STRICT_SOURCE_EXAMPLE_VALIDATION"))
        if rag_context["ragMode"] == "local" or strict_validation:
            raise QuestionGenerationError(
                "INVALID_GENERATED_QUESTION",
                "sourceExampleQuestionIds must come from retrieved example questions",
                status_code=502,
                details={"unknownSourceExampleQuestionIds": unknown_example_ids},
            )
        local_known_unknown = [item for item in unknown_example_ids if item in local_standard_ids]
        dify_known_unknown = [item for item in unknown_example_ids if item in dify_source_ids]
        if len(local_known_unknown) == len(unknown_example_ids):
            rag_context["sourceValidationMode"] = "local_strict"
        elif len(dify_known_unknown) == len(unknown_example_ids):
            rag_context["sourceValidationMode"] = "dify_metadata"
        else:
            rag_context["sourceValidationMode"] = "warning_only"
            _append_quality_flag(question, "sourceExampleQuestionIds 未能在本地规范题库中验证")
    elif question["sourceExampleQuestionIds"]:
        rag_context["sourceValidationMode"] = "local_strict"
    if example_questions and not question["sourceExampleQuestionIds"]:
        _append_quality_flag(question, "未返回规范题目来源标识")
    if not example_questions:
        rag_context["exampleQuestionSimilarityChecked"] = bool(dify_snippets)
        if not question["sourceExampleQuestionIds"]:
            question["sourceExampleQuestionIds"] = []

    duplicate_match = check_question_similarity(question["stem"], example_questions)
    if duplicate_match:
        raise QuestionGenerationError(
            "DUPLICATE_EXAMPLE_QUESTION",
            "generated question is too similar to a standard example",
            status_code=502,
            details=duplicate_match,
        )
    snippet_duplicate_match = _check_snippet_similarity(question["stem"], dify_snippets)
    if snippet_duplicate_match:
        raise QuestionGenerationError(
            "DUPLICATE_EXAMPLE_QUESTION",
            "generated question is too similar to a retrieved example snippet",
            status_code=502,
            details=snippet_duplicate_match,
        )
    if not example_questions and rag_context["ragMode"] == "dify" and not dify_snippets:
        _append_quality_flag(question, "无法执行完整范例题相似度校验，原因：Dify 未返回范例题全文")
    _check_answer_similarity(question, example_questions)

    safe_texts = [
        question["title"],
        question["stem"],
        question["standardAnswer"],
        question["explanation"],
        question["teachingObjective"],
        question["expectedSkill"],
        question["difficultyReason"],
        question["qualitySummary"],
        *question["commonMistakes"],
        *question["qualityFlags"],
        *[item["point"] for item in question["gradingRubric"]],
    ]
    if question.get("correctOption"):
        safe_texts.append(question["correctOption"])
    if isinstance(question.get("options"), list):
        safe_texts.extend([str(item) for item in question["options"]])

    _validate_training_safety(question, safe_texts)

    if question["questionType"] != req["question_type"]:
        raise QuestionGenerationError(
            "INVALID_GENERATED_QUESTION",
            "generated questionType does not match request",
            status_code=502,
        )

    if question["questionType"] == "MCQ":
        options = question.get("options")
        if not isinstance(options, list) or len(options) < 4:
            raise QuestionGenerationError("INVALID_GENERATED_QUESTION", "MCQ requires at least 4 options", status_code=502)
        if question.get("correctOption") not in {"A", "B", "C", "D"}:
            raise QuestionGenerationError("INVALID_GENERATED_QUESTION", "MCQ requires correctOption A-D", status_code=502)
    else:
        question["options"] = None
        question["correctOption"] = None

    validation_hints = question.get("validationHints")
    if not isinstance(validation_hints, dict):
        raise QuestionGenerationError("INVALID_GENERATED_QUESTION", "validationHints must be an object", status_code=502)
    validation_hints.setdefault("keywords", question["knowledgeTags"][:2] or req["knowledge_tags"][:2])
    validation_hints.setdefault("minLength", 10 if question["questionType"] != "MCQ" else 1)
    question["validationHints"] = validation_hints
    return question


def _pick_knowledge_point_id(knowledge_units: list[dict[str, Any]]) -> Optional[int]:
    for unit in knowledge_units:
        value = _to_int(unit.get("knowledgePointId"))
        if value is not None:
            return value
    return None


def _pick_module_id(req: dict[str, Any], knowledge_units: list[dict[str, Any]]) -> Optional[int]:
    if req["module_id"] is not None:
        return req["module_id"]
    for unit in knowledge_units:
        value = _to_int(unit.get("moduleId"))
        if value is not None:
            return value
    return None


def _retrieve_standard_examples(req: dict[str, Any]) -> list[dict[str, Any]]:
    if _get_dify_rag_mode() == "dify":
        return []
    return retrieve_example_questions(
        knowledge_tags=req["knowledge_tags"],
        dimension=req["dimension"],
        question_type=req["question_type"],
        difficulty=req["difficulty"],
        module_id=req["module_id"],
        course_id=req["course_id"],
        top_k=3,
    )


def _example_question_summary(example_questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "exampleQuestionId": item["exampleQuestionId"],
            "questionType": item["questionType"],
            "difficulty": item["difficulty"],
            "knowledgeTags": item["knowledgeTags"],
            "source": item["source"],
            "sourceDocument": item["sourceDocument"],
            "qualityLevel": item["qualityLevel"],
            "reviewed": item["reviewed"],
        }
        for item in example_questions
    ]


def _build_session_records(
    req: dict[str, Any],
    knowledge_units: list[dict[str, Any]],
    question: dict[str, Any],
    generator: str,
    example_questions: list[dict[str, Any]],
    rag_context: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    profile = get_latest_student_profile(req["user_id"])
    recommendation = _extract_recommendation_context(profile, req)
    training_context = {
        "source": req["source"],
        "dimension": req["dimension"],
        "difficulty": req["difficulty"],
        "questionType": req["question_type"],
        "recommendationId": req["recommendation_id"],
        "knowledgeTags": req["knowledge_tags"],
        "knowledgeUnitIds": question["sourceKnowledgeUnitIds"],
        "knowledgeUnitCount": len(knowledge_units),
        "ragMode": rag_context["ragMode"],
        "retrievalQuery": rag_context["retrievalQuery"],
        "retrievalMetadata": rag_context["retrievalMetadata"],
        "localExampleQuestionIds": rag_context.get("localExampleQuestionIds") or [],
        "difySourceExampleQuestionIds": rag_context.get("difySourceExampleQuestionIds") or [],
        "sourceValidationMode": rag_context.get("sourceValidationMode") or "warning_only",
        "exampleQuestionSimilarityChecked": bool(rag_context.get("exampleQuestionSimilarityChecked")),
        "difyRetrievedExampleSnippets": rag_context.get("difyRetrievedExampleSnippets") or [],
        "exampleQuestionIds": [item["exampleQuestionId"] for item in example_questions],
        "sourceExampleQuestionIds": question.get("sourceExampleQuestionIds") or [],
        "exampleQuestions": _example_question_summary(example_questions),
        "generator": generator,
        "sourceSnapshotId": (profile or {}).get("snapshot_id"),
    }
    diagnose_result = {
        "user_id": req["user_id"],
        "profile_snapshot_id": training_context["sourceSnapshotId"],
        "weak_dimensions": [req["dimension"]],
        "recent_focus": recommendation.get("reason"),
        "weak_knowledge_points": [],
        "generation_constraints": {
            "difficulty": req["difficulty"],
            "question_type": req["question_type"],
            "question_count": 1,
        },
    }
    return diagnose_result, training_context


def persist_generated_question(
    req: dict[str, Any],
    knowledge_units: list[dict[str, Any]],
    question: dict[str, Any],
    generator: str,
    example_questions: list[dict[str, Any]],
    rag_context: dict[str, Any],
) -> dict[str, Any]:
    diagnose_result, training_context = _build_session_records(req, knowledge_units, question, generator, example_questions, rag_context)
    session = create_training_session(
        user_id=req["user_id"],
        class_id=None,
        course_id=req["course_id"],
        profile_snapshot_id=training_context.get("sourceSnapshotId"),
        diagnose_result=diagnose_result,
        training_context=training_context,
    )

    module_id = _pick_module_id(req, knowledge_units)
    knowledge_point_id = _pick_knowledge_point_id(knowledge_units)
    generated_id = f"gq-{uuid4()}"
    row = {
        "question_id": generated_id,
        "question_type": question["questionType"],
        "knowledge_point_id": knowledge_point_id,
        "module_id": module_id,
        "task_id": None,
        "difficulty": str(question["difficulty"]),
        "title": question["title"],
        "stem": question["stem"],
        "options": question.get("options"),
        "answer": question["correctOption"] if question["questionType"] == "MCQ" else question["standardAnswer"],
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
    }
    saved = save_generated_questions(
        training_session_id=session["training_session_id"],
        questions=[row],
        source_model=generator,
    )
    if not saved:
        raise QuestionGenerationError("SAVE_FAILED", "failed to persist generated question", status_code=500)
    generated_question = get_generated_question(saved[0]["generated_question_id"])
    if not generated_question:
        raise QuestionGenerationError("SAVE_FAILED", "generated question not found after save", status_code=500)
    return {
        "training_session_id": session["training_session_id"],
        "generated_question": generated_question,
        "source_snapshot_id": training_context.get("sourceSnapshotId"),
    }


async def generate_single_training_question(data: dict[str, Any]) -> dict[str, Any]:
    req = _normalize_request(data)
    profile = get_latest_student_profile(req["user_id"])
    recommendation = _extract_recommendation_context(profile, req)
    knowledge_units = retrieve_knowledge_units(req, top_k=5)
    example_questions = _retrieve_standard_examples(req)
    rag_context = _build_rag_context(req, example_questions)
    llm_result = await generate_question_with_llm(req, knowledge_units, recommendation, example_questions, rag_context)
    generator = llm_result["generator"]
    question = validate_generated_question(
        llm_result["payload"],
        req,
        knowledge_units,
        example_questions,
        rag_context,
        llm_result.get("difyMetadata") or {},
    )
    saved = persist_generated_question(req, knowledge_units, question, generator, example_questions, rag_context)
    generated_question = saved["generated_question"]
    return {
        "success": True,
        "generatedQuestionId": generated_question["generated_question_id"],
        "question": {
            "title": question["title"],
            "stem": question["stem"],
            "questionType": question["questionType"],
            "difficulty": question["difficulty"],
            "dimension": question["dimension"],
            "knowledgeTags": question["knowledgeTags"],
            "standardAnswer": question["standardAnswer"],
            "explanation": question["explanation"],
            "sourceKnowledgeUnitIds": question["sourceKnowledgeUnitIds"],
            "sourceExampleQuestionIds": question["sourceExampleQuestionIds"],
            "validationHints": question["validationHints"],
            "teachingObjective": question["teachingObjective"],
            "expectedSkill": question["expectedSkill"],
            "difficultyReason": question["difficultyReason"],
            "commonMistakes": question["commonMistakes"],
            "gradingRubric": question["gradingRubric"],
            "qualityScore": question["qualityScore"],
            "qualitySummary": question["qualitySummary"],
            "qualityFlags": question["qualityFlags"],
            "options": question.get("options"),
            "correctOption": question.get("correctOption"),
        },
        "metadata": {
            "userId": req["user_id"],
            "moduleId": req["module_id"],
            "recommendationId": req["recommendation_id"],
            "generator": generator,
            "knowledgeUnitCount": len(knowledge_units),
            "ragMode": rag_context["ragMode"],
            "sourceValidationMode": rag_context.get("sourceValidationMode"),
            "trainingSessionId": saved["training_session_id"],
            "sourceSnapshotId": saved["source_snapshot_id"],
        },
    }
