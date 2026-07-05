# Governing specification: Doc 14 §10.5 (Paper Trading) / §10.3 (Backtesting)
#   — T-3 Paper-Live Parity: paper trading and backtesting shall share the same
#   signal pipeline, order management, and execution path; only the data source
#   (live bars vs historical replay) and the fill (simulated) differ.
# Layer: Application — Doc 07 §Layers (orchestration only; no SQL of its own)
# Invariants: T-3 (Paper-Live Parity), P-13 (deterministic processing)
# Scope: handbook/KNOWN_LIMITATIONS.md S-5 (backtest) / Phase 5 (paper trading)
# Per Doc 00 §14.11
#
# Step 5.1 — the shared per-bar trade cycle EXTRACTED verbatim from Step 3.7's
# BacktestEngine. This is the parity guarantee the paper-to-live graduation
# gate depends on: the backtest engine (historical replay) and the paper
# trading runner (5.2, live bars) both drive THIS handler identically, so their
# Signal -> Construction -> Sizing -> Order -> Risk -> Fill -> Position logic
# cannot diverge. The only per-driver differences are the two inputs handed in:
# the MarketDataView (point-in-time historical slice vs live) and the market
# `price`/`timestamp` (bar close vs live tick). Extraction is behaviour-
# preserving — proven by the backtest reproducibility hash being byte-identical
# before/after this refactor (same standard as the F-12 inversion).
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from quant_hub.application.execution.order_generation_service import OrderGenerationService
from quant_hub.application.execution.service import ExecutionService
from quant_hub.application.portfolio.construction_service import PortfolioConstructionService
from quant_hub.application.portfolio.sizing_service import PositionSizingService
from quant_hub.application.strategy_engine.signal_recording_service import SignalRecordingService
from quant_hub.domain.execution.entities import CurrentPosition, OrderStatus, TargetPosition
from quant_hub.domain.market_data.entities import AssetRef
from quant_hub.domain.portfolio.construction import PortfolioConstructor, StrategyContribution
from quant_hub.domain.portfolio.interfaces import PositionRepository
from quant_hub.domain.portfolio.sizing import PositionSizer, SizingConstraints, SizingContext
from quant_hub.domain.risk.entities import PreTradeRiskRequest
from quant_hub.domain.strategy_engine.strategy import MarketDataView, Strategy

_ZERO = Decimal("0")


@dataclass(frozen=True)
class CycleStepOutcome:
    """Per-step tally returned by TradingCycle.run_step. `fills` carries the
    ordered ECONOMIC fill tuples (ts_iso, side, quantity, price) the caller
    accumulates — the backtest hashes these for §10.3.6 replay verification;
    the paper runner records them per bar (5.3)."""

    signals_generated: int
    orders_created: int
    orders_filled: int
    orders_rejected: int
    fills: tuple[tuple[str, str, str, str], ...]


class TradingCycle:
    """The shared per-bar trade cycle both backtest and paper trading drive.

    Holds the REAL live-path collaborators (parity, §10.5.4): the same
    SignalRecordingService, PortfolioConstructionService/PositionSizingService,
    OrderGenerationService, and ExecutionService that run live. Instantiates the
    two pure orchestrators (sizing/construction services) internally, exactly as
    the Step 3.7 engine did. Does not commit — the caller owns the transaction
    boundary (Doc 07): a backtest is one atomic unit; the paper runner commits
    per bar (5.2).
    """

    def __init__(
        self,
        *,
        strategy: Strategy,
        signal_recorder: SignalRecordingService,
        sizer: PositionSizer,
        constructor: PortfolioConstructor,
        order_gen: OrderGenerationService,
        execution: ExecutionService,
        positions: PositionRepository,
    ) -> None:
        self._strategy = strategy
        self._signal_recorder = signal_recorder
        self._sizer = sizer
        self._constructor = constructor
        self._order_gen = order_gen
        self._execution = execution
        self._positions = positions
        # Pure orchestrators — the real Step 3.1/3.2 services (no I/O of their own).
        self._sizing = PositionSizingService()
        self._construction = PortfolioConstructionService()

    async def run_step(
        self,
        *,
        view: MarketDataView,
        asset: AssetRef,
        asset_id: UUID,
        price: Decimal,
        timestamp: object,
        strategy_id: UUID,
        portfolio_id: UUID,
        portfolio_value: Decimal,
        strategy_config: Mapping[str, object],
        constraints: SizingConstraints,
    ) -> CycleStepOutcome:
        """Process one bar: generate signals from the handed-in view, then for
        each signal run the real Construction -> Sizing -> Order -> Risk -> Fill
        -> Position path. `price`/`timestamp` are this step's market context
        (bar close + bar ts for a backtest; live tick + wall/bar ts for paper).
        """
        signals = await self._strategy.generate_signals(view, strategy_config)

        signals_generated = orders_created = orders_filled = orders_rejected = 0
        fills: list[tuple[str, str, str, str]] = []

        for signal in signals:
            signals_generated += 1
            recorded = await self._signal_recorder.record_signal(strategy_id, asset_id, signal)

            # Step 3.2 Construction (weights) -> Step 3.1 Sizing (sizes), the real
            # services in Doc 15 §11.3.1 order (Construction first, the F-12 order).
            cons = self._construction.construct_portfolio(
                self._constructor,
                [StrategyContribution(strategy_id=strategy_id, strategy_weight=Decimal("1"), signal=signal)],
            )[0]
            sizing = self._sizing.size_position(
                self._sizer,
                SizingContext(asset=asset, target_weight=cons.target_weight, portfolio_value=portfolio_value),
                constraints,
            )

            current = await self._positions.get_by_portfolio_and_asset(portfolio_id, asset_id)
            cur_qty = current.quantity if current is not None else _ZERO

            # Step 3.3 Order Generation consumes the SIZED output (§11.3.7 ->
            # §10.6.5). TargetPosition takes a weight, so the sized notional is
            # expressed back as a post-sizing weight (identity for N=1, F-12).
            order_target_weight = (
                sizing.target_notional / portfolio_value if portfolio_value > _ZERO else _ZERO
            )
            order = await self._order_gen.generate_order(
                target=TargetPosition(
                    asset=asset, target_weight=order_target_weight,
                    portfolio_value=portfolio_value, reference_price=price,
                ),
                current=CurrentPosition(asset=asset, quantity=cur_qty),
                portfolio_id=portfolio_id, strategy_id=strategy_id, signal_id=recorded.id,
            )
            if order is None:
                continue  # already at target — no order this step

            orders_created += 1
            # Step 3.4 Risk gate + Step 3.5 Fill/Position (the real service).
            request = PreTradeRiskRequest(
                order_id=order.id, portfolio_id=portfolio_id, strategy_id=strategy_id,
                asset_id=asset_id, side=order.side, quantity=order.quantity, price=price,
                current_quantity=cur_qty, portfolio_value=portfolio_value, timestamp=timestamp,
            )
            outcome = await self._execution.process_order(order, request, timestamp)
            if outcome.terminal_status is OrderStatus.FILLED:
                orders_filled += 1
                fills.append((timestamp.isoformat(), order.side.value, str(order.quantity), str(price)))
            else:
                orders_rejected += 1

        return CycleStepOutcome(
            signals_generated=signals_generated,
            orders_created=orders_created,
            orders_filled=orders_filled,
            orders_rejected=orders_rejected,
            fills=tuple(fills),
        )
