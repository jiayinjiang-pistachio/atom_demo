from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def merge(self, other: Usage) -> None:
        self.prompt_tokens = max(self.prompt_tokens, other.prompt_tokens)
        self.completion_tokens = max(self.completion_tokens, other.completion_tokens)


@dataclass(slots=True)
class ToolCallDelta:
    index: int
    id: str | None = None
    name: str | None = None
    arguments: str | None = None


@dataclass(slots=True)
class StreamChunk:
    content: str = ""
    tool_calls: list[ToolCallDelta] = field(default_factory=list)
    finish_reason: str | None = None
    usage: Usage | None = None


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass(slots=True)
class LLMResponse:
    content: str
    tool_calls: list[ToolCall]
    finish_reason: str | None
    usage: Usage


class LLMError(Exception):
    def __init__(self, message: str, *, transient: bool = False) -> None:
        super().__init__(message)
        self.transient = transient


class ChatProvider(Protocol):
    def stream_chat(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        max_tokens: int,
    ) -> AsyncIterator[StreamChunk]: ...


class LLMGateway:
    """Retries only transient failures that happen before any chunk was emitted."""

    def __init__(self, provider: ChatProvider, *, max_attempts: int = 3) -> None:
        self._provider = provider
        self._max_attempts = max_attempts

    async def stream_chat(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        max_tokens: int,
    ) -> AsyncIterator[StreamChunk]:
        for attempt in range(self._max_attempts):
            emitted = False
            try:
                async for chunk in self._provider.stream_chat(
                    messages=messages, tools=tools, max_tokens=max_tokens
                ):
                    emitted = True
                    yield chunk
                return
            except LLMError as exc:
                if emitted or not exc.transient or attempt + 1 >= self._max_attempts:
                    raise
                await asyncio.sleep(0.5 * (2**attempt))


class MessageAccumulator:
    def __init__(self) -> None:
        self.content = ""
        self._calls: dict[int, dict[str, str]] = {}
        self.finish_reason: str | None = None
        self.usage = Usage()

    def absorb(self, chunk: StreamChunk) -> str:
        if chunk.content:
            self.content += chunk.content
        for delta in chunk.tool_calls:
            slot = self._calls.setdefault(delta.index, {"id": "", "name": "", "arguments": ""})
            if delta.id:
                slot["id"] += delta.id
            if delta.name:
                slot["name"] += delta.name
            if delta.arguments:
                slot["arguments"] += delta.arguments
        if chunk.usage is not None:
            self.usage.merge(chunk.usage)
        if chunk.finish_reason is not None:
            self.finish_reason = chunk.finish_reason
        return chunk.content

    def response(self) -> LLMResponse:
        tool_calls = [
            ToolCall(id=slot["id"], name=slot["name"], arguments=slot["arguments"])
            for _, slot in sorted(self._calls.items())
            if slot["name"]
        ]
        return LLMResponse(
            content=self.content,
            tool_calls=tool_calls,
            finish_reason=self.finish_reason,
            usage=self.usage,
        )
