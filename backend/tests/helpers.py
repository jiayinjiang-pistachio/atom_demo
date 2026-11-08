from __future__ import annotations

from app.db.models import Project
from app.db.session import SessionFactory
from app.services import versions as version_service
from app.services import vfs


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def snapshot(
    project_id: str,
    files: dict[str, str],
    *,
    label: str,
    source: str = "agent",
    entry: str = "index.html",
) -> int:
    """Replace the working files and create an immutable version from them."""
    async with SessionFactory() as session:
        project = await session.get(Project, project_id)
        assert project is not None
        for existing in await vfs.list_files(session, project_id):
            await vfs.delete_file(session, project_id, existing.path)
        project.entry_path = entry
        for path, content in files.items():
            await vfs.write_file(session, project_id, path, content)
        rows = await vfs.list_files(session, project_id)
        version = await version_service.create_version(
            session, project, rows, label=label, source=source
        )
        await session.commit()
        return version.number
