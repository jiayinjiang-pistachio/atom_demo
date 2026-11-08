from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, select

from app.agent.orchestrator import execute_run
from app.agent.tools import AgentTools
from app.core.ids import new_ulid
from app.db.models import Guest, Message, Project, ProjectVersion, Run, RunEvent
from app.db.session import SessionFactory
from app.services.guests import create_guest
from app.services.llm.base import LLMGateway, StreamChunk, ToolCallDelta
from app.services.projects import create_project


@dataclass
class FlowContext:
    token: str
    guest_id: str
    project_id: str
    run_id: str


class ScriptedProvider:
    def __init__(self) -> None:
        self._turns = [
            [
                StreamChunk(
                    content="先规划，再写文件。",
                    tool_calls=[
                        ToolCallDelta(
                            index=0,
                            id="call-plan",
                            name="update_plan",
                            arguments=json.dumps(
                                {
                                    "steps": [
                                        {"title": "规划页面", "status": "done"},
                                        {"title": "写入文件", "status": "in_progress"},
                                    ]
                                },
                                ensure_ascii=False,
                            ),
                        )
                    ],
                    finish_reason="tool_calls",
                )
            ],
            [_write_turn("call-html", "index.html", _HTML)],
            [_write_turn("call-css", "styles.css", _CSS)],
            [_write_turn("call-js", "app.js", _JS)],
            [
                StreamChunk(
                    tool_calls=[
                        ToolCallDelta(
                            index=0,
                            id="call-finish",
                            name="finish",
                            arguments=json.dumps({"summary": "看板应用已生成"}, ensure_ascii=False),
                        )
                    ],
                    finish_reason="tool_calls",
                )
            ],
        ]
        self._cursor = 0

    async def stream_chat(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        max_tokens: int,
    ) -> AsyncIterator[StreamChunk]:
        if self._cursor >= len(self._turns):
            return
        chunks = self._turns[self._cursor]
        self._cursor += 1
        for chunk in chunks:
            yield chunk


class TruncatingProvider(ScriptedProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0
        self.saw_nudge = False

    async def stream_chat(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        max_tokens: int,
    ) -> AsyncIterator[StreamChunk]:
        self.calls += 1
        if any("上一条输出因长度限制被截断" in str(item["content"]) for item in messages):
            self.saw_nudge = True
        if self.calls == 1:
            yield StreamChunk(content="尝试一次写完整页面", finish_reason="length")
            return
        async for chunk in super().stream_chat(
            messages=messages, tools=tools, max_tokens=max_tokens
        ):
            yield chunk


class RewritingProvider:
    """Writes a valid app once, then keeps rewriting app.js with identical content."""

    def __init__(self) -> None:
        self.calls = 0

    async def stream_chat(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        max_tokens: int,
    ) -> AsyncIterator[StreamChunk]:
        self.calls += 1
        if self.calls == 1:
            yield _write_turn("call-html", "index.html", _HTML)
            return
        if self.calls == 2:
            yield _write_turn("call-css", "styles.css", _CSS)
            return
        yield _write_turn(f"call-js-{self.calls}", "app.js", _JS)


def _write_turn(call_id: str, path: str, content: str) -> StreamChunk:
    return StreamChunk(
        tool_calls=[
            ToolCallDelta(
                index=0,
                id=call_id,
                name="write_file",
                arguments=json.dumps({"path": path, "content": content}, ensure_ascii=False),
            )
        ],
        finish_reason="tool_calls",
    )


_HTML = """<!doctype html>
<html><head><link rel="stylesheet" href="styles.css"></head>
<body><main id="app"></main><script src="app.js"></script></body></html>
"""
_CSS = "body{margin:0;font-family:system-ui}#app{min-height:40vh}"
_JS = "document.getElementById('app').textContent='board ready'"


async def _database_available() -> tuple[bool, str]:
    try:
        async with SessionFactory() as session:
            await session.execute(select(Project).limit(1))
        return True, ""
    except Exception as exc:
        return False, repr(exc)


@pytest_asyncio.fixture
async def flow(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[FlowContext]:
    available, reason = await _database_available()
    if not available:
        pytest.skip(f"MySQL is not available; integration tests need the real database ({reason})")

    async with SessionFactory() as session:
        token, guest = await create_guest(session)
        project = await create_project(session, guest.id, "做一个任务看板", "测试看板")
        user_message = Message(project_id=project.id, role="user", content="做一个任务看板")
        session.add(user_message)
        await session.flush()
        run = Run(
            id=new_ulid(),
            project_id=project.id,
            user_message_id=user_message.id,
            status="queued",
        )
        session.add(run)
        await session.commit()

    monkeypatch.setattr("app.agent.orchestrator.resolve_mode", lambda: "live")
    await execute_run(run.id, gateway=LLMGateway(ScriptedProvider()))

    context = FlowContext(
        token=token,
        guest_id=guest.id,
        project_id=project.id,
        run_id=run.id,
    )
    yield context

    async with SessionFactory() as session:
        await session.execute(delete(Guest).where(Guest.id == guest.id))
        await session.commit()


async def test_output_truncation_retries_with_smaller_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    available, reason = await _database_available()
    if not available:
        pytest.skip(f"MySQL is not available; integration tests need the real database ({reason})")

    async with SessionFactory() as session:
        _token, guest = await create_guest(session)
        project = await create_project(session, guest.id, "做一个任务看板", "测试看板")
        user_message = Message(project_id=project.id, role="user", content="做一个任务看板")
        session.add(user_message)
        await session.flush()
        run = Run(
            id=new_ulid(),
            project_id=project.id,
            user_message_id=user_message.id,
            status="queued",
        )
        session.add(run)
        await session.commit()
        run_id = run.id
        project_id = project.id
        guest_id = guest.id

    monkeypatch.setattr("app.agent.orchestrator.resolve_mode", lambda: "live")
    provider = TruncatingProvider()
    await execute_run(run_id, gateway=LLMGateway(provider))

    try:
        async with SessionFactory() as session:
            stored = await session.get(Run, run_id)
            stored_project = await session.get(Project, project_id)

        assert provider.calls > 1
        assert provider.saw_nudge is True
        assert stored is not None and stored.status == "succeeded"
        assert stored_project is not None and stored_project.current_version == 1
    finally:
        async with SessionFactory() as session:
            await session.execute(delete(Guest).where(Guest.id == guest_id))
            await session.commit()


async def test_repeated_writes_are_finalized_instead_of_hitting_step_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    available, reason = await _database_available()
    if not available:
        pytest.skip(f"MySQL is not available; integration tests need the real database ({reason})")

    async with SessionFactory() as session:
        _token, guest = await create_guest(session)
        project = await create_project(session, guest.id, "做一个任务看板", "测试看板")
        user_message = Message(project_id=project.id, role="user", content="做一个任务看板")
        session.add(user_message)
        await session.flush()
        run = Run(
            id=new_ulid(),
            project_id=project.id,
            user_message_id=user_message.id,
            status="queued",
        )
        session.add(run)
        await session.commit()
        run_id = run.id
        project_id = project.id
        guest_id = guest.id

    monkeypatch.setattr("app.agent.orchestrator.resolve_mode", lambda: "live")
    provider = RewritingProvider()
    await execute_run(run_id, gateway=LLMGateway(provider))

    try:
        async with SessionFactory() as session:
            stored = await session.get(Run, run_id)
            stored_project = await session.get(Project, project_id)
            events = (
                (await session.execute(select(RunEvent).where(RunEvent.run_id == run_id)))
                .scalars()
                .all()
            )

        assert stored is not None and stored.status == "succeeded"
        assert stored_project is not None and stored_project.current_version == 1
        assert provider.calls < 24
        updated = [event for event in events if event.type == "file.updated"]
        assert len(updated) == 3
        assert {event.payload["path"] for event in updated} == {
            "index.html",
            "styles.css",
            "app.js",
        }
    finally:
        async with SessionFactory() as session:
            await session.execute(delete(Guest).where(Guest.id == guest_id))
            await session.commit()
def test_finish_keeps_full_summary() -> None:
    summary = "已生成完整应用。" + "功能说明。" * 120
    assert len(summary) > 500

    outcome = AgentTools._finish({"summary": summary})

    assert outcome.finished is True
    assert outcome.summary == summary


async def test_agent_flow_persists_files_and_version(flow: FlowContext) -> None:
    async with SessionFactory() as session:
        run = await session.get(Run, flow.run_id)
        project = await session.get(Project, flow.project_id)
        versions = (
            (
                await session.execute(
                    select(ProjectVersion).where(ProjectVersion.project_id == flow.project_id)
                )
            )
            .scalars()
            .all()
        )
        events = (
            (await session.execute(select(RunEvent).where(RunEvent.run_id == flow.run_id)))
            .scalars()
            .all()
        )

    assert run is not None and run.status == "succeeded"
    assert project is not None and project.current_version == 1
    assert len(versions) == 1
    assert set(versions[0].manifest["files"]) == {"index.html", "styles.css", "app.js"}
    event_types = {event.type for event in events}
    assert {"run.status", "plan.updated", "file.updated", "preview.ready", "usage"} <= event_types


async def test_run_requires_owner(client: AsyncClient, flow: FlowContext) -> None:
    response = await client.get(
        f"/api/v1/runs/{flow.run_id}/events",
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == 401


async def test_sse_replay_contains_terminal_event(client: AsyncClient, flow: FlowContext) -> None:
    response = await client.get(
        f"/api/v1/runs/{flow.run_id}/events?after_seq=0",
        headers={"Authorization": f"Bearer {flow.token}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: preview.ready" in response.text
    assert '"status":"succeeded"' in response.text


async def test_sse_pushes_events_committed_while_streaming(
    client: AsyncClient, flow: FlowContext
) -> None:
    live_run = Run(
        id=new_ulid(),
        project_id=flow.project_id,
        user_message_id=None,
        status="queued",
    )
    async with SessionFactory() as session:
        session.add(live_run)
        await session.commit()

    streaming = asyncio.create_task(
        client.get(
            f"/api/v1/runs/{live_run.id}/events?after_seq=0",
            headers={"Authorization": f"Bearer {flow.token}"},
        )
    )
    await asyncio.sleep(0.4)

    async with SessionFactory() as session:
        session.add_all(
            [
                RunEvent(
                    run_id=live_run.id,
                    seq=1,
                    type="assistant.delta",
                    payload={"text": "实时输出"},
                ),
                RunEvent(
                    run_id=live_run.id,
                    seq=2,
                    type="file.updated",
                    payload={"path": "index.html", "size": 10, "deleted": False},
                ),
                RunEvent(
                    run_id=live_run.id,
                    seq=3,
                    type="run.status",
                    payload={"status": "succeeded"},
                ),
            ]
        )
        stored = await session.get(Run, live_run.id)
        assert stored is not None
        stored.status = "succeeded"
        await session.commit()

    response = await asyncio.wait_for(streaming, timeout=5.0)

    assert response.status_code == 200
    assert "event: assistant.delta" in response.text
    assert "event: file.updated" in response.text
    assert '"status":"succeeded"' in response.text


async def test_preview_serves_version_file(client: AsyncClient, flow: FlowContext) -> None:
    response = await client.get(
        f"/preview/{flow.project_id}/1/index.html",
        headers={"Host": "localhost"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "board ready" not in response.text
    assert "app.js" in response.text
    assert "frame-ancestors" in response.headers["content-security-policy"]


async def test_preview_rejects_wrong_host(client: AsyncClient, flow: FlowContext) -> None:
    response = await client.get(
        f"/preview/{flow.project_id}/1/index.html",
        headers={"Host": "evil.example.com"},
    )

    assert response.status_code == 404


async def test_preview_rejects_path_traversal(client: AsyncClient, flow: FlowContext) -> None:
    response = await client.get(
        f"/preview/{flow.project_id}/1/%2E%2E/index.html",
        headers={"Host": "localhost"},
    )

    assert response.status_code == 404


async def test_file_tool_rejects_escaping_project() -> None:
    from app.core.errors import AppError
    from app.services import vfs

    with pytest.raises(AppError):
        vfs.validate_path("../../etc/passwd")
