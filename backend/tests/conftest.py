from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.session import engine
from app.main import app


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
