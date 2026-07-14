// Governing specification: Doc 00 §14.5/§14.7 — DATA HONESTY. Every figure
// here is a deterministic transform of real ingested OHLCV bars — no
// fabricated prices, no synthetic history. Pure helpers kept out of the
// component files so the math is independently readable, shared by the
// Markets page's stats strip, volume/performance rankings, and price
// statistics panel.
import type { OHLCVBar } from './types'

export const num = (v: string) => Number.parseFloat(v)

export interface DayChange {
  last: number
  change: number
  changePct: number
  high: number
  low: number
  volume: number
}

// Last-24-bar (1h interval) window — an honest "24h" proxy: exactly the most
// recent 24 ingested hourly bars, not a calendar-day boundary.
export function computeDayChange(bars: OHLCVBar[]): DayChange | null {
  if (bars.length < 2) return null
  const window = bars.slice(-24)
  const last = num(bars.at(-1)!.close)
  const first = num(window[0].open)
  const change = last - first
  return {
    last,
    change,
    changePct: first !== 0 ? (change / first) * 100 : 0,
    high: Math.max(...window.map((b) => num(b.high))),
    low: Math.min(...window.map((b) => num(b.low))),
    volume: window.reduce((s, b) => s + num(b.volume), 0),
  }
}

export interface RankedAsset {
  assetId: string
  symbol: string
  value: number
}

// Descending by latest bar volume — real per-asset volume, no fabrication.
export function rankByVolume(entries: { assetId: string; symbol: string; bars: OHLCVBar[] }[]): RankedAsset[] {
  return entries
    .filter((e) => e.bars.length > 0)
    .map((e) => ({ assetId: e.assetId, symbol: e.symbol, value: num(e.bars.at(-1)!.volume) }))
    .sort((a, b) => b.value - a.value)
}

// Sorted by 24h return magnitude (biggest movers first, sign preserved).
export function rankByPerformance(entries: { assetId: string; symbol: string; bars: OHLCVBar[] }[]): RankedAsset[] {
  return entries
    .map((e) => {
      const dc = computeDayChange(e.bars)
      return dc ? { assetId: e.assetId, symbol: e.symbol, value: dc.changePct } : null
    })
    .filter((r): r is RankedAsset => r !== null)
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
}

export interface PriceStats {
  range7d: { high: number; low: number } | null
  return30d: number | null
  avgVolume7d: number | null
  sma20: number | null
  momentumZScore: number | null
  volatilityAnnualizedPct: number | null
}

export type MomentumZone = 'oversold' | 'neutral' | 'overbought'

export function momentumZone(z: number): MomentumZone {
  if (z < -1.5) return 'oversold'
  if (z > 1.5) return 'overbought'
  return 'neutral'
}

// All computed client-side from already-fetched bars — no new endpoints.
// `bars` must be 1h-interval, oldest -> newest, for the "Nd" windows below to
// mean what their label says (N*24 bars).
export function computePriceStats(bars: OHLCVBar[]): PriceStats {
  if (bars.length === 0) {
    return { range7d: null, return30d: null, avgVolume7d: null, sma20: null, momentumZScore: null, volatilityAnnualizedPct: null }
  }

  const last7d = bars.slice(-7 * 24)
  const range7d = last7d.length
    ? { high: Math.max(...last7d.map((b) => num(b.high))), low: Math.min(...last7d.map((b) => num(b.low))) }
    : null
  const avgVolume7d = last7d.length ? last7d.reduce((s, b) => s + num(b.volume), 0) / last7d.length : null

  const window30d = bars.slice(-30 * 24)
  const return30d =
    window30d.length >= 2 ? ((num(bars.at(-1)!.close) - num(window30d[0].open)) / num(window30d[0].open)) * 100 : null

  const last20 = bars.slice(-20)
  const sma20 = last20.length === 20 ? last20.reduce((s, b) => s + num(b.close), 0) / 20 : null
  const currentPrice = num(bars.at(-1)!.close)

  // Momentum z-score: (price - SMA20) / stdev(last 20 closes) — a
  // volatility-normalized distance from the mean, not a raw % deviation.
  // Oversold (<-1.5) / Neutral / Overbought (>1.5) thresholds per Doc 14
  // §10.9's momentum-indicator convention.
  let momentumZScore: number | null = null
  if (sma20 != null && last20.length === 20) {
    const closes = last20.map((b) => num(b.close))
    const variance = closes.reduce((s, c) => s + (c - sma20) ** 2, 0) / closes.length
    const stdDev = Math.sqrt(variance)
    momentumZScore = stdDev !== 0 ? (currentPrice - sma20) / stdDev : null
  }

  // Volatility: stdev of the last 20 simple bar-over-bar returns, annualized
  // by sqrt(8760) (hours/year) — honest for 1h-interval input; labeled
  // "annualized" in the UI with that basis stated, not a fabricated figure.
  let volatilityAnnualizedPct: number | null = null
  if (last20.length === 20) {
    const returns: number[] = []
    for (let i = 1; i < last20.length; i++) {
      const prevClose = num(last20[i - 1].close)
      if (prevClose !== 0) returns.push((num(last20[i].close) - prevClose) / prevClose)
    }
    if (returns.length >= 2) {
      const mean = returns.reduce((a, b) => a + b, 0) / returns.length
      const variance = returns.reduce((s, r) => s + (r - mean) ** 2, 0) / (returns.length - 1)
      volatilityAnnualizedPct = Math.sqrt(variance) * Math.sqrt(8760) * 100
    }
  }

  return { range7d, return30d, avgVolume7d, sma20, momentumZScore, volatilityAnnualizedPct }
}

// Merge a live-polled bar into an oldest->newest bar series: replaces the
// last bar in place if it shares the same ts (the current, still-forming bar
// got a fresher close/volume), appends if it's a genuinely new period, and is
// a no-op if the live poll returned something stale (race with the next
// regular bars refetch). Never fabricates a gap-filling bar in between.
export function mergeLatestBar(bars: OHLCVBar[], latest: OHLCVBar | null): OHLCVBar[] {
  if (!latest) return bars
  if (bars.length === 0) return [latest]
  const lastTs = Date.parse(bars[bars.length - 1].ts)
  const latestTs = Date.parse(latest.ts)
  if (latestTs === lastTs) return [...bars.slice(0, -1), latest]
  if (latestTs > lastTs) return [...bars, latest]
  return bars
}

// Compact volume formatter: 1.2B / 450M / 12.3K / 980.
export function fmtCompactVolume(v: number): string {
  const abs = Math.abs(v)
  if (abs >= 1e9) return `${(v / 1e9).toFixed(1)}B`
  if (abs >= 1e6) return `${(v / 1e6).toFixed(1)}M`
  if (abs >= 1e3) return `${(v / 1e3).toFixed(1)}K`
  return v.toFixed(0)
}
