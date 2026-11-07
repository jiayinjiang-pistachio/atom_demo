from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.types import UTCDateTime


class RunCreate(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def _strip_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message cannot be blank")
        return stripped


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    status: str
    model: str
    tokens_in: int
    tokens_out: int
    error_code: str | None
    error_message: str | None
    created_at: UTCDateTime
    started_at: UTCDateTime | None
    finished_at: UTCDateTime | None


class RunEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq: int
    type: str
    payload: dict[str, Any]
    created_at: UTCDateTime


class RunCancelResponse(BaseModel):
    id: str
    status: str
