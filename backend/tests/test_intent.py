from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

import pytest

from app.services.intent import classify, classify_rule
from app.services.llm.base import LLMError, LLMGateway, StreamChunk


class ScriptedIntentProvider:
    def __init__(self, output: str) -> None:
        self._output = output

    async def stream_chat(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        max_tokens: int,
    ) -> AsyncIterator[StreamChunk]:
        yield StreamChunk(content=self._output)


class FailingIntentProvider:
    async def stream_chat(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        max_tokens: int,
    ) -> AsyncIterator[StreamChunk]:
        yield StreamChunk()
        raise LLMError("模型不可用")


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("你好", "chat"),
        ("谢谢！", "chat"),
        ("今天天气怎么样？", "chat"),
        ("1+1等于几？", "chat"),
        ("帮我做一个任务看板", "build"),
        ("把背景改成蓝色", "build"),
        ("修改 index.html 的标题", "build"),
        ("页面太丑了", None),
    ],
)
def test_classify_rule(message: str, expected: str | None) -> None:
    assert classify_rule(message) == expected


@pytest.mark.asyncio
async def test_ambiguous_message_uses_llm_review_for_chat() -> None:
    gateway = LLMGateway(ScriptedIntentProvider("CHAT"))

    intent = await classify(
        "页面太丑了",
        gateway=gateway,
        project_title="任务看板",
        has_files=True,
    )

    assert intent == "chat"


@pytest.mark.asyncio
async def test_ambiguous_message_uses_llm_review_for_build() -> None:
    gateway = LLMGateway(ScriptedIntentProvider("BUILD"))

    intent = await classify(
        "页面太丑了",
        gateway=gateway,
        project_title="任务看板",
        has_files=True,
    )

    assert intent == "build"


@pytest.mark.asyncio
async def test_ambiguous_message_defaults_to_build_without_llm() -> None:
    intent = await classify(
        "页面太丑了",
        gateway=None,
        project_title="任务看板",
        has_files=True,
    )

    assert intent == "build"


@pytest.mark.asyncio
async def test_llm_failure_defaults_to_build() -> None:
    gateway = LLMGateway(FailingIntentProvider())

    intent = await classify(
        "页面太丑了",
        gateway=gateway,
        project_title="任务看板",
        has_files=True,
    )

    assert intent == "build"
