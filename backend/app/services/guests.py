from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import new_ulid
from app.core.security import hash_guest_token, new_guest_token
from app.db.models import Guest


async def create_guest(session: AsyncSession) -> tuple[str, Guest]:
    raw_token = new_guest_token()
    guest = Guest(id=new_ulid(), token_hash=hash_guest_token(raw_token))
    session.add(guest)
    await session.commit()
    await session.refresh(guest)
    return raw_token, guest


async def find_guest_by_token(session: AsyncSession, token: str) -> Guest | None:
    token_hash = hash_guest_token(token)
    result = await session.execute(select(Guest).where(Guest.token_hash == token_hash))
    return result.scalar_one_or_none()
