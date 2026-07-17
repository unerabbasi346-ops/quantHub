// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0) §API Layer
// Typed models mirroring the backend StrategyOut / SignalOut / BacktestOut
// (api/v1/strategies.py, Step 4.5). Reconciled from the Step 0.5 speculative
// shapes (same reconciliation as Steps 4.2–4.4):
//   - snake_case field names (the real JSON contract);
//   - Decimal fields are strings (signal value NUMERIC, backtest returns/capital);
//   - `status` is a FREE-FORM string, not a fixed union: core.strategies.status
//     is a VARCHAR with no enum constraint (real rows carry 'ACTIVE'; the Step
//     0.5 union of INACTIVE/PAPER/LIVE/ARCHIVED never matched the data). Typing
//     it as a literal union would misrepresent what the backend actually sends.
//   - `version` is the CURRENT registration only — no version history exists
//     (F-9); the UI annotates this rather than implying history.
//   - config/metadata are opaque (P-1) — typed as open records, not inspected.
import type { UUID, ISOTimestamp } from '@/types'

export interface Strategy {
  id: UUID
  name: string
  description: string | null
  version: string
  status: string
  config: Record<string, unknown>
  portfolio_id: UUID | null
  created_at: ISOTimestamp | null
  updated_at: ISOTimestamp | null
}

export interface Signal {
  id: UUID
  strategy_id: UUID
  asset_id: UUID
  value: string
  ts: ISOTimestamp
  validation_status: string
  metadata: Record<string, string>
  created_at: ISOTimestamp | null
  // Computed on-the-fly by the API (never stored) — see
  // domain/strategy_engine/implied_sizing.py. implied_size_usdt is null when
  // the strategy has no linked portfolio or that portfolio's capital was
  // never configured (F-19: never fabricated). These are sizing SUGGESTIONS,
  // not executed positions.
  direction: string
  implied_size_usdt: string | null
  implied_leverage: string
  // ML suggestion fields (api/v1/strategies.py's SignalOut docstring): all
  // null unless a DEPLOYED XGBoost_MetaLabeler model exists. Never persisted
  // to core.signals — computed at read time, same pattern as the implied-
  // sizing fields above. ml_tp_suggestion/ml_sl_suggestion/ml_breakeven are
  // SUGGESTIONS derived from real bar volatility, not executed levels.
  ml_confidence: string | null
  ml_probability: string | null
  ml_direction_agreement: boolean | null
  ml_tp_suggestion: string | null
  ml_sl_suggestion: string | null
  ml_breakeven: string | null
  // Read-time quality assessment (domain/strategy_engine/signal_quality.py,
  // surfaced by SignalOut) — never persisted, real rule evaluation only.
  quality_score: string | null
  quality_recommendation: string | null // TRADE | SKIP | REVIEW
  quality_reasons: string[]
}

// The engine's self-describing §10.3.7 result summary (Decimals already
// serialized as strings inside the stored JSONB). Passed through verbatim.
export interface BacktestResults {
  bars_processed: number
  signals_generated: number
  orders_created: number
  orders_filled: number
  orders_rejected: number
  final_position_quantity: string
  realized_pnl: string
  unrealized_pnl: string
  final_capital: string
  total_return: string
  trade_count: number
  reproducibility_hash: string
}

// Computed performance metrics (api/v1/strategies.py's ComputedMetricsOut) —
// the analytics.backtest_computed_metrics row for a strategy's most recent
// COMPLETED backtest. Each field is null when it genuinely couldn't be
// computed (insufficient trade data) — never a fabricated number.
export interface ComputedMetrics {
  backtest_id: UUID
  win_rate: string | null
  sharpe_ratio: string | null
  sortino_ratio: string | null
  max_drawdown_pct: string | null
  calmar_ratio: string | null
  profit_factor: string | null
  expectancy_per_trade: string | null
}

export interface Backtest {
  id: UUID
  strategy_id: UUID | null
  name: string
  status: string
  symbol: string | null
  start_date: ISOTimestamp | null
  end_date: ISOTimestamp | null
  total_return: string | null
  trade_count: number | null
  final_capital: string | null
  reproducibility_hash: string | null
  benchmark_return: string | null
  results: BacktestResults | null
  started_at: ISOTimestamp | null
  completed_at: ISOTimestamp | null
  created_at: ISOTimestamp
}

// GET /v1/strategies/{id}/monthly-returns — one row per calendar month with
// executions; realized_pnl is REAL aggregated execution P&L (NUMERIC string).
export interface MonthlyReturn {
  year: number
  month: number // 1-12
  realized_pnl: string
  trade_count: number
}

// GET /v1/strategies/{id}/trade-pnl-distribution — server-computed histogram
// over realized execution P&L; empty buckets/nulls when no closed trades.
export interface PnlBucket {
  bucket_min: string
  bucket_max: string
  count: number
  total_pnl: string
}

export interface TradePnlDistribution {
  buckets: PnlBucket[]
  trade_count: number
  win_count: number
  loss_count: number
  avg_win: string | null
  avg_loss: string | null
  best_trade: string | null
  worst_trade: string | null
}
