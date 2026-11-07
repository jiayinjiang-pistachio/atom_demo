from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_guest
from app.db.models import Guest
from app.db.session import get_session
from app.schemas.version import VersionDiff, VersionSummary
from app.services import projects as project_service
from app.services import versions as version_service

router = APIRouter(prefix="/projects", tags=["versions"])


@router.get("/{project_id}/versions", response_model=list[VersionSummary])
async def list_versions(
    project_id: str,
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[VersionSummary]:
    project = await project_service.get_project(session, project_id, guest.id)
    return await version_service.list_versions(session, project.id, project.current_version)


@router.get(
    "/{project_id}/versions/{from_version}/diff/{to_version}",
    response_model=VersionDiff,
)
async def diff_versions(
    project_id: str,
    from_version: Annotated[int, Path(ge=0)],
    to_version: Annotated[int, Path(ge=1)],
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VersionDiff:
    project = await project_service.get_project(session, project_id, guest.id)
    return await version_service.diff_versions(session, project.id, from_version, to_version)


@router.post("/{project_id}/versions/{number}/restore", response_model=VersionSummary)
async def restore_version(
    project_id: str,
    number: Annotated[int, Path(ge=1)],
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VersionSummary:
    project = await project_service.get_project(session, project_id, guest.id)
    version = await version_service.restore_version(session, project, number)
    return version_service.version_summary(version, project.current_version)


@router.get("/{project_id}/export")
async def export_version(
    project_id: str,
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
    version: Annotated[int | None, Query(ge=1)] = None,
) -> Response:
    project = await project_service.get_project(session, project_id, guest.id)
    filename, payload = await version_service.export_zip(session, project, version)
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
