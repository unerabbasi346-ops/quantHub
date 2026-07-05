# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Paper Trading — Doc 07 §Core Services
#                          Doc 14 §10.5 — Paper Trading Architecture
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class PaperTradingSimulatorInterface(ABC):
    """Contract for paper trading simulation — Doc 07 §Implementation Rules.

    Paper trading shares the Order/Execution/Position schema with live trading
    (distinguished by portfolio_type='PAPER' in core.portfolios): the TRADE
    artifacts (orders/fills/positions) reuse core.*, preserving T-3 Paper-Live
    Parity — no separate trade tables.

    NOTE (Step 5.0): that reuse is about trade artifacts only. The governed
    paper-trading SESSION record (Doc 14 §10.5.3 config, §10.5.9 promotion
    gate, §10.5.10 artifacts) is a distinct entity with no home in core.* — it
    lives in analytics.paper_trading_sessions (migration f1c8a3e94d20), the
    live-market sibling of analytics.backtests. See PaperTradingSessionRepository.
    """

    @abstractmethod
    async def simulate_fill(self, order: object) -> object: ...


class PaperTradingSessionRepository(ABC):
    """Persistence contract for analytics.paper_trading_sessions — Doc 14 §10.5.

    A paper trading session is the governed live-market validation run (§10.5.3):
    the strategy/portfolio under test, its config, initial capital, status, and
    session-lifetime P&L. The trades it produces live in core.* per T-3 parity;
    this repository owns the session record itself. Concrete implementation is
    raw-SQL and does not commit (the caller owns the transaction boundary,
    Doc 07 §Implementation Rules).

    Read methods return plain dict rows (same shape choice as
    SQLAlchemyBacktestRepository, the sibling); a typed session entity is
    introduced by the 5.2/5.3 runner/service if/when it needs typed access.
    """

    @abstractmethod
    async def create(
        self,
        *,
        strategy_id: UUID,
        portfolio_id: UUID,
        name: str,
        config: dict,
        initial_capital: Decimal,
        description: str | None = None,
        backtest_id: UUID | None = None,
        created_by: UUID | None = None,
    ) -> UUID:
        """Register a RUNNING session (§10.5.3 config recorded, started_at set)."""
        ...

    @abstractmethod
    async def get_by_id(self, session_id: UUID) -> object | None: ...

    @abstractmethod
    async def update_runtime(
        self,
        session_id: UUID,
        *,
        status: str | None = None,
        realized_pnl: Decimal | None = None,
        unrealized_pnl: Decimal | None = None,
        last_pnl_reset_at: datetime | None = None,
        ended_at: datetime | None = None,
        results: dict | None = None,
    ) -> None:
        """Partial update of a session's mutable runtime state (§10.5.7 P&L,
        F-20 reset bookkeeping, status transitions, §10.5.10 artifacts). Only
        provided fields are written; updated_at is always bumped."""
        ...
