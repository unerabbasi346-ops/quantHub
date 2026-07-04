// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0) §API Layer
// Typed models mirroring the backend RiskLimitOut / PreTradeAssessmentOut /
// RiskSnapshotOut (api/v1/risk.py, Step 4.6). Reconciled from the Step 0.5
// speculative shape (same reconciliation as Steps 4.2–4.5):
//   - snake_case field names (the real JSON contract);
//   - Decimal fields are strings (exposures, leverage, limit values, utilization);
//   - the snapshot does NOT carry VaR/CVaR/volatility/drawdown/beta as values:
//     they are DEFERRED (F-18) and arrive as a `deferred_metrics` list (name +
//     reason), so the UI shows them as not-computed, never as a real 0.
// Per Doc 00 §14.11
import type { UUID, ISOTimestamp } from '@/types'

export interface RiskLimit {
  limit_id: UUID
  metric_name: string
  limit_value: string
  warning_threshold: string
  // "continuous" (utilization computed vs the latest snapshot) or "pre_trade"
  // (evaluated per order at §10.7.5 — no standing portfolio utilization).
  evaluation: string
  current_value: string | null
  utilization: string | null
  status: string | null // "ok" | "warning" | "breach" | null (not evaluated)
}

export interface PreTradeCheck {
  check_name: string
  passed: boolean
  detail: string
}

export interface PreTradeAssessment {
  check_id: UUID
  order_id: UUID
  portfolio_id: UUID
  authorized: boolean
  rejection_reason: string | null
  individual_checks: PreTradeCheck[]
  computation_latency_ns: number
  assessed_at: ISOTimestamp
}

// A §11.5.3 metric NOT computed yet (F-18) — named + reason, shown as deferred.
export interface DeferredMetric {
  name: string
  reason: string
}

export interface RiskBreach {
  metric_name: string
  current_value: string
  limit_value: string
  utilization: string
  status: string
}

export interface RiskSnapshot {
  portfolio_id: UUID
  snapshot_at: ISOTimestamp
  // COMPUTED (real, from positions) — Doc 15 §11.5.3
  gross_exposure: string
  net_exposure: string
  gross_leverage: string
  net_leverage: string
  // DEFERRED (F-18) — named, never presented as real values
  deferred_metrics: DeferredMetric[]
  breaches: RiskBreach[]
}
