from __future__ import annotations

from datetime import UTC, datetime


def naive_utc_now() -> datetime:
    """Return the current UTC time without tzinfo, matching naive DateTime columns."""
    return datetime.now(UTC).replace(tzinfo=None)
