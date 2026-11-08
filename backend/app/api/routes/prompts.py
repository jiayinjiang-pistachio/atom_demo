from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_guest
from app.db.models import Guest
from app.db.session import get_session
from app.schemas.prompt import PromptOptimizeIn, PromptOptimizeOut
from app.services import projects as project_service
from app.services import prompts as prompt_service

router = APIRouter(tags=["prompts"])


@router.post(
    "/projects/{project_id}/prompts/optimize",
    response_model=PromptOptimizeOut,
)
async def optimize_prompt(
    project_id: str,
    payload: PromptOptimizeIn,
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PromptOptimizeOut:
    project = await project_service.get_project(session, project_id, guest.id)
    optimized = await prompt_service.optimize(session, project, payload.message)
    return PromptOptimizeOut(original=payload.message, optimized=optimized)
