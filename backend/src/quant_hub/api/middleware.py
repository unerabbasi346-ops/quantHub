# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Presentation/API — Doc 07 §Layers
# Observability: request IDs, structured logs — Doc 07 §Logging & Observability
# Per Doc 00 §14.11
from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ContextVar makes the request ID available to structured log formatters
# on the same async task without passing it through every call frame.
REQUEST_ID_CTX: ContextVar[str] = ContextVar("request_id", default="")

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Generate or propagate a request ID for every inbound request.

    Doc 07 §Logging & Observability: request IDs link log lines to a single
    request across all layers. Clients may supply X-Request-ID; if absent,
    a UUID v4 is generated. The ID is echoed in the response header so
    callers can correlate client-side and server-side traces.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = REQUEST_ID_CTX.set(request_id)
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except Exception:
            REQUEST_ID_CTX.reset(token)
            raise
        response.headers[REQUEST_ID_HEADER] = request_id
        REQUEST_ID_CTX.reset(token)
        return response
