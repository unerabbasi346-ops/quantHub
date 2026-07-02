# Governing specification: Doc 11 §3 — Corporate Actions Processing (Data Engineering)
# Layer: Application — Doc 07 §Layers
# Per Doc 00 §14.11
#
# Step 1.10: Acquire/Validate/Persist orchestration for corporate actions,
# mirroring MarketDataIngestionService's structure (service.py) but as a
# separate, small, focused service (Doc 07 §Implementation Rules) rather
# than an added method there — CorporateActionsConnector is a distinct
# interface from MarketDataConnector (see domain/market_data/connectors.py
# for why: ccxt/crypto has no corporate-actions concept), so not every
# MarketDataIngestionService caller could even satisfy this dependency.
#
# SCOPE (per handbook/KNOWN_LIMITATIONS.md S-1/S-2): no Quality Scoring
# stage — market_data.corporate_actions has no data_quality column (Step
# 1.1 schema), so Doc 11 §6 doesn't apply here. No late-arrival/version-
# history wiring (Doc 11 §7, Step 1.9) — corporate actions are low-volume,
# not a continuous time series the same way bars/ticks are; the
# insert/revised tally in SQLAlchemyCorporateActionsRepository.
# upsert_actions already gives the same minimal version-history signal
# (S-3) without needing a separate watermark query.
from __future__ import annotations

import logging

from quant_hub.domain.market_data.connectors import CorporateActionsConnector
from quant_hub.domain.market_data.entities import CorporateAction
from quant_hub.domain.market_data.interfaces import AssetRepository, CorporateActionsRepository
from quant_hub.domain.market_data.validation import validate_corporate_action
from quant_hub.infrastructure.market_data.retry import RetryExhaustedError

logger = logging.getLogger(__name__)


class CorporateActionsIngestionService:
    """Corporate-actions ingestion orchestration — Doc 11 §3, §2 (Acquire, Validate, Persist).

    Doc 11 §3 Rules: "Original raw values remain preserved" — this
    service never touches market_data.ohlcv_bars. Retroactively computing
    and applying a split/dividend adjustment factor to historical bars is
    explicitly NOT implemented here — that is a distinct, materially
    larger feature (correctly chaining multiple adjustments over a price
    series) that Doc 11 §3 does not detail either. Flagged as a gap for a
    future step, not silently built or silently ignored.
    """

    def __init__(
        self,
        connector: CorporateActionsConnector,
        assets: AssetRepository,
        corporate_actions: CorporateActionsRepository,
    ) -> None:
        self._connector = connector
        self._assets = assets
        self._corporate_actions = corporate_actions

    async def ingest_corporate_actions(self, symbol: str) -> int:
        """Acquire, validate, and persist corporate actions for `symbol`.

        Returns the count persisted (inserted + revised), mirroring
        MarketDataIngestionService.ingest_ohlcv's `persisted` semantics.
        """
        try:
            raw_actions = await self._connector.fetch_corporate_actions(symbol)
        except RetryExhaustedError as exc:
            # Doc 11 §8 — same S-2-scoped reasoning as
            # MarketDataIngestionService.ingest_ohlcv's acquire-failure log.
            logger.error(
                "ingest_corporate_actions: acquire failed after retries, symbol=%s "
                "attempts=%d last_error=%r",
                symbol, exc.attempts, exc.last_error,
            )
            return 0

        if not raw_actions:
            return 0

        valid_raw_actions = []
        for action in raw_actions:
            result = validate_corporate_action(action)
            if result.is_valid:
                valid_raw_actions.append(action)
            else:
                # Doc 11 §5 Failure Policy — same S-2-scoped structured-log
                # rejection as MarketDataIngestionService.ingest_ohlcv.
                logger.warning(
                    "ingest_corporate_actions: rejected invalid action, symbol=%s "
                    "errors=%s action=%r",
                    symbol, list(result.errors), action,
                )

        if not valid_raw_actions:
            return 0

        asset_id = await self._assets.upsert(valid_raw_actions[0].asset)
        actions = [
            CorporateAction(
                asset_id=asset_id,
                action_type=action.action_type,
                ex_date=action.ex_date,
                ratio=action.ratio,
                amount=action.amount,
                currency=action.currency,
                record_date=action.record_date,
                payment_date=action.payment_date,
                notes=action.notes,
            )
            for action in valid_raw_actions
        ]
        return await self._corporate_actions.upsert_actions(actions)
