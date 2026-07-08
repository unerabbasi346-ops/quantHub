# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Domain — Doc 07 §Layers
# Service: Strategy Engine — Doc 07 §Core Services
# P-1: platform never assumes any specific strategy — strategies are opaque configs
# Per Doc 00 §14.11
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from quant_hub.domain.strategy_engine.entities import (
    RecordedSignal,
    RegisteredStrategy,
    Signal,
    StrategyRef,
)


class StrategyRepository(ABC):
    """Persistence contract for core.strategies — Doc 07 §Implementation Rules.

    P-1: strategy config stored as opaque JSONB; domain never inspects strategy logic.
    """

    @abstractmethod
    async def upsert(self, strategy: StrategyRef) -> UUID:
        """Resolve-or-register on core.strategies.name — Step 2.3.

        Makes a strategy's identity concrete and persistent: `strategy_id`
        (referenced by core.signals, Step 2.2) must resolve to a real,
        registered row here, never an arbitrary caller-supplied UUID.
        """
        ...

    @abstractmethod
    async def get_by_id(self, strategy_id: UUID) -> RegisteredStrategy | None: ...

    @abstractmethod
    async def list_by_portfolio(self, portfolio_id: UUID) -> list[RegisteredStrategy]: ...

    @abstractmethod
    async def list_all(self) -> list[RegisteredStrategy]:
        """All registered (non-soft-deleted) strategies, stably ordered.

        Added in Step 4.5 (Strategies Vertical Slice), its first real consumer
        (GET /v1/strategies — the strategy registry). list_by_portfolio scopes
        to one portfolio; the registry shows every strategy.
        """
        ...

    @abstractmethod
    async def set_status(self, strategy_id: UUID, status: str) -> RegisteredStrategy | None:
        """Transition a strategy's lifecycle `status` (Doc 14 §10.2.6 —
        "State transitions shall be governed with explicit approval"), returning
        the updated row or None if no such strategy exists.

        This is the deliberate, separate lifecycle-write that `upsert`
        intentionally does NOT perform (upsert excludes status from its SET
        clause so resolve-or-register never silently flips lifecycle state).
        The "explicit approval" §10.2.6 requires is the operator invoking this
        via the Activate/Deactivate control — the first real write action in
        the dashboard. Does not commit (caller owns the transaction).
        """
        ...


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

    @abstractmethod
    async def list_by_strategy(self, strategy_id: UUID, limit: int) -> list[RecordedSignal]:
        """Most-recent-first recorded signals for `strategy_id`, up to `limit`.

        Added in Step 4.5 (the signals feed, GET /v1/strategies/{id}/signals).
        A bounded recent window over the immutable event log — where
        get_latest returns only the single newest across an (strategy, asset),
        this returns the recent stream for the whole strategy for display.
        """
        ...
