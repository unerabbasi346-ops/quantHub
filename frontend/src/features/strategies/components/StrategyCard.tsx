// Governing specification: Doc 03 §Strategy Cards ("miniature research reports":
//   Status, mini equity curve, Signal Count, Current Alpha Score, Current Asset,
//   Last Signal + the risk metrics), Doc 04 §Strategy Performance Card.
// Doc 00 §14.5/§14.7 — DATA HONESTY: every number real; a metric with no
//   completed backtest to compute it from shows a plain dash, never a
//   fabricated value. Per Doc 00 §14.11
//
// One glowing card per registered strategy. Clicking it opens /strategies/[id].
// The card packs the Doc 03 field set that REAL data supports (signals-derived:
// count, current Alpha Score, asset, last signal) plus the backtest-computed
// risk metrics (drawdown / win rate / Sharpe) from the strategy's most recent
// completed backtest.
//
// FLIP (UI wiring step, owner request): the circle icon at the top flips the
// card to a back face showing a real portfolio donut — allocation across
// every DISTINCT symbol this strategy has backtested, weighted by each
// backtest's final_capital. Real per-backtest data (BacktestOut.symbol,
// promoted from config->>'symbol'), never fabricated; a strategy with no
// completed backtests shows an honest empty state on the back instead of a
// donut with nothing to plot.
'use client'

import { memo, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { ArrowUpRight, Brain, RotateCw } from 'lucide-react'
import { Badge, Card, DonutChart, Sparkline } from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { formatBacktestReturn, formatMaxDrawdownPct, formatSharpe, formatSignalStrength, formatTimestamp, formatWinRate } from '@/lib/utils/format'
import { useSyncStore } from '@/lib/store/sync'
import { useBacktests, useStrategyMetrics } from '../hooks/useStrategies'
import type { StrategyPerformance } from '../hooks/useStrategyPerformance'
import { isReferenceStrategy, REFERENCE_BADGE, REFERENCE_CAPTION, REFERENCE_TOOLTIP } from '../labels'

function returnPct(v: string | null): { text: string; tone: 'profit' | 'risk' | 'muted' } {
  if (v === null) return { text: '—', tone: 'muted' }
  const n = Number.parseFloat(v)
  return { text: formatBacktestReturn(n), tone: n >= 0 ? 'profit' : 'risk' }
}

function fmtSignalTime(iso: string): string {
  return formatTimestamp(iso)
}

// A real, computed metric cell.
function Metric({ label, value, tone = 'default' }: { label: string; value: string; tone?: 'default' | 'profit' | 'risk' }) {
  return (
    <div className="flex flex-col gap-1 min-w-0">
      <span className="truncate text-[11px] uppercase tracking-wide text-fg-subtle">{label}</span>
      <span
        className={cn(
          'truncate font-mono text-sm font-semibold tabular-nums',
          tone === 'profit' ? 'text-profit' : tone === 'risk' ? 'text-risk' : 'text-fg',
        )}
      >
        {value}
      </span>
    </div>
  )
}

export const StrategyCard = memo(function StrategyCard({ perf }: { perf: StrategyPerformance }) {
  const { strategy, signals, sparkline, latestReturn, hasBacktest, loading } = perf
  const ret = returnPct(latestReturn)
  const reference = isReferenceStrategy(strategy.name)
  const metricsQuery = useStrategyMetrics(strategy.id)
  const metrics = metricsQuery.data
  const backtestsQuery = useBacktests(strategy.id)
  const [flipped, setFlipped] = useState(false)

  // Real, signals-derived fields (no fetch beyond what the card already has).
  const ordered = [...signals].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime())
  const last = ordered.at(-1)
  const alphaScore = last ? Number.parseFloat(last.value) : null
  const asset = typeof strategy.config?.symbol === 'string' ? (strategy.config.symbol as string) : null
  // Global Synchronization (Doc 11): opening a strategy from anywhere makes
  // it the default selection everywhere else (e.g. the /strategies list).
  const setSyncedStrategyId = useSyncStore((s) => s.setSelectedStrategyId)

  // Back face (owner request): slice per backtested asset, sized by TRADE
  // COUNT — the most actively backtested asset gets the largest slice. Label
  // carries symbol + trades + return%; all real analytics.backtests fields.
  const byAsset = new Map<string, { trades: number; ret: number | null }>()
  let totalTrades = 0
  for (const bt of backtestsQuery.data ?? []) {
    if (!bt.symbol || bt.trade_count == null || bt.trade_count === 0) continue
    const prev = byAsset.get(bt.symbol) ?? { trades: 0, ret: null }
    byAsset.set(bt.symbol, {
      trades: prev.trades + bt.trade_count,
      // Latest listed return for that symbol (rows come newest-first).
      ret: prev.ret ?? (bt.total_return != null ? Number.parseFloat(bt.total_return) : null),
    })
    totalTrades += bt.trade_count
  }
  const allocation = [...byAsset.entries()]
    .map(([symbol, d]) => ({
      name: `${symbol} · ${d.trades} trades${d.ret != null ? ` · ${formatBacktestReturn(d.ret)}` : ''}`,
      value: d.trades,
    }))
    .sort((a, b) => b.value - a.value)

  // Benchmark comparison (Rule 5): the latest backtest's own strategy return
  // vs BTC/USDT buy-and-hold over the same window — both real, both from the
  // same backtest row, never fabricated when either is absent.
  const latestBacktest = backtestsQuery.data?.[0]
  const benchmarkReturn = latestBacktest?.benchmark_return != null ? Number.parseFloat(latestBacktest.benchmark_return) : null
  const strategyReturn = latestBacktest?.total_return != null ? Number.parseFloat(latestBacktest.total_return) : null
  const beatsBenchmark = strategyReturn != null && benchmarkReturn != null ? strategyReturn > benchmarkReturn : null

  return (
    <Card elevation="elevated" interactive className="group relative h-full" style={{ perspective: '1600px' }}>
      <button
        type="button"
        aria-label={flipped ? 'Show strategy summary' : 'Show asset allocation'}
        title={flipped ? 'Show strategy summary' : 'Show asset allocation'}
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          setFlipped((f) => !f)
        }}
        className="absolute right-3 top-3 z-10 flex h-7 w-7 items-center justify-center rounded-full border border-border bg-surface/80 text-fg-subtle backdrop-blur transition-colors hover:border-accent/50 hover:text-accent"
      >
        <RotateCw size={13} />
      </button>

      <motion.div
        className="relative h-full w-full"
        style={{ transformStyle: 'preserve-3d' }}
        animate={{ rotateY: flipped ? 180 : 0 }}
        transition={{ duration: 0.45, ease: 'easeInOut' }}
      >
        {/* Front */}
        <div style={{ backfaceVisibility: 'hidden' }}>
          <Link
            href={`/strategies/${strategy.id}`}
            className="flex h-full flex-col gap-4 p-5"
            aria-label={`Open ${strategy.name} detail`}
            onClick={() => setSyncedStrategyId(strategy.id)}
          >
            {/* Header: name + status/reference badges */}
            <div className="flex items-start justify-between gap-3 pr-8">
              <div className="flex min-w-0 items-start gap-2.5">
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
                  <Brain size={16} />
                </span>
                <div className="min-w-0">
                  <h3 className="truncate text-sm font-semibold tracking-tight text-fg">{strategy.name}</h3>
                  <p className="mt-0.5 truncate text-[11px] text-fg-subtle">
                    {reference ? REFERENCE_CAPTION : <>v{strategy.version}</>}
                  </p>
                </div>
              </div>
              <ArrowUpRight size={16} className="shrink-0 text-fg-subtle transition-colors group-hover:text-accent" />
            </div>

            {/* Status row */}
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge variant={strategy.status.toUpperCase() === 'ACTIVE' ? 'profit' : 'neutral'}>{strategy.status}</Badge>
              {reference && (
                <Badge variant="warning" title={REFERENCE_TOOLTIP}>
                  {REFERENCE_BADGE}
                </Badge>
              )}
            </div>

            {/* Return + mini Alpha Score curve */}
            <div className="flex items-end justify-between gap-3">
              <div className="min-w-0">
                <div className="text-[11px] uppercase tracking-wide text-fg-subtle">Return (backtest)</div>
                <div
                  className={cn(
                    'mt-0.5 font-mono text-metric font-bold tabular-nums',
                    ret.tone === 'profit' ? 'text-profit' : ret.tone === 'risk' ? 'text-risk' : 'text-fg-muted',
                  )}
                >
                  {ret.text}
                </div>
                <div className="text-[11px] text-fg-subtle">{hasBacktest ? 'latest backtest total return' : 'no backtest run yet'}</div>
                {benchmarkReturn != null && (
                  <div className={cn('mt-1 text-[11px]', beatsBenchmark ? 'text-profit' : 'text-fg-subtle')}>
                    vs BTC {formatBacktestReturn(benchmarkReturn)} {beatsBenchmark ? '· beats benchmark' : ''}
                  </div>
                )}
              </div>
              <div className="shrink-0">
                {loading ? (
                  <div className="skeleton h-8 w-24" />
                ) : sparkline.length > 1 ? (
                  <Sparkline data={sparkline} tone="info" width={104} height={34} />
                ) : (
                  <div className="flex h-[34px] w-[104px] items-center justify-center text-[11px] text-fg-subtle">no signals</div>
                )}
              </div>
            </div>

            {/* Real, signals-derived metrics (Doc 03 field set that data supports) */}
            <div className="grid grid-cols-3 gap-3 border-t border-border/60 pt-3">
              <Metric label="Signals" value={String(signals.length)} />
              <Metric
                label="Alpha Score"
                value={alphaScore != null ? formatSignalStrength(alphaScore) : '—'}
                tone={alphaScore == null ? 'default' : alphaScore >= 0 ? 'profit' : 'risk'}
              />
              <Metric label="Asset" value={asset ?? '—'} />
            </div>

            {/* Backtest-computed risk metrics — real numbers where a completed
                backtest has them, an honest dash otherwise. */}
            <div className="mt-auto grid grid-cols-3 gap-3">
              <Metric
                label="Max drawdown"
                value={metrics?.max_drawdown_pct != null ? formatMaxDrawdownPct(Number.parseFloat(metrics.max_drawdown_pct)) : '—'}
                tone={metrics?.max_drawdown_pct != null ? 'risk' : 'default'}
              />
              <Metric label="Win rate" value={metrics?.win_rate != null ? formatWinRate(Number.parseFloat(metrics.win_rate)) : '—'} />
              <Metric label="Sharpe" value={metrics?.sharpe_ratio != null ? formatSharpe(Number.parseFloat(metrics.sharpe_ratio)) : '—'} />
            </div>

            {/* Last signal footer */}
            <div className="text-[11px] text-fg-subtle">
              {last ? <>Last signal · {fmtSignalTime(last.ts)}</> : 'No signals recorded yet'}
            </div>
          </Link>
        </div>

        {/* Back — asset allocation across this strategy's backtests */}
        <div
          className="absolute inset-0 flex flex-col gap-3 p-5"
          style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}
        >
          <div className="flex items-center gap-2.5 pr-8">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
              <Brain size={16} />
            </span>
            <div className="min-w-0">
              <h3 className="truncate text-sm font-semibold tracking-tight text-fg">{strategy.name}</h3>
              <p className="mt-0.5 truncate text-[11px] text-fg-subtle">Backtest activity by asset (trade count)</p>
            </div>
          </div>
          <div className="flex flex-1 items-center justify-center">
            {backtestsQuery.isLoading ? (
              <div className="skeleton h-32 w-32 rounded-full" />
            ) : allocation.length > 0 ? (
              <DonutChart
                data={allocation}
                height={180}
                centerValue={String(allocation.length)}
                centerLabel={`asset${allocation.length === 1 ? '' : 's'} · ${totalTrades.toLocaleString()} trades`}
                valueFormat={(v) => `${v.toLocaleString()} trades`}
              />
            ) : (
              <p className="text-center text-[11px] text-fg-subtle">No completed backtests with a recorded asset yet.</p>
            )}
          </div>
        </div>
      </motion.div>
    </Card>
  )
})
