# Governing specification: Doc 14 §10.6.4 (Signal Generation Pipeline);
#   Doc 07 — Backend Architecture (QH-007 v1.0)
# Layer: Application — Doc 07 §Layers
# Per Doc 00 §14.11
#
# Step 2.4: the full vertical slice — resolve a registered strategy (Step
# 2.3) -> resolve its plugin class (Step 2.4 plugin_registry) -> instantiate
# -> generate_signals(view, config) (Step 2.1) -> validate + record each
# returned Signal (Step 2.2). This is the smallest orchestration that
# proves Steps 2.1-2.3's interfaces are genuinely pluggable end-to-end; it
# is NOT the full StrategyEngineService (application/strategy_engine/
# service.py, Step 0.4 stub, still unimplemented) — no scheduling, no
# multi-strategy fan-out, no paper/live trading modes (Doc 14 §10.5/§10.6),
# none of which this step's scope calls for.
from __future__ import annotations

from uuid import UUID

from quant_hub.application.strategy_engine.signal_recording_service import (
    SignalRecordingService,
)
from quant_hub.domain.market_data.interfaces import AssetRepository
from quant_hub.domain.strategy_engine.entities import RecordedSignal, StrategyRef
from quant_hub.domain.strategy_engine.interfaces import StrategyRepository
from quant_hub.domain.strategy_engine.strategy import MarketDataView
from quant_hub.infrastructure.strategy_engine.plugin_registry import resolve_plugin


async def run_strategy_once(
    strategy_ref: StrategyRef,
    strategies: StrategyRepository,
    assets: AssetRepository,
    view: MarketDataView,
    recorder: SignalRecordingService,
) -> list[RecordedSignal]:
    """Resolve-or-register `strategy_ref`, run its plugin once, record every
    emitted signal (valid or invalid — Step 2.2), return what was recorded.

    JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged): "run once" rather than a
    scheduled/looping engine — Doc 14 §10.6 (Live Trading) implies a
    continuously-running process, but building a scheduler is out of this
    step's scope (proving pluggability, not building the production
    engine loop). A caller (e.g. scripts/run_reference_strategy.py, or a
    future scheduler) invokes this once per desired signal-generation
    cycle.
    """
    strategy_id = await strategies.upsert(strategy_ref)
    plugin_cls = resolve_plugin(strategy_ref.name)
    plugin = plugin_cls()

    signals = await plugin.generate_signals(view, strategy_ref.config)

    recorded: list[RecordedSignal] = []
    for signal in signals:
        # JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, deliberately NOT
        # assets.upsert()): a signal's asset must already exist — the
        # plugin could only have emitted this signal by successfully
        # reading bars/ticks for it through the view (Step 2.1's
        # MarketDataView), which itself requires the asset to already be
        # registered (see RepositoryBackedMarketDataView). Calling
        # assets.upsert(signal.asset) here would be a real correctness
        # bug, not a harmless idempotent no-op: AssetRef as reconstructed
        # by a plugin (e.g. MovingAverageCrossoverStrategy) carries no
        # `name`/`currency` (they default to None/"USD"), and upsert's
        # ON CONFLICT DO UPDATE would silently overwrite the real
        # name/currency Phase 1 ingestion already wrote with those
        # defaults. Resolve-only (get_by_symbol_exchange) avoids that.
        asset_id: UUID | None = await assets.get_by_symbol_exchange(
            signal.asset.symbol, signal.asset.exchange
        )
        if asset_id is None:
            raise ValueError(
                f"strategy {strategy_ref.name!r} emitted a signal for an "
                f"unregistered asset symbol={signal.asset.symbol!r} "
                f"exchange={signal.asset.exchange!r} — this should be "
                "unreachable if the signal was derived from view data"
            )
        recorded.append(await recorder.record_signal(strategy_id, asset_id, signal))
    return recorded
