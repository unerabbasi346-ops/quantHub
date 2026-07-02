# Governing specification: Doc 14 §10.6.5 — Order Generation
# Layer: Application — Doc 07 §Layers
# Invariants: P-1 (no strategy logic in validation/generation — §10.7.5), P-13
# Scope: handbook/KNOWN_LIMITATIONS.md S-5
# Per Doc 00 §14.11
#
# Thin orchestration around the pure domain computation
# (domain/execution/order_generation.compute_order_intent): resolve the
# AssetRef to an asset_id, mint the client-generated UUID v7 idempotency key
# (§10.7.5), run the pure computation, and persist a CREATED order. Mirrors
# SignalRecordingService's shape (application/strategy_engine/
# signal_recording_service.py): a small service that wires one pure
# domain step to one repository write for live verification.
#
# NOT the full ExecutionService (application/execution/service.py, Step 0.4
# stub) — that owns the risk-gated submission/routing loop (§10.7.6/§10.8,
# Steps 3.4/3.5). This service stops at CREATED (§10.7.4): it does no
# pre-trade validation (Step 3.4, §10.7.5) and no routing/execution (Step 3.5).
from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID, uuid7

from quant_hub.domain.execution.entities import (
    CurrentPosition,
    RecordedOrder,
    TargetPosition,
)
from quant_hub.domain.execution.interfaces import OrderRepository
from quant_hub.domain.execution.order_generation import compute_order_intent
from quant_hub.domain.market_data.interfaces import AssetRepository

logger = logging.getLogger(__name__)


class OrderGenerationService:
    """Generate and persist an order from a §11.2 target — Doc 14 §10.6.5.

    Order Generation is a pure PLATFORM mechanism (§10.7.5: "Validation shall
    not embed strategy-specific logic per P-1"); there is no external
    methodology plugin here, unlike Sizing/Construction. The service adds only
    the I/O the pure computation cannot do: asset-id resolution, idempotency-key
    generation, and the CREATED write.
    """

    def __init__(self, orders: OrderRepository, assets: AssetRepository) -> None:
        self._orders = orders
        self._assets = assets

    async def generate_order(
        self,
        *,
        target: TargetPosition,
        current: CurrentPosition,
        portfolio_id: UUID,
        strategy_id: UUID | None,
        signal_id: UUID | None = None,
        min_quantity: Decimal = Decimal("0"),
    ) -> RecordedOrder | None:
        """Compute the order moving `current` toward `target` and persist it as
        CREATED, or return None if no order is needed (already at target).

        The idempotency key (§10.7.5, UUID v7) is minted here — client-side,
        per unique order intent — not inside the pure computation, so the
        domain function stays deterministic (P-13). Python 3.14's stdlib
        uuid.uuid7 provides the time-ordered v7 the spec requires.
        """
        asset_id = await self._assets.get_by_symbol_exchange(
            target.asset.symbol, target.asset.exchange
        )
        if asset_id is None:
            # §10.7.5 "Instrument Validation — Instrument is ... currently
            # tradable". A target for an unregistered instrument cannot be
            # ordered; fail loudly rather than write a dangling asset_id.
            raise ValueError(
                f"asset not registered: {target.asset.symbol}@{target.asset.exchange}"
            )

        intent = compute_order_intent(
            target=target,
            current=current,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            signal_id=signal_id,
            idempotency_key=uuid7(),
            min_quantity=min_quantity,
        )
        if intent is None:
            logger.info(
                "generate_order: no order — already at target, portfolio_id=%s asset=%s@%s",
                portfolio_id, target.asset.symbol, target.asset.exchange,
            )
            return None

        return await self._orders.create(intent, asset_id)
