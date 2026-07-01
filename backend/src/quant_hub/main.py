# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Architectural style: modular monolith, domain-extractable — Doc 07 §Architectural Style
# API standards: FastAPI, versioned endpoints, OpenAPI docs — Doc 07 §API Standards
# Observability: structured logs, request IDs, health endpoints — Doc 07 §Logging & Observability
# Security: CORS restricted to configured origins — Doc 07 §Security
# Background processing: long-running tasks async — Doc 07 §Background Processing
# Per Doc 00 §14.11
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from quant_hub.api.middleware import RequestIDMiddleware
from quant_hub.api.v1 import health
from quant_hub.config import settings
from quant_hub.infrastructure.cache import redis_pool
from quant_hub.infrastructure.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Doc 07 §Logging & Observability: configure structured logging at startup
    configure_logging(settings.log_level)
    yield
    # Shutdown: release Redis connection pool
    await redis_pool.aclose()


app = FastAPI(
    title="Quant Hub API",
    version="1.0.0",
    description="Quant Hub backend — Doc 07 §API Standards (QH-007 v1.0)",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware registration — Starlette processes in LIFO order on inbound requests,
# so RequestIDMiddleware is registered last to run first (request ID must be set
# before CORS headers are evaluated so the ID is available in all log lines).
# Doc 07 §Security: CORS origin restriction
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Doc 07 §Logging & Observability: request-ID propagation — runs first on every request
app.add_middleware(RequestIDMiddleware)

# Doc 07 §API Standards: version all endpoints
# Doc 07 §Logging & Observability: health endpoint registered
app.include_router(health.router, prefix="/v1")
