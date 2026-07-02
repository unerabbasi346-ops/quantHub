# Governing specification: Doc 14 §10.6.4 — Signal Validation, Signal Recording
# Layer: Application — Doc 07 §Layers
# Per Doc 00 §14.11
#
# Step 2.2: minimal orchestration wiring Signal Validation (domain/strategy_engine/
# validation.py) to Signal Recording (SignalRepository.record) — the smallest
# unit needed to live-verify the full validate-then-record flow against
# Postgres, mirroring application/market_data/corporate_actions_service.py's
# Acquire/Validate/Persist shape from Step 1.10.
#
# NOT the full StrategyEngineService (application/strategy_engine/service.py,
# Step 0.4 stub) — that requires the strategy registry (Step 2.3) and a real
# plugin invocation (Step 2.4), neither built yet. This service takes an
# already-emitted Signal plus its already-resolved strategy_id/asset_id and
# handles only validation + recording, per this step's explicit scope.
from __future__ import annotations

import logging
from uuid import UUID

from quant_hub.domain.strategy_engine.entities import RecordedSignal, Signal
from quant_hub.domain.strategy_engine.interfaces import SignalRepository
from quant_hub.domain.strategy_engine.validation import (
    VALIDATION_INVALID,
    VALIDATION_VALID,
    validate_signal,
)

logger = logging.getLogger(__name__)


class SignalRecordingService:
    """Validates then records a signal — Doc 14 §10.6.4.

    BEHAVIOR, flagged as a deliberate departure from the Step 1.6 market-data
    pattern (where an invalid bar/tick is rejected and NOT persisted): here,
    every signal is recorded regardless of validation outcome, because Doc
    14 §10.6.4 explicitly says "Every generated signal recorded as immutable
    event per P-5 with timestamp, values, and validation status" — the
    validation_status column IS the record of rejection; there is no
    "reject and drop" path for signals the way there is for bars/ticks.
    An invalid signal is recorded with validation_status=INVALID and a
    WARNING is logged (so the failure is visible, per Doc 11 §5's "reject
    ..., log it clearly" spirit even though this isn't a Doc-11-governed
    stage) — but §10.6.4 also says invalid signals "shall not generate
    orders"; enforcing that gate is downstream of this service (Order
    Generation, out of Phase 2 scope per handbook/KNOWN_LIMITATIONS.md S-4)
    and is not implemented here since no order-generation code exists yet.
    """

    def __init__(self, signals: SignalRepository) -> None:
        self._signals = signals

    async def record_signal(
        self, strategy_id: UUID, asset_id: UUID, signal: Signal
    ) -> RecordedSignal:
        previous = await self._signals.get_latest(strategy_id, asset_id)
        result = validate_signal(signal, previous=previous)
        status = VALIDATION_VALID if result.is_valid else VALIDATION_INVALID

        if not result.is_valid:
            logger.warning(
                "record_signal: recording invalid signal (will not generate orders), "
                "strategy_id=%s asset_id=%s ts=%s errors=%s",
                strategy_id, asset_id, signal.ts, list(result.errors),
            )

        signal_id = await self._signals.record(strategy_id, asset_id, signal, status)
        return RecordedSignal(
            id=signal_id,
            strategy_id=strategy_id,
            asset_id=asset_id,
            value=signal.value,
            ts=signal.ts,
            validation_status=status,
            metadata=signal.metadata,
        )
