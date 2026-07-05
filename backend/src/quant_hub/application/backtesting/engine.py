# Governing specification: Doc 14 §10.3 — Backtesting Engine Architecture
#   §10.3.4 (Point-in-Time), §10.3.5 (Execution Simulation), §10.3.6 (Deterministic Replay)
# Layer: Application — Doc 07 §Layers (orchestration only; no SQL of its own)
# Invariants: P-13 (deterministic backtesting), Paper-Live Parity (§10.3, §343)
# Scope: handbook/KNOWN_LIMITATIONS.md S-5 / F-21
# Per Doc 00 §14.11
#
# Step 3.7 — the final Phase 3A step. This engine does NOT re-implement the
# trade loop; it REPLAYS the exact Step 3.1–3.5 path over historical bars.
# Paper-live parity (Doc 14's own principle, §343 "paper-live parity testing"):
# the same PositionSizingService, PortfolioConstructionService,
# OrderGenerationService, and ExecutionService that run live are the ones
# invoked here — the only backtest-specific pieces are (a) the point-in-time
# MarketDataView that clamps the strategy to bars at/before each step, and
# (b) using each bar's close as the step's market price instead of a live tick.
# There is no wall-clock dependency and no randomness, so replay is
# deterministic per P-13 / §10.3.6.
#
# Step 5.1 — the per-bar body (Signal -> Construction -> Sizing -> Order -> Risk
# -> Fill -> Position) is EXTRACTED into the shared TradingCycle so the paper
# trading runner (5.2) drives byte-identical logic (T-3 parity). This engine
# now owns only the backtest-specific shell: loading the historical bar range,
# building the point-in-time view per bar, recording the backtest row, and the
# §10.3.6 reproducibility hash. The constructor is unchanged — it still accepts
# the same collaborators and assembles the TradingCycle internally.
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from uuid import UUID

from quant_hub.application.execution.service import ExecutionService
from quant_hub.application.execution.order_generation_service import OrderGenerationService
from quant_hub.application.strategy_engine.signal_recording_service import SignalRecordingService
from quant_hub.application.trading.cycle import TradingCycle
from quant_hub.domain.backtesting.entities import BacktestConfig, BacktestResult
from quant_hub.domain.backtesting.interfaces import BacktestRepository
from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.market_data.interfaces import AssetRepository, OHLCVRepository
from quant_hub.domain.portfolio.construction import PortfolioConstructor
from quant_hub.domain.portfolio.interfaces import PositionRepository
from quant_hub.domain.portfolio.sizing import PositionSizer, SizingConstraints
from quant_hub.domain.strategy_engine.strategy import Strategy
from quant_hub.infrastructure.backtesting.point_in_time_view import PointInTimeMarketDataView

_ZERO = Decimal("0")


class BacktestEngine:
    """Deterministic historical replay reusing the live Step 3.1–3.5 path.

    Every collaborator is a REAL live-path service/repository (parity, §10.3):
    the engine adds only the replay loop and the point-in-time view. Does not
    commit — the caller owns the transaction boundary (Doc 07), so an entire
    backtest is one atomic unit of work.
    """

    def __init__(
        self,
        *,
        bars: OHLCVRepository,
        assets: AssetRepository,
        positions: PositionRepository,
        backtests: BacktestRepository,
        signal_recorder: SignalRecordingService,
        sizer: PositionSizer,
        constructor: PortfolioConstructor,
        order_gen: OrderGenerationService,
        execution: ExecutionService,
        strategy_plugin: Strategy,
    ) -> None:
        self._bars = bars
        self._assets = assets
        self._positions = positions
        self._backtests = backtests
        # The shared per-bar trade cycle (Step 5.1) — the same handler the paper
        # trading runner drives, so backtest and paper logic cannot diverge (T-3).
        self._cycle = TradingCycle(
            strategy=strategy_plugin,
            signal_recorder=signal_recorder,
            sizer=sizer,
            constructor=constructor,
            order_gen=order_gen,
            execution=execution,
            positions=positions,
        )

    async def run(
        self, config: BacktestConfig, *, strategy_id: UUID, portfolio_id: UUID
    ) -> tuple[UUID, BacktestResult]:
        asset = AssetRef(symbol=config.symbol, exchange=config.exchange, asset_class=config.asset_class)
        asset_id = await self._assets.get_by_symbol_exchange(config.symbol, config.exchange)
        if asset_id is None:
            raise ValueError(f"no ingested data for {config.symbol}@{config.exchange}")

        all_bars = await self._bars.get_bars_range(asset_id, config.interval, config.start, config.end)
        constraints = SizingConstraints(max_position_pct=config.max_position_pct)

        backtest_id = await self._backtests.create(config, strategy_id)

        bars_processed = signals_generated = orders_created = orders_filled = orders_rejected = 0
        fills: list[tuple[str, str, str, str]] = []  # (bar_ts, side, quantity, price) — deterministic

        for i in range(len(all_bars)):
            bars_processed += 1
            bar = all_bars[i]
            # §10.3.4 point-in-time: strategy sees only bars at/before this one.
            # Backtest-specific inputs to the shared cycle: the clamped view and
            # the bar close as this step's market price (no live tick).
            view = PointInTimeMarketDataView(all_bars[: i + 1], asset, config.interval)
            outcome = await self._cycle.run_step(
                view=view,
                asset=asset,
                asset_id=asset_id,
                price=bar.close,
                timestamp=bar.ts,
                strategy_id=strategy_id,
                portfolio_id=portfolio_id,
                portfolio_value=config.initial_capital,
                strategy_config=config.strategy_config,
                constraints=constraints,
            )
            signals_generated += outcome.signals_generated
            orders_created += outcome.orders_created
            orders_filled += outcome.orders_filled
            orders_rejected += outcome.orders_rejected
            fills.extend(outcome.fills)

        # Final marks from the position Step 3.6 maintains.
        final = await self._positions.get_by_portfolio_and_asset(portfolio_id, asset_id)
        final_qty = final.quantity if final is not None else _ZERO
        realized = final.realized_pnl_today if final is not None else _ZERO
        unrealized = final.unrealized_pnl if final is not None else _ZERO
        final_capital = config.initial_capital + realized + unrealized
        total_return = (
            ((final_capital - config.initial_capital) / config.initial_capital)
            if config.initial_capital > _ZERO else _ZERO
        )

        # §10.3.6 Replay Verification: hash the ordered ECONOMIC outputs only —
        # never the non-deterministic UUIDv7 ids / wall-clock created_at — so an
        # identical replay reproduces an identical digest.
        reproducibility_hash = hashlib.sha256(
            json.dumps({"fills": fills, "initial_capital": str(config.initial_capital)},
                       separators=(",", ":")).encode()
        ).hexdigest()

        result = BacktestResult(
            bars_processed=bars_processed,
            signals_generated=signals_generated,
            orders_created=orders_created,
            orders_filled=orders_filled,
            orders_rejected=orders_rejected,
            final_position_quantity=final_qty,
            realized_pnl=realized,
            unrealized_pnl=unrealized,
            final_capital=final_capital,
            total_return=total_return,
            trade_count=orders_filled,
            reproducibility_hash=reproducibility_hash,
        )
        await self._backtests.complete(backtest_id, result)
        return backtest_id, result
