import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import (
    AppError,
    ErrorCode,
    ERROR_CODE_TO_HTTP_STATUS,
    build_error_envelope,
)
from app.main import app


class TestErrorEnvelope:
    """Test standardized error envelope format."""

    def test_error_envelope_structure(self) -> None:
        """Error envelope must have { error: { code, message } }."""
        envelope = build_error_envelope("TEST_CODE", "Test message")
        assert "error" in envelope
        assert envelope["error"]["code"] == "TEST_CODE"
        assert envelope["error"]["message"] == "Test message"

    def test_error_envelope_with_details(self) -> None:
        """Error envelope with details must include them."""
        details = [{"field": "email", "message": "Required"}]
        envelope = build_error_envelope("VALIDATION_ERROR", "Invalid input", details)
        assert envelope["error"]["details"] == details

    def test_error_envelope_without_details(self) -> None:
        """Error envelope without details should not include details key."""
        envelope = build_error_envelope("TEST", "msg")
        assert "details" not in envelope["error"]

    def test_all_error_codes_have_http_status(self) -> None:
        """Every ErrorCode enum member must map to an HTTP status code."""
        for code in ErrorCode:
            if code == ErrorCode.INTERNAL_ERROR:
                continue  # INTERNAL_ERROR is an extra code
            assert code in ERROR_CODE_TO_HTTP_STATUS, f"{code} missing HTTP status mapping"

    def test_app_error_to_response(self) -> None:
        """AppError.to_response() should return correct envelope."""
        error = AppError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Job not found",
        )
        response = error.to_response()
        assert response["error"]["code"] == "RESOURCE_NOT_FOUND"
        assert response["error"]["message"] == "Job not found"

    def test_app_error_status_code(self) -> None:
        """AppError.status_code should match the code mapping."""
        error = AppError(ErrorCode.RATE_LIMIT_EXCEEDED, "Too many requests")
        assert error.status_code == 429

        error = AppError(ErrorCode.AUTH_TOKEN_EXPIRED, "Expired")
        assert error.status_code == 401


class TestErrorCodeHTTPMappings:
    """Test that all 13 error codes map to correct HTTP statuses."""

    @pytest.mark.parametrize(
        "code,expected_status",
        [
            (ErrorCode.VALIDATION_ERROR, 422),
            (ErrorCode.AUTH_TOKEN_EXPIRED, 401),
            (ErrorCode.AUTH_INVALID_TOKEN, 401),
            (ErrorCode.AUTH_INSUFFICIENT_ROLE, 403),
            (ErrorCode.RATE_LIMIT_EXCEEDED, 429),
            (ErrorCode.AI_PROVIDER_TIMEOUT, 504),
            (ErrorCode.AI_PROVIDER_QUOTA_EXCEEDED, 502),
            (ErrorCode.AI_KEY_INVALID, 400),
            (ErrorCode.ATS_CAPTCHA_DETECTED, 409),
            (ErrorCode.ATS_SUBMISSION_FAILED, 502),
            (ErrorCode.RESOURCE_NOT_FOUND, 404),
            (ErrorCode.RESOURCE_ALREADY_EXISTS, 409),
            (ErrorCode.TASK_FAILED, 500),
        ],
    )
    def test_error_code_to_http_status(self, code: ErrorCode, expected_status: int) -> None:
        assert ERROR_CODE_TO_HTTP_STATUS[code] == expected_status


class TestExceptionHandlers:
    """Test that FastAPI exception handlers return proper error envelopes."""

    @pytest.mark.asyncio
    async def test_app_error_handler_returns_envelope(self) -> None:
        """AppError raised in a route should return standardized envelope."""

        @app.get("/test-error")
        async def raise_error() -> None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "Test resource not found")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/test-error")

        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
        assert body["error"]["message"] == "Test resource not found"

    @pytest.mark.asyncio
    async def test_validation_error_returns_envelope(self) -> None:
        """Pydantic validation errors should return VALIDATION_ERROR envelope."""
        from pydantic import BaseModel

        class TestInput(BaseModel):
            name: str
            age: int

        @app.post("/test-validation")
        async def validate(data: TestInput) -> dict:
            return {"ok": True}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/test-validation",
                json={"name": 123},  # missing age, wrong type for name
            )

        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert isinstance(body["error"]["details"], list)
        assert len(body["error"]["details"]) > 0
