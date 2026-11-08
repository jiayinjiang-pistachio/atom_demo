from __future__ import annotations

import io
import zipfile
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.time import naive_utc_now
from app.db.models import Project, ProjectFile, ProjectVersion, Share
from app.schemas.version import (
    ChangeKind,
    VersionDiff,
    VersionDiffFile,
    VersionDiffSummary,
    VersionSummary,
)
from app.services import runs as run_service
from app.services import vfs

MAX_VERSIONS = 20
DIFF_MAX_CHARS = 6000


def _manifest_files(manifest: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(manifest, dict):
        return {}
    raw = manifest.get("files")
    if not isinstance(raw, dict):
        return {}
    return {
        path: content
        for path, content in raw.items()
        if isinstance(path, str) and isinstance(content, str)
    }


def _manifest_entry(manifest: dict[str, Any] | None) -> str | None:
    if not isinstance(manifest, dict):
        return None
    entry = manifest.get("entry")
    return entry if isinstance(entry, str) else None


def _total_bytes(files: dict[str, str]) -> int:
    return sum(len(content.encode("utf-8")) for content in files.values())


def version_summary(version: ProjectVersion, current_version: int | None) -> VersionSummary:
    files = _manifest_files(version.manifest)
    return VersionSummary(
        number=version.number,
        label=version.label,
        source=version.source,
        created_at=version.created_at,
        file_count=len(files),
        total_bytes=_total_bytes(files),
        is_current=version.number == current_version,
    )


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


async def list_versions(
    session: AsyncSession, project_id: str, current_version: int | None
) -> list[VersionSummary]:
    result = await session.execute(
        select(ProjectVersion)
        .where(ProjectVersion.project_id == project_id)
        .order_by(ProjectVersion.number.desc())
        .limit(100)
    )
    return [version_summary(version, current_version) for version in result.scalars().all()]


async def diff_versions(
    session: AsyncSession, project_id: str, from_number: int, to_number: int
) -> VersionDiff:
    if to_number == 0:
        raise AppError(422, "invalid_version_range", "目标版本不能为 0")
    before: dict[str, str] = {}
    if from_number != 0:
        before = _manifest_files((await get_version(session, project_id, from_number)).manifest)
    after = _manifest_files((await get_version(session, project_id, to_number)).manifest)

    files: list[VersionDiffFile] = []
    counts: dict[ChangeKind, int] = {"added": 0, "removed": 0, "modified": 0}
    total_additions = 0
    total_deletions = 0

    for path in sorted(set(before) | set(after)):
        old = before.get(path)
        new = after.get(path)
        if old == new:
            continue
        change: ChangeKind
        if old is None:
            assert new is not None
            change = "added"
            full_diff = vfs.unified_diff(None, new, path, max_chars=10_000_000)
        elif new is None:
            change = "removed"
            full_diff = vfs.unified_diff(old, "", path, max_chars=10_000_000)
        else:
            change = "modified"
            full_diff = vfs.unified_diff(old, new, path, max_chars=10_000_000)
        additions, deletions = _count_changes(full_diff)
        counts[change] += 1
        total_additions += additions
        total_deletions += deletions
        files.append(
            VersionDiffFile(
                path=path,
                change=change,
                additions=additions,
                deletions=deletions,
                diff=_truncate(full_diff),
            )
        )

    return VersionDiff(
        from_version=from_number,
        to_version=to_number,
        files=files,
        summary=VersionDiffSummary(
            files_added=counts["added"],
            files_removed=counts["removed"],
            files_modified=counts["modified"],
            additions=total_additions,
            deletions=total_deletions,
        ),
    )


def _count_changes(diff: str) -> tuple[int, int]:
    additions = 0
    deletions = 0
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1
    return additions, deletions


def _truncate(diff: str) -> str:
    if len(diff) <= DIFF_MAX_CHARS:
        return diff
    return diff[:DIFF_MAX_CHARS] + "\n… diff 已截断"


async def restore_version(session: AsyncSession, project: Project, number: int) -> ProjectVersion:
    if await run_service.find_active_run(session, project.id) is not None:
        raise AppError(409, "run_in_progress", "生成任务进行中，暂不能回滚")

    result = await session.execute(
        select(Project).where(Project.id == project.id).with_for_update()
    )
    locked = result.scalar_one_or_none()
    if locked is None:
        raise AppError(404, "project_not_found", "项目不存在或无权访问")
    if locked.current_version == number:
        raise AppError(409, "version_is_current", "该版本已经是当前版本")

    target = await get_version(session, project.id, number)
    files = _manifest_files(target.manifest)
    entry = _manifest_entry(target.manifest) or locked.entry_path
    if entry not in files:
        raise AppError(422, "invalid_version_manifest", "版本快照缺少入口文件")

    await session.execute(delete(ProjectFile).where(ProjectFile.project_id == project.id))
    await session.flush()
    for path in sorted(files):
        await vfs.write_file(session, project.id, path, files[path])
    locked.entry_path = vfs.validate_path(entry)

    restored_files = await vfs.list_files(session, project.id)
    version = await create_version(
        session,
        locked,
        restored_files,
        label=f"回滚到 v{number}",
        source="restore",
    )
    await session.commit()
    await session.refresh(version)
    return version


async def export_zip(
    session: AsyncSession, project: Project, number: int | None
) -> tuple[str, bytes]:
    target = number if number is not None else project.current_version
    if target is None:
        raise AppError(404, "version_not_found", "项目还没有可导出的版本")
    version = await get_version(session, project.id, target)
    files = _manifest_files(version.manifest)
    if not files:
        raise AppError(422, "empty_version", "该版本没有可导出的文件")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            safe_path = vfs.validate_path(path)
            archive.writestr(safe_path, files[path])
    filename = f"atom-{project.id}-v{version.number}.zip"
    return filename, buffer.getvalue()


async def _prune(session: AsyncSession, project_id: str) -> None:
    result = await session.execute(
        select(ProjectVersion)
        .where(ProjectVersion.project_id == project_id)
        .order_by(ProjectVersion.number.desc())
    )
    protected = await _share_protected_versions(session, project_id)
    for stale in list(result.scalars().all())[MAX_VERSIONS:]:
        if stale.number in protected:
            continue
        await session.delete(stale)


async def _share_protected_versions(session: AsyncSession, project_id: str) -> set[int]:
    now = naive_utc_now()
    result = await session.execute(
        select(Share.version).where(
            Share.project_id == project_id,
            Share.revoked.is_(False),
            or_(Share.expires_at.is_(None), Share.expires_at > now),
        )
    )
    return set(result.scalars().all())


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
