from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.ids import new_ulid
from app.db.models import Message, Project, Run, RunEvent

ACTIVE_STATUSES = ("queued", "running")
TERMINAL_STATUSES = ("succeeded", "failed", "cancelled")

_run_slots = asyncio.Semaphore(2)


async def find_active_run(session: AsyncSession, project_id: str) -> Run | None:
    result = await session.execute(
        select(Run)
        .where(Run.project_id == project_id, Run.status.in_(ACTIVE_STATUSES))
        .order_by(Run.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_run(session: AsyncSession, project: Project, message: str) -> Run:
    active = await find_active_run(session, project.id)
    if active is not None:
        raise AppError(409, "run_in_progress", "该项目已有生成任务在进行中")

    user_message = Message(project_id=project.id, role="user", content=message)
    session.add(user_message)
    await session.flush()

    run = Run(
        id=new_ulid(),
        project_id=project.id,
        user_message_id=user_message.id,
        status="queued",
    )
    session.add(run)
    user_message.run_id = run.id
    project.status = "queued"
    await session.commit()
    await session.refresh(run)

    asyncio.create_task(_run_guarded(run.id))
    return run


async def _run_guarded(run_id: str) -> None:
    from app.agent.orchestrator import execute_run

    async with _run_slots:
        await execute_run(run_id)


async def get_run(session: AsyncSession, run_id: str) -> Run:
    run = await session.get(Run, run_id)
    if run is None:
        raise AppError(404, "run_not_found", "生成任务不存在")
    return run


async def get_owned_run(session: AsyncSession, run_id: str, owner_id: str) -> tuple[Run, Project]:
    run = await get_run(session, run_id)
    project = await session.get(Project, run.project_id)
    if project is None or project.owner_id != owner_id:
        raise AppError(404, "run_not_found", "生成任务不存在")
    return run, project


async def list_events_after(
    session: AsyncSession, run_id: str, after_seq: int, limit: int = 200
) -> list[RunEvent]:
    result = await session.execute(
        select(RunEvent)
        .where(RunEvent.run_id == run_id, RunEvent.seq > after_seq)
        .order_by(RunEvent.seq.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def max_event_seq(session: AsyncSession, run_id: str) -> int:
    result = await session.execute(
        select(func.coalesce(func.max(RunEvent.seq), 0)).where(RunEvent.run_id == run_id)
    )
    return int(result.scalar_one())


class RunEmitter:
    def __init__(self, session: AsyncSession, run_id: str, start_seq: int) -> None:
        self._session = session
        self._run_id = run_id
        self._seq = start_seq

    @property
    def seq(self) -> int:
        return self._seq

    async def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        self._seq += 1
        self._session.add(
            RunEvent(run_id=self._run_id, seq=self._seq, type=event_type, payload=payload)
        )
        await self._session.commit()


async def mark_running(session: AsyncSession, run: Run, project: Project) -> None:
    run.status = "running"
    run.started_at = datetime.now(UTC)
    project.status = "running"
    await session.commit()


async def cancel_run(session: AsyncSession, run: Run, project: Project) -> None:
    if run.status in TERMINAL_STATUSES:
        raise AppError(409, "run_finished", "任务已结束，无法取消")
    run.status = "cancelled"
    run.finished_at = datetime.now(UTC)
    project.status = "idle"
    await session.commit()


async def latest_run(session: AsyncSession, project_id: str) -> Run | None:
    result = await session.execute(
        select(Run).where(Run.project_id == project_id).order_by(Run.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


def recent_messages(messages: Sequence[Message], limit: int = 12) -> list[Message]:
    return list(messages[-limit:])


async def is_run_cancelled(session: AsyncSession, run_id: str) -> bool:
    result = await session.execute(select(Run.status).where(Run.id == run_id))
    return result.scalar_one_or_none() == "cancelled"
