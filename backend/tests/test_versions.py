from __future__ import annotations

import io
import zipfile

import pytest_asyncio
from helpers import auth, snapshot
from httpx import AsyncClient
from sqlalchemy import select

from app.core.ids import new_ulid
from app.db.models import Project, ProjectVersion, Run
from app.db.session import SessionFactory
from app.services import shares as share_service

V1_FILES = {
    "index.html": (
        '<!doctype html><html><head><link rel="stylesheet" href="styles.css"></head>'
        "<body><p>hello</p></body></html>"
    ),
    "styles.css": "body{color:#111}",
}
V2_FILES = {
    "index.html": (
        "<!doctype html><html><head></head>"
        '<body><p>hello world</p><script src="app.js"></script></body></html>'
    ),
    "app.js": "console.log('v2');",
}


@pytest_asyncio.fixture
async def versioned(guest_project):
    v1 = await snapshot(guest_project.project_id, V1_FILES, label="第一版")
    v2 = await snapshot(guest_project.project_id, V2_FILES, label="第二版")
    return guest_project, v1, v2


async def test_list_versions_reverse_order_and_stats(client: AsyncClient, versioned) -> None:
    ctx, _v1, _v2 = versioned
    response = await client.get(
        f"/api/v1/projects/{ctx.project_id}/versions", headers=auth(ctx.token)
    )

    assert response.status_code == 200
    data = response.json()
    assert [item["number"] for item in data] == [2, 1]
    assert data[0]["label"] == "第二版"
    assert data[0]["source"] == "agent"
    assert data[0]["file_count"] == 2
    assert data[0]["total_bytes"] > 0
    assert data[0]["is_current"] is True
    assert data[1]["is_current"] is False


async def test_list_versions_requires_owner(client: AsyncClient, versioned) -> None:
    ctx, _v1, _v2 = versioned
    response = await client.get(
        f"/api/v1/projects/{ctx.project_id}/versions",
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == 401


async def test_diff_reports_added_removed_and_modified(client: AsyncClient, versioned) -> None:
    ctx, _v1, _v2 = versioned
    response = await client.get(
        f"/api/v1/projects/{ctx.project_id}/versions/1/diff/2",
        headers=auth(ctx.token),
    )

    assert response.status_code == 200
    data = response.json()
    files = {item["path"]: item for item in data["files"]}
    assert set(files) == {"index.html", "styles.css", "app.js"}
    assert files["styles.css"]["change"] == "removed"
    assert files["app.js"]["change"] == "added"
    assert files["index.html"]["change"] == "modified"
    assert "@@" in files["index.html"]["diff"]
    assert data["summary"]["files_added"] == 1
    assert data["summary"]["files_removed"] == 1
    assert data["summary"]["files_modified"] == 1
    assert data["summary"]["additions"] > 0
    assert data["summary"]["deletions"] > 0


async def test_diff_from_empty_baseline(client: AsyncClient, versioned) -> None:
    ctx, _v1, _v2 = versioned
    response = await client.get(
        f"/api/v1/projects/{ctx.project_id}/versions/0/diff/2",
        headers=auth(ctx.token),
    )

    assert response.status_code == 200
    data = response.json()
    assert {item["change"] for item in data["files"]} == {"added"}
    assert data["summary"]["files_added"] == 2


async def test_diff_rejects_missing_versions(client: AsyncClient, versioned) -> None:
    ctx, _v1, _v2 = versioned
    missing = await client.get(
        f"/api/v1/projects/{ctx.project_id}/versions/9/diff/2",
        headers=auth(ctx.token),
    )
    zero_target = await client.get(
        f"/api/v1/projects/{ctx.project_id}/versions/1/diff/0",
        headers=auth(ctx.token),
    )

    assert missing.status_code == 404
    assert zero_target.status_code == 422


async def test_restore_creates_new_version_without_mutating_history(
    client: AsyncClient, versioned
) -> None:
    ctx, _v1, _v2 = versioned
    response = await client.post(
        f"/api/v1/projects/{ctx.project_id}/versions/1/restore",
        headers=auth(ctx.token),
    )

    assert response.status_code == 200
    restored = response.json()
    assert restored["number"] == 3
    assert restored["source"] == "restore"
    assert restored["label"] == "回滚到 v1"
    assert restored["is_current"] is True

    detail = await client.get(f"/api/v1/projects/{ctx.project_id}", headers=auth(ctx.token))
    files = {item["path"]: item["content"] for item in detail.json()["files"]}
    assert files == V1_FILES

    versions = await client.get(
        f"/api/v1/projects/{ctx.project_id}/versions", headers=auth(ctx.token)
    )
    assert [item["number"] for item in versions.json()] == [3, 2, 1]


async def test_restore_current_version_conflicts(client: AsyncClient, versioned) -> None:
    ctx, _v1, _v2 = versioned
    response = await client.post(
        f"/api/v1/projects/{ctx.project_id}/versions/2/restore",
        headers=auth(ctx.token),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "version_is_current"


async def test_restore_while_run_active_conflicts(client: AsyncClient, versioned) -> None:
    ctx, _v1, _v2 = versioned
    async with SessionFactory() as session:
        session.add(Run(id=new_ulid(), project_id=ctx.project_id, status="queued"))
        await session.commit()

    response = await client.post(
        f"/api/v1/projects/{ctx.project_id}/versions/1/restore",
        headers=auth(ctx.token),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "run_in_progress"


async def test_export_zip_defaults_to_current_version(client: AsyncClient, versioned) -> None:
    ctx, _v1, _v2 = versioned
    response = await client.get(
        f"/api/v1/projects/{ctx.project_id}/export", headers=auth(ctx.token)
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    assert f"atom-{ctx.project_id}-v2.zip" in response.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {"index.html", "app.js"}
        assert "hello world" in archive.read("index.html").decode("utf-8")


async def test_export_zip_specific_version(client: AsyncClient, versioned) -> None:
    ctx, _v1, _v2 = versioned
    response = await client.get(
        f"/api/v1/projects/{ctx.project_id}/export?version=1", headers=auth(ctx.token)
    )

    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {"index.html", "styles.css"}


async def test_prune_keeps_versions_referenced_by_active_share(guest_project) -> None:
    project_id = guest_project.project_id
    protected = await snapshot(project_id, {"index.html": "v1"}, label="v1")

    async with SessionFactory() as session:
        project = await session.get(Project, project_id)
        assert project is not None
        await share_service.create_share(session, project, protected, 7)

    for number in range(2, 23):
        await snapshot(project_id, {"index.html": f"v{number}"}, label=f"v{number}")

    async with SessionFactory() as session:
        rows = (
            await session.execute(
                select(ProjectVersion.number).where(ProjectVersion.project_id == project_id)
            )
        ).scalars()
        numbers = set(rows.all())
    assert protected in numbers
    assert 2 not in numbers
    assert 22 in numbers
    assert len(numbers) == 21
