// Governing specification: Doc 00 §14.5/§14.7 — DATA HONESTY. Every figure
// here is a deterministic transform of real Order/Execution/Signal data — no
// fabricated slippage, TWAP/VWAP, or latency metrics (none exist in this
// schema; Doc 14 §10.7 models a simulated immediate fill with no routing
// round-trip, F-16). Pure helpers kept out of the component files so the
// math is independently readable/testable, matching every prior page's
// analytics.ts convention (strategies/portfolio/risk).
import type { Signal } from '@/features/strategies/types'
import type { Execution, Order, OrderStatus } from './types'

export const num = (v: string | null) => (v == null ? 0 : Number.parseFloat(v))

export interface TradeRatio {
  wins: number
  losses: number
  winPct: number
  lossPct: number
  avgWin: number | null
  avgLoss: number | null
}

// "Win"/"loss" here means fill-level realized P&L sign (positive/negative),
// NOT strategy-level P&L — labeled explicitly in the UI per the task's data
// honesty note. Fills with realized_pnl exactly 0 (pure opens/adds — no
// existing position closed) carry no win/loss verdict and are excluded from
// both the ratio and the averages, same as how compute_direction treats an
// exact-zero conviction as its own FLAT case rather than forcing a sign.
export function computeTradeRatio(executions: Execution[]): TradeRatio {
  const wins = executions.filter((e) => num(e.realized_pnl) > 0)
  const losses = executions.filter((e) => num(e.realized_pnl) < 0)
  const decided = wins.length + losses.length
  return {
    wins: wins.length,
    losses: losses.length,
    winPct: decided ? (wins.length / decided) * 100 : 0,
    lossPct: decided ? (losses.length / decided) * 100 : 0,
    avgWin: wins.length ? wins.reduce((s, e) => s + num(e.realized_pnl), 0) / wins.length : null,
    avgLoss: losses.length ? losses.reduce((s, e) => s + num(e.realized_pnl), 0) / losses.length : null,
  }
}

export interface StatusCount {
  status: OrderStatus
  count: number
}

// Only the FOUR statuses the S-5 lifecycle actually models
// (domain/execution/entities.py::OrderStatus) — never a fabricated PENDING
// or EXPIRED bucket. CREATED/VALIDATED are real intermediate states (an
// order mid-flight through the risk gate), shown as their own segments
// rather than merged into an invented "pending" label.
export function computeStatusDistribution(orders: Order[]): StatusCount[] {
  const order: OrderStatus[] = ['FILLED', 'VALIDATED', 'CREATED', 'REJECTED']
  return order
    .map((status) => ({ status, count: orders.filter((o) => o.status === status).length }))
    .filter((s) => s.count > 0)
}

// Fill notional in USDT = quantity * price — real, deterministic.
export function computeFillNotionals(executions: Execution[]): number[] {
  return executions.map((e) => num(e.quantity) * num(e.price))
}

export interface HourBucket {
  hour: number
  count: number
}

// UTC hour-of-day breakdown of order creation — real timestamps, no binning
// assumption beyond the 24 UTC hours themselves.
export function computeOrdersByHour(orders: Order[]): HourBucket[] {
  const buckets = Array.from({ length: 24 }, (_, hour) => ({ hour, count: 0 }))
  for (const o of orders) {
    const hour = new Date(o.created_at).getUTCHours()
    buckets[hour].count++
  }
  return buckets
}

export interface FunnelStage {
  label: string
  value: number
}

// Signal -> Order -> Fill lineage, real counts only. "Valid signals" is
// validation_status === 'VALID' (domain/strategy_engine/validation.py);
// "Orders created"/"Orders filled" come straight off the strategy-scoped
// order list. Drop-off % between adjacent stages is computed by the caller
// (needs the funnel shape, not buried in this data structure).
export function computeSignalFunnel(signals: Signal[], orders: Order[]): FunnelStage[] {
  const validSignals = signals.filter((s) => s.validation_status === 'VALID')
  const filledOrders = orders.filter((o) => o.status === 'FILLED')
  return [
    { label: 'Signals generated', value: signals.length },
    { label: 'Valid signals', value: validSignals.length },
    { label: 'Orders created', value: orders.length },
    { label: 'Orders filled', value: filledOrders.length },
  ]
}

export interface CumulativePnlPoint {
  ts: string
  cumulative: number
}

// Running sum of fill-level realized P&L, oldest-first — the only P&L
// series this platform can honestly plot per-fill (F-21: backtests are
// aggregate-only, no per-fill breakdown; this is the live-execution
// equivalent, now that realized_pnl is persisted per fill).
export function computeCumulativePnl(executions: Execution[]): CumulativePnlPoint[] {
  const sorted = [...executions].sort((a, b) => new Date(a.executed_at).getTime() - new Date(b.executed_at).getTime())
  let running = 0
  return sorted.map((e) => {
    running += num(e.realized_pnl)
    return { ts: e.executed_at, cumulative: running }
  })
}

export interface StrategyPnlRow {
  strategyId: string
  strategyName: string
  pnl: number
}

// Realized P&L grouped by strategy — real, from orders' strategy_name
// (server-resolved) joined to their fill's realized_pnl by order_id.
export function computePnlByStrategy(orders: Order[]): StrategyPnlRow[] {
  const byStrategy = new Map<string, StrategyPnlRow>()
  for (const o of orders) {
    if (!o.strategy_id || o.realized_pnl == null) continue
    const existing = byStrategy.get(o.strategy_id)
    const pnl = num(o.realized_pnl)
    if (existing) existing.pnl += pnl
    else byStrategy.set(o.strategy_id, { strategyId: o.strategy_id, strategyName: o.strategy_name ?? o.strategy_id, pnl })
  }
  return Array.from(byStrategy.values()).sort((a, b) => b.pnl - a.pnl)
}
