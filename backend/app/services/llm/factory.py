from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.services.llm.base import LLMError, LLMGateway
from app.services.llm.deepseek import DeepSeekProvider

settings = get_settings()

_http_client: httpx.AsyncClient | None = None


def resolve_mode() -> str:
    mode = settings.llm_mode.lower()
    if mode == "demo":
        return "demo"
    if mode == "live":
        if not settings.llm_api_key:
            raise LLMError("LLM_MODE=live 但未配置 LLM_API_KEY")
        return "live"
    return "live" if settings.llm_api_key else "demo"


def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
    return _http_client


def build_gateway() -> LLMGateway | None:
    """Returns None when demo mode should be used instead of a live model."""
    if resolve_mode() == "demo":
        return None
    provider = DeepSeekProvider(
        _get_client(),
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )
    return LLMGateway(provider)


async def shutdown_llm() -> None:
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
