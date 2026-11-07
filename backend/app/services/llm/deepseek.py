from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from typing import Any

import httpx

from app.services.llm.base import (
    LLMError,
    StreamChunk,
    ToolCallDelta,
    Usage,
)


class DeepSeekProvider:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        base_url: str,
        api_key: str,
        model: str,
    ) -> None:
        self._client = client
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._api_key = api_key
        self._model = model

    async def stream_chat(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        max_tokens: int,
    ) -> AsyncIterator[StreamChunk]:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": list(messages),
            "stream": True,
            "temperature": 0.3,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = list(tools)
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with self._client.stream(
            "POST", self._url, json=payload, headers=headers
        ) as response:
            if response.status_code != 200:
                body = (await response.aread()).decode("utf-8", "replace")[:300]
                raise LLMError(
                    f"DeepSeek 返回 {response.status_code}: {body}",
                    transient=response.status_code == 429 or response.status_code >= 500,
                )

            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError as exc:
                    raise LLMError("DeepSeek 流式响应格式异常") from exc
                yield self._parse_chunk(parsed)

    @staticmethod
    def _parse_chunk(payload: dict[str, Any]) -> StreamChunk:
        choices = payload.get("choices") or []
        if not choices:
            usage = payload.get("usage")
            return StreamChunk(usage=_parse_usage(usage)) if usage else StreamChunk()

        choice = choices[0]
        delta = choice.get("delta") or {}
        tool_calls = [
            ToolCallDelta(
                index=int(item.get("index", 0)),
                id=item.get("id"),
                name=(item.get("function") or {}).get("name"),
                arguments=(item.get("function") or {}).get("arguments"),
            )
            for item in delta.get("tool_calls") or []
        ]
        return StreamChunk(
            content=delta.get("content") or "",
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason"),
            usage=_parse_usage(payload.get("usage")),
        )


def _parse_usage(raw: dict[str, Any] | None) -> Usage | None:
    if not raw:
        return None
    return Usage(
        prompt_tokens=int(raw.get("prompt_tokens") or 0),
        completion_tokens=int(raw.get("completion_tokens") or 0),
    )
