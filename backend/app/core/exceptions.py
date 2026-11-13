"""
CrisisLens Custom Exceptions & Error Response Handlers
Strictly implements the CrisisLens API Contract v1.0 error format:
{
  "error": {
    "code": "not_found",
    "message": "...",
    "details": null
  }
}
"""
from typing import Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class CrisisLensException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: Optional[Any] = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundException(CrisisLensException):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            code="not_found",
            message=f"{resource} {resource_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details=None,
        )


class ValidationException(CrisisLensException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            code="validation_error",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


def format_error_response(code: str, message: str, status_code: int, details: Optional[Any] = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        },
    )


async def crisislens_exception_handler(request: Request, exc: CrisisLensException):
    return format_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Format FastAPI Pydantic validation errors to match contract
    return format_error_response(
        code="validation_error",
        message="Request failed validation",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=exc.errors(),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code_map = {
        400: "validation_error",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        422: "validation_error",
        500: "server_error",
    }
    code = code_map.get(exc.status_code, "server_error")
    return format_error_response(
        code=code,
        message=str(exc.detail) if exc.detail else "An HTTP error occurred",
        status_code=exc.status_code,
        details=None,
    )


async def generic_exception_handler(request: Request, exc: Exception):
    return format_error_response(
        code="server_error",
        message="An unexpected internal server error occurred",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=str(exc) if request.app.debug else None,
    )
