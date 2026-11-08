from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Message, Project, Run
from app.services import intent as intent_service
from app.services import projects as project_service
from app.services import runs as run_service
from app.services.llm import LLMError, LLMGateway, build_gateway

_HISTORY_LIMIT = 20


@dataclass(slots=True)
class PreparedMessage:
    kind: intent_service.Intent
    gateway: LLMGateway | None
    title: str
    has_files: bool
    history: list[tuple[str, str]] = field(default_factory=list)
    run: Run | None = None
    user_message_id: int | None = None


async def prepare(
    session: AsyncSession,
    project: Project,
    message: str,
) -> PreparedMessage:
    files = await project_service.list_files(session, project.id)
    rows = await project_service.list_messages(session, project.id)
    history = [(row.role, row.content) for row in rows[-_HISTORY_LIMIT:]]
    project_title = project.title
    has_files = bool(files)

    # Release the auth/read transaction before any LLM call.
    await session.commit()

    try:
        gateway = build_gateway()
    except LLMError:
        gateway = None

    kind = await intent_service.classify(
        message,
        gateway=gateway,
        project_title=project_title,
        has_files=has_files,
    )
    if kind == "build":
        run = await run_service.create_run(session, project, message)
        return PreparedMessage(
            kind="build",
            gateway=gateway,
            title=project_title,
            has_files=has_files,
            run=run,
            user_message_id=run.user_message_id,
        )

    user_message = Message(project_id=project.id, role="user", content=message)
    session.add(user_message)
    await session.commit()
    await session.refresh(user_message)
    return PreparedMessage(
        kind="chat",
        gateway=gateway,
        title=project_title,
        has_files=has_files,
        history=history,
        user_message_id=user_message.id,
    )
