from fastapi import APIRouter

from app.api.routes.guest import router as guest_router
from app.api.routes.projects import router as projects_router
from app.api.routes.runs import router as runs_router
from app.api.routes.shares import owner_router as shares_owner_router
from app.api.routes.shares import public_router as shares_public_router
from app.api.routes.versions import router as versions_router
from app.core.config import get_settings

api_router = APIRouter(prefix=get_settings().api_prefix)
api_router.include_router(guest_router)
api_router.include_router(projects_router)
api_router.include_router(runs_router)
api_router.include_router(versions_router)
api_router.include_router(shares_owner_router)
api_router.include_router(shares_public_router)
