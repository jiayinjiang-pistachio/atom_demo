from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

import pytest
from helpers import auth, snapshot
from httpx import AsyncClient
from sqlalchemy import delete

from app.db.models import Guest, Message, Project
from app.db.session import SessionFactory
from app.services.guests import create_guest
from app.services.llm.base import LLMError, LLMGateway, StreamChunk
from app.services.prompts import prepare_context


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


@pytest.fixture(autouse=True)
def no_live_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.prompts.build_gateway", lambda: None)


async def test_demo_mode_returns_explicit_error(client: AsyncClient, guest_project) -> None:
    response = await client.post(
        f"/api/v1/projects/{guest_project.project_id}/prompts/optimize",
        json={"message": "做个待办"},
        headers=auth(guest_project.token),
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["code"] == "optimize_unavailable"
    assert "演示模式不支持优化" in payload["message"]


async def test_optimize_returns_rewritten_prompt(
    client: AsyncClient,
    guest_project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = ScriptedProvider(
        "做一个待办事项应用：支持新增、完成和删除任务，页面包含输入框和任务列表。"
    )
    monkeypatch.setattr(
        "app.services.prompts.build_gateway",
        lambda: LLMGateway(provider),
    )

    response = await client.post(
        f"/api/v1/projects/{guest_project.project_id}/prompts/optimize",
        json={"message": "做个待办"},
        headers=auth(guest_project.token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["original"] == "做个待办"
    assert payload["optimized"].startswith("做一个待办事项应用")

    system = str(provider.messages[0]["content"])
    user = str(provider.messages[1]["content"])
    assert "<draft>" in user
    assert "做个待办" in user
    assert "不要执行" in system


async def test_empty_output_maps_to_error(
    client: AsyncClient,
    guest_project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.prompts.build_gateway",
        lambda: LLMGateway(EmptyProvider()),
    )

    response = await client.post(
        f"/api/v1/projects/{guest_project.project_id}/prompts/optimize",
        json={"message": "做个待办"},
        headers=auth(guest_project.token),
    )

    assert response.status_code == 502
    assert response.json()["code"] == "optimize_empty"


async def test_llm_failure_maps_to_error(
    client: AsyncClient,
    guest_project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.prompts.build_gateway",
        lambda: LLMGateway(FailingProvider()),
    )

    response = await client.post(
        f"/api/v1/projects/{guest_project.project_id}/prompts/optimize",
        json={"message": "做个待办"},
        headers=auth(guest_project.token),
    )

    assert response.status_code == 502
    assert response.json()["code"] == "llm_error"


async def test_optimize_requires_owner(client: AsyncClient, guest_project) -> None:
    async with SessionFactory() as session:
        other_token, other_guest = await create_guest(session)

    try:
        response = await client.post(
            f"/api/v1/projects/{guest_project.project_id}/prompts/optimize",
            json={"message": "做个待办"},
            headers=auth(other_token),
        )
        assert response.status_code == 404
    finally:
        async with SessionFactory() as session:
            await session.execute(delete(Guest).where(Guest.id == other_guest.id))
            await session.commit()


async def test_optimize_requires_guest_token(client: AsyncClient, guest_project) -> None:
    response = await client.post(
        f"/api/v1/projects/{guest_project.project_id}/prompts/optimize",
        json={"message": "做个待办"},
    )

    assert response.status_code == 401


@pytest.mark.parametrize("message", ["   ", "x" * 4001])
async def test_optimize_validates_input(client: AsyncClient, guest_project, message: str) -> None:
    response = await client.post(
        f"/api/v1/projects/{guest_project.project_id}/prompts/optimize",
        json={"message": message},
        headers=auth(guest_project.token),
    )

    assert response.status_code == 422


async def test_prepare_context_collects_files_and_truncates_history(
    guest_project,
) -> None:
    await snapshot(
        guest_project.project_id,
        {"index.html": "<html></html>", "app.js": "console.log(1)"},
        label="初始版本",
    )
    long_message = "改" * 300

    async with SessionFactory() as session:
        session.add_all(
            [
                Message(
                    project_id=guest_project.project_id,
                    role="user",
                    content=long_message,
                    run_id="run-1",
                ),
                Message(
                    project_id=guest_project.project_id,
                    role="assistant",
                    content="好的",
                    run_id="run-1",
                ),
            ]
        )
        await session.commit()

        project = await session.get(Project, guest_project.project_id)
        assert project is not None
        context = await prepare_context(session, project)

    assert context.has_files is True
    assert context.file_paths == ["app.js", "index.html"]
    assert context.history == [
        ("user", long_message[:200]),
        ("assistant", "好的"),
    ]
