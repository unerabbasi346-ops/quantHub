# Governing specification: Doc 11 §1 — Market Data Connectors (Data Engineering)
# Layer: Domain — Doc 07 §Layers
# Dependency rule: domain defines the interface; infrastructure implements it
#   — Doc 07 §Dependency Rules
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from quant_hub.domain.market_data.entities import RawCorporateAction, RawOHLCVBar, RawTick


class MarketDataConnector(ABC):
    """Common internal contract for all market-data provider adapters — Doc 11 §1.

    Doc 11 §1 Design Principles: "Adapters expose a common internal contract
    regardless of provider." Concrete adapters live in infrastructure/market_data/
    (CCXT for crypto, yfinance for equities — Doc 03 §Quantitative Libraries),
    satisfying Doc 07 §Dependency Rules ("infrastructure implements interfaces
    defined by the domain").

    GAP (flagged per Doc 00 §14.5, not silently implemented): Doc 11 §1 lists
    Authentication, Rate-limit handling, Retry policies, and Source health
    monitoring as connector Responsibilities. This Step 1.2 skeleton does not
    implement rate-limiting, retries, or health monitoring — only the
    unauthenticated/public data path. These remain open follow-up work.
    """

    source_id: str

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        since: datetime | None = None,
        limit: int = 500,
    ) -> list[RawOHLCVBar]: ...

    @abstractmethod
    async def fetch_latest_tick(self, symbol: str) -> RawTick | None: ...


class CorporateActionsConnector(ABC):
    """Corporate-actions data source contract — Doc 11 §3 Corporate Actions Processing.

    JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, Step 1.10): kept as a
    SEPARATE ABC from MarketDataConnector (§1) rather than an additional
    method on it. Corporate actions (splits, dividends, etc.) are an
    equities-market construct with no crypto analog — ccxt/CCXTConnector
    has no equivalent concept, so forcing this onto the shared connector
    contract would require crypto connectors to implement a meaningless
    NotImplementedError stub. Only equities connectors (YFinanceConnector)
    implement this; a connector class may implement both ABCs.

    GAP: Doc 11 §3 names 6 supported event types (Splits, Reverse Splits,
    Dividends, Symbol Changes, Delistings, Mergers); no data source
    implemented in Step 1.10 provides Symbol Changes, Delistings, or
    Mergers — see YFinanceConnector's docstring for why. Doc 11 does not
    name a corporate-actions vendor at all, for any event type.
    """

    source_id: str

    @abstractmethod
    async def fetch_corporate_actions(self, symbol: str) -> list[RawCorporateAction]: ...
