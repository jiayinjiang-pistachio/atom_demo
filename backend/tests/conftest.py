from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.db.models import Guest, Project
from app.db.session import SessionFactory, engine
from app.main import app
from app.services.guests import create_guest
from app.services.projects import create_project


@dataclass
class GuestProject:
    token: str
    guest_id: str
    project_id: str


async def _database_available() -> tuple[bool, str]:
    try:
        async with SessionFactory() as session:
            await session.execute(select(Project).limit(1))
        return True, ""
    except Exception as exc:
        return False, repr(exc)


@pytest_asyncio.fixture
async def guest_project() -> AsyncIterator[GuestProject]:
    available, reason = await _database_available()
    if not available:
        pytest.skip(f"MySQL is not available; integration tests need the real database ({reason})")

    async with SessionFactory() as session:
        token, guest = await create_guest(session)
        project = await create_project(session, guest.id, "测试项目", "测试项目")

    yield GuestProject(token=token, guest_id=guest.id, project_id=project.id)

    async with SessionFactory() as session:
        await session.execute(delete(Guest).where(Guest.id == guest.id))
        await session.commit()


@pytest_asyncio.fixture(autouse=True)
async def dispose_engine_between_tests() -> AsyncIterator[None]:
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest_asyncio.fixture(autouse=True)
async def clear_dependency_overrides() -> AsyncIterator[None]:
    yield
    app.dependency_overrides.clear()
