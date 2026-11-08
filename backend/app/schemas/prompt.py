from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class PromptOptimizeIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def _strip_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message cannot be blank")
        return stripped


class PromptOptimizeOut(BaseModel):
    original: str
    optimized: str
