from httpx import AsyncClient

from app.api.routes.health import database_is_available
from app.main import app


async def test_meta(client: AsyncClient) -> None:
    response = await client.get("/api/v1/meta")

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert "X-Request-ID" in response.headers


async def test_health_ok(client: AsyncClient) -> None:
    app.dependency_overrides[database_is_available] = lambda: True

    response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "version": "0.1.0"}


async def test_health_degraded(client: AsyncClient) -> None:
    app.dependency_overrides[database_is_available] = lambda: False

    response = await client.get("/healthz")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "down"
