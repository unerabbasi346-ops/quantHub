# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Strategy Engine — Doc 07 §Core Services
# P-1: platform never assumes any specific strategy — strategies are opaque configs
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from quant_hub.domain.strategy_engine.entities import RecordedSignal, Signal


class StrategyRepository(ABC):
    """Persistence contract for core.strategies — Doc 07 §Implementation Rules.

    P-1: strategy config stored as opaque JSONB; domain never inspects strategy logic.
    """

    @abstractmethod
    async def get_by_id(self, strategy_id: UUID) -> object | None: ...

    @abstractmethod
    async def list_by_portfolio(self, portfolio_id: UUID) -> list[object]: ...


class SignalRepository(ABC):
    """Persistence contract for core.signals — Doc 14 §10.6.4 Signal Recording (Step 2.2).

    Append-only per P-5: no update method exists on this interface — a
    recorded signal is never modified, mirroring TickRepository's
    write-only-append shape (domain/market_data/interfaces.py).
    """

    @abstractmethod
    async def record(
        self,
        strategy_id: UUID,
        asset_id: UUID,
        signal: Signal,
        validation_status: str,
    ) -> UUID:
        """Persist one signal as an immutable event; returns the assigned signal id.

        `strategy_id`, `asset_id`, and `validation_status` are supplied by
        the caller (already resolved/stamped by the platform, per Step
        2.1's design) — never read off `signal` itself, which carries
        none of these three per the emitted-Signal/RecordedSignal split.
        """
        ...

    @abstractmethod
    async def get_latest(self, strategy_id: UUID, asset_id: UUID) -> RecordedSignal | None:
        """Most recently recorded signal for (strategy_id, asset_id), or None.

        Consumed by Signal Validation's rate-of-change/consistency checks
        (domain/strategy_engine/validation.py) as the `previous` argument.
        """
        ...
