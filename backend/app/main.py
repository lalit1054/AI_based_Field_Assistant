import logging
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import (
    routes_admin,
    routes_assets,
    routes_auth,
    routes_chat,
    routes_dashboard,
    routes_health,
    routes_kb,
    routes_qr,
    routes_tickets,
    routes_uploads,
)
from app.config import get_settings
from app.logging import configure_logging, request_id_ctx

logger = logging.getLogger("app")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        req_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        token = request_id_ctx.set(req_id)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["x-request-id"] = req_id
        return response


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging("DEBUG" if settings.debug else "INFO")

    app = FastAPI(
        title="AI Field Assistant API",
        description=(
            "AI-assisted troubleshooting & ticketing platform for manufacturing plant "
            "vision-based inspection systems."
        ),
        version="0.1.0",
    )

    app.add_middleware(RequestIdMiddleware)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": "validation_error", "detail": exc.errors()},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "http_error", "detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "detail": "An unexpected error occurred."},
        )

    @app.get("/healthz", tags=["health"])
    async def liveness() -> dict:
        return {"status": "ok"}

    app.include_router(routes_auth.router)
    app.include_router(routes_admin.router)
    app.include_router(routes_assets.router)
    app.include_router(routes_qr.router)
    app.include_router(routes_uploads.router)
    app.include_router(routes_health.router)
    app.include_router(routes_kb.router)
    app.include_router(routes_chat.router)
    app.include_router(routes_tickets.router)
    app.include_router(routes_dashboard.router)

    return app


app = create_app()
