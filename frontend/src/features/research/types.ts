// Doc 08 §API Layer: typed models over the REAL research surface —
// /v1/backtests (cross-strategy explorer + run + equity curve) and
// /api/ml/train (background training jobs). The old research_projects/
// experiments shapes pointed at endpoints that never existed; replaced.

// GET /v1/backtests — one analytics.backtests row joined with its computed
// metric suite. Metric fields null when not computed (RUNNING/legacy row).
export interface BacktestSummary {
  id: string
  strategy_id: string | null
  strategy_name: string | null
  name: string
  symbol: string | null
  status: string
  start_date: string | null
  end_date: string | null
  total_return: string | null
  benchmark_return: string | null
  trade_count: number | null
  win_rate: string | null
  sharpe_ratio: string | null
  sortino_ratio: string | null
  max_drawdown_pct: string | null
  profit_factor: string | null
  initial_capital: string | null
  final_capital: string | null
  created_at: string
}

// GET /v1/backtests/{id}/equity-curve — real engine-computed marks,
// stride-downsampled server-side (never interpolated).
export interface EquityPoint {
  ts: string
  portfolio_value: string
  return_pct: string
}

// POST /v1/backtests — 202; poll GET /v1/backtests for run_name.
export interface RunBacktestRequest {
  strategy_id: string
  symbol: string
  exchange?: string
  start: string
  end: string
  // Research capital (sandbox) — the engine's starting equity for this run.
  initial_capital?: string
}

export interface RunBacktestResponse {
  run_name: string
  status: string
  note: string
}

// POST /api/ml/train + GET /api/ml/train/{job_id}/status (api/ml.py).
export interface TrainJob {
  job_id: string
}

// GET /api/ml/regime — latest trained HMM regime state (train-time computed).
export interface RegimeState {
  model_id: string
  trained_at: string
  symbol: string | null
  current_regime: number | null
  current_regime_label: string | null
  current_confidence: number | null
  regime_distribution: Record<string, number> | null
  regime_history: { ts: string; regime: number }[] | null
}

export interface TrainStatus {
  job_id: string
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  model_type: string
  created_at: string
  completed_at: string | null
  metrics: Record<string, unknown> | null
  error: string | null
}
