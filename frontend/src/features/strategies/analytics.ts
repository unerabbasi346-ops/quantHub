// Governing specification: Doc 00 §14.5/§14.7 — DATA HONESTY. Every figure
// here is a deterministic transform of REAL signal data (core.signals) — no
// synthetic P&L, no fabricated equity. These are the shared derivations used
// by the Strategy detail workspace's monthly heatmap, timeline scatter and
// consecutive-run chart, kept out of the component file so the math is
// independently readable/testable.
import type { Signal } from './types'

const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export interface MonthlyConvictionGrid {
  years: string[]
  months: string[]
  /** grid[yearIndex][monthIndex] = mean signal value for that month, or null if no signals fired. */
  grid: (number | null)[][]
  /** Largest absolute mean across all populated cells — for symmetric color scaling. */
  maxAbs: number
}

// Groups signals by (year, month) and averages their signed `value` — an
// honest proxy for "how this strategy leaned that month", not a real monthly
// return (the platform doesn't track per-step equity yet, see F-21).
export function monthlyConvictionGrid(signals: Signal[]): MonthlyConvictionGrid {
  if (signals.length === 0) return { years: [], months: MONTH_LABELS, grid: [], maxAbs: 0 }

  const buckets = new Map<string, number[]>() // "YYYY-M" -> values
  let minYear = Infinity
  let maxYear = -Infinity
  for (const s of signals) {
    const d = new Date(s.ts)
    const y = d.getFullYear()
    const m = d.getMonth()
    minYear = Math.min(minYear, y)
    maxYear = Math.max(maxYear, y)
    const key = `${y}-${m}`
    const arr = buckets.get(key) ?? []
    arr.push(Number.parseFloat(s.value))
    buckets.set(key, arr)
  }

  const years: string[] = []
  for (let y = minYear; y <= maxYear; y++) years.push(String(y))

  let maxAbs = 0
  const grid: (number | null)[][] = years.map((yStr) => {
    const y = Number(yStr)
    return MONTH_LABELS.map((_, m) => {
      const arr = buckets.get(`${y}-${m}`)
      if (!arr || arr.length === 0) return null
      const mean = arr.reduce((a, b) => a + b, 0) / arr.length
      maxAbs = Math.max(maxAbs, Math.abs(mean))
      return mean
    })
  })

  return { years, months: MONTH_LABELS, grid, maxAbs: maxAbs || 1 }
}

export interface SignalPoint {
  ts: string
  value: number
}

export function signalPoints(signals: Signal[]): SignalPoint[] {
  return [...signals]
    .sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime())
    .map((s) => ({ ts: s.ts, value: Number.parseFloat(s.value) }))
}

export interface MLConfidencePoint {
  ts: string
  confidence: number
  strength: number
  agreement: boolean | null
}

// Only signals with a real ml_confidence (DEPLOYED XGBoost_MetaLabeler at
// signal-read time — api/v1/strategies.py's SignalOut) contribute a point;
// signals from before a model was deployed are silently excluded rather than
// plotted at a fabricated confidence of 0.
export function mlConfidencePoints(signals: Signal[]): MLConfidencePoint[] {
  return [...signals]
    .filter((s) => s.ml_confidence != null)
    .sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime())
    .map((s) => ({
      ts: s.ts,
      confidence: Number.parseFloat(s.ml_confidence!),
      strength: Math.abs(Number.parseFloat(s.value)),
      agreement: s.ml_direction_agreement,
    }))
}

export interface ConsecutiveRun {
  /** +1 for a run of positive (or zero) conviction, -1 for negative. */
  sign: 1 | -1
  /** Number of consecutive same-sign signals in the run. */
  length: number
  /** Timestamp of the run's first signal. */
  startTs: string
}

// Runs of consecutive same-direction signals, time-ordered — a real read on
// how "streaky" a strategy's conviction is, computed purely from the sign of
// each recorded signal (no trade attribution required).
export function consecutiveRuns(signals: Signal[]): ConsecutiveRun[] {
  const points = signalPoints(signals)
  const runs: ConsecutiveRun[] = []
  for (const p of points) {
    const sign: 1 | -1 = p.value >= 0 ? 1 : -1
    const last = runs.at(-1)
    if (last && last.sign === sign) {
      last.length += 1
    } else {
      runs.push({ sign, length: 1, startTs: p.ts })
    }
  }
  return runs
}
