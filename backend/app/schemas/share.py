from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.types import UTCDateTime


class ShareCreate(BaseModel):
    version: int | None = Field(default=None, ge=1)
    expires_in_days: Literal[7, 30] | None = 7


class ShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    version: int
    created_at: UTCDateTime
    expires_at: UTCDateTime | None
    revoked: bool


class PublicShare(BaseModel):
    slug: str
    title: str
    version: int
    entry: str
    created_at: UTCDateTime
    expires_at: UTCDateTime | None
