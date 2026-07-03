# Governing specification: Doc 10 — API Specification (QH-010 v1.0)
#   §6 "Common Error Model": every error returns error_code, message,
#     request_id, timestamp, details — "stable across API versions."
#   §9 "Common Error Catalog": the canonical HTTP-status -> error_code names.
#   "Every response contains: request_id, timestamp, status, version,
#     data or error envelope." (Doc 10, Part 6 §... request/response contract)
#   §1 "Consistent success/error envelopes with request IDs and timestamps."
# Doc 07 — Backend Architecture (QH-007 v1.0) §API Standards: "Return
#   consistent error schemas." Doc 07 defines no schema itself, so this
#   module REUSES Doc 10's rather than inventing one.
# Per Doc 00 §14.11
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from quant_hub.api.middleware import REQUEST_ID_CTX

# Doc 10 §7 "Semantic versioning": the API contract version carried in every
# envelope. Distinct from the app/build version in main.py — this is the
# version of the response *contract*, bumped only on envelope-shape changes.
API_VERSION = "1.0"

T = TypeVar("T")


class ErrorCode:
    """Doc 10 §9 Common Error Catalog — the canonical error_code names.

    Kept as string constants (not an Enum) so the values are exactly the
    catalog names Doc 10 publishes; handlers map an HTTP status to one of
    these. Extend only when Doc 10 §9 itself grows.
    """

    VALIDATION_ERROR = "ValidationError"          # 400
    UNAUTHORIZED = "Unauthorized"                  # 401
    FORBIDDEN = "Forbidden"                        # 403
    RESOURCE_NOT_FOUND = "ResourceNotFound"        # 404
    CONFLICT = "Conflict"                          # 409
    BUSINESS_RULE_VIOLATION = "BusinessRuleViolation"  # 422
    RATE_LIMIT_EXCEEDED = "RateLimitExceeded"      # 429
    INTERNAL_ERROR = "InternalError"               # 500
    SERVICE_UNAVAILABLE = "ServiceUnavailable"     # 503


# Doc 10 §9: HTTP status -> catalog error_code. Any status not listed maps
# to InternalError (500-shaped) — a deliberately conservative default.
_STATUS_TO_ERROR_CODE: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: ErrorCode.VALIDATION_ERROR,
    status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED,
    status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
    status.HTTP_404_NOT_FOUND: ErrorCode.RESOURCE_NOT_FOUND,
    status.HTTP_409_CONFLICT: ErrorCode.CONFLICT,
    status.HTTP_422_UNPROCESSABLE_ENTITY: ErrorCode.BUSINESS_RULE_VIOLATION,
    status.HTTP_429_TOO_MANY_REQUESTS: ErrorCode.RATE_LIMIT_EXCEEDED,
    status.HTTP_500_INTERNAL_SERVER_ERROR: ErrorCode.INTERNAL_ERROR,
    status.HTTP_503_SERVICE_UNAVAILABLE: ErrorCode.SERVICE_UNAVAILABLE,
}


class ErrorDetail(BaseModel):
    """Doc 10 §6 error body: error_code + message (+ optional details).

    request_id/timestamp live at the envelope top level (they are shared by
    success and error responses per the "every response contains" contract),
    so they are NOT duplicated inside this nested object.
    """

    error_code: str
    message: str
    details: Any | None = None


class ResponseEnvelope(BaseModel, Generic[T]):
    """Doc 10 success envelope — "every response contains request_id,
    timestamp, status, version, data or error envelope." `status` is always
    the literal "success" here; the error counterpart is ErrorEnvelope."""

    status: str = "success"
    version: str = API_VERSION
    request_id: str
    timestamp: datetime
    data: T


class ErrorEnvelope(BaseModel):
    """Doc 10 error envelope — same top-level shape as ResponseEnvelope, with
    `error` in place of `data` and status == "error"."""

    status: str = "error"
    version: str = API_VERSION
    request_id: str
    timestamp: datetime
    error: ErrorDetail


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ok(data: T) -> ResponseEnvelope[T]:
    """Wrap a handler's payload in the Doc 10 success envelope.

    request_id is read from REQUEST_ID_CTX (set by RequestIDMiddleware for
    every request) so handlers don't have to thread the Request through just
    to echo it — the same contextvar the structured logger already reads.
    """
    return ResponseEnvelope(
        request_id=REQUEST_ID_CTX.get(),
        timestamp=_now(),
        data=data,
    )


class ApiError(Exception):
    """Raise from any handler to produce a Doc 10 error envelope.

    Carries the HTTP status plus a §9 catalog error_code; the handler layer
    (register_exception_handlers) renders it. Handlers should prefer this
    over FastAPI's HTTPException so the error_code is explicit and matches
    the §9 catalog exactly, rather than being inferred from the status.
    """

    def __init__(
        self,
        http_status: int,
        error_code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.error_code = error_code
        self.message = message
        self.details = details


def _error_response(
    http_status: int, error_code: str, message: str, details: Any | None = None
) -> JSONResponse:
    envelope = ErrorEnvelope(
        request_id=REQUEST_ID_CTX.get(),
        timestamp=_now(),
        error=ErrorDetail(error_code=error_code, message=message, details=details),
    )
    return JSONResponse(status_code=http_status, content=envelope.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    """Install handlers so EVERY error path returns the Doc 10 error envelope.

    Without these, FastAPI would emit its own default `{"detail": ...}` body
    for HTTPException/validation errors — violating Doc 07 §API Standards'
    "consistent error schemas". Four handlers cover the paths:
      - ApiError: explicit, handler-raised (carries its own error_code).
      - StarletteHTTPException: FastAPI-internal (unknown route 404, etc.).
      - RequestValidationError: request-schema validation.
      - Exception: last-resort catch so an unhandled bug still envelopes.
    """

    @app.exception_handler(ApiError)
    async def _handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return _error_response(exc.http_status, exc.error_code, exc.message, exc.details)

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_TO_ERROR_CODE.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        return _error_response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged): FastAPI's default for
        # request-schema validation is HTTP 422, but Doc 10 §9 assigns 422 to
        # "BusinessRuleViolation" and 400 to "ValidationError". A malformed
        # request is a ValidationError, not a business-rule breach, so this
        # returns 400/ValidationError to honor Doc 10's catalog rather than
        # FastAPI's 422 default. 422/BusinessRuleViolation is reserved for a
        # real domain-rule rejection raised via ApiError.
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            "Request validation failed",
            details=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Do NOT leak internal exception detail to the client (Doc 07
        # §Security). The real error is logged by the logging stack; the
        # response carries only a stable generic message + the request_id a
        # caller can quote when reporting it.
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCode.INTERNAL_ERROR,
            "An internal error occurred",
        )
