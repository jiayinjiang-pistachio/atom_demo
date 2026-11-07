from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.ids import new_ulid
from app.core.time import naive_utc_now
from app.db.models import Project, ProjectVersion, Share
from app.schemas.share import PublicShare
from app.services import versions as version_service

MAX_ACTIVE_SHARES = 10
_SLUG_BYTES = 9


async def create_share(
    session: AsyncSession,
    project: Project,
    version_number: int | None,
    expires_in_days: Literal[7, 30] | None,
) -> Share:
    target = version_number if version_number is not None else project.current_version
    if target is None:
        raise AppError(422, "version_not_available", "项目还没有可分享的版本")
    await version_service.get_version(session, project.id, target)

    if await _count_active_shares(session, project.id) >= MAX_ACTIVE_SHARES:
        raise AppError(429, "share_limit", f"每个项目最多保留 {MAX_ACTIVE_SHARES} 个有效分享")

    expires_at = (
        None if expires_in_days is None else naive_utc_now() + timedelta(days=expires_in_days)
    )

    for _ in range(6):
        share = Share(
            id=new_ulid(),
            slug=secrets.token_urlsafe(_SLUG_BYTES),
            project_id=project.id,
            version=target,
            expires_at=expires_at,
            revoked=False,
        )
        try:
            async with session.begin_nested():
                session.add(share)
                await session.flush()
        except IntegrityError:
            continue
        await session.commit()
        await session.refresh(share)
        return share

    raise AppError(500, "share_slug_failed", "无法生成分享链接，请重试")


async def list_active_shares(session: AsyncSession, project_id: str) -> list[Share]:
    now = naive_utc_now()
    result = await session.execute(
        select(Share)
        .where(
            Share.project_id == project_id,
            Share.revoked.is_(False),
            or_(Share.expires_at.is_(None), Share.expires_at > now),
        )
        .order_by(Share.created_at.desc(), Share.id.desc())
    )
    return list(result.scalars().all())


async def revoke_share(session: AsyncSession, project_id: str, slug: str) -> None:
    result = await session.execute(
        select(Share).where(Share.slug == slug, Share.project_id == project_id)
    )
    share = result.scalar_one_or_none()
    if share is None:
        raise AppError(404, "share_not_found", "分享不存在")
    if share.revoked:
        return
    share.revoked = True
    await session.commit()


async def get_active_share(
    session: AsyncSession, slug: str
) -> tuple[Share, Project, ProjectVersion]:
    result = await session.execute(select(Share).where(Share.slug == slug))
    share = result.scalar_one_or_none()
    if share is None or share.revoked or _is_expired(share):
        raise AppError(404, "share_not_found", "分享不存在或已失效")

    project = await session.get(Project, share.project_id)
    if project is None:
        raise AppError(404, "share_not_found", "分享不存在或已失效")
    try:
        version = await version_service.get_version(session, project.id, share.version)
    except AppError as exc:
        raise AppError(404, "share_not_found", "分享不存在或已失效") from exc
    return share, project, version


def public_metadata(share: Share, project: Project, version: ProjectVersion) -> PublicShare:
    manifest = version.manifest if isinstance(version.manifest, dict) else {}
    raw_entry = manifest.get("entry")
    entry = raw_entry if isinstance(raw_entry, str) else project.entry_path
    return PublicShare(
        slug=share.slug,
        title=project.title,
        version=version.number,
        entry=entry,
        created_at=share.created_at,
        expires_at=share.expires_at,
    )


async def _count_active_shares(session: AsyncSession, project_id: str) -> int:
    now = naive_utc_now()
    result = await session.execute(
        select(func.count(Share.id)).where(
            Share.project_id == project_id,
            Share.revoked.is_(False),
            or_(Share.expires_at.is_(None), Share.expires_at > now),
        )
    )
    return int(result.scalar_one())


def _is_expired(share: Share) -> bool:
    return share.expires_at is not None and share.expires_at <= naive_utc_now()
