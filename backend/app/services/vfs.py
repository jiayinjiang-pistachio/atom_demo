from __future__ import annotations

import difflib
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models import ProjectFile

ALLOWED_EXTENSIONS = {".html", ".css", ".js", ".json", ".svg", ".md", ".txt"}
_PATH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
_MAX_PATH_LENGTH = 200

settings = get_settings()


def validate_path(raw: str) -> str:
    path = (raw or "").strip()
    if not path:
        raise AppError(422, "invalid_path", "文件路径不能为空")
    if len(path) > _MAX_PATH_LENGTH:
        raise AppError(422, "invalid_path", "文件路径过长")
    if path.startswith("/") or "\\" in path or "\x00" in path:
        raise AppError(422, "invalid_path", "只允许相对路径")
    segments = path.split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        raise AppError(422, "invalid_path", "文件路径不合法")
    if not _PATH_PATTERN.fullmatch(path):
        raise AppError(422, "invalid_path", "文件路径包含非法字符")
    extension = "." + path.rsplit(".", 1)[-1].lower() if "." in segments[-1] else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise AppError(422, "invalid_extension", f"不支持的文件类型：{extension or '无扩展名'}")
    return path


def validate_content(path: str, content: str) -> str:
    if not isinstance(content, str) or not content.strip():
        raise AppError(422, "empty_file", f"{path} 内容为空")
    if len(content.encode("utf-8")) > settings.max_file_bytes:
        raise AppError(
            422,
            "file_too_large",
            f"{path} 超过单文件上限 {settings.max_file_bytes} 字节",
        )
    return content


async def list_files(session: AsyncSession, project_id: str) -> list[ProjectFile]:
    result = await session.execute(
        select(ProjectFile)
        .where(ProjectFile.project_id == project_id)
        .order_by(ProjectFile.path.asc())
    )
    return list(result.scalars().all())


async def get_file(session: AsyncSession, project_id: str, path: str) -> ProjectFile | None:
    result = await session.execute(
        select(ProjectFile).where(ProjectFile.project_id == project_id, ProjectFile.path == path)
    )
    return result.scalar_one_or_none()


async def project_size(session: AsyncSession, project_id: str) -> int:
    result = await session.execute(
        select(func.coalesce(func.sum(ProjectFile.size), 0)).where(
            ProjectFile.project_id == project_id
        )
    )
    return int(result.scalar_one())


async def write_file(
    session: AsyncSession, project_id: str, raw_path: str, content: str
) -> tuple[str, str | None]:
    path = validate_path(raw_path)
    validate_content(path, content)

    existing = await get_file(session, project_id, path)
    old_content = existing.content if existing is not None else None
    new_size = len(content.encode("utf-8"))
    old_size = existing.size if existing is not None else 0
    if await project_size(session, project_id) - old_size + new_size > settings.max_project_bytes:
        raise AppError(
            422,
            "project_too_large",
            f"工程总大小超过上限 {settings.max_project_bytes} 字节",
        )
    if existing is None:
        session.add(
            ProjectFile(
                project_id=project_id,
                path=path,
                content=content,
                size=len(content.encode("utf-8")),
            )
        )
    else:
        existing.content = content
        existing.size = len(content.encode("utf-8"))
    await session.flush()
    return path, old_content


async def delete_file(session: AsyncSession, project_id: str, raw_path: str) -> bool:
    path = validate_path(raw_path)
    existing = await get_file(session, project_id, path)
    if existing is None:
        return False
    await session.delete(existing)
    await session.flush()
    return True


def unified_diff(old: str | None, new: str, path: str, *, max_chars: int = 6000) -> str:
    if old is None:
        lines = new.splitlines(keepends=True)
        old_lines: list[str] = []
    else:
        old_lines = old.splitlines(keepends=True)
        lines = new.splitlines(keepends=True)
    diff = "".join(
        difflib.unified_diff(
            old_lines,
            lines,
            fromfile=f"a/{path}" if old is not None else "/dev/null",
            tofile=f"b/{path}",
            lineterm="\n",
        )
    )
    if len(diff) > max_chars:
        return diff[:max_chars] + "\n… diff 已截断"
    return diff
