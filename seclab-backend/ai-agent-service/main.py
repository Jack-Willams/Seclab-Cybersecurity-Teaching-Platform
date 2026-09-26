"""
SecLab AI Agent Service
职责：
  1. 处理前端的聊天请求并以 SSE 流式返回：配置 LLM_API_KEY 时直连模型
     （见 chat_agent_service），否则转发至 Dify Agent
  2. 暴露 Docker 工具 HTTP API，供助手本地调用或 Dify 通过外部 API 工具调用
"""
import json
import os
import base64
import hashlib
import hmac
import time
import httpx
from datetime import datetime, date
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Security, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field
from typing import Optional, Any

from config import DIFY_API_URL, DIFY_API_KEY, CORS_ORIGINS, SERVICE_HOST, SERVICE_PORT
import asyncio
import docker_tools
import llm_provider
from chat_agent_service import stream_assistant_reply
from llm_provider import direct_llm_enabled
import operation_env
import operation_session_repository as operation_session_repo
from ai_repository import ensure_ai_schema
from ai_repository import get_or_create_conversation, save_ai_message, save_context_injection, save_tool_calls
from class_profile_repository import (
    get_latest_class_profile,
    list_class_profile_students,
    rebuild_class_profile,
)
from container_command_repository import ensure_container_command_schema, save_container_command_event
from container_file_repository import ensure_container_file_schema, save_container_file_event
from database import get_connection
from error_repository import ensure_error_schema, save_error_event
from event_repository import ensure_schema as ensure_learning_event_schema
from event_repository import list_learning_events, save_learning_event
from lab_repository import ensure_lab_schema, start_lab_session as repo_start_lab_session
from lab_repository import stop_lab_session as repo_stop_lab_session
from lab_repository import submit_flag as repo_submit_flag
from knowledge_repository import list_knowledge_units
from profile_dashboard_repository import get_profile_dashboard as repo_get_profile_dashboard
from profile_repository import ensure_profile_schema, get_latest_student_profile, rebuild_student_profile
from question_repository import ensure_question_schema, save_question_submission
from scoreboard_repository import get_scoreboard as repo_get_scoreboard
from single_question_generation_service import (
    QuestionGenerationError,
    generate_single_training_question,
)
from standard_question_repository import list_standard_questions, to_jsonable as standard_questions_to_jsonable
from training_diagnosis_service import diagnose_training_need
from training_generation_service import generate_personalized_questions
from training_submission_service import GeneratedQuestionSubmissionError, submit_generated_question_answer
from training_session_service import (
    TrainingSessionServiceError,
    generate_training_question_set,
    get_training_session_summary,
)
from training_repository import (
    ensure_training_schema,
    get_generated_question,
    get_training_session,
    list_generated_questions,
    list_user_training_sessions,
    save_generated_question_attempt,
)
from teacher_repository import (
    get_student_profile_for_teacher,
    list_class_students as repo_list_teacher_class_students,
    list_generated_questions_for_teacher,
    list_teacher_classes,
    read_teacher_dashboard,
)


class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"

# 靶机事件内存存储（生产环境建议替换为 Redis/DB）
_lab_events: list[dict] = []
_LAB_EVENT_CACHE_LIMIT = 500
_LAB_EVENT_FIELDS = (
    "event_id",
    "event_type",
    "event_time",
    "user_id",
    "class_id",
    "course_id",
    "module_id",
    "task_id",
    "question_id",
    "lab_session_id",
    "source",
    "container_name",
    "flag_text",
    "score",
    "is_correct",
    "command",
    "output_digest",
    "file_path",
    "action",
    "error_signature",
    "error_category",
    "raw_excerpt",
    "severity",
    "extra",
)


def _isoformat_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat() + ("Z" if value.tzinfo is None else "")
    return value


def _normalize_lab_feed_event(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload_json")
    payload = payload if isinstance(payload, dict) else {}

    merged: dict[str, Any] = {}
    if payload:
        merged.update(payload)
    merged.update(event)

    normalized: dict[str, Any] = {}
    for field in _LAB_EVENT_FIELDS:
        value = merged.get(field)
        if field == "extra" and not isinstance(value, dict):
            value = {}
        normalized[field] = _isoformat_value(value)

    if not normalized.get("event_id"):
        normalized["event_id"] = str(merged.get("id") or merged.get("request_id") or f"evt-{datetime.utcnow().timestamp()}")
    normalized["event_type"] = str(
        normalized.get("event_type")
        or merged.get("type")
        or payload.get("event_type")
        or ""
    ).strip().upper()
    normalized["event_time"] = str(
        normalized.get("event_time")
        or merged.get("timestamp")
        or merged.get("received_at")
        or ""
    )
    normalized["source"] = str(normalized.get("source") or merged.get("source") or "ai-agent-service")
    normalized["extra"] = normalized.get("extra") if isinstance(normalized.get("extra"), dict) else {}

    for key, value in payload.items():
        if key not in normalized:
            normalized[key] = _isoformat_value(value)

    return normalized


def _remember_lab_event(event: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_lab_feed_event(event)
    event_id = str(normalized.get("event_id") or "").strip()
    if event_id:
        for index, existing in enumerate(list(_lab_events)):
            if str(existing.get("event_id") or "") == event_id:
                _lab_events.pop(index)
                break
    _lab_events.append(normalized)
    overflow = len(_lab_events) - _LAB_EVENT_CACHE_LIMIT
    if overflow > 0:
        del _lab_events[:overflow]
    return normalized


def _normalize_lab_event_filter(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return _normalize_event_type(raw)
    except Exception:
        return raw.upper()

# 内部工具 API Key（供 Dify 调用 Docker 工具时校验）
# 留空 = 不校验（推荐内网/本地开发时使用）
TOOL_API_KEY = os.getenv("TOOL_API_KEY", "")

# 支持两种传递方式：
#   1. 自定义头  X-SecLab-Token: <key>
#   2. 标准 Bearer  Authorization: Bearer <key>  （Dify 默认方式）
_api_key_header = APIKeyHeader(name="X-SecLab-Token", auto_error=False)
_auth_header    = APIKeyHeader(name="Authorization",   auto_error=False)


async def verify_tool_key(
    x_token: Optional[str] = Security(_api_key_header),
    auth:    Optional[str] = Security(_auth_header),
) -> None:
    """当 TOOL_API_KEY 为空时直接放行；否则校验任意一种 Key 格式"""
    if not TOOL_API_KEY:
        return          # 未配置 → 不校验（内网友好模式）
    bearer = auth.replace("Bearer ", "").strip() if auth else None
    if x_token != TOOL_API_KEY and bearer != TOOL_API_KEY:
        raise HTTPException(status_code=403, detail="无效的工具 API Key")

app = FastAPI(
    title="SecLab AI Agent Service",
    description="Dify Agent 代理 + Docker 靶场工具 API",
    version="1.0.0",
    default_response_class=UTF8JSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
#  请求 / 响应模型
# ─────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = ""
    user: Optional[str] = "student"
    inputs: Optional[dict] = {}


class LLMProxyRequest(BaseModel):
    messages: list[dict[str, Any]]
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = True


class ExecRequest(BaseModel):
    command: str


class LabEventRequest(BaseModel):
    """靶机发送的事件数据模型"""
    type: str                          # lab_opened / hint_request / timer_milestone / timer_expired / progress_update
    user_id: Optional[int] = None
    class_id: Optional[int] = None
    course_id: Optional[int] = None
    module_id: Optional[int] = None
    task_id: Optional[int] = None
    question_id: Optional[int] = None
    lab_session_id: Optional[str] = None
    container: Optional[str] = ""     # 容器名称，如 sqli-lab-web-1
    level: Optional[int] = None       # 关卡编号
    levelTitle: Optional[str] = ""    # 关卡标题
    timerSeconds: Optional[int] = None # 总倒计时秒数（lab_opened 时）
    remainingSeconds: Optional[int] = None  # 剩余秒数
    milestone: Optional[str] = ""     # 时间里程碑，如 "50%" / "10%"
    prompt: Optional[str] = ""        # 提示请求的 prompt（hint_request 时）
    timestamp: Optional[str] = ""     # ISO 时间戳
    extra: Optional[Any] = None       # 扩展字段


class QuestionSubmitRequest(BaseModel):
    user_id: Optional[int] = None
    class_id: Optional[int] = None
    course_id: Optional[int] = None
    module_id: Optional[int] = None
    task_id: Optional[int] = None
    question_id: Any
    question_uid: Optional[str] = None
    question_type: str
    answer: Any
    cost_time: Optional[int] = None
    request_id: Optional[str] = None
    lab_session_id: Optional[str] = None
    question_score: Optional[float] = None
    standard_answer: Optional[Any] = None
    question_snapshot: Optional[dict[str, Any]] = None
    training_session_id: Optional[str] = None
    question_source: Optional[str] = "course_question"
    knowledge_point_id: Optional[int] = None


class TrainingDiagnoseRequest(BaseModel):
    user_id: int
    class_id: Optional[int] = None
    course_id: Optional[int] = None
    top_k: Optional[int] = 3
    question_count: Optional[int] = 5


class TrainingGenerateRequest(BaseModel):
    user_id: int
    class_id: Optional[int] = None
    course_id: Optional[int] = None
    profile_snapshot_id: Optional[str] = None
    dimension_scores: Optional[dict[str, Any]] = None
    weak_dimensions: list[str] = Field(default_factory=list)
    weak_knowledge_points: list[dict[str, Any]] = Field(default_factory=list)
    recent_focus: Optional[str] = None
    tags: list[Any] = Field(default_factory=list)
    recent_evidence: Optional[dict[str, Any]] = None
    question_types: list[str] = Field(default_factory=lambda: ["single_choice", "fill_blank", "short_answer"])
    difficulty: Optional[str] = "medium"
    question_count: Optional[int] = 5
    course_context: list[dict[str, Any]] = Field(default_factory=list)


class TrainingGenerateSingleQuestionRequest(BaseModel):
    userId: int
    dimension: str
    recommendationId: Optional[str] = None
    moduleId: Optional[int] = None
    courseId: Optional[int] = None
    knowledgeTags: list[str] = Field(default_factory=list)
    difficulty: int
    questionType: str
    count: int = 1
    source: Optional[str] = "student_profile_snapshot"


class TrainingGenerateQuestionSetRequest(BaseModel):
    userId: int
    dimension: str
    recommendationId: Optional[str] = None
    moduleId: Optional[int] = None
    courseId: Optional[int] = None
    knowledgeTags: list[str] = Field(default_factory=list)
    difficulty: int
    questionType: str
    count: Optional[int] = 7
    source: Optional[str] = "student_profile_snapshot"


class TrainingSubmitRequest(BaseModel):
    user_id: int
    class_id: Optional[int] = None
    course_id: Optional[int] = None
    module_id: Optional[int] = None
    task_id: Optional[int] = None
    training_session_id: str
    question_id: str
    question_uid: Optional[str] = None
    question_type: Optional[str] = None
    answer: Any
    cost_time: Optional[int] = None
    request_id: Optional[str] = None
    knowledge_point_id: Optional[int] = None
    question_score: Optional[float] = 10
    auto_rebuild: bool = True


class GeneratedQuestionSubmitRequest(BaseModel):
    userId: int
    answer: str
    source: Optional[str] = "user_profile_recommendation"


class LabSessionStartRequest(BaseModel):
    user_id: Optional[int] = None
    class_id: Optional[int] = None
    course_id: Optional[int] = None
    module_id: Optional[int] = None
    task_id: Optional[int] = None
    session_id: Optional[str] = None
    container_name: Optional[str] = None
    container_id: Optional[str] = None
    target_url: Optional[str] = None
    request_id: Optional[str] = None


class FlagSubmitRequest(BaseModel):
    user_id: Optional[int] = None
    class_id: Optional[int] = None
    course_id: Optional[int] = None
    module_id: Optional[int] = None
    task_id: Optional[int] = None
    lab_session_id: Optional[str] = None
    container_name: Optional[str] = None
    flag_text: str
    request_id: Optional[str] = None
    score: Optional[float] = None


class ContainerCommandEventRequest(BaseModel):
    lab_session_id: Optional[str] = None
    user_id: Optional[int] = None
    class_id: Optional[int] = None
    course_id: Optional[int] = None
    module_id: Optional[int] = None
    task_id: Optional[int] = None
    container_name: Optional[str] = None
    command_id: Optional[str] = None
    command: str
    cwd: Optional[str] = None
    exit_code: Optional[int] = None
    duration_ms: Optional[int] = None
    output_digest: Optional[str] = None
    source: Optional[str] = "api"
    request_id: Optional[str] = None
    executed_at: Optional[str] = None


class ContainerFileEventRequest(BaseModel):
    lab_session_id: Optional[str] = None
    user_id: Optional[int] = None
    class_id: Optional[int] = None
    course_id: Optional[int] = None
    module_id: Optional[int] = None
    task_id: Optional[int] = None
    container_name: Optional[str] = None
    file_event_id: Optional[str] = None
    file_path: str
    file_ext: Optional[str] = None
    action: str
    size_before: Optional[int] = None
    size_after: Optional[int] = None
    sha256: Optional[str] = None
    is_key_file: Optional[bool] = None
    source: Optional[str] = "api"
    request_id: Optional[str] = None
    changed_at: Optional[str] = None


class ErrorEventRequest(BaseModel):
    lab_session_id: Optional[str] = None
    user_id: Optional[int] = None
    class_id: Optional[int] = None
    course_id: Optional[int] = None
    module_id: Optional[int] = None
    task_id: Optional[int] = None
    container_name: Optional[str] = None
    command_id: Optional[str] = None
    error_id: Optional[str] = None
    error_signature: Optional[str] = None
    error_category: Optional[str] = None
    raw_excerpt: Optional[str] = None
    severity: Optional[str] = None
    source: Optional[str] = "api"
    request_id: Optional[str] = None
    occurred_at: Optional[str] = None
    exit_code: Optional[int] = None


STUDENT_EVENT_TYPES = {
    "QUESTION_SUBMIT",
    "FLAG_SUBMIT",
    "LAB_START",
    "LAB_STOP",
    "COMMAND_EXEC",
    "FILE_CHANGE",
    "ERROR_EVENT",
    "AI_INTERACTION",
    "HINT_REQUEST",
    "TIMER_MILESTONE",
    "PROGRESS_UPDATE",
    "TIMER_EXPIRED",
}

EVENT_REQUIRED_FIELDS = {
    "QUESTION_SUBMIT": ("question_id", "question_type", "answer"),
    "FLAG_SUBMIT": ("flag_text",),
    "LAB_START": (),
    "LAB_STOP": ("lab_session_id",),
    "COMMAND_EXEC": ("command",),
    "FILE_CHANGE": ("file_path", "action"),
    "ERROR_EVENT": (),
    "AI_INTERACTION": (),
    "HINT_REQUEST": (),
    "TIMER_MILESTONE": (),
    "PROGRESS_UPDATE": (),
    "TIMER_EXPIRED": (),
}

LAB_EVENT_TYPE_MAP = {
    "lab_opened": "LAB_START",
    "hint_request": "HINT_REQUEST",
    "timer_milestone": "TIMER_MILESTONE",
    "timer_expired": "TIMER_EXPIRED",
    "progress_update": "PROGRESS_UPDATE",
}


class UnifiedStudentEventRequest(BaseModel):
    event_id: Optional[str] = None
    request_id: Optional[str] = None
    event_type: Optional[str] = None
    event_time: Optional[str] = None
    user_id: Optional[int] = None
    class_id: Optional[int] = None
    course_id: Optional[int] = None
    module_id: Optional[int] = None
    task_id: Optional[int] = None
    question_id: Optional[int] = None
    lab_session_id: Optional[str] = None
    source: Optional[str] = None
    question_type: Optional[str] = None
    answer: Optional[Any] = None
    standard_answer: Optional[Any] = None
    question_score: Optional[float] = None
    cost_time: Optional[int] = None
    is_correct: Optional[bool] = None
    session_id: Optional[str] = None
    target_url: Optional[str] = None
    container_id: Optional[str] = None
    container_name: Optional[str] = None
    flag_text: Optional[str] = None
    score: Optional[float] = None
    command_id: Optional[str] = None
    command: Optional[str] = None
    cwd: Optional[str] = None
    exit_code: Optional[int] = None
    duration_ms: Optional[int] = None
    output_digest: Optional[str] = None
    file_path: Optional[str] = None
    file_ext: Optional[str] = None
    action: Optional[str] = None
    size_before: Optional[int] = None
    size_after: Optional[int] = None
    sha256: Optional[str] = None
    is_key_file: Optional[bool] = None
    error_signature: Optional[str] = None
    error_category: Optional[str] = None
    raw_excerpt: Optional[str] = None
    severity: Optional[str] = None
    extra: Optional[dict[str, Any]] = None


class ExternalEventItem(UnifiedStudentEventRequest):
    event_type: str


class ExternalProfileRebuildRequest(BaseModel):
    user_id: Optional[int] = None
    class_id: Optional[int] = None
    rebuild_after_ingest: bool = False


class ExternalEventsIngestRequest(BaseModel):
    batch_id: Optional[str] = None
    source_system: Optional[str] = "external-agent"
    generated_at: Optional[str] = None
    user_context: dict[str, Any] = Field(default_factory=dict)
    events: list[ExternalEventItem] = Field(default_factory=list)
    ai_generated_questions: list[Any] = Field(default_factory=list)
    profile_rebuild: Optional[ExternalProfileRebuildRequest] = None


def _model_data(model: BaseModel, *, exclude_none: bool = False) -> dict[str, Any]:
    return model.model_dump(exclude_none=exclude_none)


def _repo_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, KeyError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


def _ensure_profile_source_schemas() -> None:
    ensure_question_schema()
    ensure_training_schema()
    ensure_lab_schema()
    ensure_container_command_schema()
    ensure_container_file_schema()
    ensure_error_schema()
    ensure_ai_schema()
    ensure_profile_schema()


def _merge_event_context(
    user_context: dict[str, Any],
    event: dict[str, Any],
    *,
    source_system: Optional[str],
    generated_at: Optional[str],
) -> dict[str, Any]:
    data = dict(user_context or {})
    for key, value in event.items():
        if value is not None:
            data[key] = value
        elif key not in data:
            data[key] = None
    data["source"] = data.get("source") or source_system or "external-agent"
    data["event_time"] = data.get("event_time") or generated_at
    data["request_id"] = data.get("request_id") or data.get("event_id")
    return data


def _has_value(value: Any) -> bool:
    return value is not None and value != ""


def _normalize_event_type(value: Any) -> str:
    event_type = str(value or "").strip()
    if not event_type:
        raise ValueError("event_type is required")
    normalized = event_type.replace("-", "_").upper()
    normalized = LAB_EVENT_TYPE_MAP.get(normalized.lower(), normalized)
    if normalized not in STUDENT_EVENT_TYPES:
        raise ValueError(f"unsupported event_type: {normalized}")
    return normalized


def _event_extra(data: dict[str, Any]) -> dict[str, Any]:
    extra = data.get("extra") or {}
    return extra if isinstance(extra, dict) else {}


def _promote_extra_fields(data: dict[str, Any]) -> dict[str, Any]:
    extra = _event_extra(data)
    for key in (
        "target_url",
        "level",
        "levelTitle",
        "timer_seconds",
        "remaining_seconds",
        "milestone",
        "prompt",
        "progress_percent",
        "status",
        "current_step",
        "note",
        "stop_reason",
        "duration_seconds",
        "completed",
    ):
        if data.get(key) is None and extra.get(key) is not None:
            data[key] = extra.get(key)
    return data


def _validate_event_payload(data: dict[str, Any]) -> None:
    event_type = data["event_type"]
    missing = [field for field in EVENT_REQUIRED_FIELDS.get(event_type, ()) if not _has_value(data.get(field))]
    if missing:
        raise ValueError(f"{event_type} missing required field(s): {', '.join(missing)}")


def _existing_learning_event(data: dict[str, Any]) -> Optional[dict[str, Any]]:
    event_id = data.get("event_id")
    request_id = data.get("request_id")
    if not event_id and not request_id:
        return None
    ensure_learning_event_schema()
    where = []
    params: dict[str, Any] = {}
    if event_id:
        where.append("event_id = %(event_id)s")
        params["event_id"] = str(event_id)
    if request_id:
        where.append("request_id = %(request_id)s")
        params["request_id"] = str(request_id)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, event_id, event_type, request_id, created_at
                FROM learning_event
                WHERE {' OR '.join(where)}
                ORDER BY id DESC
                LIMIT 1
                """,
                params,
            )
            row = cursor.fetchone()
    if row and isinstance(row.get("created_at"), datetime):
        row["created_at"] = row["created_at"].isoformat()
    return row


def _save_learning_only_event(data: dict[str, Any]) -> dict[str, Any]:
    return save_learning_event(data)


def _save_ai_interaction_event(data: dict[str, Any]) -> dict[str, Any]:
    ensure_ai_schema()
    extra = _event_extra(data)
    conversation_hint = (
        extra.get("conversation_id")
        or data.get("conversation_id")
        or data.get("lab_session_id")
        or data.get("request_id")
        or data.get("event_id")
        or ""
    )
    context = {
        "user_id": data.get("user_id"),
        "class_id": data.get("class_id"),
        "course_id": data.get("course_id"),
        "module_id": data.get("module_id"),
        "task_id": data.get("task_id"),
        "question_id": data.get("question_id"),
        "lab_session_id": data.get("lab_session_id"),
        "source": data.get("source") or "student-event",
    }
    conversation = get_or_create_conversation(
        request_conversation_id=str(conversation_hint or ""),
        context=context,
    )
    conversation_id = conversation["conversation_id"]

    saved_messages = []
    role = str(extra.get("message_role") or "user")
    message_text = extra.get("message_text") or data.get("prompt")
    assistant_reply = extra.get("assistant_reply")
    contains_context = bool(extra.get("used_context_injection"))
    hint_level = extra.get("hint_level")
    raw_payload = {"event": data}

    if message_text:
        saved_messages.append(save_ai_message(
            conversation_id=conversation_id,
            role=role,
            content=str(message_text),
            event_name=data["event_type"],
            hint_level=hint_level,
            contains_context=contains_context,
            raw_payload=raw_payload,
            message_id=data.get("event_id") if role == "user" else None,
        ))
    if assistant_reply:
        saved_messages.append(save_ai_message(
            conversation_id=conversation_id,
            role="assistant",
            content=str(assistant_reply),
            event_name=data["event_type"],
            hint_level=hint_level,
            contains_context=contains_context,
            raw_payload=raw_payload,
        ))

    context_row_id = None
    if contains_context or extra.get("context"):
        anchor_message = saved_messages[0]["message_id"] if saved_messages else ""
        if anchor_message:
            context_row_id = save_context_injection(
                conversation_id=conversation_id,
                message_id=anchor_message,
                context_type="ai_interaction",
                raw_context=extra.get("context") or extra,
            )

    tool_calls = extra.get("tool_calls")
    if not tool_calls and extra.get("tool_called"):
        tool_calls = [{
            "tool_name": extra.get("tool_called"),
            "status": extra.get("tool_status") or "unknown",
            "tool_input": extra.get("tool_input"),
            "tool_output": extra.get("tool_output"),
        }]
    if tool_calls and saved_messages:
        save_tool_calls(
            conversation_id=conversation_id,
            message_id=saved_messages[-1]["message_id"],
            tool_calls=tool_calls if isinstance(tool_calls, list) else [tool_calls],
        )

    learning_event = save_learning_event({
        **data,
        "conversation_id": conversation_id,
        "message_ids": [item["message_id"] for item in saved_messages],
        "context_injection_id": context_row_id,
    })
    return {
        "saved": True,
        "conversation_id": conversation_id,
        "messages": saved_messages,
        "context_injection_id": context_row_id,
        "learning_event": learning_event,
        "message": "ai interaction event saved",
    }


def dispatch_student_event(data: dict[str, Any]) -> dict[str, Any]:
    event_type = str(data.get("event_type") or "").strip().upper()
    if not event_type and data.get("type"):
        event_type = LAB_EVENT_TYPE_MAP.get(str(data.get("type")).strip().lower(), str(data.get("type")).strip().upper())
    event_type = _normalize_event_type(event_type)
    data["event_type"] = event_type
    data = _promote_extra_fields(data)
    data["source"] = data.get("source") or "ai-agent-service"
    data["request_id"] = data.get("request_id") or data.get("event_id")
    data["event_time"] = data.get("event_time") or data.get("timestamp") or datetime.utcnow().isoformat() + "Z"
    _validate_event_payload(data)

    existing = _existing_learning_event(data)
    if existing:
        return {
            "status": "duplicate",
            "event_type": event_type,
            "event_id": data.get("event_id"),
            "request_id": data.get("request_id"),
            "existing_learning_event": existing,
        }

    if event_type == "QUESTION_SUBMIT":
        data["submission_id"] = data.get("submission_id") or data.get("event_id")
        result = save_question_submission(data)
    elif event_type == "FLAG_SUBMIT":
        data["submission_id"] = data.get("submission_id") or data.get("event_id")
        result = repo_submit_flag(data)
    elif event_type == "LAB_START":
        data["session_id"] = data.get("session_id") or data.get("lab_session_id") or data.get("event_id")
        result = repo_start_lab_session(data)
    elif event_type == "LAB_STOP":
        session_id = data.get("session_id") or data.get("lab_session_id")
        if not session_id:
            raise ValueError("lab_session_id is required for LAB_STOP")
        result = repo_stop_lab_session(str(session_id), data)
    elif event_type == "COMMAND_EXEC":
        data["command_id"] = data.get("command_id") or data.get("event_id")
        data["executed_at"] = data.get("executed_at") or data.get("event_time")
        result = save_container_command_event(data)
    elif event_type == "FILE_CHANGE":
        data["file_event_id"] = data.get("file_event_id") or data.get("event_id")
        data["changed_at"] = data.get("changed_at") or data.get("event_time")
        result = save_container_file_event(data)
    elif event_type == "ERROR_EVENT":
        data["error_id"] = data.get("error_id") or data.get("event_id")
        data["occurred_at"] = data.get("occurred_at") or data.get("event_time")
        result = save_error_event(data)
    elif event_type == "AI_INTERACTION":
        result = _save_ai_interaction_event(data)
    else:
        result = _save_learning_only_event(data)

    return {
        "status": "saved",
        "event_type": event_type,
        "event_id": data.get("event_id"),
        "request_id": data.get("request_id"),
        "result": result,
    }


def _dispatch_profile_event(data: dict[str, Any], *, auto_rebuild: bool = False) -> dict[str, Any]:
    dispatch_result = dispatch_student_event(data)
    result = dispatch_result.get("result", dispatch_result)
    return _attach_profile_rebuild(result, data, auto_rebuild=auto_rebuild)


def _rebuild_profile_bridge(user_id: int, class_id: Optional[int] = None) -> dict[str, Any]:
    _ensure_profile_source_schemas()
    profile = rebuild_student_profile(int(user_id))
    rebuild_class_id = class_id if class_id is not None else profile.get("class_id")
    class_profile = rebuild_class_profile(int(rebuild_class_id)) if rebuild_class_id is not None else None
    return {
        "status": "ok",
        "profile": profile,
        "class_profile": class_profile,
        "latest_snapshot_id": profile.get("snapshot_id"),
    }


def _attach_profile_rebuild(
    result: dict[str, Any],
    data: dict[str, Any],
    *,
    auto_rebuild: bool = False,
) -> dict[str, Any]:
    if not auto_rebuild:
        return result

    user_id = data.get("user_id")
    if user_id is None:
        return {
            **result,
            "profile_rebuild_triggered": False,
            "latest_snapshot_id": None,
            "profile_rebuild": None,
        }

    rebuild_result = _rebuild_profile_bridge(int(user_id), data.get("class_id"))
    return {
        **result,
        "profile_rebuild_triggered": True,
        "latest_snapshot_id": rebuild_result.get("latest_snapshot_id"),
        "profile_rebuild": rebuild_result,
    }


def _training_question_payload(data: dict[str, Any]) -> dict[str, Any]:
    question_uid = str(data.get("question_uid") or data.get("question_id") or "").strip()
    generated = get_generated_question(question_uid)
    if not generated:
        raise KeyError("generated_question not found")

    standard_answer = generated.get("standard_answer") or generated.get("reference_answer")
    question_snapshot = {
        "question_id": generated.get("generated_question_id"),
        "question_type": generated.get("question_type"),
        "title": generated.get("title"),
        "stem": generated.get("stem"),
        "options": generated.get("options") or [],
        "answer": standard_answer,
        "reference_answer": generated.get("reference_answer"),
        "explanation": generated.get("explanation"),
        "scoring_rubric": generated.get("scoring_rubric") or [],
        "score": data.get("question_score") or 10,
    }
    return {
        **data,
        "question_id": generated.get("generated_question_id"),
        "question_uid": generated.get("generated_question_id"),
        "question_numeric_id": generated.get("question_numeric_id"),
        "question_type": data.get("question_type") or generated.get("question_type"),
        "question_source": "personalized_training",
        "training_session_id": data.get("training_session_id") or generated.get("training_session_id"),
        "knowledge_point_id": data.get("knowledge_point_id") or generated.get("knowledge_point_id"),
        "module_id": data.get("module_id") or generated.get("module_id"),
        "task_id": data.get("task_id") or generated.get("task_id"),
        "standard_answer": data.get("standard_answer") if data.get("standard_answer") is not None else standard_answer,
        "question_score": data.get("question_score") or 10,
        "question_snapshot": data.get("question_snapshot") or question_snapshot,
    }


def _submit_question_with_training_bridge(data: dict[str, Any], *, auto_rebuild: bool = False) -> dict[str, Any]:
    question_source = str(data.get("question_source") or "course_question")
    is_training = question_source == "personalized_training" or bool(data.get("training_session_id"))
    submit_data = _training_question_payload(data) if is_training else data
    submit_result = _dispatch_profile_event(
        {"event_type": "QUESTION_SUBMIT", **submit_data},
        auto_rebuild=auto_rebuild and submit_data.get("user_id") is not None,
    )

    if not is_training:
        return submit_result

    rebuild_result = submit_result.get("profile_rebuild")
    latest_snapshot_id = submit_result.get("latest_snapshot_id")

    attempt = save_generated_question_attempt(
        training_session_id=str(submit_data["training_session_id"]),
        generated_question_id=str(submit_data["question_uid"]),
        user_id=int(submit_data["user_id"]),
        answer=submit_data.get("answer"),
        is_correct=submit_result.get("is_correct"),
        score=float(submit_result.get("score") or 0),
        cost_time=submit_data.get("cost_time"),
        submission_id=submit_result.get("submission_id"),
        profile_rebuild_snapshot_id=latest_snapshot_id,
    )

    return {
        **submit_result,
        "attempt": attempt,
        "profile_rebuild_triggered": bool(submit_result.get("profile_rebuild_triggered")),
        "latest_snapshot_id": latest_snapshot_id,
        "profile_rebuild": rebuild_result,
    }


# ─────────────────────────────────────────
#  健康检查
# ─────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "SecLab AI Agent Service"}


# ─────────────────────────────────────────
#  靶机事件接收 API
# ─────────────────────────────────────────

@app.post("/api/lab/event")
async def receive_lab_event(event: LabEventRequest):
    """
    接收靶场发送的事件信号。
    支持的事件类型：
      - lab_opened       : 学生开启靶机（发送"开机"信号）
      - hint_request     : 学生主动请求 AI 提示
      - timer_milestone  : 沙漏倒计时达到里程碑（50% / 10%）
      - timer_expired    : 倒计时归零
      - progress_update  : 学生操作进度更新
    """
    record = event.dict()
    record["received_at"] = datetime.utcnow().isoformat() + "Z"

    saved_learning_event = None
    try:
        legacy_event_type = LAB_EVENT_TYPE_MAP.get(str(event.type or "").strip().lower(), str(event.type or "PROGRESS_UPDATE").upper())
        saved_learning_event = save_learning_event({
            **record,
            "event_type": legacy_event_type,
            "event_time": event.timestamp or record["received_at"],
            "container_name": event.container,
            "extra": {
                **(_event_extra(record)),
                "level": event.level,
                "levelTitle": event.levelTitle,
                "timer_seconds": event.timerSeconds,
                "remaining_seconds": event.remainingSeconds,
                "milestone": event.milestone,
                "prompt": event.prompt,
            },
            "source": "ai-agent-service",
        })
        _remember_lab_event({
            **record,
            "event_type": legacy_event_type,
            "event_time": event.timestamp or record["received_at"],
            "container_name": event.container,
            "source": "ai-agent-service",
        })
    except Exception as exc:
        record["learning_event_error"] = str(exc)
        _remember_lab_event({
            **record,
            "event_type": LAB_EVENT_TYPE_MAP.get(str(event.type or "").strip().lower(), str(event.type or "PROGRESS_UPDATE").upper()),
            "event_time": event.timestamp or record["received_at"],
            "container_name": event.container,
            "source": "ai-agent-service",
        })

    # 根据事件类型决定是否主动触发 Dify Agent
    auto_prompt = None

    if event.type == "lab_opened":
        # ── 自动拉取容器状态与最新日志，附加到通知消息 ──────────────
        container_name = event.container or "sqli-lab-web-1"

        status_info = docker_tools.get_container_status(container_name)
        status_text = ""
        if status_info.get("success") and isinstance(status_info.get("data"), dict):
            d = status_info["data"]
            status_text = (
                f"\n【容器状态】名称={d.get('name','-')} | "
                f"运行状态={d.get('status','-')} | "
                f"镜像={d.get('image','-')} | "
                f"启动时间={d.get('started_at','-')}"
            )

        log_info = docker_tools.get_container_logs(container_name, tail=30)
        log_text = ""
        if log_info.get("success") and log_info.get("logs"):
            log_text = f"\n【最近30行日志】\n{log_info['logs']}"
        elif not log_info.get("success"):
            log_text = f"\n【日志获取失败】{log_info.get('error','')}"

        # 同步记录到事件记录中
        record["docker_status"] = status_info
        record["docker_logs_preview"] = log_info.get("logs", "")[:2000]

        auto_prompt = (
            f"✅ 靶机启动通知：学生已开启容器【{container_name}】\n"
            f"正在挑战「{event.levelTitle}」（Level {event.level}），"
            f"倒计时 {event.timerSeconds} 秒。"
            f"{status_text}"
            f"{log_text}\n"
            f"请记录此开机事件。如果学生后续发出提示请求或倒计时结束，"
            f"请根据容器日志给出阶梯式中文提示（先给最小提示）。"
        )

    elif event.type == "timer_milestone":
        # ── 里程碑时自动拉取最新日志辅助判断进度 ──────────────────
        container_name = event.container or "sqli-lab-web-1"
        log_info = docker_tools.get_container_logs(container_name, tail=20)
        log_text = ""
        if log_info.get("success") and log_info.get("logs"):
            log_text = f"\n【最近20行日志】\n{log_info['logs']}"

        auto_prompt = (
            f"⏳ 倒计时里程碑 [{event.milestone}]：靶机【{container_name}】剩余 {event.remainingSeconds} 秒。\n"
            f"学生正在挑战「{event.levelTitle}」。"
            f"{log_text}\n"
            f"请根据上方日志分析学生当前进度，若学生明显卡住则给出最小提示（一句话）。"
        )

    elif event.type == "timer_expired":
        # ── 时间到时拉取完整日志 ────────────────────────────────────
        container_name = event.container or "sqli-lab-web-1"
        log_info = docker_tools.get_container_logs(container_name, tail=50)
        log_text = ""
        if log_info.get("success") and log_info.get("logs"):
            log_text = f"\n【最近50行日志】\n{log_info['logs']}"

        auto_prompt = (
            f"⌛ 倒计时归零！靶机【{container_name}】，"
            f"学生正在挑战「{event.levelTitle}」（Level {event.level}）。"
            f"{log_text}\n"
            f"请立即分析以上 Apache 日志，给出完整阶梯式提示（从最小提示到完整答案逐步展示，使用中文）。"
        )

    elif event.type == "hint_request" and event.prompt:
        # ── 手动提示请求：附加最新日志 ─────────────────────────────
        container_name = event.container or "sqli-lab-web-1"
        log_info = docker_tools.get_container_logs(container_name, tail=20)
        log_text = ""
        if log_info.get("success") and log_info.get("logs"):
            log_text = f"\n【最近20行日志】\n{log_info['logs']}"

        auto_prompt = f"{event.prompt}{log_text}"

    # 若需要自动触发，异步向 Dify 发送消息
    if auto_prompt:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(
                    f"{DIFY_API_URL}/chat-messages",
                    headers={
                        "Authorization": f"Bearer {DIFY_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": auto_prompt,
                        "response_mode": "blocking",
                        "conversation_id": "",
                        "user": f"lab-event-{event.container or 'unknown'}",
                        "inputs": {
                            "event_type": event.type,
                            "container": event.container or "",
                            "level": str(event.level or ""),
                        },
                    },
                )
        except Exception:
            pass  # 不阻塞靶机请求，静默失败

    return {
        "status": "ok",
        "event_type": event.type,
        "message": f"事件 [{event.type}] 已记录",
        "auto_triggered": auto_prompt is not None,
        "learning_event_saved": saved_learning_event is not None,
    }


@app.get("/api/lab/events")
async def get_lab_events(
    limit: int = Query(50, ge=1, le=200, description="返回最近 N 条事件"),
    event_type: Optional[str] = Query(None, description="按事件类型过滤"),
    _: None = Security(verify_tool_key),
):
    """查询靶机事件历史（供 Dify 工具或管理员调用）"""
    normalized_event_type = _normalize_lab_event_filter(event_type)
    try:
        result = list_learning_events(
            page=1,
            page_size=min(limit, 200),
            event_type=normalized_event_type,
        )
        events = [_normalize_lab_feed_event(row) for row in result.get("events", [])]
        for item in reversed(events):
            _remember_lab_event(item)
        return {
            "total": int(result.get("total", len(events))),
            "events": events,
        }
    except Exception:
        filtered = list(_lab_events)
        if normalized_event_type:
            filtered = [e for e in filtered if str(e.get("event_type") or "").upper() == normalized_event_type]
        return {
            "total": len(filtered),
            "events": filtered[-limit:][::-1],
        }


# ─────────────────────────────────────────
#  Dify 流式聊天代理
# ─────────────────────────────────────────

async def _save_single_student_event(event_type: str, req: UnifiedStudentEventRequest):
    try:
        data = _model_data(req)
        data["event_type"] = event_type
        result = dispatch_student_event(data)
        return _attach_profile_rebuild(result, data, auto_rebuild=True)
    except Exception as exc:
        raise _repo_error(exc)


@app.post("/api/events/question-submit")
async def event_question_submit(req: UnifiedStudentEventRequest):
    return await _save_single_student_event("QUESTION_SUBMIT", req)


@app.post("/api/events/flag-submit")
async def event_flag_submit(req: UnifiedStudentEventRequest):
    return await _save_single_student_event("FLAG_SUBMIT", req)


@app.post("/api/events/lab-start")
async def event_lab_start(req: UnifiedStudentEventRequest):
    return await _save_single_student_event("LAB_START", req)


@app.post("/api/events/lab-stop")
async def event_lab_stop(req: UnifiedStudentEventRequest):
    return await _save_single_student_event("LAB_STOP", req)


@app.post("/api/events/command-exec")
async def event_command_exec(req: UnifiedStudentEventRequest):
    return await _save_single_student_event("COMMAND_EXEC", req)


@app.post("/api/events/file-change")
async def event_file_change(req: UnifiedStudentEventRequest):
    return await _save_single_student_event("FILE_CHANGE", req)


@app.post("/api/events/error")
async def event_error(req: UnifiedStudentEventRequest):
    return await _save_single_student_event("ERROR_EVENT", req)


@app.post("/api/events/ai-interaction")
async def event_ai_interaction(req: UnifiedStudentEventRequest):
    return await _save_single_student_event("AI_INTERACTION", req)


@app.post("/api/events/hint-request")
async def event_hint_request(req: UnifiedStudentEventRequest):
    return await _save_single_student_event("HINT_REQUEST", req)


@app.post("/api/events/timer-milestone")
async def event_timer_milestone(req: UnifiedStudentEventRequest):
    return await _save_single_student_event("TIMER_MILESTONE", req)


@app.post("/api/events/progress-update")
async def event_progress_update(req: UnifiedStudentEventRequest):
    return await _save_single_student_event("PROGRESS_UPDATE", req)


@app.post("/api/events/timer-expired")
async def event_timer_expired(req: UnifiedStudentEventRequest):
    return await _save_single_student_event("TIMER_EXPIRED", req)


@app.post("/api/training/diagnose")
async def training_diagnose(req: TrainingDiagnoseRequest):
    try:
        return diagnose_training_need(_model_data(req))
    except Exception as exc:
        raise _repo_error(exc)


@app.post("/api/training/generate")
async def training_generate(req: TrainingGenerateRequest):
    try:
        return await generate_personalized_questions(_model_data(req))
    except Exception as exc:
        raise _repo_error(exc)


@app.post("/api/training/generate-question")
async def training_generate_question(req: TrainingGenerateSingleQuestionRequest):
    try:
        payload = _model_data(req)
        return await generate_single_training_question(
            {
                "user_id": payload.get("userId"),
                "dimension": payload.get("dimension"),
                "recommendation_id": payload.get("recommendationId"),
                "module_id": payload.get("moduleId"),
                "course_id": payload.get("courseId"),
                "knowledge_tags": payload.get("knowledgeTags"),
                "difficulty": payload.get("difficulty"),
                "question_type": payload.get("questionType"),
                "count": payload.get("count"),
                "source": payload.get("source"),
            }
        )
    except QuestionGenerationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail())
    except Exception as exc:
        raise _repo_error(exc)


@app.post("/api/training/generate-question-set")
async def training_generate_question_set(req: TrainingGenerateQuestionSetRequest):
    try:
        payload = _model_data(req)
        return await generate_training_question_set(
            {
                "user_id": payload.get("userId"),
                "dimension": payload.get("dimension"),
                "recommendation_id": payload.get("recommendationId"),
                "module_id": payload.get("moduleId"),
                "course_id": payload.get("courseId"),
                "knowledge_tags": payload.get("knowledgeTags"),
                "difficulty": payload.get("difficulty"),
                "question_type": payload.get("questionType"),
                "count": payload.get("count"),
                "source": payload.get("source"),
            }
        )
    except TrainingSessionServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail())
    except QuestionGenerationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail())
    except Exception as exc:
        raise _repo_error(exc)


@app.get("/api/training/session/{training_session_id}")
async def training_session(training_session_id: str):
    try:
        session = get_training_session(training_session_id)
        if not session:
            raise KeyError("training_session not found")
        return {
            "session": session,
            "questions": list_generated_questions(training_session_id),
        }
    except Exception as exc:
        raise _repo_error(exc)


@app.get("/api/training/session/{training_session_id}/summary")
async def training_session_summary(training_session_id: str, userId: Optional[int] = Query(None)):
    try:
        return get_training_session_summary(training_session_id, userId)
    except TrainingSessionServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail())
    except Exception as exc:
        raise _repo_error(exc)


@app.get("/api/training/questions/{training_session_id}")
async def training_questions(training_session_id: str):
    try:
        return {
            "training_session_id": training_session_id,
            "questions": list_generated_questions(training_session_id),
        }
    except Exception as exc:
        raise _repo_error(exc)


@app.get("/api/training/users/{user_id}/sessions")
async def training_user_sessions(user_id: int, limit: int = Query(20, ge=1, le=100)):
    try:
        return {
            "user_id": user_id,
            "sessions": list_user_training_sessions(user_id, limit=limit),
        }
    except Exception as exc:
        raise _repo_error(exc)


@app.post("/api/training/submit")
async def training_submit(req: TrainingSubmitRequest):
    try:
        data = _model_data(req)
        data["question_source"] = "personalized_training"
        return _submit_question_with_training_bridge(data, auto_rebuild=req.auto_rebuild)
    except Exception as exc:
        raise _repo_error(exc)


@app.post("/api/training/submit-and-rebuild")
async def training_submit_and_rebuild(req: TrainingSubmitRequest):
    try:
        data = _model_data(req)
        data["question_source"] = "personalized_training"
        return _submit_question_with_training_bridge(data, auto_rebuild=True)
    except Exception as exc:
        raise _repo_error(exc)


@app.post("/api/training/generated-question/{generated_question_id}/submit")
async def submit_generated_training_question(generated_question_id: str, req: GeneratedQuestionSubmitRequest):
    try:
        result = submit_generated_question_answer(
            generated_question_id=generated_question_id,
            user_id=req.userId,
            answer=req.answer,
            source=req.source or "user_profile_recommendation",
        )
        try:
            rebuild_result = _rebuild_profile_bridge(req.userId, None)
            result["profileRebuildTriggered"] = True
            result["latestSnapshotId"] = rebuild_result.get("latest_snapshot_id")
            result["profileRebuild"] = rebuild_result
        except Exception as rebuild_exc:
            result["profileRebuildTriggered"] = False
            result["profileRebuildError"] = str(rebuild_exc)
        return result
    except GeneratedQuestionSubmissionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail())
    except Exception as exc:
        raise _repo_error(exc)


@app.post("/api/questions/submit")
async def submit_question_answer(req: QuestionSubmitRequest):
    try:
        data = _model_data(req)
        is_training = data.get("question_source") == "personalized_training" or bool(data.get("training_session_id"))
        return _submit_question_with_training_bridge(data, auto_rebuild=is_training or data.get("user_id") is not None)
    except Exception as exc:
        raise _repo_error(exc)


@app.post("/api/lab-sessions/start")
async def start_lab_session(req: LabSessionStartRequest):
    try:
        return _dispatch_profile_event({"event_type": "LAB_START", **_model_data(req)}, auto_rebuild=True)
    except Exception as exc:
        raise _repo_error(exc)


@app.post("/api/lab-sessions/{session_id}/stop")
async def stop_lab_session(session_id: str):
    try:
        return _dispatch_profile_event({"event_type": "LAB_STOP", "lab_session_id": session_id})
    except Exception as exc:
        raise _repo_error(exc)


@app.post("/api/flags/submit")
async def submit_flag_answer(req: FlagSubmitRequest):
    try:
        return _dispatch_profile_event({"event_type": "FLAG_SUBMIT", **_model_data(req)}, auto_rebuild=True)
    except Exception as exc:
        raise _repo_error(exc)


@app.post("/api/container/commands")
async def save_container_command(req: ContainerCommandEventRequest):
    try:
        return _dispatch_profile_event({"event_type": "COMMAND_EXEC", **_model_data(req)})
    except Exception as exc:
        raise _repo_error(exc)


@app.post("/api/container/files")
async def save_container_file(req: ContainerFileEventRequest):
    try:
        return _dispatch_profile_event({"event_type": "FILE_CHANGE", **_model_data(req)})
    except Exception as exc:
        raise _repo_error(exc)


@app.post("/api/container/errors")
async def save_container_error(req: ErrorEventRequest):
    try:
        return _dispatch_profile_event({"event_type": "ERROR_EVENT", **_model_data(req)})
    except Exception as exc:
        raise _repo_error(exc)


@app.post("/api/profile/rebuild/{user_id}")
async def rebuild_profile(user_id: int):
    try:
        _ensure_profile_source_schemas()
        profile = rebuild_student_profile(user_id)
        class_id = profile.get("class_id")
        class_profile = rebuild_class_profile(int(class_id)) if class_id is not None else None
        return {
            "status": "ok",
            "profile": profile,
            "class_profile": class_profile,
        }
    except Exception as exc:
        raise _repo_error(exc)


@app.get("/api/profile/{user_id}/latest")
async def latest_profile(user_id: int):
    try:
        ensure_profile_schema()
        profile = get_latest_student_profile(user_id)
        return profile or {
            "user_id": user_id,
            "profile": None,
            "message": "no profile snapshot found",
        }
    except Exception as exc:
        raise _repo_error(exc)


@app.get("/api/profile/{user_id}/dashboard")
async def profile_dashboard(user_id: int):
    try:
        _ensure_profile_source_schemas()
        return repo_get_profile_dashboard(user_id)
    except Exception as exc:
        raise _repo_error(exc)


@app.get("/api/scoreboard")
# 名单以教学班为准后，一次要能取回整个班（几十人），上限从 100 提到 500
async def scoreboard(limit: int = Query(default=50, ge=1, le=500)):
    try:
        _ensure_profile_source_schemas()
        return repo_get_scoreboard(limit=limit)
    except Exception as exc:
        raise _repo_error(exc)












@app.get("/api/knowledge-units")
async def knowledge_units(
    moduleId: Optional[int] = Query(default=None),
    courseId: Optional[int] = Query(default=None),
    tag: Optional[str] = Query(default=None),
):
    try:
        return list_knowledge_units(module_id=moduleId, course_id=courseId, tag=tag)
    except Exception as exc:
        raise _repo_error(exc)


@app.get("/api/standard-questions")
async def standard_questions(
    tag: Optional[str] = Query(default=None),
    moduleId: Optional[int] = Query(default=None),
    courseId: Optional[int] = Query(default=None),
    questionType: Optional[str] = Query(default=None),
    difficulty: Optional[int] = Query(default=None, ge=1, le=5),
    reviewedOnly: bool = Query(default=False),
):
    try:
        items = list_standard_questions(
            tag=tag,
            module_id=moduleId,
            course_id=courseId,
            question_type=questionType,
            difficulty=difficulty,
            reviewed_only=reviewedOnly,
        )
        return {
            "success": True,
            "total": len(items),
            "items": standard_questions_to_jsonable(items),
        }
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"code": "STANDARD_QUESTION_LOAD_FAILED", "message": "failed to load standard questions"},
        )


@app.get("/api/class-profile/{class_id}/latest")
async def latest_class_profile(class_id: int):
    try:
        profile = get_latest_class_profile(class_id)
        if profile:
            return profile

        try:
            return rebuild_class_profile(class_id)
        except ValueError:
            return {
                "class_id": class_id,
                "snapshot_id": None,
                "course_id": None,
                "computed_at": None,
                "student_count": 0,
                "class_avg_knowledge_mastery": 0,
                "class_avg_troubleshooting": 0,
                "class_avg_autonomy": 0,
                "class_avg_ai_collaboration": 0,
                "class_avg_engagement": 0,
                "class_overall_score": 0,
                "weak_dimensions_json": [],
                "strengths_json": [],
                "risk_students_json": [],
                "summary_json": {},
                "source_range_start": None,
                "source_range_end": None,
                "created_at": None,
                "message": "no class profile snapshot found",
            }
    except Exception as exc:
        raise _repo_error(exc)


@app.get("/api/class-profile/{class_id}/students")
async def class_profile_students(class_id: int):
    try:
        return list_class_profile_students(class_id)
    except ValueError:
        latest = get_latest_class_profile(class_id)
        return {
            "class_id": class_id,
            "snapshot_id": latest.get("snapshot_id") if latest else None,
            "student_count": 0,
            "source": "class_profile_student_metric",
            "students": [],
            "message": "no class profile student metrics found",
        }
    except Exception as exc:
        raise _repo_error(exc)


def _extract_external_container_name(events: list[dict[str, Any]], user_context: dict[str, Any]) -> Optional[str]:
    container_name = user_context.get("container_name")
    if container_name:
        return str(container_name)
    for event in reversed(events):
        event_container = event.get("container_name")
        if event_container:
            return str(event_container)
        extra = event.get("extra")
        if isinstance(extra, dict) and extra.get("container_name"):
            return str(extra.get("container_name"))
    return None


def _enrich_external_events(
    events: list[dict[str, Any]],
    user_context: dict[str, Any],
    source_system: Optional[str],
) -> tuple[list[dict[str, Any]], dict[str, Any], int]:
    container_name = _extract_external_container_name(events, user_context)
    if not container_name:
        return list(events), {"success": False, "reason": "missing_container_name"}, 0

    runtime_data = docker_tools.collect_container_runtime_data(container_name)
    if not runtime_data.get("success"):
        return list(events), runtime_data, 0

    enriched_events = [dict(event) for event in events]
    appended_count = 0
    session_id = user_context.get("lab_session_id")
    existing_ids = {str(event.get("event_id")) for event in enriched_events if event.get("event_id")}

    for runtime_event in runtime_data.get("log_events", []):
        if not isinstance(runtime_event, dict):
            continue
        event_type = runtime_event.get("event_type")
        event_id = runtime_event.get("event_id")
        if not event_type or (event_id and str(event_id) in existing_ids):
            continue
        enriched_events.append({
            **runtime_event,
            "lab_session_id": runtime_event.get("lab_session_id") or session_id,
            "source": runtime_event.get("source") or "docker-runtime",
        })
        if event_id:
            existing_ids.add(str(event_id))
        appended_count += 1

    for event in enriched_events:
        if str(event.get("event_type") or "").strip().upper() != "LAB_STOP":
            continue
        extra = event.get("extra")
        if not isinstance(extra, dict):
            extra = {}
        extra.setdefault("docker_container_info", runtime_data.get("container_info", {}))
        extra.setdefault("docker_resource_usage", runtime_data.get("resource_usage", {}))
        extra.setdefault("docker_processes", runtime_data.get("processes", {}))
        event["extra"] = extra
        event.setdefault("container_name", container_name)
        event.setdefault("source", source_system or "external-agent")

    return enriched_events, runtime_data, appended_count


@app.post("/api/external/events/ingest")
async def ingest_external_events(req: ExternalEventsIngestRequest):
    frontend_events = [_model_data(event) for event in req.events]
    merged_events, runtime_data, docker_enriched_events = _enrich_external_events(
        frontend_events,
        req.user_context,
        req.source_system,
    )
    events = []
    success_count = 0
    failed_count = 0
    by_type: dict[str, int] = {}

    for index, raw_event in enumerate(merged_events):
        data = _merge_event_context(
            req.user_context,
            raw_event,
            source_system=req.source_system,
            generated_at=req.generated_at,
        )
        event_type = str(data.get("event_type") or "").strip().upper()
        by_type[event_type] = by_type.get(event_type, 0) + 1
        try:
            result = dispatch_student_event(data)
            _remember_lab_event(data)
            success_count += 1
            events.append({
                "index": index,
                "event_id": data.get("event_id"),
                "event_type": event_type,
                "status": result.get("status", "saved"),
                "result": result,
            })
        except Exception as exc:
            failed_count += 1
            events.append({
                "index": index,
                "event_id": data.get("event_id"),
                "event_type": event_type,
                "status": "failed",
                "error": str(exc),
            })

    rebuild_result = None
    profile_rebuild = req.profile_rebuild
    if profile_rebuild and profile_rebuild.rebuild_after_ingest:
        rebuild_user_id = profile_rebuild.user_id or req.user_context.get("user_id")
        if rebuild_user_id is None:
            failed_count += 1
            rebuild_result = {"status": "failed", "error": "profile_rebuild.user_id is required"}
        else:
            try:
                _ensure_profile_source_schemas()
                profile = rebuild_student_profile(int(rebuild_user_id))
                class_id = profile_rebuild.class_id if profile_rebuild.class_id is not None else profile.get("class_id")
                class_profile = rebuild_class_profile(int(class_id)) if class_id is not None else None
                rebuild_result = {
                    "status": "ok",
                    "profile": profile,
                    "class_profile": class_profile,
                }
            except Exception as exc:
                failed_count += 1
                rebuild_result = {"status": "failed", "error": str(exc)}

    status_code = 200 if failed_count == 0 else 207
    summary = {
        "result": "ok" if failed_count == 0 else "partial",
        "batch_id": req.batch_id,
        "received": len(frontend_events),
        "processed": len(merged_events),
        "saved": success_count,
        "failed": failed_count,
        "by_type": by_type,
        "events": events,
        "frontend_events": len(frontend_events),
        "docker_enriched_events": docker_enriched_events,
        "container_runtime_available": bool(runtime_data.get("success")),
        "runtime_collection": runtime_data,
        "ai_generated_questions_received": len(req.ai_generated_questions),
        "profile_rebuild": rebuild_result,
    }
    return {
        "isSuccess": 1 if failed_count == 0 else 0,
        "status": status_code,
        "message": f"事件上报完成，共处理 {len(merged_events)} 条事件",
        "data": summary,
    }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """
    接收前端消息并以 SSE 流式返回：配置了 LLM_API_KEY 时直连模型（DeepSeek 等）
    并在本地完成工具调用，否则原样转发至 Dify Agent。两条路径的事件格式一致。
    """
    if direct_llm_enabled():
        return StreamingResponse(
            stream_assistant_reply(
                req.query,
                user=req.user or "student",
                conversation_id=req.conversation_id,
                inputs=req.inputs,
            ),
            media_type="text/event-stream",
        )

    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": req.query,
        "response_mode": "streaming",
        "conversation_id": req.conversation_id or "",
        "user": req.user or "student",
        "inputs": req.inputs or {},
    }

    async def event_stream():
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{DIFY_API_URL}/chat-messages",
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    error_msg = body.decode("utf-8", errors="replace")
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                    return
                async for line in response.aiter_lines():
                    if line:
                        yield f"{line}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/llm/chat/completions")
async def llm_chat_completions(req: LLMProxyRequest):
    """OpenAI 兼容的透传代理，供前端聊天页的 OpenAI SDK 直接调用。

    前端只需把 baseURL 指到 `${AGENT_BASE_URL}/api/llm`，真实密钥留在服务端，
    不会被打进前端产物。model 走白名单，避免本端点被当成免费 API 网关。
    """
    if not direct_llm_enabled():
        raise HTTPException(status_code=503, detail="LLM 未配置：请在 ai-agent-service/.env 设置 LLM_API_KEY")

    payload = {
        "model": llm_provider.resolve_proxy_model(req.model),
        "messages": req.messages,
        "temperature": req.temperature,
        "stream": bool(req.stream),
    }
    if not payload["stream"]:
        try:
            return await llm_provider.complete_raw(payload)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"上游调用失败：{type(exc).__name__}")

    return StreamingResponse(llm_provider.proxy_completions(payload), media_type="text/event-stream")


# ─────────────────────────────────────────
#  Docker 工具 API（供 Dify 外部工具调用）
# ─────────────────────────────────────────
# --- 新增：获取容器列表 (读取容器名字) ---
@app.get("/api/docker/list")
async def list_all_containers(
    _: None = Security(verify_tool_key)
):
    """获取所有容器列表（Dify 工具：list_containers）"""
    result = docker_tools.list_containers() # 需要在 docker_tools 里实现
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

# --- 新增：启动容器 ---
@app.post("/api/docker/start/{container_name}")
async def start_container(
    container_name: str,
    _: None = Security(verify_tool_key)
):
    """开启容器（Dify 工具：start_container）"""
    result = docker_tools.start_container(container_name) # 需要在 docker_tools 里实现
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result
TARGET_LABS = {
    "sqli": {"container": "sqli-lab-web-1", "host_port": 8091, "entry": "index.php", "target_url": "/targets/sqli/"},
    "xss": {"container": "xss-lab-web-1", "host_port": 8092, "entry": "index.php", "target_url": "/targets/xss/"},
    "csrf": {"container": "csrf-lab-web-1", "host_port": 8093, "entry": "index.php", "target_url": "/targets/csrf/"},
    "cmd": {"container": "command-inject-web-1", "host_port": 8090, "entry": "index.html", "target_url": "/targets/cmd/"},
    "upload": {"container": "file-upload-lab-web-1", "host_port": 8094, "entry": "index.php", "target_url": "/targets/upload/"},
    "dir": {"container": "directory-traversal-lab-web-1", "host_port": 8095, "entry": "index.php", "target_url": "/targets/dir/"},
}

TARGET_HTTP_OK = {200, 301, 302, 403}


def _tcp_listening(host: str, port: int, timeout: float = 1.2) -> bool:
    import socket

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _probe_target_http(port: int, entry: str, timeout: float = 2.0) -> tuple[bool, int | None, str | None]:
    import urllib.error
    import urllib.request

    url = f"http://127.0.0.1:{port}/{entry.lstrip('/')}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            status = int(response.getcode() or 0)
            return status in TARGET_HTTP_OK, status, None
    except urllib.error.HTTPError as exc:
        status = int(exc.code or 0)
        return status in TARGET_HTTP_OK, status, None
    except Exception as exc:
        return False, None, str(exc)


def _target_status_payload(lab_key: str) -> dict:
    lab = TARGET_LABS.get(lab_key)
    if not lab:
        raise HTTPException(status_code=400, detail="Unknown target lab")

    container_name = lab["container"]
    container_info = docker_tools.get_container_status(container_name)
    container_exists = bool(container_info.get("success"))
    data = container_info.get("data") or {}
    container_running = data.get("status") == "running"
    host_port = int(lab["host_port"])
    port_listening = _tcp_listening("127.0.0.1", host_port) if container_running else False
    http_reachable = False
    http_status = None
    probe_error = None
    if port_listening:
        http_reachable, http_status, probe_error = _probe_target_http(host_port, str(lab["entry"]))

    status = "offline"
    message = "Target container does not exist"
    reason = "container_missing"
    if container_exists and not container_running:
        message = "Target container is not running"
        reason = "container_not_running"
    elif container_running and not port_listening:
        status = "starting"
        message = "Target web port is not listening yet"
        reason = "port_not_listening"
    elif container_running and port_listening and not http_reachable:
        status = "starting"
        message = "Target web service is not ready yet"
        reason = "http_probe_failed"
    elif container_running and port_listening and http_reachable:
        status = "online"
        message = "Target web service is reachable"
        reason = "ok"

    return {
        "lab": lab_key,
        "containerName": container_name,
        "containerId": data.get("name") if container_exists else None,
        "containerExists": container_exists,
        "containerRunning": container_running,
        "hostPort": host_port,
        "portListening": port_listening,
        "targetUrl": lab["target_url"],
        "url": lab["target_url"] if status == "online" else None,
        "httpReachable": http_reachable,
        "httpStatus": http_status,
        "status": status,
        "message": message,
        "reason": reason,
        "error": probe_error,
    }


async def _wait_target_status(lab_key: str, attempts: int = 6, interval: float = 1.0) -> dict:
    import asyncio

    latest = _target_status_payload(lab_key)
    for _ in range(1, attempts):
        if latest.get("status") == "online":
            return latest
        await asyncio.sleep(interval)
        latest = _target_status_payload(lab_key)
    return latest


async def _start_target_lab(lab_key: str):
    lab = TARGET_LABS.get(lab_key)
    if not lab:
        raise HTTPException(status_code=400, detail="Unknown target lab")
    result = docker_tools.start_container(str(lab["container"]))
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "start target failed"))
    status = await _wait_target_status(lab_key)
    return {
        "isSuccess": 1,
        "status": 200,
        "message": "Target lab is online" if status.get("status") == "online" else status.get("message", "Target lab starting"),
        "data": status,
    }


@app.get("/api/docker/target-status/{lab_key}")
async def target_status(lab_key: str):
    return {
        "isSuccess": 1,
        "status": 200,
        "message": "success",
        "data": _target_status_payload(lab_key),
    }


@app.post("/api/docker/start-sqli")
async def start_sqli_target():
    return await _start_target_lab("sqli")


@app.post("/api/docker/start-xss")
async def start_xss_target():
    return await _start_target_lab("xss")


@app.post("/api/docker/start-csrf")
async def start_csrf_target():
    return await _start_target_lab("csrf")


@app.post("/api/docker/start-cmd")
async def start_cmd_target():
    return await _start_target_lab("cmd")


@app.post("/api/docker/start-upload")
async def start_upload_target():
    return await _start_target_lab("upload")


@app.post("/api/docker/start-dir")
async def start_dir_target():
    return await _start_target_lab("dir")


@app.get("/api/docker/containers")
async def list_containers(
    name: Optional[str] = Query(None, description="容器名称，不填则返回全部靶场容器"),
    _: None = Security(verify_tool_key)
):
    """获取容器状态（Dify 工具：get_container_status）"""
    result = docker_tools.get_container_status(name)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@app.get("/api/docker/logs/{container_name}")
async def container_logs(
    container_name: str,
    tail: int = Query(100, ge=1, le=200, description="返回最近 N 行日志"),
    _: None = Security(verify_tool_key)
):
    """获取容器日志（Dify 工具：get_container_logs）"""
    result = docker_tools.get_container_logs(container_name, tail)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@app.post("/api/docker/exec/{container_name}")
async def exec_command(
    container_name: str,
    body: ExecRequest,
    _: None = Security(verify_tool_key)
):
    """在容器内执行指令（Dify 工具：exec_in_container）"""
    result = docker_tools.exec_in_container(container_name, body.command)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@app.post("/api/docker/stop/{container_name}")
async def stop_container(
    container_name: str,
    _: None = Security(verify_tool_key)
):
    """停止容器（Dify 工具：stop_container）"""
    result = docker_tools.stop_container(container_name)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


# ─────────────────────────────────────────
#  操作环境 (noVNC 虚拟桌面)
# ─────────────────────────────────────────

class OperationStartRequest(BaseModel):
    user_id: int
    module_id: Optional[int] = None
    course_id: Optional[int] = None


class OperationStopRequest(BaseModel):
    session_id: str


@app.post("/api/docker/operation/start")
async def operation_start(req: OperationStartRequest):
    try:
        result = await asyncio.to_thread(
            operation_env.start_operation_env,
            req.user_id, req.module_id, req.course_id,
        )
        return {"success": True, "data": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/docker/operation/stop")
async def operation_stop(req: OperationStopRequest):
    result = await asyncio.to_thread(operation_env.stop_operation_env, req.session_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "stop failed"))
    return result


@app.get("/api/docker/operation/status/{session_id}")
async def operation_status(session_id: str):
    result = await asyncio.to_thread(operation_env.get_operation_env_status, session_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "not found"))
    return result


@app.websocket("/api/docker/vnc/{session_id}")
async def vnc_bridge(ws: WebSocket, session_id: str):
    """Pure byte bridge between the browser WebSocket and the operation
    container VNC TCP port. noVNC handles the RFB protocol on the client."""
    await ws.accept()
    session = await asyncio.to_thread(operation_session_repo.find_session, session_id)
    if not session or session.get("status") != "running":
        await ws.close(code=1011)
        return

    try:
        reader, writer = await asyncio.open_connection(session["vnc_host"], int(session["vnc_port"]))
    except Exception:
        await ws.close(code=1011)
        return

    async def upstream():
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                await ws.send_bytes(data)
        except Exception:
            pass

    async def downstream():
        try:
            while True:
                msg = await ws.receive_bytes()
                writer.write(msg)
                await writer.drain()
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    try:
        await asyncio.gather(upstream(), downstream())
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        try:
            await ws.close()
        except Exception:
            pass


@app.on_event("startup")
async def _start_operation_cleanup_loop():
    """Schedule the idle operation-session cleanup loop."""
    asyncio.create_task(operation_env.cleanup_loop())


# ─────────────────────────────────────────
#  入口
# ─────────────────────────────────────────



# 队友教师端鉴权用 JWT 密钥(与 user-service 一致)
USER_SERVICE_JWT_SECRET = os.getenv(
    "USER_SERVICE_JWT_SECRET",
    "SecLabUserServiceJwtSecretChangeMeAtLeast32Chars",
)

# ================= 队友教师端(Teacher) 集成: 由 main.py 抽取合并 =================
# 说明：以下 import 位于文件中段是历史合并遗留。Python 允许函数定义前的模块级 import 出现在
# 任意位置，且这些符号仅被下方教师端路由使用，因此保持原位；新增导入统一并入对应分组，
# 避免再次出现重复导入。
from teacher_ai_analysis_service import (
    generate_teacher_student_ai_analysis,
    get_latest_student_analysis,
    get_latest_teaching_class_analysis,
    run_manual_student_analysis,
    run_manual_teaching_class_analysis,
)
from teacher_analysis_repository import (
    AnalysisAlreadyRunningError,
    InsufficientAnalysisDataError,
    TeacherAnalysisProviderError,
)
from teacher_repository import (
    get_generated_question_for_teacher,
    get_student_profile_for_teacher,
    list_class_students as repo_list_teacher_class_students,
    list_generated_questions_for_teacher,
    list_teacher_classes,
    mark_generated_question_typical,
    read_teacher_dashboard,
    summarize_generated_questions_for_class,
    unmark_generated_question_typical,
)
from teacher_profile_service import rebuild_teaching_class_profiles
from teacher_course_analysis_service import (
    collect_course_question_records,
    get_course_analysis,
    run_course_analysis,
)
from teacher_learning_insight_repository import (
    get_capability_evidence,
    get_class_risk_map,
    get_knowledge_risk_detail,
    get_learning_replay,
)
from capability_growth_repository import (
    get_student_capability_growth,
    get_teacher_student_capability_growth,
)
from teacher_knowledge_analysis_service import (
    AnalysisAlreadyRunningError as KnowledgeAnalysisAlreadyRunningError,
    KNOWLEDGE_ANALYSIS_SERVICE,
    ProviderUnavailableError as KnowledgeProviderUnavailableError,
)
from teacher_intervention_repository import (
    create_intervention,
    get_student_assignment,
    get_intervention,
    list_interventions,
    list_student_assignments,
    mark_student_assignment_started,
    refresh_intervention_metrics,
    start_student_assignment_from_snapshots,
    update_intervention_status,
)

class TeacherInterventionCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    actionType: str
    studentIds: list[int] = Field(min_length=1)
    courseId: Optional[int] = None
    knowledgePointId: Optional[int] = None
    description: Optional[str] = Field(default="", max_length=2000)
    questionIds: list[str] = Field(default_factory=list)
    approvedExerciseIds: list[int] = Field(default_factory=list)
    dueAt: Optional[datetime] = None


class KnowledgeExerciseUpdateRequest(BaseModel):
    questionType: Optional[str] = None
    stem: Optional[str] = None
    options: Optional[list[str]] = None
    standardAnswer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    generationRationale: Optional[str] = None


class KnowledgeExerciseReviewRequest(BaseModel):
    status: str
    comment: str = Field(default="", max_length=1000)

class TeacherInterventionStatusRequest(BaseModel):
    status: str

def _teacher_repo_error(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        if exc.status_code >= 500:
            return HTTPException(status_code=exc.status_code, detail="数据加载失败，请重新加载。")
        return exc
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail="当前账号无权查看该数据。")
    if isinstance(exc, AnalysisAlreadyRunningError):
        return HTTPException(status_code=409, detail="该教学班正在分析，请稍后再试。")
    if isinstance(exc, KnowledgeAnalysisAlreadyRunningError):
        return HTTPException(status_code=409, detail="该知识点正在分析，请稍后再试。")
    if isinstance(exc, InsufficientAnalysisDataError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, TeacherAnalysisProviderError):
        # 不把 Dify/提示词等内部实现细节透出给教师，统一成可操作的业务文案
        return HTTPException(
            status_code=503,
            detail="本次智能分析未生成可用结论，当前仍显示上次成功结果；原始作答统计不受影响，请稍后重试。",
        )
    if isinstance(exc, KnowledgeProviderUnavailableError):
        return HTTPException(
            status_code=503,
            detail="本次智能分析未生成可用结论，当前仍显示上次成功结果；原始作答统计不受影响，请稍后重试。",
        )
    if isinstance(exc, KeyError):
        return HTTPException(status_code=404, detail="请求的数据已不存在或无权访问。")
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail="请求内容有误，请检查后重试。")
    return HTTPException(status_code=500, detail="数据加载失败，请重新加载。")

def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("utf-8"))

def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is required")
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(status_code=401, detail="Bearer token is required")
    return parts[1].strip()

def _parse_user_token(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Token format is invalid")
    signing_input = f"{parts[0]}.{parts[1]}".encode("utf-8")
    expected = base64.urlsafe_b64encode(
        hmac.new(USER_SERVICE_JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    ).decode("utf-8").rstrip("=")
    if not hmac.compare_digest(expected, parts[2]):
        raise HTTPException(status_code=401, detail="Token signature is invalid")
    try:
        payload = json.loads(_base64url_decode(parts[1]).decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=401, detail="Token payload is invalid")
    exp = payload.get("exp")
    if exp is None or int(exp) <= int(time.time()):
        raise HTTPException(status_code=401, detail="Token has expired")
    user_id = str(payload.get("sub") or "").strip()
    if not user_id.isdigit():
        raise HTTPException(status_code=401, detail="Token subject is invalid")
    return {"user_id": int(user_id), "student_number": payload.get("studentNumber")}

def _load_teacher_auth_context(user_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    u.user_id,
                    u.user_student_number,
                    u.user_name,
                    COALESCE(u.is_deleted, 0) AS is_deleted,
                    u.user_role
                FROM `userservice`.`user` u
                WHERE u.user_id = %(user_id)s
                LIMIT 1
                """,
                {"user_id": user_id},
            )
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=401, detail="Token user does not exist")
            if int(user.get("is_deleted") or 0) == 1:
                raise HTTPException(status_code=403, detail="This account is disabled")

            cursor.execute(
                """
                SELECT teaching_class_id
                FROM `userservice`.`teaching_class`
                WHERE teacher_id = %(user_id)s
                ORDER BY teaching_class_id
                """,
                {"user_id": user_id},
            )
            owned_teaching_class_ids = [
                int(row["teaching_class_id"])
                for row in cursor.fetchall() or []
            ]

    if str(user.get("user_role") or "").upper() != "TEACHER":
        raise HTTPException(status_code=403, detail="Only teacher accounts can access this endpoint")

    return {
        "user_id": int(user["user_id"]),
        "student_number": user.get("user_student_number"),
        "name": user.get("user_name"),
        "role": "teacher",
        # Legacy administrative-class endpoints must not fall back to global access.
        "scope_class_ids": [],
        "owned_teaching_class_ids": owned_teaching_class_ids,
    }

def _load_authenticated_user_context(user_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, user_student_number, user_name,
                       COALESCE(is_deleted, 0) AS is_deleted, user_role
                FROM `userservice`.`user`
                WHERE user_id = %(user_id)s
                LIMIT 1
                """,
                {"user_id": user_id},
            )
            user = cursor.fetchone()
    if not user or int(user.get("is_deleted") or 0) != 0:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录。")
    return {
        "user_id": int(user["user_id"]),
        "student_number": user.get("user_student_number"),
        "name": user.get("user_name"),
        "role": str(user.get("user_role") or "STUDENT").strip().lower(),
    }

async def require_authenticated_user(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    payload = _parse_user_token(_extract_bearer_token(authorization))
    return _load_authenticated_user_context(int(payload["user_id"]))

def _require_student_self(current_user: dict[str, Any], student_id: int) -> None:
    if current_user.get("role") != "student" or int(current_user.get("user_id") or 0) != int(student_id):
        raise HTTPException(status_code=403, detail="只能查看和开始自己的教师布置训练。")

def _build_teacher_assignment_training_request(
    student_id: int,
    assignment: dict[str, Any],
) -> dict[str, Any]:
    knowledge_point_name = str(assignment.get("knowledgePointName") or "网络安全综合能力").strip()
    return {
        "user_id": int(student_id),
        "dimension": "knowledge_mastery",
        "recommendation_id": f"intervention-{int(assignment['interventionId'])}",
        "module_id": None,
        "course_id": None,
        "knowledge_tags": [knowledge_point_name],
        "difficulty": 2,
        "question_type": "SHORT_ANSWER",
        "count": 5,
        "source": "teacher_assignment",
    }

async def require_teacher_user(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    payload = _parse_user_token(_extract_bearer_token(authorization))
    return _load_teacher_auth_context(int(payload["user_id"]))

async def _probe_dify_configuration() -> dict[str, Any]:
    if not DIFY_API_URL or not DIFY_API_KEY:
        return {
            "configured": False,
            "providerReachable": False,
            "message": "Dify 尚未配置。",
        }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0)) as client:
            response = await client.get(
                f"{DIFY_API_URL.rstrip('/')}/parameters",
                headers={"Authorization": f"Bearer {DIFY_API_KEY}"},
            )
            response.raise_for_status()
    except httpx.HTTPError:
        return {
            "configured": True,
            "providerReachable": False,
            "message": "Dify 已配置，但当前无法连接。",
        }
    except Exception as exc:
        # 健康探测端点必须永远返回 200，否则未捕获异常会绕过 CORS 中间件，
        # 浏览器只看到 CORS 报错而不是"AI 分析暂不可用"。
        # 已知触发场景：机器设了 ALL_PROXY=socks5://... 但未安装 httpx[socks]，
        # httpx.AsyncClient() 构造阶段直接抛 ImportError（不是 HTTPError）。
        return {
            "configured": True,
            "providerReachable": False,
            "message": f"Dify 已配置，但探测失败：{type(exc).__name__}。",
        }
    return {
        "configured": True,
        "providerReachable": True,
        "message": "Dify 连接正常。",
    }

# 探测要向模型服务发一次真实请求（DeepSeek 实测 1.9~2.0 秒）。教师端每打开一次教学分析
# 就问一次，而这个结果几十秒内不会变，所以缓存成功结果。失败结果不缓存：网络恢复后
# 下一次打开就能立刻探到，不用等缓存过期。
_AI_HEALTH_CACHE_SECONDS = float(os.getenv("AI_HEALTH_CACHE_SECONDS", "60"))
_ai_health_cache: Optional[tuple[float, dict[str, Any]]] = None


@app.get("/health/ai-analysis")
async def ai_analysis_health():
    global _ai_health_cache
    now = time.monotonic()
    if _ai_health_cache is not None and now - _ai_health_cache[0] < _AI_HEALTH_CACHE_SECONDS:
        return _ai_health_cache[1]
    if direct_llm_enabled():
        result = await llm_provider.probe()
    else:
        result = await _probe_dify_configuration()
    if result.get("providerReachable"):
        _ai_health_cache = (now, result)
    return result

@app.get("/api/teacher/dashboard")
async def teacher_dashboard(
    teacherId: Optional[int] = Query(default=None),
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return read_teacher_dashboard(current_user=current_user)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/students/{student_id}/teacher-assignments")
async def student_teacher_assignments(
    student_id: int,
    current_user: dict[str, Any] = Depends(require_authenticated_user),
):
    _require_student_self(current_user, student_id)
    try:
        return list_student_assignments(student_id)
    except Exception as exc:
        raise _repo_error(exc)


@app.get("/api/students/{student_id}/capability-growth")
async def student_capability_growth(
    student_id: int,
    teachingClassId: Optional[int] = Query(default=None),
    current_user: dict[str, Any] = Depends(require_authenticated_user),
):
    _require_student_self(current_user, student_id)
    try:
        return get_student_capability_growth(student_id, teachingClassId)
    except Exception as exc:
        raise _repo_error(exc)


@app.post("/api/students/{student_id}/teacher-assignments/{intervention_id}/start")
async def student_start_teacher_assignment(
    student_id: int,
    intervention_id: int,
    current_user: dict[str, Any] = Depends(require_authenticated_user),
):
    _require_student_self(current_user, student_id)
    try:
        assignment = get_student_assignment(student_id, intervention_id)
        if assignment.get("trainingSessionId"):
            return {
                **assignment,
                "startedNow": False,
                "generation": None,
            }
        # 教师已批准的知识点例题在下发时被冻结成快照，优先直接下发，无需再调大模型出题
        snapshot_result = start_student_assignment_from_snapshots(student_id, intervention_id)
        if snapshot_result is not None:
            return snapshot_result
        generation = await generate_training_question_set(
            _build_teacher_assignment_training_request(student_id, assignment)
        )
        started = mark_student_assignment_started(
            student_id,
            intervention_id,
            str(generation["trainingSessionId"]),
        )
        return {**started, "generation": generation}
    except TrainingSessionServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail())
    except QuestionGenerationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail())
    except Exception as exc:
        raise _repo_error(exc)

@app.get("/api/teacher/classes")
@app.get("/api/teacher/dashboard/classes")
async def teacher_classes(
    teacherId: Optional[int] = Query(default=None),
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return list_teacher_classes(current_user=current_user)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/teacher/classes/{class_id}/students")
@app.get("/api/teacher/dashboard/classes/{class_id}/students")
async def teacher_class_students(
    class_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return repo_list_teacher_class_students(class_id, current_user=current_user)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.post("/api/teacher/classes/{class_id}/ai-analysis")
@app.post("/api/teacher/teaching-classes/{class_id}/ai-analysis")
async def teacher_class_ai_analysis(
    class_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return await run_manual_teaching_class_analysis(class_id, current_user=current_user)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/teacher/teaching-classes/{class_id}/ai-analysis")
async def teacher_latest_class_ai_analysis(
    class_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return get_latest_teaching_class_analysis(class_id, current_user=current_user)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.post("/api/teacher/teaching-classes/{class_id}/profiles/rebuild")
async def teacher_rebuild_class_profiles(
    class_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return rebuild_teaching_class_profiles(
            class_id,
            int(current_user.get("user_id") or 0),
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/teacher/teaching-classes/{class_id}/students/{student_id}/capability-evidence")
async def teacher_student_capability_evidence(
    class_id: int,
    student_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return get_capability_evidence(
            int(current_user.get("user_id") or 0),
            class_id,
            student_id,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/teacher/teaching-classes/{class_id}/students/{student_id}/capability-growth")
async def teacher_student_capability_growth(
    class_id: int,
    student_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return get_teacher_student_capability_growth(
            int(current_user.get("user_id") or 0),
            class_id,
            student_id,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)


@app.get("/api/teacher/teaching-classes/{class_id}/students/{student_id}/learning-replay")
async def teacher_student_learning_replay(
    class_id: int,
    student_id: int,
    limit: int = Query(default=100, ge=10, le=200),
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return get_learning_replay(
            int(current_user.get("user_id") or 0),
            class_id,
            student_id,
            limit=limit,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/teacher/teaching-classes/{class_id}/risk-map")
async def teacher_class_risk_map(
    class_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return get_class_risk_map(
            int(current_user.get("user_id") or 0),
            class_id,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)


@app.get("/api/teacher/teaching-classes/{class_id}/experiments/{course_id}/knowledge-risks")
async def teacher_experiment_knowledge_risks(
    class_id: int,
    course_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return get_class_risk_map(
            int(current_user.get("user_id") or 0),
            class_id,
            course_id,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)


@app.get("/api/teacher/teaching-classes/{class_id}/experiments/{course_id}/knowledge-risks/{knowledge_point_id}")
async def teacher_experiment_knowledge_risk_detail(
    class_id: int,
    course_id: int,
    knowledge_point_id: int,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return get_knowledge_risk_detail(
            int(current_user.get("user_id") or 0),
            class_id,
            course_id,
            knowledge_point_id,
            page,
            size,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)


@app.get("/api/teacher/teaching-classes/{class_id}/experiments/{course_id}/knowledge-points/{knowledge_point_id}/ai-analysis")
async def teacher_get_knowledge_ai_analysis(
    class_id: int,
    course_id: int,
    knowledge_point_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return KNOWLEDGE_ANALYSIS_SERVICE.get_analysis(
            int(current_user.get("user_id") or 0), class_id, course_id, knowledge_point_id,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)


@app.post("/api/teacher/teaching-classes/{class_id}/experiments/{course_id}/knowledge-points/{knowledge_point_id}/ai-analysis")
async def teacher_run_knowledge_ai_analysis(
    class_id: int,
    course_id: int,
    knowledge_point_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return await KNOWLEDGE_ANALYSIS_SERVICE.run_analysis(
            int(current_user.get("user_id") or 0), class_id, course_id, knowledge_point_id,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)


@app.patch("/api/teacher/teaching-classes/{class_id}/knowledge-exercises/{exercise_id}")
async def teacher_update_knowledge_exercise(
    class_id: int,
    exercise_id: int,
    request: KnowledgeExerciseUpdateRequest,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return KNOWLEDGE_ANALYSIS_SERVICE.update_exercise(
            int(current_user.get("user_id") or 0),
            class_id,
            exercise_id,
            request.model_dump(exclude_none=True),
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)


@app.post("/api/teacher/teaching-classes/{class_id}/knowledge-exercises/{exercise_id}/review")
async def teacher_review_knowledge_exercise(
    class_id: int,
    exercise_id: int,
    request: KnowledgeExerciseReviewRequest,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return KNOWLEDGE_ANALYSIS_SERVICE.review_exercise(
            int(current_user.get("user_id") or 0),
            class_id,
            exercise_id,
            request.status,
            request.comment,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)


@app.post("/api/teacher/teaching-classes/{class_id}/knowledge-exercises/{exercise_id}/regenerate")
async def teacher_regenerate_knowledge_exercise(
    class_id: int,
    exercise_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return await KNOWLEDGE_ANALYSIS_SERVICE.regenerate_exercise(
            int(current_user.get("user_id") or 0), class_id, exercise_id,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)


@app.get("/api/teacher/teaching-classes/{class_id}/interventions")
async def teacher_class_interventions(
    class_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return list_interventions(int(current_user.get("user_id") or 0), class_id)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.post("/api/teacher/teaching-classes/{class_id}/interventions")
async def teacher_create_class_intervention(
    class_id: int,
    request: TeacherInterventionCreateRequest,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return create_intervention(
            teacher_id=int(current_user.get("user_id") or 0),
            class_id=class_id,
            title=request.title,
            action_type=request.actionType,
            student_ids=request.studentIds,
            knowledge_point_id=request.knowledgePointId,
            description=request.description or "",
            question_ids=request.questionIds,
            due_at=request.dueAt,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/teacher/teaching-classes/{class_id}/interventions/{intervention_id}")
async def teacher_class_intervention_detail(
    class_id: int,
    intervention_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return get_intervention(
            int(current_user.get("user_id") or 0),
            class_id,
            intervention_id,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.patch("/api/teacher/teaching-classes/{class_id}/interventions/{intervention_id}")
async def teacher_update_class_intervention(
    class_id: int,
    intervention_id: int,
    request: TeacherInterventionStatusRequest,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return update_intervention_status(
            int(current_user.get("user_id") or 0),
            class_id,
            intervention_id,
            request.status,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.post("/api/teacher/teaching-classes/{class_id}/interventions/{intervention_id}/refresh")
async def teacher_refresh_class_intervention(
    class_id: int,
    intervention_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return refresh_intervention_metrics(
            int(current_user.get("user_id") or 0),
            class_id,
            intervention_id,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/teacher/students/{user_id}/profile")
async def teacher_student_profile(
    user_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return get_student_profile_for_teacher(user_id, current_user=current_user)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/teacher/teaching-classes/{class_id}/students/{user_id}/profile")
async def teacher_teaching_class_student_profile(
    class_id: int,
    user_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return get_student_profile_for_teacher(
            user_id,
            current_user=current_user,
            teaching_class_id=class_id,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/teacher/teaching-classes/{class_id}/students/{user_id}/ai-analysis")
async def teacher_latest_student_ai_analysis(
    class_id: int,
    user_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return get_latest_student_analysis(
            class_id,
            user_id,
            current_user=current_user,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.post("/api/teacher/teaching-classes/{class_id}/students/{user_id}/ai-analysis")
async def teacher_start_student_ai_analysis(
    class_id: int,
    user_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return await run_manual_student_analysis(
            class_id,
            user_id,
            current_user=current_user,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.post("/api/teacher/students/{user_id}/profile/ai-analysis")
async def teacher_student_profile_ai_analysis(
    user_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return await generate_teacher_student_ai_analysis(user_id, current_user=current_user)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/teacher/generated-questions")
@app.get("/api/teacher/dashboard/classes/generated-questions")
async def teacher_generated_questions(
    teacherId: Optional[int] = Query(default=None),
    teachingClassId: Optional[int] = Query(default=None),
    courseId: Optional[int] = Query(default=None),
    knowledgePointId: Optional[int] = Query(default=None),
    studentId: Optional[int] = Query(default=None),
    answerResult: Optional[str] = Query(default=None),
    typicalOnly: bool = Query(default=False),
    dateFrom: Optional[date] = Query(default=None),
    dateTo: Optional[date] = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return list_generated_questions_for_teacher(
            current_user=current_user,
            teaching_class_id=teachingClassId,
            course_id=courseId,
            knowledge_point_id=knowledgePointId,
            student_id=studentId,
            answer_result=answerResult,
            typical_only=typicalOnly,
            date_from=dateFrom,
            date_to=dateTo,
            page=page,
            size=size,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/teacher/teaching-classes/{class_id}/courses/{course_id}/questions")
async def teacher_class_course_questions(
    class_id: int,
    course_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return collect_course_question_records(class_id, course_id, current_user)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/teacher/teaching-classes/{class_id}/courses/{course_id}/students/{student_id}/questions")
async def teacher_student_course_questions(
    class_id: int,
    course_id: int,
    student_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return collect_course_question_records(class_id, course_id, current_user, student_id)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/teacher/teaching-classes/{class_id}/courses/{course_id}/ai-analysis")
async def teacher_latest_class_course_analysis(
    class_id: int,
    course_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return get_course_analysis(class_id, course_id, current_user)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.post("/api/teacher/teaching-classes/{class_id}/courses/{course_id}/ai-analysis")
async def teacher_start_class_course_analysis(
    class_id: int,
    course_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return await run_course_analysis(class_id, course_id, current_user)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/teacher/teaching-classes/{class_id}/courses/{course_id}/students/{student_id}/ai-analysis")
async def teacher_latest_student_course_analysis(
    class_id: int,
    course_id: int,
    student_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return get_course_analysis(class_id, course_id, current_user, student_id)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.post("/api/teacher/teaching-classes/{class_id}/courses/{course_id}/students/{student_id}/ai-analysis")
async def teacher_start_student_course_analysis(
    class_id: int,
    course_id: int,
    student_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return await run_course_analysis(class_id, course_id, current_user, student_id)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/teacher/generated-questions/{generated_question_id}")
async def teacher_generated_question_detail(
    generated_question_id: str,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return get_generated_question_for_teacher(generated_question_id, current_user=current_user)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.put("/api/teacher/generated-questions/{generated_question_id}/typical")
async def teacher_mark_generated_question_typical(
    generated_question_id: str,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        get_generated_question_for_teacher(generated_question_id, current_user=current_user)
        return mark_generated_question_typical(int(current_user["user_id"]), generated_question_id)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.delete("/api/teacher/generated-questions/{generated_question_id}/typical")
async def teacher_unmark_generated_question_typical(
    generated_question_id: str,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        get_generated_question_for_teacher(generated_question_id, current_user=current_user)
        return unmark_generated_question_typical(int(current_user["user_id"]), generated_question_id)
    except Exception as exc:
        raise _teacher_repo_error(exc)

@app.get("/api/teacher/teaching-classes/{teaching_class_id}/generated-question-summary")
async def teacher_generated_question_summary(
    teaching_class_id: int,
    current_user: dict[str, Any] = Depends(require_teacher_user),
):
    try:
        return summarize_generated_questions_for_class(
            teaching_class_id,
            current_user=current_user,
        )
    except Exception as exc:
        raise _teacher_repo_error(exc)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=SERVICE_HOST, port=SERVICE_PORT, reload=True)
