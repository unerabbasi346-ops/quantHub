// Canonical top-20 liquid USDT pairs — the ONLY assets the research
// backtester and strategy backtest surfaces offer. Display is the clean
// symbol ("BTC/USDT"), in this exact order. A clean symbol may resolve to a
// SPOT or PERPETUAL DB asset (whichever actually carries usable bars);
// resolveTop20 handles that so the label stays clean while the backtest runs
// against real data.
//
// REBUILT from what's actually ingested (owner request) — the prior list
// named 7 tickers (DOT, MATIC, UNI, LTC, BCH, OP, ARB) that didn't exist in
// market_data.assets, so they always rendered greyed-out. This list is the
// real top-20 by bar count in market_data.ohlcv_bars (a liquidity/history
// proxy — more bars means the asset has been tracked longer/more
// consistently), so every entry is actually backtestable today:
//   LTC 57292 · ZEC 56463 · UNI 51221 · NEAR 50393 · BTC 43100 · DOT 38377 ·
//   PEPE(1000PEPE) 28017 · WLD 26101 · DODOX 25741 · ONDO 21781 · POL 16271
//   (MATIC's Binance successor — MATIC itself is delisted/inactive) ·
//   DEXE 13647 · BCH 13000 · HYPE 9877 · PUMP 8898 · AKE 7019 · EVAA 6855 ·
//   US 5176 · LAB 1202 · ADA 1007.
export const TOP_20_SYMBOLS: readonly string[] = [
  'LTC/USDT', 'ZEC/USDT', 'UNI/USDT', 'NEAR/USDT', 'BTC/USDT',
  'DOT/USDT', 'PEPE/USDT', 'WLD/USDT', 'DODOX/USDT', 'ONDO/USDT',
  'POL/USDT', 'DEXE/USDT', 'BCH/USDT', 'HYPE/USDT', 'PUMP/USDT',
  'AKE/USDT', 'EVAA/USDT', 'US/USDT', 'LAB/USDT', 'ADA/USDT',
]

// A few clean names live under a different DB symbol (Binance lists the perp
// with a leading multiplier). Map clean -> the base the DB actually stores.
const DB_ALIASES: Record<string, string> = {
  'PEPE/USDT': '1000PEPE/USDT',
}

// Minimum bars for an asset to be considered backtestable (not a sparse
// daily-only stub). ~6 weeks of 1h data.
export const TOP20_MIN_BARS = 1000

export interface Top20Resolved {
  /** Clean display symbol, e.g. "BTC/USDT". */
  clean: string
  /** The real DB asset id to run against, or null when unavailable. */
  assetId: string | null
  /** The real DB symbol chosen (spot or perp variant). */
  dbSymbol: string | null
  bars: number
  available: boolean
}

interface AssetLike { id: string; symbol: string }

/**
 * Resolve the canonical top-20 list against the DB asset universe + bar
 * counts. For each clean symbol, prefer the variant (spot base, or the
 * `<base>:USDT` perp) with the most bars; mark unavailable when nothing has
 * >= TOP20_MIN_BARS. Order is preserved exactly.
 */
export function resolveTop20(
  assets: AssetLike[],
  barCount: (symbol: string) => number,
): Top20Resolved[] {
  const bySymbol = new Map(assets.map((a) => [a.symbol, a]))
  return TOP_20_SYMBOLS.map((clean) => {
    const base = DB_ALIASES[clean] ?? clean
    const candidates = [base, `${base}:USDT`]
      .map((sym) => {
        const a = bySymbol.get(sym)
        return a ? { id: a.id, symbol: sym, bars: barCount(sym) } : null
      })
      .filter((c): c is { id: string; symbol: string; bars: number } => c != null)
    const best = candidates.sort((x, y) => y.bars - x.bars)[0] ?? null
    const available = best != null && best.bars >= TOP20_MIN_BARS
    return {
      clean,
      assetId: available ? best!.id : null,
      dbSymbol: available ? best!.symbol : null,
      bars: best?.bars ?? 0,
      available,
    }
  })
}
