from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_guest
from app.db.models import Guest, Message
from app.db.session import SessionFactory, get_session
from app.schemas.message import ChatDoneOut, MessageCreate, MessageIntentOut
from app.schemas.run import RunOut
from app.services import chat as chat_service
from app.services import messages as message_service
from app.services import projects as project_service
from app.services.llm import LLMError, LLMGateway

router = APIRouter(tags=["messages"])
logger = structlog.get_logger()

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.post("/projects/{project_id}/messages/stream")
async def stream_message(
    project_id: str,
    payload: MessageCreate,
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StreamingResponse:
    project = await project_service.get_project(session, project_id, guest.id)
    prepared = await message_service.prepare(session, project, payload.message)

    intent = MessageIntentOut(
        kind=prepared.kind,
        run=RunOut.model_validate(prepared.run) if prepared.run is not None else None,
        user_message_id=prepared.user_message_id,
    )
    intent_payload = intent.model_dump(mode="json")

    if prepared.kind == "build":
        return StreamingResponse(
            _build_stream(intent_payload),
            media_type="text/event-stream",
            headers=_SSE_HEADERS,
        )

    messages = chat_service.build_chat_messages(
        title=prepared.title,
        has_files=prepared.has_files,
        history=prepared.history,
        message=payload.message,
    )
    return StreamingResponse(
        _chat_stream(project.id, intent_payload, messages, prepared.gateway),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


async def _build_stream(intent_payload: dict[str, Any]) -> AsyncIterator[str]:
    yield _format("message.intent", intent_payload)


async def _chat_stream(
    project_id: str,
    intent_payload: dict[str, Any],
    messages: list[dict[str, Any]],
    gateway: LLMGateway | None,
) -> AsyncIterator[str]:
    yield _format("message.intent", intent_payload)
    reply = ""
    try:
        async for text in chat_service.stream_reply(messages, gateway):
            reply += text
            yield _format("assistant.delta", {"text": text})
        assistant_id = await _persist_reply(project_id, reply)
        done = ChatDoneOut(reply=reply, assistant_message_id=assistant_id)
        yield _format("chat.done", done.model_dump(mode="json"))
    except LLMError:
        logger.warning("message.reply_llm_error", project_id=project_id)
        yield _format("error", {"code": "llm_error", "message": "回复失败，请稍后重试"})
    except Exception:
        logger.exception("message.reply_unhandled", project_id=project_id)
        yield _format("error", {"code": "internal_error", "message": "回复失败，请稍后重试"})


async def _persist_reply(project_id: str, reply: str) -> int | None:
    async with SessionFactory() as session:
        message = Message(project_id=project_id, role="assistant", content=reply)
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message.id


def _format(event: str, payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"
