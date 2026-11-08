from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.ids import new_ulid
from app.db.models import Message, Project, ProjectFile
from app.services import titles


async def list_projects(session: AsyncSession, owner_id: str, limit: int) -> list[Project]:
    result = await session.execute(
        select(Project)
        .where(Project.owner_id == owner_id)
        .order_by(Project.updated_at.desc(), Project.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_project(
    session: AsyncSession, owner_id: str, prompt: str, title: str | None
) -> Project:
    if not title:
        # Release the auth read transaction before calling the title model.
        await session.commit()
        title = await titles.generate_title(prompt)
    project = Project(
        id=new_ulid(),
        owner_id=owner_id,
        title=title,
        prompt=prompt,
        entry_path="index.html",
        status="idle",
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def get_project(session: AsyncSession, project_id: str, owner_id: str) -> Project:
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise AppError(404, "project_not_found", "项目不存在或无权访问")
    return project


async def list_messages(session: AsyncSession, project_id: str) -> list[Message]:
    result = await session.execute(
        select(Message).where(Message.project_id == project_id).order_by(Message.id.asc())
    )
    return list(result.scalars().all())


async def list_files(session: AsyncSession, project_id: str) -> list[ProjectFile]:
    result = await session.execute(
        select(ProjectFile)
        .where(ProjectFile.project_id == project_id)
        .order_by(ProjectFile.path.asc())
    )
    return list(result.scalars().all())


async def update_project(
    session: AsyncSession, project_id: str, owner_id: str, title: str
) -> Project:
    project = await get_project(session, project_id, owner_id)
    project.title = title
    await session.commit()
    await session.refresh(project)
    return project


async def delete_project(session: AsyncSession, project_id: str, owner_id: str) -> None:
    project = await get_project(session, project_id, owner_id)
    await session.delete(project)
    await session.commit()
