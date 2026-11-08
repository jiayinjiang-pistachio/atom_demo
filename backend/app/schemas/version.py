from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.schemas.types import UTCDateTime

ChangeKind = Literal["added", "removed", "modified"]


class VersionSummary(BaseModel):
    number: int
    label: str
    source: str
    created_at: UTCDateTime
    file_count: int
    total_bytes: int
    is_current: bool


class VersionDiffFile(BaseModel):
    path: str
    change: ChangeKind
    additions: int
    deletions: int
    diff: str


class VersionDiffSummary(BaseModel):
    files_added: int
    files_removed: int
    files_modified: int
    additions: int
    deletions: int


class VersionDiff(BaseModel):
    from_version: int
    to_version: int
    files: list[VersionDiffFile]
    summary: VersionDiffSummary
