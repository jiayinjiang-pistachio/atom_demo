from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import extract_bearer_token
from app.db.models import Guest
from app.db.session import get_session
from app.services.guests import find_guest_by_token


async def get_current_guest(
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> Guest:
    token = extract_bearer_token(authorization)
    guest = await find_guest_by_token(session, token)
    if guest is None:
        raise AppError(401, "invalid_token", "访客身份无效，请刷新页面重试")
    return guest
