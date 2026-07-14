// Governing specification: Doc 00 §14.5/§14.7 — DATA HONESTY. Every figure
// here is a deterministic transform of real Position/OpenInterest/OHLCVBar
// data — no synthetic risk scores, no fabricated exposure. Pure helpers kept
// out of the component files so the math is independently readable/testable.
import type { Position } from '@/features/portfolio/types'
import type { OHLCVBar, OpenInterest } from '@/features/markets/types'

export const num = (v: string) => Number.parseFloat(v)

export interface ExposureSplit {
  long: number
  short: number
  gross: number
}

// Long side = sum of market_value where signed quantity >= 0; short side =
// sum of |market_value| where quantity < 0 (S-10: quantity is signed).
export function computeExposureSplit(positions: Position[]): ExposureSplit {
  const open = positions.filter((p) => !p.is_closed)
  let long = 0
  let short = 0
  for (const p of open) {
    const qty = num(p.quantity)
    const mv = Math.abs(num(p.market_value))
    if (qty >= 0) long += mv
    else short += mv
  }
  return { long, short, gross: long + short }
}

export interface MarginUtilization {
  marginUsed: number
  configuredCapital: number
  utilizationPct: number
}

// Real sum of position-level margin_used (S-10, PERPETUAL-only field) vs
// configured capital. Null when capital was never configured (F-19) or no
// position carries a margin_used figure (all-spot book).
export function computeMarginUtilization(positions: Position[], configuredCapital: string | null): MarginUtilization | null {
  const capital = configuredCapital != null ? num(configuredCapital) : null
  if (capital == null || !(capital > 0)) return null
  const marginUsed = positions.filter((p) => !p.is_closed).reduce((s, p) => s + (p.margin_used ? num(p.margin_used) : 0), 0)
  return { marginUsed, configuredCapital: capital, utilizationPct: (marginUsed / capital) * 100 }
}

export interface ConcentrationRow {
  assetId: string
  symbol: string
  value: number
  pctOfPortfolio: number
}

// Each open position's share of total open-position value — real, computed,
// sorted descending (highest concentration first, per task spec).
export function computeConcentration(positions: Position[]): ConcentrationRow[] {
  const open = positions.filter((p) => !p.is_closed)
  const total = open.reduce((s, p) => s + Math.abs(num(p.market_value)), 0)
  if (total === 0) return []
  return open
    .map((p) => {
      const value = Math.abs(num(p.market_value))
      return {
        assetId: p.asset_id,
        symbol: p.symbol ?? p.asset_id,
        value,
        pctOfPortfolio: (value / total) * 100,
      }
    })
    .sort((a, b) => b.pctOfPortfolio - a.pctOfPortfolio)
}

export interface LeverageRow {
  assetId: string
  symbol: string
  leverage: number
}

// Real leverage per open position — 1.0x for SPOT (honest default, no
// margin concept), the real stored figure for PERPETUAL.
export function computeLeverageRows(positions: Position[]): LeverageRow[] {
  return positions
    .filter((p) => !p.is_closed)
    .map((p) => ({
      assetId: p.asset_id,
      symbol: p.symbol ?? p.asset_id,
      leverage: p.instrument_type === 'PERPETUAL' && p.leverage ? num(p.leverage) : 1.0,
    }))
}

export interface DivergencePoint {
  ts: string
  oi: number
  signal: 'bullish' | 'bearish'
}

// Bars are 1h-interval; a "nearest at-or-before" match more than this stale
// is treated as NO price data for that timestamp, never silently reused —
// without this, a real gap between the two series (observed live: BTC spot
// bars end Jul 8, BTC perp OI starts Jul 12 — a 4-day non-overlap) would
// compare every OI point against the same frozen last-known price, which
// reads as "price never moved" and would fabricate a flat comparison rather
// than honestly reporting "no overlapping data here".
const MAX_PRICE_STALENESS_MS = 3 * 60 * 60 * 1000 // 3 bar-widths

// Real OI-vs-price divergence tagging: for each pair of consecutive OI
// observations, find the nearest bar at-or-before each OI timestamp (within
// tolerance) and compare price direction over the same window. Task's
// literal two cases: OI rising + price rising -> bullish confirmation; OI
// rising + price falling -> bearish confirmation. OI-falling periods are
// left untagged (the task only defines these two signals) — never invents a
// third label.
export function computeOiDivergence(oiRows: OpenInterest[], bars: OHLCVBar[]): DivergencePoint[] {
  if (oiRows.length < 2 || bars.length < 2) return []
  const sortedBars = [...bars].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime())

  const priceAt = (ts: string): number | null => {
    const t = new Date(ts).getTime()
    let candidate: OHLCVBar | null = null
    for (const b of sortedBars) {
      if (new Date(b.ts).getTime() <= t) candidate = b
      else break
    }
    if (!candidate) return null
    if (t - new Date(candidate.ts).getTime() > MAX_PRICE_STALENESS_MS) return null
    return num(candidate.close)
  }

  const points: DivergencePoint[] = []
  for (let i = 1; i < oiRows.length; i++) {
    const prevOi = num(oiRows[i - 1].open_interest_usdt)
    const curOi = num(oiRows[i].open_interest_usdt)
    if (curOi <= prevOi) continue // only OI-rising periods carry a defined signal

    const prevPrice = priceAt(oiRows[i - 1].ts)
    const curPrice = priceAt(oiRows[i].ts)
    if (prevPrice == null || curPrice == null) continue

    if (curPrice > prevPrice) {
      points.push({ ts: oiRows[i].ts, oi: curOi, signal: 'bullish' })
    } else if (curPrice < prevPrice) {
      points.push({ ts: oiRows[i].ts, oi: curOi, signal: 'bearish' })
    }
  }
  return points
}
