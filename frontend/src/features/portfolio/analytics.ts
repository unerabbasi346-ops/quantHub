// Governing specification: Doc 00 §14.5/§14.7 — DATA HONESTY. Every figure
// here is a deterministic transform of real Position/Signal data — no
// synthetic P&L, no fabricated NAV. Pure helpers kept out of the component
// files so the math is independently readable/testable.
import type { Position } from './types'

export const num = (v: string) => Number.parseFloat(v)

export interface CapitalUtilization {
  deployed: number
  configured: number
  utilizationPct: number
  idle: number
}

// Deployed = sum of |market_value| across OPEN positions (a short's capital
// footprint counts too). Null when no capital has ever been configured for
// this portfolio (F-19: never divide against a fabricated denominator).
export function computeCapitalUtilization(positions: Position[], configuredCapital: string | null): CapitalUtilization | null {
  const capital = configuredCapital != null ? num(configuredCapital) : null
  if (capital == null || !(capital > 0)) return null
  const deployed = positions.filter((p) => !p.is_closed).reduce((s, p) => s + Math.abs(num(p.market_value)), 0)
  return {
    deployed,
    configured: capital,
    utilizationPct: (deployed / capital) * 100,
    idle: Math.max(capital - deployed, 0),
  }
}

// Task-specified thresholds: green <80%, amber 80-95%, red >95%.
export function utilizationTone(pct: number): 'profit' | 'warning' | 'risk' {
  if (pct > 95) return 'risk'
  if (pct >= 80) return 'warning'
  return 'profit'
}

export interface LongShortCounts {
  long: number
  short: number
  flat: number
}

// Real signal-sign split — NOT a fill/trade-direction split (no per-trade
// fill data exists at the backtest level, F-21).
export function longShortSplit(signalValues: number[]): LongShortCounts {
  let long = 0
  let short = 0
  let flat = 0
  for (const v of signalValues) {
    if (v > 0) long++
    else if (v < 0) short++
    else flat++
  }
  return { long, short, flat }
}
