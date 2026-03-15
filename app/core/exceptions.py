from enum import Enum
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    AUTH_INSUFFICIENT_ROLE = "AUTH_INSUFFICIENT_ROLE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    AI_PROVIDER_TIMEOUT = "AI_PROVIDER_TIMEOUT"
    AI_PROVIDER_QUOTA_EXCEEDED = "AI_PROVIDER_QUOTA_EXCEEDED"
    AI_KEY_INVALID = "AI_KEY_INVALID"
    ATS_CAPTCHA_DETECTED = "ATS_CAPTCHA_DETECTED"
    ATS_SUBMISSION_FAILED = "ATS_SUBMISSION_FAILED"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    TASK_FAILED = "TASK_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


ERROR_CODE_TO_HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.AUTH_TOKEN_EXPIRED: 401,
    ErrorCode.AUTH_INVALID_TOKEN: 401,
    ErrorCode.AUTH_INSUFFICIENT_ROLE: 403,
    ErrorCode.RATE_LIMIT_EXCEEDED: 429,
    ErrorCode.AI_PROVIDER_TIMEOUT: 504,
    ErrorCode.AI_PROVIDER_QUOTA_EXCEEDED: 502,
    ErrorCode.AI_KEY_INVALID: 400,
    ErrorCode.ATS_CAPTCHA_DETECTED: 409,
    ErrorCode.ATS_SUBMISSION_FAILED: 502,
    ErrorCode.RESOURCE_NOT_FOUND: 404,
    ErrorCode.RESOURCE_ALREADY_EXISTS: 409,
    ErrorCode.TASK_FAILED: 500,
    ErrorCode.INTERNAL_ERROR: 500,
}


class AppError(Exception):
    """Base application error that maps to standardized error envelope."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)

    @property
    def status_code(self) -> int:
        return ERROR_CODE_TO_HTTP_STATUS.get(self.code, 500)

    def to_response(self) -> dict[str, Any]:
        error_body: dict[str, Any] = {
            "code": self.code.value,
            "message": self.message,
        }
        if self.details:
            error_body["details"] = self.details
        return {"error": error_body}


def build_error_envelope(
    code: str, message: str, details: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    error_body: dict[str, Any] = {"code": code, "message": message}
    if details:
        error_body["details"] = details
    return {"error": error_body}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response(),
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        details.append({"field": field, "message": error["msg"]})

    return JSONResponse(
        status_code=422,
        content=build_error_envelope(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Invalid input",
            details=details,
        ),
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    from loguru import logger

    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=build_error_envelope(
            code=ErrorCode.INTERNAL_ERROR.value,
            message="Internal server error",
        ),
    )
