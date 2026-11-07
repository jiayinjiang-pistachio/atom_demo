from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import Project, ProjectFile, ProjectVersion

MAX_VERSIONS = 20


async def next_version_number(session: AsyncSession, project_id: str) -> int:
    result = await session.execute(
        select(func.coalesce(func.max(ProjectVersion.number), 0)).where(
            ProjectVersion.project_id == project_id
        )
    )
    return int(result.scalar_one()) + 1


async def create_version(
    session: AsyncSession,
    project: Project,
    files: list[ProjectFile],
    *,
    label: str,
    source: str = "agent",
) -> ProjectVersion:
    number = await next_version_number(session, project.id)
    manifest: dict[str, Any] = {
        "entry": project.entry_path,
        "files": {file.path: file.content for file in files},
    }
    version = ProjectVersion(
        project_id=project.id,
        number=number,
        label=label[:120],
        source=source,
        manifest=manifest,
    )
    session.add(version)
    project.current_version = number
    await session.flush()
    await _prune(session, project.id)
    return version


async def _prune(session: AsyncSession, project_id: str) -> None:
    result = await session.execute(
        select(ProjectVersion)
        .where(ProjectVersion.project_id == project_id)
        .order_by(ProjectVersion.number.desc())
    )
    versions = list(result.scalars().all())
    for stale in versions[MAX_VERSIONS:]:
        await session.delete(stale)


async def get_version(session: AsyncSession, project_id: str, number: int) -> ProjectVersion:
    result = await session.execute(
        select(ProjectVersion).where(
            ProjectVersion.project_id == project_id, ProjectVersion.number == number
        )
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise AppError(404, "version_not_found", "版本不存在")
    return version
