// Multi-asset backtest view for the Strategy detail page (owner request):
// summary row + per-asset breakdown across EVERY asset this strategy has
// been backtested on, an expandable equity curve per asset, a simulated-
// capital input (localStorage, per strategy), a "run fresh backtests"
// control, and the real server-computed trade P&L distribution.
// Doc 00 §14.5/§14.7 DATA HONESTY: every figure is an engine-persisted
// backtest row / computed metric / execution aggregate — never derived here.
'use client'

import { useEffect, useMemo, useState } from 'react'
import { ChevronDown, ChevronUp, DollarSign, Play, Sigma } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import {
  Badge,
  Chart,
  CryptoIcon,
  EmptyState,
  LineChart,
  Panel,
  Section,
  StatCard,
} from '@/components/ui'
import { chartAxis, chartTooltip, type ChartTheme } from '@/components/ui/chart-theme'
import { cn } from '@/lib/utils/cn'
import { formatBacktestReturn, formatCapital, formatSharpe, formatTimestamp, formatWinRate } from '@/lib/utils/format'
import { researchService } from '@/features/research/services/research.service'
import { useEquityCurve, useRunBacktest } from '@/features/research/hooks/useResearch'
import { useTradePnlDistribution } from '../hooks/useStrategies'
import type { Strategy } from '../types'
import type { BacktestSummary } from '@/features/research/types'

// ── Simulated capital (one place, localStorage per strategy) ──────────────
const capitalKey = (strategyId: string) => `quanthub-sim-capital-${strategyId}`
export const DEFAULT_SIM_CAPITAL = 10_000

export function useSimCapital(strategyId: string): [number, (v: number) => void] {
  const [capital, setCapital] = useState(DEFAULT_SIM_CAPITAL)
  useEffect(() => {
    const raw = window.localStorage.getItem(capitalKey(strategyId))
    const n = raw != null ? Number.parseFloat(raw) : NaN
    setCapital(Number.isFinite(n) && n > 0 ? n : DEFAULT_SIM_CAPITAL)
  }, [strategyId])
  const set = (v: number) => {
    setCapital(v)
    window.localStorage.setItem(capitalKey(strategyId), String(v))
  }
  return [capital, set]
}

export function SimCapitalInput({ capital, onChange }: { capital: number; onChange: (v: number) => void }) {
  return (
    <label className="flex items-center gap-2 text-xs text-fg-muted">
      <DollarSign size={14} className="text-fg-subtle" />
      <span className="whitespace-nowrap">Simulated capital</span>
      <input
        type="number"
        suppressHydrationWarning
        min={100}
        step={1000}
        value={capital}
        onChange={(e) => {
          const n = Number.parseFloat(e.target.value)
          if (Number.isFinite(n) && n > 0) onChange(n)
        }}
        className="h-8 w-28 rounded-lg border border-border bg-surface px-2 font-mono text-sm text-fg outline-none focus:border-accent"
      />
      <span className="hidden text-[11px] text-fg-subtle sm:inline">affects sizing calculations · 2% = {formatCapital(capital * 0.02)}</span>
    </label>
  )
}

// Latest COMPLETED run per symbol — the strategy's current multi-asset view.
function latestPerAsset(rows: BacktestSummary[]): BacktestSummary[] {
  const bySymbol = new Map<string, BacktestSummary>()
  for (const r of rows) {
    if (r.status !== 'COMPLETED' || !r.symbol || r.total_return == null) continue
    const prev = bySymbol.get(r.symbol)
    if (!prev || new Date(r.created_at) > new Date(prev.created_at)) bySymbol.set(r.symbol, r)
  }
  return [...bySymbol.values()].sort(
    (a, b) => Number.parseFloat(b.total_return!) - Number.parseFloat(a.total_return!),
  )
}

const num = (v: string | null) => (v == null ? null : Number.parseFloat(v))

function ExpandedCurve({ backtestId }: { backtestId: string }) {
  const curveQuery = useEquityCurve(backtestId)
  const points = (curveQuery.data ?? []).map((p) => ({
    label: formatTimestamp(p.ts),
    value: Number.parseFloat(p.portfolio_value),
  }))
  if (curveQuery.isLoading) return <div className="skeleton h-[200px] w-full" />
  if (points.length < 2) return <EmptyState title="No equity curve" description="This run has no persisted equity curve." />
  return <LineChart data={points} height={200} valueFormat={(v) => formatCapital(v)} />
}

export function MultiAssetBacktestSection({ strategy, capital }: { strategy: Strategy; capital: number }) {
  const allQuery = useQuery({
    queryKey: ['all-backtests-strategy', strategy.id],
    queryFn: () => researchService.getBacktests(500),
  })
  const mine = useMemo(
    () => (allQuery.data ?? []).filter((b) => b.strategy_id === strategy.id),
    [allQuery.data, strategy.id],
  )
  const perAsset = useMemo(() => latestPerAsset(mine), [mine])
  const [expanded, setExpanded] = useState<string | null>(null)

  // Summary across the per-asset rows: trade-weighted average return, best/
  // worst asset — all from real engine rows.
  const totalTrades = perAsset.reduce((s, r) => s + (r.trade_count ?? 0), 0)
  const weightedReturn = totalTrades > 0
    ? perAsset.reduce((s, r) => s + Number.parseFloat(r.total_return!) * (r.trade_count ?? 0), 0) / totalTrades
    : null
  const best = perAsset[0] ?? null
  const worst = perAsset.at(-1) ?? null
  const sharpes = perAsset.map((r) => num(r.sharpe_ratio)).filter((v): v is number => v != null)
  const avgSharpe = sharpes.length ? sharpes.reduce((a, b) => a + b, 0) / sharpes.length : null

  // Fresh sweep: re-run every asset already backtested, with the current
  // simulated capital. Sequential fire-and-forget 202s; the list refetches.
  const runMutation = useRunBacktest()
  const [sweeping, setSweeping] = useState(false)
  const runFresh = async () => {
    setSweeping(true)
    try {
      for (const row of perAsset) {
        await runMutation.mutateAsync({
          strategy_id: strategy.id,
          symbol: row.symbol!,
          start: `${row.start_date ?? '2026-01-01'}T00:00:00Z`.slice(0, 20) + 'Z',
          end: `${row.end_date ?? '2026-07-01'}T00:00:00Z`.slice(0, 20) + 'Z',
          initial_capital: String(capital),
        })
      }
    } finally {
      setSweeping(false)
    }
  }

  return (
    <Section
      icon={<Sigma size={16} />}
      title="Backtests across all assets"
      description={`Latest completed run per asset this strategy has been tested on — sizing display assumes ${formatCapital(capital)} simulated capital.`}
      actions={
        perAsset.length > 0 ? (
          <button
            type="button"
            suppressHydrationWarning
            onClick={runFresh}
            disabled={sweeping}
            className="flex items-center gap-1.5 rounded-lg border border-border bg-surface-raised/60 px-3 py-1.5 text-xs font-medium text-fg transition-colors hover:border-border-strong disabled:opacity-50"
          >
            <Play size={12} /> {sweeping ? 'Starting runs…' : 'Run fresh backtests'}
          </button>
        ) : null
      }
    >
      {allQuery.isLoading && <div className="skeleton h-48 w-full" />}
      {allQuery.isSuccess && perAsset.length === 0 && (
        <Panel className="p-6">
          <EmptyState title="No completed backtests" description="This strategy has no completed backtest runs yet." />
        </Panel>
      )}
      {perAsset.length > 0 && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <StatCard label="Assets tested" value={String(perAsset.length)} />
            <StatCard label="Total trades" value={totalTrades.toLocaleString()} />
            <StatCard
              label="Weighted avg return"
              value={weightedReturn != null ? formatBacktestReturn(weightedReturn) : '—'}
              tone={weightedReturn == null ? 'default' : weightedReturn >= 0 ? 'profit' : 'risk'}
              hint="trade-weighted"
            />
            <StatCard
              label="Best asset"
              value={best?.symbol ?? '—'}
              hint={best?.total_return != null ? formatBacktestReturn(Number.parseFloat(best.total_return)) : undefined}
              tone="profit"
            />
            <StatCard
              label="Worst asset"
              value={worst?.symbol ?? '—'}
              hint={worst?.total_return != null ? formatBacktestReturn(Number.parseFloat(worst.total_return)) : undefined}
              tone={worst?.total_return != null && Number.parseFloat(worst.total_return) < 0 ? 'risk' : 'default'}
            />
          </div>
          {avgSharpe != null && (
            <p className="text-[11px] text-fg-subtle">Average Sharpe across assets with computed metrics: <span className="font-mono text-fg-muted">{formatSharpe(avgSharpe)}</span></p>
          )}

          <Panel className="divide-y divide-border/60 overflow-hidden">
            <div className="grid grid-cols-[1.6fr_1fr_1fr_1fr_1fr_1fr_0.8fr_auto] items-center gap-2 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-fg-subtle">
              <span>Asset</span><span className="text-right">Return</span><span className="text-right">vs BTC</span>
              <span className="text-right">Win rate</span><span className="text-right">Sharpe</span>
              <span className="text-right">Max DD</span><span className="text-right">Trades</span><span />
            </div>
            {perAsset.map((r) => {
              const ret = Number.parseFloat(r.total_return!)
              const bench = num(r.benchmark_return)
              const open = expanded === r.id
              return (
                <div key={r.id} className={cn(ret >= 0 ? 'bg-profit/[0.04]' : 'bg-risk/[0.05]')}>
                  <button
                    type="button"
                    suppressHydrationWarning
                    onClick={() => setExpanded(open ? null : r.id)}
                    className="grid w-full grid-cols-[1.6fr_1fr_1fr_1fr_1fr_1fr_0.8fr_auto] items-center gap-2 px-3 py-2.5 text-left font-mono text-xs tabular-nums transition-colors hover:bg-surface-hover"
                  >
                    <span className="flex items-center gap-2 font-sans font-medium text-fg">
                      <CryptoIcon symbol={r.symbol!} size={18} /> {r.symbol}
                    </span>
                    <span className={cn('text-right font-semibold', ret >= 0 ? 'text-profit' : 'text-risk')}>{formatBacktestReturn(ret)}</span>
                    <span className="text-right text-fg-muted">{bench != null ? formatBacktestReturn(bench) : '—'}</span>
                    <span className="text-right text-fg-muted">{r.win_rate != null ? formatWinRate(Number.parseFloat(r.win_rate)) : '—'}</span>
                    <span className="text-right text-fg-muted">{r.sharpe_ratio != null ? formatSharpe(Number.parseFloat(r.sharpe_ratio)) : '—'}</span>
                    <span className="text-right text-risk">{r.max_drawdown_pct != null ? `-${Math.abs(Number.parseFloat(r.max_drawdown_pct)).toFixed(2)}%` : '—'}</span>
                    <span className="text-right text-fg-muted">{r.trade_count ?? '—'}</span>
                    <span className="text-fg-subtle">{open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</span>
                  </button>
                  {open && (
                    <div className="border-t border-border/60 px-3 py-3">
                      <ExpandedCurve backtestId={r.id} />
                    </div>
                  )}
                </div>
              )
            })}
          </Panel>
        </div>
      )}
    </Section>
  )
}

// ── Trade P&L distribution — real server-computed histogram ───────────────
export function TradePnlDistributionSection({ strategyId }: { strategyId: string }) {
  const query = useTradePnlDistribution(strategyId)
  const dist = query.data ?? null

  return (
    <Section
      icon={<Sigma size={16} />}
      title="Trade P&L distribution"
      description="Realized trade outcomes bucketed server-side from this strategy's executions — green gains, red losses."
    >
      <Panel className="p-4">
        {query.isLoading && <div className="skeleton h-[240px] w-full" />}
        {query.isSuccess && (!dist || dist.trade_count === 0) && (
          <EmptyState title="No closed trades" description="No executions with realized P&L recorded for this strategy yet." />
        )}
        {dist && dist.trade_count > 0 && (
          <>
            <Chart
              height={220}
              ariaLabel="Trade P&L distribution"
              option={(theme: ChartTheme) => {
                const axis = chartAxis(theme)
                return {
                  tooltip: chartTooltip(theme, {
                    formatter: (p: unknown) => {
                      const d = p as { dataIndex: number }
                      const b = dist.buckets[d.dataIndex]
                      return `${formatCapital(Number.parseFloat(b.bucket_min))} → ${formatCapital(Number.parseFloat(b.bucket_max))}<br/><b>${b.count.toLocaleString()}</b> trades · ${formatCapital(Number.parseFloat(b.total_pnl))} total`
                    },
                  }),
                  grid: { left: 56, right: 16, top: 16, bottom: 28 },
                  xAxis: {
                    type: 'category',
                    data: dist.buckets.map((b) => formatCapital((Number.parseFloat(b.bucket_min) + Number.parseFloat(b.bucket_max)) / 2)),
                    ...axis,
                    axisLabel: { ...axis.axisLabel, rotate: 30 },
                  },
                  yAxis: { type: 'log', logBase: 10, min: 1, ...axis },
                  series: [{
                    type: 'bar',
                    data: dist.buckets.map((b) => ({
                      value: Math.max(b.count, 1e-9),
                      itemStyle: { color: Number.parseFloat(b.bucket_max) <= 0 ? theme.risk : Number.parseFloat(b.bucket_min) >= 0 ? theme.profit : theme.borderStrong },
                    })),
                    barMaxWidth: 40,
                  }],
                }
              }}
            />
            <p className="mt-1 text-[10px] text-fg-subtle">Log-scale count axis — the near-zero bucket dominates otherwise.</p>
            <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatCard label="Avg win" value={dist.avg_win != null ? formatCapital(Number.parseFloat(dist.avg_win)) : '—'} tone="profit" hint={`${dist.win_count.toLocaleString()} wins`} />
              <StatCard label="Avg loss" value={dist.avg_loss != null ? formatCapital(Number.parseFloat(dist.avg_loss)) : '—'} tone="risk" hint={`${dist.loss_count.toLocaleString()} losses`} />
              <StatCard label="Best trade" value={dist.best_trade != null ? formatCapital(Number.parseFloat(dist.best_trade)) : '—'} tone="profit" />
              <StatCard label="Worst trade" value={dist.worst_trade != null ? formatCapital(Number.parseFloat(dist.worst_trade)) : '—'} tone="risk" />
            </div>
          </>
        )}
      </Panel>
    </Section>
  )
}
