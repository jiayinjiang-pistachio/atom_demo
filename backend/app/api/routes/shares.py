from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_guest
from app.db.models import Guest
from app.db.session import get_session
from app.schemas.share import PublicShare, ShareCreate, ShareOut
from app.services import projects as project_service
from app.services import shares as share_service

owner_router = APIRouter(prefix="/projects", tags=["shares"])
public_router = APIRouter(tags=["shares"])


@owner_router.post(
    "/{project_id}/shares",
    response_model=ShareOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_share(
    project_id: str,
    payload: ShareCreate,
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ShareOut:
    project = await project_service.get_project(session, project_id, guest.id)
    share = await share_service.create_share(
        session, project, payload.version, payload.expires_in_days
    )
    return ShareOut.model_validate(share)


@owner_router.get("/{project_id}/shares", response_model=list[ShareOut])
async def list_shares(
    project_id: str,
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ShareOut]:
    project = await project_service.get_project(session, project_id, guest.id)
    shares = await share_service.list_active_shares(session, project.id)
    return [ShareOut.model_validate(share) for share in shares]


@owner_router.delete(
    "/{project_id}/shares/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_share(
    project_id: str,
    slug: str,
    guest: Annotated[Guest, Depends(get_current_guest)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    project = await project_service.get_project(session, project_id, guest.id)
    await share_service.revoke_share(session, project.id, slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@public_router.get("/shares/{slug}", response_model=PublicShare)
async def get_public_share(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PublicShare:
    share, project, version = await share_service.get_active_share(session, slug)
    return share_service.public_metadata(share, project, version)
