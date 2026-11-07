from datetime import UTC, datetime
from typing import Annotated

from pydantic import BeforeValidator


def _ensure_utc(value: object) -> object:
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


UTCDateTime = Annotated[datetime, BeforeValidator(_ensure_utc)]
