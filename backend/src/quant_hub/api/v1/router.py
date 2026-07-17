# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
#   §API Standards: "Version endpoints." This is the single aggregation
#   point for all /v1 routers — main.py mounts THIS with prefix="/v1", and
#   new feature slices (Step 4.2+: portfolio, execution, ...) register here
#   rather than each editing main.py.
# Per Doc 00 §14.11
#
# A dedicated router module (not the package __init__) so importing
# quant_hub.api.v1 stays side-effect-free — aggregation is an explicit
# import of this module, avoiding import-time coupling in the package init.
from __future__ import annotations

from fastapi import APIRouter

from quant_hub.api.v1 import backtests, execution, health, markets, portfolio, risk, strategies

api_router = APIRouter()

# Doc 07 §Logging & Observability: health endpoint (unchanged, intentionally
# NOT enveloped — a liveness probe returns a fixed minimal shape).
api_router.include_router(health.router)

# Step 4.1: markets vertical slice — the first real data endpoints.
api_router.include_router(markets.router)

# Step 4.3: portfolio vertical slice — portfolios + positions.
api_router.include_router(portfolio.router)

# Step 4.4: execution vertical slice — orders + executions (the blotter).
api_router.include_router(execution.router)

# Step 4.5: strategies vertical slice — strategies + signals + backtests.
api_router.include_router(strategies.router)

# Step 4.6: risk vertical slice — limits + pre-trade assessments + snapshot.
api_router.include_router(risk.router)

# Research page: cross-strategy backtest explorer + run/equity-curve surface.
api_router.include_router(backtests.router)
