# Governing specification: Doc 11 §1 — Market Data Connectors (Data Engineering)
# Layer: Domain — Doc 07 §Layers
# Dependency rule: domain defines the interface; infrastructure implements it
#   — Doc 07 §Dependency Rules
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from quant_hub.domain.market_data.entities import (
    RawCorporateAction,
    RawFundingRate,
    RawOHLCVBar,
    RawOpenInterest,
    RawTick,
)


def infer_instrument_type(symbol: str, market: dict | None = None) -> str:
    """Classify a ccxt symbol as SPOT or PERPETUAL — pure, no I/O (unit-testable).

    Preference order (most authoritative first):
      1. ccxt market metadata: `market['swap'] is True` (ccxt's own flag for a
         perpetual swap) -> PERPETUAL. This is the ccxt-native source of truth
         and is used whenever the caller has loaded the market dict.
      2. ccxt unified-symbol convention (fallback when `market` is None): a
         perpetual is `BASE/QUOTE:SETTLE` (a settle suffix after ':' with NO
         dated-expiry '-YYMMDD' tail); spot is `BASE/QUOTE` (no ':').

    SCOPE (S-10): only SPOT | PERPETUAL are modelled. A dated future
    (`BASE/QUOTE:SETTLE-YYMMDD`) is NOT a perpetual and NOT in scope — it is
    classified SPOT-by-default here (its ':' carries an expiry '-'), flagged
    so a future dated-futures effort adds an explicit type rather than
    silently mis-reading this fallback. Inverse (coin-margined) perps are out
    of scope per S-10 but WOULD still classify PERPETUAL via market['swap'];
    that is harmless (the type is correct) — the margin math, not this
    classification, is what excludes them.
    """
    if market is not None:
        return "PERPETUAL" if market.get("swap") is True else "SPOT"
    # Symbol-convention fallback: perpetual = ':' present, no dated-expiry tail.
    _, _, settle = symbol.partition(":")
    if settle and "-" not in settle:
        return "PERPETUAL"
    return "SPOT"


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


class FundingRateConnector(ABC):
    """Perpetual funding-rate data source contract (Step 2 of perpetuals work).

    Kept as a SEPARATE ABC from MarketDataConnector for the same reason
    CorporateActionsConnector is (see its docstring): funding is a
    perpetual-derivative construct with no spot/equities analog, so forcing it
    onto the shared connector contract would make spot-only connectors
    (YFinanceConnector) implement a meaningless stub. Only a derivatives
    connector (CCXTConnector against a swap symbol) implements this; a class
    may implement both ABCs.

    JUDGMENT CALL (Doc 00 §14.5/§14.7): the symbol passed must be a ccxt
    PERPETUAL symbol (e.g. "BTC/USDT:USDT"); calling this with a spot symbol
    is a caller error (spot has no funding). Not enforced here — the contract
    documents it; ccxt raises BadSymbol for a non-swap symbol on most venues.
    """

    source_id: str

    @abstractmethod
    async def fetch_funding_rate_history(
        self,
        symbol: str,
        since: datetime | None = None,
        limit: int = 500,
    ) -> list[RawFundingRate]:
        """Historical periodic funding observations for a perpetual, oldest -> newest."""
        ...


class OpenInterestConnector(ABC):
    """Perpetual open-interest data source contract — follows the exact same
    pattern as FundingRateConnector (kept as a separate ABC for the same
    reason: OI is a perpetual-derivative construct with no spot analog).

    JUDGMENT CALL (Doc 00 §14.5/§14.7): the symbol passed must be a ccxt
    PERPETUAL symbol (e.g. "BTC/USDT:USDT"); calling this with a spot symbol
    is a caller error (spot has no open interest in the derivatives sense).
    Not enforced here — the contract documents it; ccxt raises BadSymbol or
    returns an error for a non-swap symbol on most venues.
    """

    source_id: str

    @abstractmethod
    async def fetch_open_interest_history(
        self,
        symbol: str,
        since: datetime | None = None,
        limit: int = 500,
    ) -> list[RawOpenInterest]:
        """Historical periodic open-interest observations for a perpetual, oldest -> newest."""
        ...
