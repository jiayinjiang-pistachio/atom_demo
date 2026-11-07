from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.run import RunOut
from app.schemas.types import UTCDateTime


class ProjectCreate(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    title: str | None = Field(default=None, max_length=120)

    @field_validator("prompt")
    @classmethod
    def normalize_prompt(cls, value: str) -> str:
        prompt = value.strip()
        if not prompt:
            raise ValueError("prompt must not be blank")
        return prompt

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        title = value.strip()
        return title or None


class ProjectUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("title must not be blank")
        return title


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    run_id: str | None
    created_at: UTCDateTime


class ProjectFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    path: str
    content: str
    size: int
    updated_at: UTCDateTime


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    prompt: str
    entry_path: str
    status: str
    current_version: int | None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class ProjectDetail(ProjectSummary):
    messages: list[MessageOut]
    files: list[ProjectFileOut]
    latest_run: RunOut | None = None
