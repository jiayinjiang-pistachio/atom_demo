import re

import pytest

from app.core.errors import AppError
from app.core.ids import new_ulid
from app.core.security import extract_bearer_token, hash_guest_token, new_guest_token

ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def test_new_ulid_shape_and_uniqueness() -> None:
    first = new_ulid()
    second = new_ulid()

    assert ULID_PATTERN.match(first)
    assert ULID_PATTERN.match(second)
    assert first != second


def test_guest_token_hashing_is_stable() -> None:
    token = new_guest_token()

    assert token == new_guest_token() or len(token) >= 40
    assert hash_guest_token(token) == hash_guest_token(token)
    assert hash_guest_token(token) != token
    assert len(hash_guest_token(token)) == 64


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("Bearer abc123", "abc123"),
        ("bearer abc123", "abc123"),
    ],
)
def test_extract_bearer_token(header: str, expected: str) -> None:
    assert extract_bearer_token(header) == expected


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer", "Bearer   "])
def test_extract_bearer_rejects_invalid_headers(header: str | None) -> None:
    with pytest.raises(AppError) as caught:
        extract_bearer_token(header)

    assert caught.value.status_code == 401
