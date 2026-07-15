// Shared human-readable metric formatting — single source of truth for every
// page (Strategy/Portfolio/Execution/Risk/Markets/Dashboard) so the same
// value never renders two different ways depending on which component
// touched it last.

function suffixify(abs: number, decimals: number): string {
  if (abs >= 1_000_000_000) return `${trimTrailingZero((abs / 1_000_000_000).toFixed(decimals))}B`
  if (abs >= 1_000_000) return `${trimTrailingZero((abs / 1_000_000).toFixed(decimals))}M`
  if (abs >= 1_000) return `${trimTrailingZero((abs / 1_000).toFixed(decimals))}K`
  return abs.toFixed(2)
}

function trimTrailingZero(s: string): string {
  return s.replace(/\.0+$/, '')
}

// Return/P&L percentages. Input is the raw fraction (e.g. 0.00016131 for a
// 0.016131% return). Sub-0.1% moves are easier to read in basis points than
// as "0.02%", so they get the bps treatment; everything else is a plain %.
export function formatReturn(value: number): string {
  if (!Number.isFinite(value)) return '—'
  const pct = value * 100
  const sign = value > 0 ? '+' : value < 0 ? '-' : ''
  if (Math.abs(pct) < 0.1) {
    const bps = Math.abs(value * 10000)
    return `${sign}${bps.toFixed(2)} bps`
  }
  return `${sign}${Math.abs(pct).toFixed(2)}%`
}

// Sharpe/Sortino/Calmar-style ratios — always 2dp, with a "~0.00" tell for
// values too close to zero for 2dp to distinguish from noise.
export function formatRatio(value: number): string {
  if (!Number.isFinite(value)) return '—'
  if (Math.abs(value) < 0.01) return '~0.00'
  return value.toFixed(2)
}

// analytics.backtest_computed_metrics fields — win_rate/profit_factor are
// 0-1 fractions (need *100); max_drawdown_pct is already stored in percent
// units, so it must NOT be multiplied again.
export function formatWinRate(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

export function formatSharpe(value: number): string {
  return value.toFixed(2)
}

export function formatMaxDrawdownPct(value: number): string {
  return `-${Math.abs(value).toFixed(2)}%`
}

// Capital/P&L dollar amounts — K/M/B suffix above $1,000, plain 2dp below,
// "$0.00" for anything that rounds to zero.
export function formatCapital(value: number): string {
  if (!Number.isFinite(value)) return '—'
  const sign = value < 0 ? '-' : ''
  const abs = Math.abs(value)
  if (abs < 1000) return `${sign}$${abs.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  return `${sign}$${suffixify(abs, 1)}`
}

// Signal ("conviction") strength — a -1..1 value shown as a signed
// percentage of max: -0.04247 -> "-4.2%".
export function formatSignalStrength(value: number): string {
  if (!Number.isFinite(value)) return '—'
  const pct = value * 100
  const sign = value > 0 ? '+' : value < 0 ? '-' : ''
  return `${sign}${Math.abs(pct).toFixed(1)}%`
}

// Relative for anything under a day old (matches the platform's existing
// "2h ago" convention), calendar date beyond that, year added past a week.
export function formatTimestamp(ts: string | Date): string {
  const date = typeof ts === 'string' ? new Date(ts) : ts
  const diffMs = Date.now() - date.getTime()
  const diffMin = diffMs / 60_000
  const diffHr = diffMin / 60
  const diffDay = diffHr / 24

  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${Math.floor(diffMin)}m ago`
  if (diffHr < 24) return `${Math.floor(diffHr)}h ago`
  if (diffDay < 7) return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

// Funding rates — same sub-0.1% bps/% split as formatReturn, but unsigned
// magnitude labels ("1 bp" / "0.01%") since funding is read as a rate, not
// a directional P&L move.
export function formatRate(value: number): string {
  if (!Number.isFinite(value)) return '—'
  const pct = value * 100
  const sign = value > 0 ? '+' : value < 0 ? '-' : ''
  if (Math.abs(pct) < 0.1) {
    const bps = Math.abs(value * 10000)
    const rounded = Number(bps.toFixed(2))
    return `${sign}${rounded} ${rounded === 1 ? 'bp' : 'bps'}`
  }
  return `${sign}${Math.abs(pct).toFixed(2)}%`
}

// Open interest — always a K/M/B-suffixed dollar figure (OI values are
// never small enough for the plain-$ branch to matter, but it's kept for
// safety), 2dp precision to match Doc 06's OI monitor.
export function formatOI(value: number): string {
  if (!Number.isFinite(value)) return '—'
  const sign = value < 0 ? '-' : ''
  const abs = Math.abs(value)
  if (abs < 1000) return `${sign}$${abs.toFixed(2)}`
  return `${sign}$${suffixify(abs, 2)}`
}

// Annualized volatility — raw decimal (0.8234) to a 1dp percentage.
export function formatVolatility(value: number): string {
  if (!Number.isFinite(value)) return '—'
  return `${(value * 100).toFixed(1)}%`
}

// Trade/signal/order counts — comma-separated integers.
export function formatCount(value: number): string {
  if (!Number.isFinite(value)) return '—'
  return Math.trunc(value).toLocaleString()
}
