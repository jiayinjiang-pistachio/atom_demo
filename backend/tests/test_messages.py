from __future__ import annotations

import pytest
from helpers import auth
from httpx import AsyncClient
from sqlalchemy import delete, select

from app.agent.orchestrator import _history
from app.db.models import Guest, Message, Project, ProjectVersion, Run
from app.db.session import SessionFactory
from app.services.guests import create_guest


@pytest.fixture(autouse=True)
def demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.messages.build_gateway", lambda: None)


async def test_chat_stream_persists_messages_without_run(
    client: AsyncClient, guest_project
) -> None:
    response = await client.post(
        f"/api/v1/projects/{guest_project.project_id}/messages/stream",
        json={"message": "你好"},
        headers=auth(guest_project.token),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: message.intent" in response.text
    assert '"kind":"chat"' in response.text
    assert "event: assistant.delta" in response.text
    assert "event: chat.done" in response.text
    assert "当前未配置模型 Key" in response.text

    async with SessionFactory() as session:
        project = await session.get(Project, guest_project.project_id)
        runs = list(
            (await session.execute(select(Run).where(Run.project_id == guest_project.project_id)))
            .scalars()
            .all()
        )
        versions = list(
            (
                await session.execute(
                    select(ProjectVersion).where(
                        ProjectVersion.project_id == guest_project.project_id
                    )
                )
            )
            .scalars()
            .all()
        )
        messages = list(
            (
                await session.execute(
                    select(Message)
                    .where(Message.project_id == guest_project.project_id)
                    .order_by(Message.id.asc())
                )
            )
            .scalars()
            .all()
        )

    assert project is not None
    assert project.status == "idle"
    assert project.current_version is None
    assert runs == []
    assert versions == []
    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[0].content == "你好"
    assert messages[0].run_id is None
    assert messages[1].run_id is None


async def test_build_intent_creates_run(
    client: AsyncClient,
    guest_project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def noop(run_id: str) -> None:
        return None

    monkeypatch.setattr("app.services.runs._run_guarded", noop)

    response = await client.post(
        f"/api/v1/projects/{guest_project.project_id}/messages/stream",
        json={"message": "帮我做一个待办应用"},
        headers=auth(guest_project.token),
    )

    assert response.status_code == 200
    assert "event: message.intent" in response.text
    assert '"kind":"build"' in response.text

    async with SessionFactory() as session:
        project = await session.get(Project, guest_project.project_id)
        runs = list(
            (await session.execute(select(Run).where(Run.project_id == guest_project.project_id)))
            .scalars()
            .all()
        )
        messages = list(
            (
                await session.execute(
                    select(Message)
                    .where(Message.project_id == guest_project.project_id)
                    .order_by(Message.id.asc())
                )
            )
            .scalars()
            .all()
        )

    assert project is not None
    assert project.status == "queued"
    assert len(runs) == 1
    assert runs[0].status == "queued"
    assert runs[0].user_message_id is not None
    assert len(messages) == 1
    assert messages[0].role == "user"
    assert messages[0].run_id == runs[0].id


async def test_message_stream_requires_owner(client: AsyncClient, guest_project) -> None:
    async with SessionFactory() as session:
        other_token, other_guest = await create_guest(session)

    try:
        response = await client.post(
            f"/api/v1/projects/{guest_project.project_id}/messages/stream",
            json={"message": "你好"},
            headers=auth(other_token),
        )
        assert response.status_code == 404
    finally:
        async with SessionFactory() as session:
            await session.execute(delete(Guest).where(Guest.id == other_guest.id))
            await session.commit()


async def test_agent_history_excludes_chat_messages(guest_project) -> None:
    async with SessionFactory() as session:
        session.add_all(
            [
                Message(
                    project_id=guest_project.project_id,
                    role="user",
                    content="你好",
                    run_id=None,
                ),
                Message(
                    project_id=guest_project.project_id,
                    role="user",
                    content="做一个任务看板",
                    run_id="run-1",
                ),
            ]
        )
        await session.commit()
        history = await _history(session, guest_project.project_id)

    assert [message.content for message in history] == ["做一个任务看板"]
