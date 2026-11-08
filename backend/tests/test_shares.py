from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest_asyncio
from helpers import auth, snapshot
from httpx import AsyncClient
from sqlalchemy import select

from app.core.time import naive_utc_now
from app.db.models import Share
from app.db.session import SessionFactory

V1_FILES = {"index.html": "<!doctype html><html><body><p>share-v1</p></body></html>"}
V2_FILES = {"index.html": "<!doctype html><html><body><p>share-v2</p></body></html>"}


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@pytest_asyncio.fixture
async def seeded(guest_project):
    await snapshot(guest_project.project_id, V1_FILES, label="v1")
    await snapshot(guest_project.project_id, V2_FILES, label="v2")
    return guest_project


async def _create(client: AsyncClient, ctx, **body):
    return await client.post(
        f"/api/v1/projects/{ctx.project_id}/shares",
        headers=auth(ctx.token),
        json=body,
    )


async def test_create_share_defaults_to_current_version_and_7_days(
    client: AsyncClient, seeded
) -> None:
    response = await _create(client, seeded)

    assert response.status_code == 201
    share = response.json()
    assert share["version"] == 2
    assert share["revoked"] is False
    days = (_parse(share["expires_at"]) - datetime.now(UTC)).total_seconds() / 86400
    assert 6.8 < days < 7.2

    public = await client.get(f"/api/v1/shares/{share['slug']}")
    assert public.status_code == 200
    data = public.json()
    assert data["title"] == "测试项目"
    assert data["version"] == 2
    assert data["entry"] == "index.html"
    assert "project_id" not in data

    preview = await client.get(
        f"/share-preview/{share['slug']}/index.html", headers={"Host": "localhost"}
    )
    assert preview.status_code == 200
    assert "share-v2" in preview.text
    assert preview.headers["cache-control"] == "no-store"
    assert "frame-ancestors" in preview.headers["content-security-policy"]


async def test_create_share_supports_30_days_and_permanent(client: AsyncClient, seeded) -> None:
    response = await _create(client, seeded, expires_in_days=30)
    assert response.status_code == 201
    days = (_parse(response.json()["expires_at"]) - datetime.now(UTC)).total_seconds() / 86400
    assert 29.8 < days < 30.2

    permanent = await _create(client, seeded, expires_in_days=None)
    assert permanent.status_code == 201
    assert permanent.json()["expires_at"] is None


async def test_create_share_rejects_invalid_expiry(client: AsyncClient, seeded) -> None:
    response = await _create(client, seeded, expires_in_days=14)

    assert response.status_code == 422


async def test_create_share_rejects_unknown_version(client: AsyncClient, seeded) -> None:
    response = await _create(client, seeded, version=99)

    assert response.status_code == 404


async def test_list_and_revoke_shares(client: AsyncClient, seeded) -> None:
    first = (await _create(client, seeded)).json()
    second = (await _create(client, seeded)).json()

    listing = await client.get(
        f"/api/v1/projects/{seeded.project_id}/shares", headers=auth(seeded.token)
    )
    assert listing.status_code == 200
    assert {item["slug"] for item in listing.json()} == {first["slug"], second["slug"]}

    revoked = await client.delete(
        f"/api/v1/projects/{seeded.project_id}/shares/{first['slug']}",
        headers=auth(seeded.token),
    )
    assert revoked.status_code == 204
    again = await client.delete(
        f"/api/v1/projects/{seeded.project_id}/shares/{first['slug']}",
        headers=auth(seeded.token),
    )
    assert again.status_code == 204

    listing = await client.get(
        f"/api/v1/projects/{seeded.project_id}/shares", headers=auth(seeded.token)
    )
    assert [item["slug"] for item in listing.json()] == [second["slug"]]


async def test_revoke_only_from_own_project(client: AsyncClient, seeded) -> None:
    share = (await _create(client, seeded)).json()
    other = await client.post(
        "/api/v1/projects", headers=auth(seeded.token), json={"prompt": "另一个项目"}
    )
    assert other.status_code == 201

    response = await client.delete(
        f"/api/v1/projects/{other.json()['id']}/shares/{share['slug']}",
        headers=auth(seeded.token),
    )

    assert response.status_code == 404


async def test_share_limit(client: AsyncClient, seeded) -> None:
    for _ in range(10):
        assert (await _create(client, seeded)).status_code == 201

    response = await _create(client, seeded)

    assert response.status_code == 429
    assert response.json()["code"] == "share_limit"


async def test_invalid_shares_return_uniform_404(client: AsyncClient, seeded) -> None:
    share = (await _create(client, seeded)).json()

    missing = await client.get("/api/v1/shares/does-not-exist")
    assert missing.status_code == 404

    await client.delete(
        f"/api/v1/projects/{seeded.project_id}/shares/{share['slug']}",
        headers=auth(seeded.token),
    )
    revoked_public = await client.get(f"/api/v1/shares/{share['slug']}")
    revoked_preview = await client.get(
        f"/share-preview/{share['slug']}/index.html", headers={"Host": "localhost"}
    )
    assert revoked_public.status_code == 404
    assert revoked_preview.status_code == 404


async def test_expired_share_disappears_and_returns_404(client: AsyncClient, seeded) -> None:
    share = (await _create(client, seeded)).json()
    async with SessionFactory() as session:
        stored = (
            await session.execute(select(Share).where(Share.slug == share["slug"]))
        ).scalar_one()
        stored.expires_at = naive_utc_now() - timedelta(hours=1)
        await session.commit()

    listing = await client.get(
        f"/api/v1/projects/{seeded.project_id}/shares", headers=auth(seeded.token)
    )
    assert listing.json() == []
    assert (await client.get(f"/api/v1/shares/{share['slug']}")).status_code == 404
    preview = await client.get(
        f"/share-preview/{share['slug']}/index.html", headers={"Host": "localhost"}
    )
    assert preview.status_code == 404


async def test_share_preview_is_pinned_to_version(client: AsyncClient, seeded) -> None:
    share = (await _create(client, seeded, version=1)).json()
    await snapshot(
        seeded.project_id,
        {"index.html": "<!doctype html><html><body><p>share-v3</p></body></html>"},
        label="v3",
    )

    preview = await client.get(
        f"/share-preview/{share['slug']}/index.html", headers={"Host": "localhost"}
    )
    assert preview.status_code == 200
    assert "share-v1" in preview.text
    assert "share-v3" not in preview.text


async def test_share_preview_rejects_bad_host_and_path_traversal(
    client: AsyncClient, seeded
) -> None:
    share = (await _create(client, seeded)).json()

    wrong_host = await client.get(
        f"/share-preview/{share['slug']}/index.html",
        headers={"Host": "evil.example.com"},
    )
    traversal = await client.get(
        f"/share-preview/{share['slug']}/%2E%2E/index.html", headers={"Host": "localhost"}
    )

    assert wrong_host.status_code == 404
    assert traversal.status_code == 404


async def test_share_mutations_require_owner(client: AsyncClient, seeded) -> None:
    response = await client.post(
        f"/api/v1/projects/{seeded.project_id}/shares",
        headers={"Authorization": "Bearer wrong-token"},
        json={},
    )

    assert response.status_code == 401


async def test_public_share_is_read_only(client: AsyncClient, seeded) -> None:
    share = (await _create(client, seeded)).json()
    response = await client.delete(
        f"/api/v1/projects/{seeded.project_id}/shares/{share['slug']}",
        headers={"Authorization": f"Bearer {share['slug']}"},
    )

    assert response.status_code == 401
