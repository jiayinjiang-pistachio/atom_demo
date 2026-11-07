from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_guest
from app.db.models import Guest
from app.db.session import get_session
from app.schemas.project import (
    MessageOut,
    ProjectCreate,
    ProjectDetail,
    ProjectFileOut,
    ProjectSummary,
    ProjectUpdate,
)
from app.schemas.run import RunOut
from app.services import projects as project_service
from app.services import runs as run_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectSummary])
async def list_projects(
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ProjectSummary]:
    projects = await project_service.list_projects(session, guest.id, limit)
    return [ProjectSummary.model_validate(project) for project in projects]


@router.post("", response_model=ProjectSummary, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectSummary:
    project = await project_service.create_project(
        session,
        owner_id=guest.id,
        prompt=payload.prompt,
        title=payload.title,
    )
    return ProjectSummary.model_validate(project)


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: str,
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectDetail:
    project = await project_service.get_project(session, project_id, guest.id)
    messages = await project_service.list_messages(session, project.id)
    files = await project_service.list_files(session, project.id)
    latest_run = await run_service.latest_run(session, project.id)
    summary = ProjectSummary.model_validate(project)
    return ProjectDetail(
        **summary.model_dump(),
        messages=[MessageOut.model_validate(message) for message in messages],
        files=[ProjectFileOut.model_validate(file) for file in files],
        latest_run=RunOut.model_validate(latest_run) if latest_run is not None else None,
    )


@router.patch("/{project_id}", response_model=ProjectSummary)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectSummary:
    project = await project_service.update_project(session, project_id, guest.id, payload.title)
    return ProjectSummary.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await project_service.delete_project(session, project_id, guest.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
