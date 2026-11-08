from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.run import RunOut


class MessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def _strip_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message cannot be blank")
        return stripped


class MessageIntentOut(BaseModel):
    kind: Literal["chat", "build"]
    run: RunOut | None = None
    user_message_id: int | None = None


class ChatDoneOut(BaseModel):
    reply: str
    assistant_message_id: int | None = None
