"""RFC 7807 problem-details error envelope.

Every error response carries `type`, `title`, `status`, `detail`, and
the MissionIQ extensions `code` and `request_id`. Internal exceptions
are mapped to safe user-facing messages.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Application-level error mapped to a structured response."""

    status_code: int = 400
    code: str = "app.error"
    title: str = "Application error"

    def __init__(self, detail: str, *, status_code: int | None = None, code: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class NotFoundError(AppError):
    status_code = 404
    code = "resource.not_found"
    title = "Resource not found"


class UnauthorizedError(AppError):
    status_code = 401
    code = "auth.unauthorized"
    title = "Unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "auth.forbidden"
    title = "Forbidden"


class ConflictError(AppError):
    status_code = 409
    code = "resource.conflict"
    title = "Conflict"


class ValidationError(AppError):
    status_code = 422
    code = "input.invalid"
    title = "Invalid input"


def _problem(
    request: Request,
    *,
    status_code: int,
    title: str,
    detail: str,
    code: str,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"https://missioniq.dev/errors/{code.replace('.', '-')}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "code": code,
        "request_id": getattr(request.state, "request_id", None),
    }
    return JSONResponse(status_code=status_code, content=body)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return _problem(
            request,
            status_code=exc.status_code,
            title=exc.title,
            detail=exc.detail,
            code=exc.code,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _problem(
            request,
            status_code=exc.status_code,
            title=exc.detail if isinstance(exc.detail, str) else "HTTP error",
            detail=str(exc.detail),
            code=f"http.{exc.status_code}",
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem(
            request,
            status_code=422,
            title="Invalid input",
            detail="One or more fields failed validation.",
            code="input.invalid",
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        return _problem(
            request,
            status_code=500,
            title="Internal server error",
            detail="An unexpected error occurred.",
            code="app.internal_error",
        )
