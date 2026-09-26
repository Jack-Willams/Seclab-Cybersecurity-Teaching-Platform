"""LLM 供应商适配层。

本服务原先只对接 Dify 的 /chat-messages。配置 LLM_API_KEY 之后，AI 能力改为直连
OpenAI 兼容接口（DeepSeek 等）的 /chat/completions，并把结果整理成调用方原本期望
的形状：阻塞调用返回答案文本（对应 Dify 的 answer 字段），流式调用产出增量文本与
工具调用，交由上层包装成 Dify 形状的 SSE 事件。
"""
from typing import Any, AsyncIterator, Optional

import json

import httpx

from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL, LLM_PROVIDER, LLM_TIMEOUT_SECONDS


class LLMError(RuntimeError):
    """直连模型调用失败。"""


def direct_llm_enabled() -> bool:
    """是否直连 OpenAI 兼容模型。LLM_PROVIDER=dify 可在保留 key 的前提下切回 Dify。"""
    if LLM_PROVIDER == "dify":
        return False
    return bool(LLM_API_KEY.strip())


def model_label() -> str:
    """健康探测与日志用的可读标识，不含密钥。"""
    return f"{LLM_MODEL} @ {LLM_API_BASE}"


def _endpoint(path: str) -> str:
    return f"{LLM_API_BASE.rstrip('/')}/{path.lstrip('/')}"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {LLM_API_KEY.strip()}",
        "Content-Type": "application/json",
    }


def new_async_client(**kwargs: Any) -> httpx.AsyncClient:
    """构造 httpx 客户端，并兜住代理环境变量带来的构造期失败。

    机器设了 ALL_PROXY=socks5://... 但没装 httpx[socks] 时，httpx 在构造阶段就抛
    ImportError（不是 HTTPError），整条 AI 链路会以「未知异常」形式挂掉。这里退回
    不读环境代理的模式：模型接口本身直连可达，不该被代理配置拖垮。
    """
    try:
        return httpx.AsyncClient(**kwargs)
    except ImportError:
        return httpx.AsyncClient(trust_env=False, **kwargs)


def _build_payload(
    messages: list[dict[str, Any]],
    *,
    tools: Optional[list[dict[str, Any]]] = None,
    stream: bool = False,
    temperature: float = 0.3,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": LLM_MODEL,
        "messages": messages,
        "stream": stream,
        "temperature": temperature,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    return payload


def build_messages(prompt: str, system: Optional[str] = None) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return messages


def extract_answer(payload: dict[str, Any]) -> str:
    """从 /chat/completions 响应里取出正文，缺字段时返回空串由调用方判定。"""
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return str(message.get("content") or "").strip()


async def complete_text(
    prompt: str,
    *,
    system: Optional[str] = None,
    timeout: Optional[float] = None,
    temperature: float = 0.3,
) -> str:
    """阻塞式调用，返回答案文本。结构化输出仍由调用方各自的 JSON 抽取逻辑处理。"""
    if not direct_llm_enabled():
        raise LLMError("LLM API is not configured")
    async with new_async_client(timeout=timeout or LLM_TIMEOUT_SECONDS) as client:
        response = await client.post(
            _endpoint("chat/completions"),
            headers=_headers(),
            json=_build_payload(build_messages(prompt, system), temperature=temperature),
        )
        response.raise_for_status()
        payload = response.json()
    answer = extract_answer(payload)
    if not answer:
        raise LLMError("LLM response has no answer")
    return answer


async def stream_round(
    client: httpx.AsyncClient,
    messages: list[dict[str, Any]],
    *,
    tools: Optional[list[dict[str, Any]]] = None,
    temperature: float = 0.3,
) -> AsyncIterator[tuple[str, Any]]:
    """流式读取一轮对话。

    依次产出 ("delta", 增量文本)；若本轮模型要求调用工具，则在流结束后产出一条
    ("tool_calls", [{"id", "name", "arguments"}, ...])。工具调用在 SSE 里是按
    index 分片下发的，这里按 index 累加还原成完整的函数名与参数 JSON。
    """
    tool_calls: dict[int, dict[str, str]] = {}
    async with client.stream(
        "POST",
        _endpoint("chat/completions"),
        headers=_headers(),
        json=_build_payload(messages, tools=tools, stream=True, temperature=temperature),
    ) as response:
        if response.status_code != 200:
            body = await response.aread()
            raise LLMError(body.decode("utf-8", errors="replace")[:500])
        async for raw_line in response.aiter_lines():
            line = raw_line.strip()
            if not line.startswith("data:"):
                continue
            data_text = line.removeprefix("data:").strip()
            if not data_text or data_text == "[DONE]":
                continue
            try:
                chunk = json.loads(data_text)
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            content = delta.get("content")
            if content:
                yield "delta", str(content)
            for item in delta.get("tool_calls") or []:
                slot = tool_calls.setdefault(
                    int(item.get("index") or 0),
                    {"id": "", "name": "", "arguments": ""},
                )
                if item.get("id"):
                    slot["id"] = str(item["id"])
                function = item.get("function") or {}
                if function.get("name"):
                    slot["name"] += str(function["name"])
                if function.get("arguments"):
                    slot["arguments"] += str(function["arguments"])
    if tool_calls:
        yield "tool_calls", [tool_calls[index] for index in sorted(tool_calls)]


PROXY_ALLOWED_MODELS = {"deepseek-chat", "deepseek-reasoner"}


def resolve_proxy_model(model: Optional[str]) -> str:
    """代理端点只放行白名单模型，避免 8010 被当成免费 API 网关。"""
    candidate = str(model or "").strip()
    if candidate and (candidate == LLM_MODEL or candidate in PROXY_ALLOWED_MODELS):
        return candidate
    return LLM_MODEL


async def proxy_completions(payload: dict[str, Any]) -> AsyncIterator[bytes]:
    """把上游 /chat/completions 的 SSE 原样透传。

    前端聊天页用 OpenAI SDK 直连本服务，密钥留在服务端，深度思考用的
    reasoning_content 等字段不做改写，SDK 侧行为与直连供应商一致。
    """
    async with new_async_client(timeout=LLM_TIMEOUT_SECONDS * 3) as client:
        async with client.stream(
            "POST",
            _endpoint("chat/completions"),
            headers=_headers(),
            json=payload,
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                message = body.decode("utf-8", errors="replace")[:500]
                error = {"error": {"message": f"上游返回 {response.status_code}：{message}"}}
                yield f"data: {json.dumps(error, ensure_ascii=False)}\n\n".encode("utf-8")
                return
            async for chunk in response.aiter_bytes():
                yield chunk


async def complete_raw(payload: dict[str, Any]) -> dict[str, Any]:
    """非流式代理，返回上游原始 JSON。"""
    async with new_async_client(timeout=LLM_TIMEOUT_SECONDS * 3) as client:
        response = await client.post(_endpoint("chat/completions"), headers=_headers(), json=payload)
        response.raise_for_status()
        return response.json()


async def probe() -> dict[str, Any]:
    """健康探测：拉一次模型列表确认地址与 key 可用。永远返回 200 形状的字典。"""
    if not direct_llm_enabled():
        return {
            "configured": False,
            "providerReachable": False,
            "message": "LLM 尚未配置。",
        }
    try:
        async with new_async_client(timeout=httpx.Timeout(20.0, connect=8.0)) as client:
            response = await client.get(_endpoint("models"), headers=_headers())
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return {
            "configured": True,
            "providerReachable": False,
            "message": f"LLM 已配置（{model_label()}），但返回 {exc.response.status_code}，请检查 key 与地址。",
        }
    except httpx.HTTPError as exc:
        return {
            "configured": True,
            "providerReachable": False,
            "message": f"LLM 已配置（{model_label()}），但当前无法连接：{type(exc).__name__}。",
        }
    except Exception as exc:
        # 探测端点必须永远返回 200，否则未捕获异常会绕过 CORS 中间件
        return {
            "configured": True,
            "providerReachable": False,
            "message": f"LLM 已配置，但探测失败：{type(exc).__name__}: {exc}",
        }
    return {
        "configured": True,
        "providerReachable": True,
        "message": f"LLM 连接正常（{model_label()}）。",
    }
