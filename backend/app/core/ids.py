import secrets
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_TIME_CHARS = 10
_RANDOM_CHARS = 16


def _encode(value: int, length: int) -> str:
    chars: list[str] = []
    for _ in range(length):
        chars.append(_CROCKFORD[value & 31])
        value >>= 5
    return "".join(reversed(chars))


def new_ulid() -> str:
    """Return a 26-character Crockford Base32 ULID."""
    timestamp_ms = time.time_ns() // 1_000_000
    if timestamp_ms >= 1 << 48:
        raise RuntimeError("ULID timestamp overflow")
    return _encode(timestamp_ms, _TIME_CHARS) + _encode(secrets.randbits(80), _RANDOM_CHARS)
