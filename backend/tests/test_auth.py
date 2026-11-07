from httpx import AsyncClient


async def test_projects_require_guest_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/projects")

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "missing_token"
    assert body["request_id"] == response.headers["X-Request-ID"]


async def test_projects_reject_wrong_auth_scheme(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/projects",
        headers={"Authorization": "Basic not-a-token"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


async def test_unknown_route_uses_error_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "http_error"
    assert body["request_id"] == response.headers["X-Request-ID"]
