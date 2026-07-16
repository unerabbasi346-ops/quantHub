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
# -> Fill -> Position) was EXTRACTED into the shared TradingCycle so the paper
# trading runner (5.2) drives byte-identical logic (T-3 parity).
#
# Engine step "TP/SL, one-trade rule, 2%/3% sizing, benchmark" (this revision):
# these five rules are BACKTEST-SPECIFIC — no paper/live trading requirement
# asked for them — so rather than bending the shared TradingCycle (and risking
# T-3 parity for a feature paper trading doesn't need), this engine now drives
# its own per-bar loop directly over the same real collaborators TradingCycle
# would have used (order_gen, execution, positions), replacing the
# TradingCycle.run_step delegation. TradingCycle itself is untouched — paper
# trading is unaffected. Deviation flagged, not silent (Doc 00 §14.5/§14.7).
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from uuid import UUID

from quant_hub.application.execution.service import ExecutionService
from quant_hub.application.execution.order_generation_service import OrderGenerationService
from quant_hub.application.strategy_engine.signal_recording_service import SignalRecordingService
from quant_hub.application.trading.cycle import TradingCycle
from quant_hub.domain.analytics.entities import EquityPoint
from quant_hub.domain.analytics.metrics_engine import compute_all_metrics
from quant_hub.domain.backtesting.entities import BacktestConfig, BacktestResult, TradeExit
from quant_hub.domain.backtesting.interfaces import BacktestRepository
from quant_hub.domain.backtesting.trade_rules import (
    compute_benchmark_return,
    compute_position_size,
    compute_tp_sl,
    compute_trade_return_pcts,
)
from quant_hub.domain.execution.entities import CurrentPosition, OrderStatus, TargetPosition
from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.market_data.interfaces import (
    AssetRepository,
    FundingRateRepository,
    OHLCVRepository,
)
from quant_hub.domain.portfolio.construction import PortfolioConstructor
from quant_hub.domain.portfolio.interfaces import PositionRepository
from quant_hub.domain.portfolio.sizing import PositionSizer
from quant_hub.domain.risk.entities import PreTradeRiskRequest
from quant_hub.domain.strategy_engine.strategy import Strategy
from quant_hub.infrastructure.backtesting.point_in_time_view import PointInTimeMarketDataView

_ZERO = Decimal("0")
_BENCHMARK_SYMBOL = "BTC/USDT"  # Rule 5: BTC/USDT buy-and-hold benchmark


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
        funding: FundingRateRepository | None = None,
    ) -> None:
        self._bars = bars
        self._assets = assets
        self._positions = positions
        self._backtests = backtests
        self._signal_recorder = signal_recorder
        self._order_gen = order_gen
        self._execution = execution
        self._strategy = strategy_plugin
        # Optional (additive): a funding-DRIVEN strategy needs point-in-time funding
        # served through the replay view. Left None for spot/equity backtests, which
        # keeps every existing construction site and reproducibility hash unchanged.
        self._funding = funding
        # Kept for constructor-signature/parity compatibility (paper trading's
        # TradingCycle is built the same way) — no longer driven by the main
        # loop below (see module docstring), only sizer/constructor stay
        # referenced here for anyone introspecting the engine's collaborators.
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

        all_funding = (
            await self._funding.get_funding_rates(asset_id, limit=100_000)
            if self._funding is not None else []
        )

        # Rule 1: leverage from strategy config (default 1x — no leverage).
        leverage = Decimal(str(config.strategy_config.get("leverage", "1")))

        backtest_id = await self._backtests.create(config, strategy_id)

        bars_processed = signals_generated = orders_created = orders_filled = orders_rejected = 0
        fills: list[tuple[str, str, str, str]] = []  # (bar_ts, side, quantity, price) — deterministic

        equity_points: list[EquityPoint] = [
            EquityPoint(step=0, ts=config.start, portfolio_value=config.initial_capital, return_pct=_ZERO)
        ]
        trade_pnls: list[Decimal] = []
        prev_equity = config.initial_capital
        prev_realized = _ZERO

        # Rule 2 — one-trade-at-a-time state.
        is_in_trade = False
        entry_price = _ZERO
        entry_bar_index = 0
        direction = 0  # 1 long, -1 short
        tp = _ZERO
        sl = _ZERO
        trades: list[TradeExit] = []

        for i in range(len(all_bars)):
            bars_processed += 1
            bar = all_bars[i]
            view = PointInTimeMarketDataView(
                all_bars[: i + 1], asset, config.interval,
                funding=all_funding, as_of=bar.ts,
            )

            # Rule 3 — TP/SL check on every bar while in a trade, BEFORE any
            # new signal is considered (one-trade-at-a-time: no new entry can
            # occur on the same bar a position is still open).
            if is_in_trade:
                hit_tp = bar.high >= tp if direction > 0 else bar.low <= tp
                hit_sl = bar.low <= sl if direction > 0 else bar.high >= sl
                exit_reason: str | None = None
                exit_price = _ZERO
                if hit_sl:
                    # Both TP and SL touched the same bar: intrabar order is
                    # unknowable from OHLC alone — SL first is the
                    # conservative assumption (never overstate a win).
                    exit_reason, exit_price = "SL_HIT", sl
                elif hit_tp:
                    exit_reason, exit_price = "TP_HIT", tp

                if exit_reason is not None:
                    (
                        is_in_trade, orders_created, orders_filled, orders_rejected,
                    ) = await self._close_trade(
                        asset=asset, asset_id=asset_id, direction=direction,
                        entry_price=entry_price, entry_bar_index=entry_bar_index,
                        exit_price=exit_price, exit_reason=exit_reason, bar_index=i,
                        timestamp=bar.ts, portfolio_id=portfolio_id, strategy_id=strategy_id,
                        portfolio_value=config.initial_capital,
                        orders_created=orders_created, orders_filled=orders_filled,
                        orders_rejected=orders_rejected, fills=fills, trades=trades,
                    )

            # Signal generation + entry only when flat (Rule 2).
            if not is_in_trade:
                signals = await self._strategy.generate_signals(view, config.strategy_config)
                signals_generated += len(signals)
                for signal in signals:
                    recorded = await self._signal_recorder.record_signal(strategy_id, asset_id, signal)
                    if is_in_trade:
                        continue  # Rule 2: an entry already happened this bar — skip the rest
                    sign = 1 if signal.value > 0 else (-1 if signal.value < 0 else 0)
                    if sign == 0:
                        continue

                    ml_confidence = _parse_optional_decimal(signal.metadata.get("ml_confidence"))
                    notional = compute_position_size(config.initial_capital, ml_confidence, leverage)
                    target_weight = (notional * sign) / config.initial_capital if config.initial_capital > _ZERO else _ZERO

                    order = await self._order_gen.generate_order(
                        target=TargetPosition(
                            asset=asset, target_weight=target_weight,
                            portfolio_value=config.initial_capital, reference_price=bar.close,
                        ),
                        current=CurrentPosition(asset=asset, quantity=_ZERO),
                        portfolio_id=portfolio_id, strategy_id=strategy_id, signal_id=recorded.id,
                    )
                    if order is None:
                        continue

                    orders_created += 1
                    request = PreTradeRiskRequest(
                        order_id=order.id, portfolio_id=portfolio_id, strategy_id=strategy_id,
                        asset_id=asset_id, side=order.side, quantity=order.quantity, price=bar.close,
                        current_quantity=_ZERO, portfolio_value=config.initial_capital, timestamp=bar.ts,
                    )
                    outcome = await self._execution.process_order(order, request, bar.ts)
                    if outcome.terminal_status is OrderStatus.FILLED:
                        orders_filled += 1
                        fills.append((bar.ts.isoformat(), order.side.value, str(order.quantity), str(bar.close)))
                        is_in_trade = True
                        entry_price = bar.close
                        entry_bar_index = i
                        direction = sign
                        tp, sl = compute_tp_sl(entry_price, direction, signal.metadata, all_bars[: i + 1])
                    else:
                        orders_rejected += 1

            # Mark-to-market at EVERY bar (not only fill bars).
            position = await self._positions.get_by_portfolio_and_asset(portfolio_id, asset_id)
            qty = position.quantity if position is not None else _ZERO
            avg_entry = position.average_entry_price if position is not None else _ZERO
            cur_realized = position.realized_pnl_today if position is not None else _ZERO
            unrealized_mtm = (bar.close - avg_entry) * qty if qty != _ZERO else _ZERO
            step_equity = config.initial_capital + cur_realized + unrealized_mtm
            step_return = (step_equity - prev_equity) / prev_equity if prev_equity != _ZERO else _ZERO
            equity_points.append(
                EquityPoint(step=i + 1, ts=bar.ts, portfolio_value=step_equity, return_pct=step_return)
            )
            prev_equity = step_equity

            step_realized_delta = cur_realized - prev_realized
            if step_realized_delta != _ZERO:
                trade_pnls.append(step_realized_delta)
            prev_realized = cur_realized

        # Rule 3 — END_OF_DATA: still in a trade when the replay runs out of
        # bars closes it at the last bar's close, never left dangling open.
        if is_in_trade and all_bars:
            last = all_bars[-1]
            (
                is_in_trade, orders_created, orders_filled, orders_rejected,
            ) = await self._close_trade(
                asset=asset, asset_id=asset_id, direction=direction,
                entry_price=entry_price, entry_bar_index=entry_bar_index,
                exit_price=last.close, exit_reason="END_OF_DATA", bar_index=len(all_bars) - 1,
                timestamp=last.ts, portfolio_id=portfolio_id, strategy_id=strategy_id,
                portfolio_value=config.initial_capital,
                orders_created=orders_created, orders_filled=orders_filled,
                orders_rejected=orders_rejected, fills=fills, trades=trades,
            )

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

        # Rule 5 — BTC/USDT buy-and-hold benchmark over the same window.
        # Reuses all_bars directly when this backtest's OWN instrument is
        # already BTC/USDT (no redundant fetch); otherwise resolves and
        # fetches BTC/USDT separately. None (not fabricated) when it isn't ingested.
        benchmark_return = None
        if config.symbol == _BENCHMARK_SYMBOL:
            benchmark_return = compute_benchmark_return(all_bars)
        else:
            btc_asset_id = await self._assets.get_by_symbol_exchange(_BENCHMARK_SYMBOL, config.exchange)
            if btc_asset_id is not None:
                btc_bars = await self._bars.get_bars_range(btc_asset_id, config.interval, config.start, config.end)
                benchmark_return = compute_benchmark_return(btc_bars)

        # §10.3.6 Replay Verification: hash the ordered ECONOMIC outputs only.
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
            benchmark_return=benchmark_return,
        )
        await self._backtests.complete(backtest_id, result)

        await self._backtests.save_equity_curve(backtest_id, equity_points)
        metrics = compute_all_metrics(
            backtest_id,
            [p.portfolio_value for p in equity_points],
            trade_pnls,
        )
        await self._backtests.save_computed_metrics(metrics)

        return backtest_id, result

    async def _close_trade(
        self,
        *,
        asset: AssetRef,
        asset_id: UUID,
        direction: int,
        entry_price: Decimal,
        entry_bar_index: int,
        exit_price: Decimal,
        exit_reason: str,
        bar_index: int,
        timestamp: object,
        portfolio_id: UUID,
        strategy_id: UUID,
        portfolio_value: Decimal,
        orders_created: int,
        orders_filled: int,
        orders_rejected: int,
        fills: list[tuple[str, str, str, str]],
        trades: list[TradeExit],
    ) -> tuple[bool, int, int, int]:
        """Flatten the open position at `exit_price` (Rule 3 TP/SL/END_OF_DATA
        exit) through the same real order_gen/execution path as an entry, and
        persist the trade's realized outcome (Rule 4) onto the closing fill.
        Returns the updated (is_in_trade, orders_created, orders_filled,
        orders_rejected) tuple for the caller to reassign.
        """
        current = await self._positions.get_by_portfolio_and_asset(portfolio_id, asset_id)
        cur_qty = current.quantity if current is not None else _ZERO

        order = await self._order_gen.generate_order(
            target=TargetPosition(
                asset=asset, target_weight=_ZERO,
                portfolio_value=portfolio_value, reference_price=exit_price,
            ),
            current=CurrentPosition(asset=asset, quantity=cur_qty),
            portfolio_id=portfolio_id, strategy_id=strategy_id, signal_id=None,
        )
        is_in_trade = True  # stays open unless the flatten order genuinely fills below
        if order is None:
            return is_in_trade, orders_created, orders_filled, orders_rejected

        orders_created += 1
        request = PreTradeRiskRequest(
            order_id=order.id, portfolio_id=portfolio_id, strategy_id=strategy_id,
            asset_id=asset_id, side=order.side, quantity=order.quantity, price=exit_price,
            current_quantity=cur_qty, portfolio_value=portfolio_value, timestamp=timestamp,
        )
        price_return_pct, market_move_pct = compute_trade_return_pcts(entry_price, exit_price, direction)
        outcome = await self._execution.process_order(
            order, request, timestamp,
            price_return_pct=price_return_pct, market_move_pct=market_move_pct, exit_reason=exit_reason,
        )
        if outcome.terminal_status is OrderStatus.FILLED:
            orders_filled += 1
            fills.append((
                timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
                order.side.value, str(order.quantity), str(exit_price),
            ))
            trades.append(TradeExit(
                entry_price=entry_price, exit_price=exit_price, exit_reason=exit_reason,
                trade_duration_bars=bar_index - entry_bar_index,
                price_return_pct=price_return_pct, market_move_pct=market_move_pct,
            ))
            is_in_trade = False
        else:
            orders_rejected += 1
            # A rejected flatten order leaves the position genuinely still
            # open — is_in_trade correctly stays True; the next bar will
            # retry the TP/SL check against the (still real) open position.

        return is_in_trade, orders_created, orders_filled, orders_rejected


def _parse_optional_decimal(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    try:
        return Decimal(raw)
    except (ValueError, ArithmeticError):
        return None
