from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

from app.services.llm import LLMGateway

DEMO_REPLY = (
    "当前未配置模型 Key，已使用演示模式。"
    "你可以继续描述想创建的应用或需要修改的地方；配置模型后可进行正常对话。"
)
FALLBACK_REPLY = "我在。可以直接描述你想创建的应用，或需要修改的地方。"
MAX_HISTORY = 8

_CHAT_SYSTEM = """你是 Atom Demo 的应用生成助手，现在和用户进行普通对话。
请用中文自然、简洁地回应，最多三句话。
不要声称已经修改、创建或删除应用；不要输出代码或文件内容。
如果用户随后提出应用需求，提醒他直接描述想要的应用或修改，工作区会切换到生成流程。
当前项目：{title}
当前状态：{state}"""


def build_chat_messages(
    *,
    title: str,
    has_files: bool,
    history: Sequence[tuple[str, str]],
    message: str,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": _CHAT_SYSTEM.format(
                title=title or "未命名应用",
                state="已有生成文件" if has_files else "尚未生成",
            ),
        }
    ]
    for role, content in history[-MAX_HISTORY:]:
        if role in ("user", "assistant") and content.strip():
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})
    return messages


async def stream_reply(
    messages: Sequence[dict[str, Any]],
    gateway: LLMGateway | None,
) -> AsyncIterator[str]:
    if gateway is None:
        yield DEMO_REPLY
        return

    emitted = False
    async for chunk in gateway.stream_chat(messages=messages, tools=[], max_tokens=600):
        if chunk.content:
            emitted = True
            yield chunk.content
    if not emitted:
        yield FALLBACK_REPLY
