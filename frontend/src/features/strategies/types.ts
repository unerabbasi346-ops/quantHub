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

export interface Backtest {
  id: UUID
  strategy_id: UUID | null
  name: string
  status: string
  start_date: ISOTimestamp | null
  end_date: ISOTimestamp | null
  total_return: string | null
  trade_count: number | null
  final_capital: string | null
  reproducibility_hash: string | null
  results: BacktestResults | null
  started_at: ISOTimestamp | null
  completed_at: ISOTimestamp | null
  created_at: ISOTimestamp
}
