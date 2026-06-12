"""Standardised API error conventions.

Every error response follows the shape:
    { "error": { "code": "<SNAKE_CASE>", "message": "...", "details": {...} } }
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


# ---------------------------------------------------------------------------
# Base exception
# ---------------------------------------------------------------------------
class AppError(Exception):
    """Base application error raised by service / route code."""

    def __init__(
        self,
        *,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        message: str = "An unexpected error occurred.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details or {}


# ---------------------------------------------------------------------------
# Common concrete errors
# ---------------------------------------------------------------------------
class NotFoundError(AppError):
    def __init__(self, resource: str = "Resource", **details: Any) -> None:
        super().__init__(
            status_code=404,
            error_code="NOT_FOUND",
            message=f"{resource} not found.",
            details=details,
        )


class ConflictError(AppError):
    def __init__(self, message: str = "Resource already exists.", **details: Any) -> None:
        super().__init__(
            status_code=409,
            error_code="CONFLICT",
            message=message,
            details=details,
        )


class ForbiddenError(AppError):
    def __init__(self, message: str = "You do not have permission.", **details: Any) -> None:
        super().__init__(
            status_code=403,
            error_code="FORBIDDEN",
            message=message,
            details=details,
        )


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required.", **details: Any) -> None:
        super().__init__(
            status_code=401,
            error_code="UNAUTHORIZED",
            message=message,
            details=details,
        )


class BadRequestError(AppError):
    def __init__(self, message: str = "Invalid request.", **details: Any) -> None:
        super().__init__(
            status_code=400,
            error_code="BAD_REQUEST",
            message=message,
            details=details,
        )


class RateLimitError(AppError):
    def __init__(self, message: str = "Too many requests.", **details: Any) -> None:
        super().__init__(
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            message=message,
            details=details,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict:
    body: dict[str, Any] = {"code": code, "message": message}
    if details:
        body["details"] = details
    return {"error": body}


from fastapi.encoders import jsonable_encoder

# ---------------------------------------------------------------------------
# Exception handlers — register on the FastAPI app
# ---------------------------------------------------------------------------
def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(_req: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(_error_body(exc.error_code, exc.message, exc.details)),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        _req: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(_error_body(
                "VALIDATION_ERROR",
                "Request validation failed.",
                {"errors": exc.errors()},
            )),
        )

    @app.exception_handler(404)
    async def _not_found_handler(_req: Request, _exc: Any) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=_error_body("NOT_FOUND", "The requested resource was not found."),
        )

    @app.exception_handler(405)
    async def _method_not_allowed_handler(_req: Request, _exc: Any) -> JSONResponse:
        return JSONResponse(
            status_code=405,
            content=_error_body("METHOD_NOT_ALLOWED", "Method not allowed."),
        )

    @app.exception_handler(500)
    async def _internal_error_handler(_req: Request, _exc: Any) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=_error_body("INTERNAL_ERROR", "An unexpected error occurred."),
        )
