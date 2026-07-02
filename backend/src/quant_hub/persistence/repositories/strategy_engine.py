# Governing specification: Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Persistence — Doc 07 §Layers
# Repository pattern — Doc 07 §Implementation Rules
# P-1: strategy config is opaque JSONB; repository never interprets it
# Doc 14 §10.6.4 Signal Recording; P-5 immutability
# Per Doc 00 §14.11
#
# SQLAlchemySignalRepository (Step 2.2): real write for SignalRepository.record,
# backed by migration 7c7482e4e00a (core.signals). Raw-SQL-first via
# sqlalchemy.text(), same approach as persistence/repositories/market_data.py —
# no ORM models exist for this schema (target_metadata=None in env.py, Doc 09
# §Migration Strategy). Does not commit the session — transaction-boundary
# ownership belongs to the caller (Doc 07 §Implementation Rules), same
# convention as market_data.py and SQLAlchemyStrategyRepository below.
from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text

from quant_hub.domain.strategy_engine.entities import RecordedSignal, Signal
from quant_hub.domain.strategy_engine.interfaces import SignalRepository, StrategyRepository
from quant_hub.persistence.repositories.base import BaseRepository


class SQLAlchemyStrategyRepository(BaseRepository[object], StrategyRepository):
    """Concrete repository for core.strategies."""

    async def get_by_id(self, strategy_id: UUID) -> object | None:
        return None  # stub

    async def list_by_portfolio(self, portfolio_id: UUID) -> list[object]:
        return []  # stub


class SQLAlchemySignalRepository(BaseRepository[object], SignalRepository):
    """Concrete repository for core.signals — Step 2.2, Doc 14 §10.6.4."""

    async def record(
        self,
        strategy_id: UUID,
        asset_id: UUID,
        signal: Signal,
        validation_status: str,
    ) -> UUID:
        """Append-only INSERT — no ON CONFLICT / upsert / update path.

        Deliberately the plainest possible write: unlike
        assets.upsert/ohlcv_bars.upsert_bars/corporate_actions.upsert_actions
        (all ON CONFLICT DO UPDATE, correctable data), a recorded signal is
        an immutable event per P-5 and this step's explicit requirement —
        there is no legitimate "correction" of a past signal, so no
        conflict-resolution clause exists at all. Closer in spirit to
        TickRepository.save_tick's append-only nature, except a signal has
        no natural idempotency key yet to conflict on (see the migration's
        "no idempotency constraint" judgment call, flagged as an open
        gap) — so this is a bare INSERT, not INSERT ... ON CONFLICT DO
        NOTHING.

        `metadata` (Signal.metadata, an opaque strategy-supplied mapping)
        is JSON-encoded and cast to ::jsonb in SQL — the codebase has no
        prior JSONB write path to follow (core.strategies.config has never
        been written by application code either), so this is a fresh,
        minimal choice: json.dumps + explicit cast avoids depending on
        driver-specific JSONB codec configuration.
        """
        stmt = text(
            """
            INSERT INTO core.signals (strategy_id, asset_id, value, ts, validation_status, metadata)
            VALUES (:strategy_id, :asset_id, :value, :ts, :validation_status, CAST(:metadata AS JSONB))
            RETURNING id
            """
        )
        result = await self._session.execute(
            stmt,
            {
                "strategy_id": strategy_id,
                "asset_id": asset_id,
                "value": signal.value,
                "ts": signal.ts,
                "validation_status": validation_status,
                "metadata": json.dumps(dict(signal.metadata)),
            },
        )
        return result.scalar_one()

    async def get_latest(self, strategy_id: UUID, asset_id: UUID) -> RecordedSignal | None:
        """Most recent recorded signal for (strategy_id, asset_id) — feeds
        Signal Validation's rate-of-change/consistency checks."""
        result = await self._session.execute(
            text(
                """
                SELECT id, strategy_id, asset_id, value, ts, validation_status, metadata, created_at
                FROM core.signals
                WHERE strategy_id = :strategy_id AND asset_id = :asset_id
                ORDER BY ts DESC
                LIMIT 1
                """
            ),
            {"strategy_id": strategy_id, "asset_id": asset_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        return RecordedSignal(
            id=row["id"],
            strategy_id=row["strategy_id"],
            asset_id=row["asset_id"],
            value=row["value"],
            ts=row["ts"],
            validation_status=row["validation_status"],
            metadata=dict(row["metadata"] or {}),
            created_at=row["created_at"],
        )
