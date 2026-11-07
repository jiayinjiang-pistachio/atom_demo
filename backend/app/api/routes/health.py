from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.schemas.health import HealthResponse, MetaResponse

router = APIRouter()
logger = structlog.get_logger()


async def database_is_available(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> bool:
    try:
        await session.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        logger.warning("health.database_check_failed")
        return False


@router.get("/healthz", response_model=HealthResponse, tags=["system"])
async def healthz(
    response: Response,
    database_ok: Annotated[bool, Depends(database_is_available)],
) -> HealthResponse:
    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ok" if database_ok else "degraded",
        database="ok" if database_ok else "down",
        version=get_settings().version,
    )


@router.get(
    f"{get_settings().api_prefix}/meta",
    response_model=MetaResponse,
    tags=["system"],
)
async def meta() -> MetaResponse:
    settings = get_settings()
    return MetaResponse(
        name=settings.app_name,
        environment=settings.environment,
        api_version="v1",
    )
