# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Application — Doc 07 §Layers
# Service: Market Data — Doc 07 §Core Services
# Implementation rules: services are small and focused; no business logic in controllers
#   — Doc 07 §Implementation Rules
# Per Doc 00 §14.11
from __future__ import annotations

from quant_hub.domain.market_data.interfaces import (
    AssetRepository,
    OHLCVRepository,
    TickRepository,
)


class MarketDataService:
    """Application service stub — business logic not implemented in Step 0.4.

    Receives repositories via constructor injection — Doc 07 §Implementation Rules.
    """

    def __init__(
        self,
        assets: AssetRepository,
        ohlcv: OHLCVRepository,
        ticks: TickRepository,
    ) -> None:
        self._assets = assets
        self._ohlcv = ohlcv
        self._ticks = ticks
