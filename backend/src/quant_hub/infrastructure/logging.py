# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Infrastructure — Doc 07 §Layers
# Observability: structured logs, request IDs — Doc 07 §Logging & Observability
# Per Doc 00 §14.11
from __future__ import annotations

import json
import logging

from quant_hub.api.middleware import REQUEST_ID_CTX


class StructuredFormatter(logging.Formatter):
    """Emit one JSON object per log record, including the active request ID.

    Doc 07 §Logging & Observability: structured logs with request IDs allow
    log aggregators to correlate all lines produced by a single request.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": REQUEST_ID_CTX.get(""),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(log_level: str = "INFO") -> None:
    """Attach the structured formatter to the root logger."""
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level.upper())
