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

from quant_hub.domain.strategy_engine.entities import (
    RecordedSignal,
    RegisteredStrategy,
    Signal,
    StrategyRef,
)
from quant_hub.domain.strategy_engine.interfaces import SignalRepository, StrategyRepository
from quant_hub.persistence.repositories.base import BaseRepository


def _row_to_strategy(row: object) -> RegisteredStrategy:
    return RegisteredStrategy(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        version=row["version"],
        status=row["status"],
        config=dict(row["config"] or {}),
        portfolio_id=row["portfolio_id"],
        registered_by=row["registered_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class SQLAlchemyStrategyRepository(BaseRepository[object], StrategyRepository):
    """Concrete repository for core.strategies — Step 2.3, Doc 09 (Step 1.1 schema)."""

    async def upsert(self, strategy: StrategyRef) -> UUID:
        """Resolve-or-register on core.strategies.name — mirrors
        SQLAlchemyAssetRepository.upsert (market_data.py, Step 1.3): ON
        CONFLICT DO UPDATE so a re-registered strategy's description/
        version/config/portfolio drift toward the latest caller-supplied
        state, `id`/`created_at`/`status` excluded from SET, `updated_at`
        via clock_timestamp() (not NOW(), frozen at transaction start —
        same reasoning as market_data.py's upsert methods).

        `status` is deliberately excluded from BOTH the INSERT column list
        (first insert takes the schema DEFAULT 'INACTIVE', Step 1.1) and
        the ON CONFLICT SET clause (re-registration never touches it):
        lifecycle state is a distinct governed concern (Doc 14 §10.2.6,
        "State transitions shall be governed with explicit approval") that
        this resolve-or-register mechanism does not perform.

        FLAGGED TENSION WITH Doc 14 §10.2.5 (Doc 00 §14.5/§14.7 — not
        silently resolved): §10.2.5 states "Every strategy modification
        shall create a new version per P-2" and "Published strategy
        versions shall be immutable... Historical strategy versions shall
        remain available for audit, comparison, and rollback." The Step
        1.1 schema (core.strategies.name UNIQUE, this table's only natural
        key, no separate version-history table) makes that impossible to
        honor with an upsert-on-name pattern: DO UPDATE necessarily
        overwrites the previous version/config row in place rather than
        preserving it. This method implements the resolve-or-register
        pattern exactly as this step's instruction specifies (mirroring
        AssetRepository.upsert), which is the only pattern the current
        schema supports — but §10.2.5's full versioning requirement
        (immutable version history, rollback) is NOT satisfied by it and
        would need a schema change (e.g. a separate core.strategy_versions
        table, or (name, version) as the natural key instead of name
        alone) to be built later. Not resolved here since it was not part
        of this step's scope and predates it (Step 1.1 schema).
        """
        stmt = text(
            """
            INSERT INTO core.strategies (name, description, version, config, portfolio_id, registered_by)
            VALUES (:name, :description, :version, CAST(:config AS JSONB), :portfolio_id, :registered_by)
            ON CONFLICT (name)
            DO UPDATE SET
                description   = EXCLUDED.description,
                version       = EXCLUDED.version,
                config        = EXCLUDED.config,
                portfolio_id  = EXCLUDED.portfolio_id,
                registered_by = EXCLUDED.registered_by,
                updated_at    = clock_timestamp()
            RETURNING id
            """
        )
        result = await self._session.execute(
            stmt,
            {
                "name": strategy.name,
                "description": strategy.description,
                "version": strategy.version,
                "config": json.dumps(dict(strategy.config)),
                "portfolio_id": strategy.portfolio_id,
                "registered_by": strategy.registered_by,
            },
        )
        return result.scalar_one()

    async def get_by_id(self, strategy_id: UUID) -> RegisteredStrategy | None:
        result = await self._session.execute(
            text(
                """
                SELECT id, name, description, version, status, config,
                       portfolio_id, registered_by, created_at, updated_at
                FROM core.strategies
                WHERE id = :id AND deleted_at IS NULL
                """
            ),
            {"id": strategy_id},
        )
        row = result.mappings().one_or_none()
        return None if row is None else _row_to_strategy(row)

    async def list_by_portfolio(self, portfolio_id: UUID) -> list[RegisteredStrategy]:
        result = await self._session.execute(
            text(
                """
                SELECT id, name, description, version, status, config,
                       portfolio_id, registered_by, created_at, updated_at
                FROM core.strategies
                WHERE portfolio_id = :portfolio_id AND deleted_at IS NULL
                ORDER BY created_at
                """
            ),
            {"portfolio_id": portfolio_id},
        )
        return [_row_to_strategy(row) for row in result.mappings().all()]


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
