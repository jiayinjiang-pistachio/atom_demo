from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.guest import GuestBootstrapResponse
from app.services.guests import create_guest

router = APIRouter(prefix="/guest", tags=["guest"])


@router.post(
    "/bootstrap",
    response_model=GuestBootstrapResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bootstrap_guest(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GuestBootstrapResponse:
    token, guest = await create_guest(session)
    return GuestBootstrapResponse(guest_id=guest.id, token=token)
