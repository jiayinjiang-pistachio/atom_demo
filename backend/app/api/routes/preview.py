from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_session
from app.services import shares as share_service
from app.services import versions as version_service
from app.services import vfs

settings = get_settings()
router = APIRouter(tags=["preview"])

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".md": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
}

IMMUTABLE_CACHE = "public, max-age=31536000, immutable"
NO_STORE = "no-store"


@router.get("/preview/{project_id}/{version}")
@router.get("/preview/{project_id}/{version}/{path:path}")
async def serve_preview(
    project_id: str,
    version: int,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    path: str = "",
) -> Response:
    _check_host(request)
    try:
        project_version = await version_service.get_version(session, project_id, version)
    except AppError:
        return _not_found()
    return _serve_manifest(project_version.manifest or {}, path, cache_control=IMMUTABLE_CACHE)


@router.get("/share-preview/{slug}")
@router.get("/share-preview/{slug}/{path:path}")
async def serve_share_preview(
    slug: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    path: str = "",
) -> Response:
    _check_host(request)
    try:
        _share, _project, project_version = await share_service.get_active_share(session, slug)
    except AppError:
        return _not_found()
    return _serve_manifest(project_version.manifest or {}, path, cache_control=NO_STORE)


def _serve_manifest(manifest: dict[str, Any], path: str, *, cache_control: str) -> Response:
    files = manifest.get("files")
    if not isinstance(files, dict):
        return _not_found()

    target = path or str(manifest.get("entry") or "index.html")
    try:
        target = vfs.validate_path(target)
    except AppError:
        return _not_found()

    content = files.get(target)
    if not isinstance(content, str):
        return _not_found()

    extension = "." + target.rsplit(".", 1)[-1].lower() if "." in target else ""
    headers = {
        "Content-Type": CONTENT_TYPES.get(extension, "application/octet-stream"),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": cache_control,
        "Content-Security-Policy": (
            "default-src 'self' data: blob:; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'none'; "
            f"frame-ancestors {settings.frontend_origin};"
        ),
    }
    return Response(content=content.encode("utf-8"), headers=headers)


def _check_host(request: Request) -> None:
    host = request.headers.get("host", "").split(":", 1)[0].lower()
    expected = settings.preview_host.lower()
    if expected and host != expected:
        raise AppError(404, "preview_not_found", "预览不存在")


def _not_found() -> Response:
    return Response(
        content=json.dumps({"code": "preview_not_found", "message": "预览文件不存在"}),
        status_code=404,
        media_type="application/json",
    )
