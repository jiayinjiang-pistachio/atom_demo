from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_guest
from app.db.models import Guest, Run
from app.db.session import get_session
from app.schemas.run import RunCancelResponse, RunCreate, RunOut
from app.services import projects as project_service
from app.services import runs as run_service

router = APIRouter(tags=["runs"])

TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}


@router.post(
    "/projects/{project_id}/runs",
    response_model=RunOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_run(
    project_id: str,
    payload: RunCreate,
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RunOut:
    project = await project_service.get_project(session, project_id, guest.id)
    run = await run_service.create_run(session, project, payload.message)
    return RunOut.model_validate(run)


@router.post("/runs/{run_id}/cancel", response_model=RunCancelResponse)
async def cancel_run(
    run_id: str,
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RunCancelResponse:
    run, project = await run_service.get_owned_run(session, run_id, guest.id)
    await run_service.cancel_run(session, run, project)
    return RunCancelResponse(id=run.id, status=run.status)


@router.get("/runs/{run_id}/events")
async def stream_events(
    run_id: str,
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
    after_seq: Annotated[int, Query(ge=0)] = 0,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    await run_service.get_owned_run(session, run_id, guest.id)
    # End the auth read transaction before streaming. MySQL defaults to
    # REPEATABLE READ, so a long-lived session would otherwise keep reading the
    # snapshot taken here and never observe events committed by the agent.
    await session.commit()

    cursor = _parse_cursor(last_event_id, after_seq)

    async def generator() -> AsyncIterator[str]:
        last_seq = cursor
        terminal_wait = 0.0
        last_ping = time.monotonic()
        while True:
            events = await run_service.list_events_after(session, run_id, last_seq)
            saw_terminal = False
            for event in events:
                last_seq = event.seq
                if event.type == "run.status" and event.payload.get("status") in TERMINAL_STATUSES:
                    saw_terminal = True
                yield _format_event(event.seq, event.type, event.payload)
            if events:
                last_ping = time.monotonic()

            result = await session.execute(select(Run.status).where(Run.id == run_id))
            run_status = result.scalar_one_or_none()
            if saw_terminal or run_status is None:
                return
            if run_status in TERMINAL_STATUSES:
                terminal_wait += 0.25
                if terminal_wait >= 5.0:
                    return
            else:
                terminal_wait = 0.0

            # Commit after every poll: releases the connection and starts a new
            # transaction, so the next SELECT sees newly committed events.
            await session.commit()
            await asyncio.sleep(0.25)

            now = time.monotonic()
            if now - last_ping >= 15.0:
                last_ping = now
                yield ": ping\n\n"

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _parse_cursor(last_event_id: str | None, after_seq: int) -> int:
    if last_event_id:
        try:
            return max(0, int(last_event_id))
        except ValueError:
            pass
    return after_seq


def _format_event(seq: int, event_type: str, payload: dict[str, object]) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"id: {seq}\nevent: {event_type}\ndata: {data}\n\n"
