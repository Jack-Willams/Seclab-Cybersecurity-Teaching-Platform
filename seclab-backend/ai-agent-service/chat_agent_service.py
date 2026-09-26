"""SecLab 助手：直连模型时的流式对话（含 Docker 工具调用）。

人设与工具编排原本放在 Dify 应用里，直连模型后由本模块承担：系统提示词定义助教
人设，工具调用直接复用本服务已有的 docker_tools，产出的 SSE 事件保持 Dify 形状
（agent_message / agent_thought / message_end），前端 FloatingChat 无需改动。
"""
from collections import OrderedDict
from typing import Any, AsyncIterator, Optional

import asyncio
import json
import uuid

import httpx

import docker_tools
from config import LLM_TIMEOUT_SECONDS
from llm_provider import LLMError, new_async_client, stream_round

SYSTEM_PROMPT = """你是 SecLab 网络安全实训平台的 AI 助教，服务对象是正在做靶场实验的学生。

教学原则：
1. 用中文回答，语气友好、简洁，优先给方法和思路，不要长篇大论。
2. 遇到"求答案"类问题采用阶梯式提示：先给最小提示（指出方向），学生仍卡住再给具体步骤，
   只有学生明确表示已多次尝试或倒计时结束时，才给出完整解法。
3. 不直接报出 flag 内容；可以说明 flag 通常出现在哪里、怎么验证。
4. 讲解漏洞原理时要连带讲防御修复方案，这是实训的考核点。
5. 平台已有靶场：SQL 注入、XSS、CSRF、命令注入、文件上传、目录遍历、栈溢出等。

工具使用：
- 学生描述"靶机打不开/连不上/环境有问题"时，先用 list_containers 或 get_container_status 查状态，
  必要时用 start_container 拉起，再回复结论。
- 需要判断学生进度或排查报错时，用 get_container_logs 读取靶机日志再分析。
- 工具只用于排查环境，不要替学生完成漏洞利用；调用结果要用自己的话总结，不要直接贴原始 JSON。
"""

# 工具调用最多来回 3 轮，防止模型在工具之间反复横跳把请求拖死
MAX_TOOL_ROUNDS = 3
# 单条工具结果注回模型的最大字符数，日志类结果很容易超长
MAX_OBSERVATION_CHARS = 4000
# 每个会话保留的历史消息条数（user/assistant 各算一条）
MAX_HISTORY_MESSAGES = 20
# 内存里最多保留的会话数，超出按最久未使用淘汰
MAX_CONVERSATIONS = 200

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_containers",
            "description": "列出所有靶机容器及其运行状态，用于确认可用靶场环境。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_container_status",
            "description": "查询指定靶机容器的详细状态；不传容器名则返回全部容器状态。",
            "parameters": {
                "type": "object",
                "properties": {
                    "container_name": {
                        "type": "string",
                        "description": "容器名称，例如 sqli-lab-web-1",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_container_logs",
            "description": "读取靶机容器最近的日志，用于判断学生进度或排查报错。",
            "parameters": {
                "type": "object",
                "properties": {
                    "container_name": {"type": "string", "description": "容器名称"},
                    "tail": {
                        "type": "integer",
                        "description": "读取最近多少行，默认 50",
                    },
                },
                "required": ["container_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_container",
            "description": "启动已停止的靶机容器。",
            "parameters": {
                "type": "object",
                "properties": {
                    "container_name": {"type": "string", "description": "容器名称"}
                },
                "required": ["container_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop_container",
            "description": "停止靶机容器，学生做完实验想释放环境时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "container_name": {"type": "string", "description": "容器名称"}
                },
                "required": ["container_name"],
            },
        },
    },
]

_conversations: "OrderedDict[str, list[dict[str, Any]]]" = OrderedDict()


def _load_history(conversation_id: str) -> list[dict[str, Any]]:
    history = _conversations.get(conversation_id)
    if history is None:
        return []
    _conversations.move_to_end(conversation_id)
    return list(history)


def _save_history(conversation_id: str, question: str, answer: str) -> None:
    if not answer:
        return
    history = _conversations.get(conversation_id, [])
    history = history + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]
    _conversations[conversation_id] = history[-MAX_HISTORY_MESSAGES:]
    _conversations.move_to_end(conversation_id)
    while len(_conversations) > MAX_CONVERSATIONS:
        _conversations.popitem(last=False)


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _build_question(query: str, inputs: Optional[dict[str, Any]]) -> str:
    """把前端携带的上下文（关卡、容器等）拼进用户消息，等价于 Dify 的 inputs 变量。"""
    context = {key: value for key, value in (inputs or {}).items() if value not in (None, "", {}, [])}
    if not context:
        return query
    return f"{query}\n\n【当前实验上下文】{json.dumps(context, ensure_ascii=False)}"


def _parse_arguments(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


async def _execute_tool(name: str, raw_arguments: str) -> str:
    """执行工具并返回给模型的观察结果文本。docker SDK 是同步阻塞的，放线程池执行。"""
    arguments = _parse_arguments(raw_arguments)
    container_name = str(arguments.get("container_name") or "").strip()
    try:
        if name == "list_containers":
            result = await asyncio.to_thread(docker_tools.list_containers)
        elif name == "get_container_status":
            result = await asyncio.to_thread(docker_tools.get_container_status, container_name or None)
        elif name == "get_container_logs":
            tail = arguments.get("tail")
            result = await asyncio.to_thread(
                docker_tools.get_container_logs,
                container_name,
                int(tail) if isinstance(tail, (int, str)) and str(tail).isdigit() else 50,
            )
        elif name == "start_container":
            result = await asyncio.to_thread(docker_tools.start_container, container_name)
        elif name == "stop_container":
            result = await asyncio.to_thread(docker_tools.stop_container, container_name)
        else:
            result = {"success": False, "error": f"未知工具 {name}"}
    except Exception as exc:
        result = {"success": False, "error": f"{type(exc).__name__}: {exc}"}
    return json.dumps(result, ensure_ascii=False, default=str)[:MAX_OBSERVATION_CHARS]


async def stream_assistant_reply(
    query: str,
    *,
    user: str = "student",
    conversation_id: Optional[str] = None,
    inputs: Optional[dict[str, Any]] = None,
) -> AsyncIterator[str]:
    """产出 Dify 形状的 SSE 事件流，供 /api/chat 直接转发给前端。"""
    cid = (conversation_id or "").strip() or uuid.uuid4().hex
    # 历史按「用户 + 会话」隔离，前端只感知 cid
    history_key = f"{user or 'student'}:{cid}"
    question = _build_question(query, inputs)
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(_load_history(history_key))
    messages.append({"role": "user", "content": question})

    answer_parts: list[str] = []
    try:
        async with new_async_client(timeout=LLM_TIMEOUT_SECONDS * 2) as client:
            for round_index in range(MAX_TOOL_ROUNDS + 1):
                # 最后一轮不再给工具，强制模型用已有观察结果作答，避免无限调用
                tools = TOOL_SPECS if round_index < MAX_TOOL_ROUNDS else None
                round_text: list[str] = []
                pending: list[dict[str, str]] = []

                async for kind, value in stream_round(client, messages, tools=tools):
                    if kind == "delta":
                        round_text.append(value)
                        answer_parts.append(value)
                        yield _sse({"event": "agent_message", "conversation_id": cid, "answer": value})
                    elif kind == "tool_calls":
                        pending = value

                if not pending:
                    break

                messages.append({
                    "role": "assistant",
                    "content": "".join(round_text),
                    "tool_calls": [
                        {
                            "id": call["id"] or f"call_{round_index}_{index}",
                            "type": "function",
                            "function": {
                                "name": call["name"],
                                "arguments": call["arguments"] or "{}",
                            },
                        }
                        for index, call in enumerate(pending)
                    ],
                })

                for index, call in enumerate(pending):
                    call_id = call["id"] or f"call_{round_index}_{index}"
                    thought = {
                        "event": "agent_thought",
                        "id": call_id,
                        "conversation_id": cid,
                        "tool": call["name"],
                        "tool_input": call["arguments"] or "{}",
                        "observation": "",
                    }
                    yield _sse(thought)
                    observation = await _execute_tool(call["name"], call["arguments"])
                    yield _sse({**thought, "observation": observation})
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": observation,
                    })
    except (LLMError, httpx.HTTPError) as exc:
        yield _sse({"event": "error", "conversation_id": cid, "message": f"AI 服务调用失败：{exc}"})
        return
    except Exception as exc:
        yield _sse({
            "event": "error",
            "conversation_id": cid,
            "message": f"AI 服务异常：{type(exc).__name__}: {exc}",
        })
        return

    answer = "".join(answer_parts).strip()
    _save_history(history_key, question, answer)
    yield _sse({
        "event": "message_end",
        "conversation_id": cid,
        "id": uuid.uuid4().hex,
        "metadata": {"usage": {}},
    })
