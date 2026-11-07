import hashlib
import secrets

from app.core.errors import AppError

_TOKEN_BYTES = 32


def new_guest_token() -> str:
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_guest_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise AppError(401, "missing_token", "缺少访客身份，请刷新页面重试")
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token.strip():
        raise AppError(401, "invalid_token", "访客身份格式不正确")
    return token.strip()
