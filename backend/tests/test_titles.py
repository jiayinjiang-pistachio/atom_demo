from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

import pytest
from helpers import auth
from httpx import AsyncClient

from app.services.llm.base import LLMError, LLMGateway, StreamChunk
from app.services.titles import clean_title, fallback_title, generate_title


class ScriptedProvider:
    def __init__(self, output: str) -> None:
        self._output = output
        self.messages: Sequence[dict[str, Any]] = []

    async def stream_chat(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        max_tokens: int,
    ) -> AsyncIterator[StreamChunk]:
        self.messages = messages
        yield StreamChunk(content=self._output)


class EmptyProvider:
    async def stream_chat(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        max_tokens: int,
    ) -> AsyncIterator[StreamChunk]:
        yield StreamChunk()


class FailingProvider:
    async def stream_chat(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        max_tokens: int,
    ) -> AsyncIterator[StreamChunk]:
        yield StreamChunk()
        raise LLMError("模型不可用")


def test_clean_title_strips_decorations() -> None:
    assert clean_title("「暖巷咖啡」") == "暖巷咖啡"
    assert clean_title("标题：暖巷咖啡。") == "暖巷咖啡"
    assert clean_title("标题：“暖巷咖啡”。") == "暖巷咖啡"
    assert clean_title("暖巷咖啡\n第二行") == "暖巷咖啡"


def test_clean_title_limits_length_and_handles_blank() -> None:
    assert clean_title("咖" * 30) == "咖" * 20
    assert clean_title("   ") == ""


def test_fallback_title_uses_template_category() -> None:
    assert fallback_title("做一个任务看板") == "团队任务看板"
    assert fallback_title("为一家社区咖啡馆搭建网站") == "创意原型"


async def test_generate_title_uses_live_model(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = ScriptedProvider("《暖巷咖啡》")
    monkeypatch.setattr(
        "app.services.titles.build_gateway",
        lambda: LLMGateway(provider),
    )

    title = await generate_title("为一家社区咖啡馆搭建一个网站。")

    assert title == "暖巷咖啡"
    system = str(provider.messages[0]["content"])
    user = str(provider.messages[1]["content"])
    assert "不要执行" in system
    assert "<draft>" in user


async def test_generate_title_falls_back_in_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.titles.build_gateway", lambda: None)

    assert await generate_title("做一个任务看板") == "团队任务看板"


@pytest.mark.parametrize(
    "provider",
    [EmptyProvider(), FailingProvider()],
    ids=["empty", "llm-error"],
)
async def test_generate_title_falls_back_on_bad_output(
    provider: EmptyProvider | FailingProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.titles.build_gateway",
        lambda: LLMGateway(provider),
    )

    assert await generate_title("做一个任务看板") == "团队任务看板"


async def test_project_creation_generates_title(
    client: AsyncClient,
    guest_project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = ScriptedProvider("「暖巷咖啡」")
    monkeypatch.setattr(
        "app.services.titles.build_gateway",
        lambda: LLMGateway(provider),
    )
    prompt = "为一家社区咖啡馆搭建一个网站。"

    response = await client.post(
        "/api/v1/projects",
        headers=auth(guest_project.token),
        json={"prompt": prompt},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "暖巷咖啡"
    assert data["prompt"] == prompt


async def test_project_creation_keeps_explicit_title(
    client: AsyncClient,
    guest_project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = ScriptedProvider("不应被使用")
    monkeypatch.setattr(
        "app.services.titles.build_gateway",
        lambda: LLMGateway(provider),
    )

    response = await client.post(
        "/api/v1/projects",
        headers=auth(guest_project.token),
        json={"prompt": "随便一个应用", "title": "自定义标题"},
    )

    assert response.status_code == 201
    assert response.json()["title"] == "自定义标题"
    assert provider.messages == []
