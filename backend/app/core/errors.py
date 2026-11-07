import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger()


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    return request_id if isinstance(request_id, str) else "unknown"


def _error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    payload = ErrorResponse(
        code=code,
        message=message,
        request_id=_request_id(request),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(request, exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info("request.validation_failed", error_count=len(exc.errors()))
        return _error_response(request, 422, "validation_error", "请求参数不合法")

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error_response(request, exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("request.unhandled_error", error_type=type(exc).__name__)
        return _error_response(request, 500, "internal_error", "服务暂时不可用，请稍后重试")
