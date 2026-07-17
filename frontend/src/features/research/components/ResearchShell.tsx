// Doc 08 §Architecture: feature shell for the Research workspace.
// Real data only (Doc 00 §14.5/§14.7): every figure comes from
// /v1/backtests (engine-persisted runs + computed metrics + equity curves)
// or /api/ml (background training jobs, regime state). Notes are the one
// deliberate exception — explicitly labeled "local only" (localStorage).
//
// REDESIGN (owner request):
//  - Backtester: research capital input (sandbox), asset list filtered to
//    100+ ingested bars (Hermes pipeline bar_count), full post-run results
//    (equity curve, extended metrics grid, monthly P&L heatmap).
//  - Explorer: strategy-filtered, fixed-height scrollable table, row colors,
//    profitable-only toggle, CSV export, click-to-load equity curve.
//  - Training: all 3 model types (XGBoost / LSTM / HMM) with per-model
//    results — accuracy vs baseline, feature importance, regime charts —
//    and a model version history table.
'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  Brain,
  FlaskConical,
  LineChart as LineChartIcon,
  NotebookPen,
  ShieldCheck,
  Table2,
} from 'lucide-react'
import {
  Badge,
  Button,
  CryptoIcon,
  EmptyState,
  Heatmap,
  InstitutionalTable,
  LineChart,
  PageHeader,
  Panel,
  Section,
  StatCard,
  type InstitutionalColumnDef,
} from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { useStrategies, useMonthlyReturns } from '@/features/strategies/hooks/useStrategies'
import { useAssets } from '@/features/markets/hooks/useMarkets'
import { useHermesPipeline } from '@/features/hermes/hooks/useHermes'
import { monthlyReturnsGrid } from '@/features/strategies/analytics'
import { FeatureImportanceChart, RegimePosteriorTimeline } from '@/features/strategies/components/charts'
import {
  formatBacktestReturn,
  formatCapital,
  formatSharpe,
  formatTimestamp,
  formatWinRate,
} from '@/lib/utils/format'
import type { Strategy } from '@/features/strategies/types'
import {
  useAllBacktests,
  useEquityCurve,
  useRegime,
  useRunBacktest,
  useTrainHmm,
  useTrainLstm,
  useTrainMetalabeler,
  useTrainStatus,
} from '../hooks/useResearch'
import { useHermesMl } from '@/features/hermes/hooks/useHermes'
import type { BacktestSummary } from '../types'

// Only strategies the backend can actually replay (plugin classes exist) —
// mirrors api/v1/backtests.py's allow-list; the API 400s anything else.
const RUNNABLE = new Set(['reference-ma-crossover', 'reference-funding-basis'])
// ~5 years of 1h bars. Only 1h-granularity assets reach this; lower-count
// assets are stored daily and produce degenerate 0-trade runs against the
// reference strategies' 1h interval.
const MIN_BARS = 40_000

const selectCls =
  'h-9 rounded-lg border border-border bg-surface px-3 text-sm text-fg outline-none focus:border-accent'

const fmtMaxDD = (v: number) => `-${Math.abs(v * 100).toFixed(1)}%`
const num = (v: string | null | undefined) => (v == null ? null : Number.parseFloat(v))

// Readable feature labels — raw model column names → human names (owner req).
const FEATURE_LABELS: Record<string, string> = {
  price_momentum_5: '5-period momentum',
  price_momentum_20: '20-period momentum',
  volatility_20: '20-period volatility',
  volume_ratio: 'Volume ratio',
  signal_value: 'Signal direction',
  signal_abs: 'Signal magnitude',
  funding_rate: 'Funding rate',
  open_interest_change: 'OI change',
  oi_interest_change: 'OI change',
  returns: 'Price returns',
  volatility: 'Volatility',
}
const featureLabel = (k: string) => FEATURE_LABELS[k] ?? k
const relabelImportance = (imp: Record<string, number>): Record<string, number> =>
  Object.fromEntries(Object.entries(imp).map(([k, v]) => [featureLabel(k), v]))

// "Jan 2020 → Jul 2026" from ISO period bounds.
const fmtPeriod = (start?: string | null, end?: string | null): string => {
  if (!start || !end) return '—'
  const f = (s: string) => new Date(s).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
  return `${f(start)} → ${f(end)}`
}
const yearsBetween = (start?: string | null, end?: string | null): string => {
  if (!start || !end) return ''
  const yrs = (new Date(end).getTime() - new Date(start).getTime()) / (365.25 * 24 * 3600 * 1000)
  return `~${yrs.toFixed(1)} years`
}
const REGIME_NAME: Record<string, string> = { '0': 'bear', '1': 'neutral', '2': 'bull' }
const regimeTone = (label?: string): 'profit' | 'risk' | 'default' =>
  label === 'bull' ? 'profit' : label === 'bear' ? 'risk' : 'default'

// Research capital — sandbox only, persisted locally per browser.
const RESEARCH_CAPITAL_KEY = 'quanthub-research-capital'

function useResearchCapital(): [number, (v: number) => void] {
  const [capital, setCapital] = useState(10_000)
  useEffect(() => {
    const n = Number.parseFloat(window.localStorage.getItem(RESEARCH_CAPITAL_KEY) ?? '')
    if (Number.isFinite(n) && n > 0) setCapital(n)
  }, [])
  const set = (v: number) => {
    setCapital(v)
    window.localStorage.setItem(RESEARCH_CAPITAL_KEY, String(v))
  }
  return [capital, set]
}

// ── Section 1: Strategy Backtester (single-asset sandbox) ──────────────────
function BacktesterSection({
  strategies,
  selectedRun,
  onSelectRun,
}: {
  strategies: Strategy[]
  selectedRun: BacktestSummary | null
  onSelectRun: (row: BacktestSummary | null) => void
}) {
  const runnable = strategies.filter((s) => RUNNABLE.has(s.name))
  const assetsQuery = useAssets()
  const pipelineQuery = useHermesPipeline()
  const barCounts = useMemo(() => {
    const m = new Map<string, number>()
    for (const a of pipelineQuery.data?.assets ?? []) m.set(a.symbol, a.bar_count)
    return m
  }, [pipelineQuery.data])
  // Clean list (owner request): only assets with >= 40,000 1h bars (~5 years).
  // These are the only assets whose bars are actually stored at 1h — the
  // reference strategies replay at "1h", so a lower-bar (daily) asset yields a
  // degenerate 0-trade run. Dedup by symbol (keep the most-ingested version),
  // alphabetical.
  const assets = useMemo(() => {
    const bySymbol = new Map<string, { id: string; symbol: string; bars: number }>()
    for (const a of assetsQuery.data ?? []) {
      const bars = barCounts.get(a.symbol) ?? 0
      if (bars < MIN_BARS) continue
      const prev = bySymbol.get(a.symbol)
      if (!prev || bars > prev.bars) bySymbol.set(a.symbol, { id: a.id, symbol: a.symbol, bars })
    }
    return [...bySymbol.values()].sort((x, y) => x.symbol.localeCompare(y.symbol))
  }, [assetsQuery.data, barCounts])
  // "~5 years" style label from bar count (1h bars → years).
  const yearsLabel = (bars: number) => {
    const yrs = bars / (24 * 365)
    return yrs >= 1 ? `~${yrs.toFixed(1)} years` : `~${Math.round(yrs * 12)} months`
  }

  const [capital, setCapital] = useResearchCapital()
  const [strategyId, setStrategyId] = useState('')
  const [symbol, setSymbol] = useState('')
  const [start, setStart] = useState('2026-01-01')
  const [end, setEnd] = useState('2026-07-01')
  const [pendingRunName, setPendingRunName] = useState<string | null>(null)

  const runMutation = useRunBacktest()
  const backtestsQuery = useAllBacktests(Boolean(pendingRunName))
  const backtests = useMemo(() => backtestsQuery.data ?? [], [backtestsQuery.data])

  // When the started run shows up COMPLETED, select it and stop polling.
  useEffect(() => {
    if (!pendingRunName) return
    const row = backtests.find((b) => b.name === pendingRunName)
    if (row && row.status === 'COMPLETED') {
      onSelectRun(row)
      setPendingRunName(null)
    }
  }, [backtests, pendingRunName, onSelectRun])

  const selected = selectedRun
  const curveQuery = useEquityCurve(selected?.id ?? null)
  const curve = curveQuery.data ?? []
  const curvePoints = curve.map((p) => ({
    label: formatTimestamp(p.ts),
    value: Number.parseFloat(p.portfolio_value),
  }))

  const strategy = runnable.find((s) => s.id === strategyId) ?? null
  const canRun = Boolean(strategy && symbol && start && end) && !runMutation.isPending && !pendingRunName

  const onRun = async () => {
    if (!strategy) return
    const res = await runMutation.mutateAsync({
      strategy_id: strategy.id,
      symbol,
      start: `${start}T00:00:00Z`,
      end: `${end}T00:00:00Z`,
      initial_capital: String(capital),
    })
    setPendingRunName(res.run_name)
  }

  const ret = num(selected?.total_return)
  const bench = num(selected?.benchmark_return)
  const zeroTrades = selected != null && selected.status === 'COMPLETED' && (selected.trade_count ?? 0) === 0
  const capitalDelta =
    selected?.initial_capital != null && selected?.final_capital != null
      ? Number.parseFloat(selected.final_capital) - Number.parseFloat(selected.initial_capital)
      : null

  // Monthly P&L heatmap for the selected run's strategy (strategy-wide
  // realized executions — labeled as such, not per-run).
  const monthlyQuery = useMonthlyReturns(selected?.strategy_id ?? '')
  const monthly = useMemo(() => monthlyReturnsGrid(monthlyQuery.data ?? []), [monthlyQuery.data])

  return (
    <Section
      icon={<LineChartIcon size={16} />}
      title="Strategy Backtester"
      description="Pick one strategy and one asset — replays through the live TP/SL engine with your research capital; results persist to the explorer below."
    >
      <Panel className="space-y-4 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-xs text-fg-muted">
            Research capital — sandbox only
            <input
              type="number"
              min={100}
              step={1000}
              className={cn(selectCls, 'w-32 font-mono')}
              value={capital}
              onChange={(e) => {
                const n = Number.parseFloat(e.target.value)
                if (Number.isFinite(n) && n > 0) setCapital(n)
              }}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-fg-muted">
            Strategy (platform plugins only)
            <select className={selectCls} value={strategyId} onChange={(e) => setStrategyId(e.target.value)}>
              <option value="">Select strategy…</option>
              {runnable.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-fg-muted">
            Asset ({assets.length} with ~5yr 1h data)
            <select className={selectCls} value={symbol} onChange={(e) => setSymbol(e.target.value)}>
              <option value="">Select asset…</option>
              {assets.map((a) => (
                <option key={a.id} value={a.symbol}>{a.symbol} · {yearsLabel(a.bars)}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-fg-muted">
            Start
            <input type="date" className={selectCls} value={start} onChange={(e) => setStart(e.target.value)} />
          </label>
          <label className="flex flex-col gap-1 text-xs text-fg-muted">
            End
            <input type="date" className={selectCls} value={end} onChange={(e) => setEnd(e.target.value)} />
          </label>
          <Button onClick={onRun} disabled={!canRun}>
            {pendingRunName ? 'Running…' : runMutation.isPending ? 'Starting…' : 'Run Backtest'}
          </Button>
        </div>

        {runMutation.isError && <p className="text-xs text-risk">{String(runMutation.error)}</p>}
        {pendingRunName && (
          <p className="text-xs text-fg-muted">
            Run <span className="font-mono">{pendingRunName}</span> in progress — refreshing every 5s…
          </p>
        )}

        {selected && zeroTrades ? (
          // One clean message, never a grid of "—" boxes (owner request). A
          // completed run with zero trades means the strategy/asset/period
          // produced no signals that cleared the engine — real, not an error.
          <div className="flex flex-col items-center gap-2 rounded-xl border border-border/60 bg-surface/40 px-6 py-10 text-center">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-surface text-fg-subtle">
              <LineChartIcon size={18} />
            </span>
            <p className="text-sm font-medium text-fg">No trades generated</p>
            <p className="max-w-md text-xs text-fg-muted">
              {selected.strategy_name} on {selected.symbol} over {selected.start_date?.slice(0, 10)} → {selected.end_date?.slice(0, 10)} produced
              no trades — no signals cleared the engine for this combination. Try a longer period or a different asset.
            </p>
          </div>
        ) : selected ? (
          <div className="space-y-4">
            {curvePoints.length >= 2 ? (
              <LineChart
                data={curvePoints}
                height={260}
                tone={ret != null && ret < 0 ? 'risk' : 'profit'}
                valueFormat={(v) => formatCapital(v)}
              />
            ) : curveQuery.isLoading ? (
              <div className="skeleton h-[260px] w-full" />
            ) : (
              <EmptyState title="No equity curve" description="This completed run persisted no equity curve — the engine recorded metrics but no per-step marks." />
            )}

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
              <StatCard label="Return" value={ret != null ? formatBacktestReturn(ret) : '—'} tone={ret == null ? 'default' : ret >= 0 ? 'profit' : 'risk'} />
              <StatCard
                label="vs BTC benchmark"
                value={bench != null ? formatBacktestReturn(bench) : '—'}
                hint={ret != null && bench != null ? (ret > bench ? 'beats benchmark' : 'below benchmark') : undefined}
                tone={ret != null && bench != null ? (ret > bench ? 'profit' : 'risk') : 'default'}
              />
              <StatCard label="Win rate" value={selected.win_rate != null ? formatWinRate(Number.parseFloat(selected.win_rate)) : '—'} />
              <StatCard label="Sharpe" value={selected.sharpe_ratio != null ? formatSharpe(Number.parseFloat(selected.sharpe_ratio)) : '—'} />
              <StatCard label="Sortino" value={selected.sortino_ratio != null ? formatSharpe(Number.parseFloat(selected.sortino_ratio)) : '—'} />
              <StatCard label="Max drawdown" value={selected.max_drawdown_pct != null ? fmtMaxDD(Number.parseFloat(selected.max_drawdown_pct) / 100) : '—'} tone="risk" />
              <StatCard label="Profit factor" value={selected.profit_factor != null ? Number.parseFloat(selected.profit_factor).toFixed(2) : '—'} />
              <StatCard label="Trades" value={selected.trade_count != null ? String(selected.trade_count) : '—'} />
              <StatCard
                label="Capital change"
                value={capitalDelta != null ? formatCapital(capitalDelta) : '—'}
                hint={selected.initial_capital != null ? `from ${formatCapital(Number.parseFloat(selected.initial_capital))}` : undefined}
                tone={capitalDelta == null ? 'default' : capitalDelta >= 0 ? 'profit' : 'risk'}
              />
              <StatCard label="Final capital" value={selected.final_capital != null ? formatCapital(Number.parseFloat(selected.final_capital)) : '—'} />
            </div>

            {monthly.years.length > 0 && (
              <div>
                <p className="mb-2 text-[11px] text-fg-subtle">
                  Monthly realized P&L — strategy-wide executions (all runs of {selected.strategy_name ?? 'this strategy'}), not this run alone.
                </p>
                <Heatmap
                  xLabels={monthly.months}
                  yLabels={monthly.years}
                  values={monthly.grid}
                  mode="diverging"
                  min={-monthly.maxAbs}
                  max={monthly.maxAbs}
                  height={Math.max(160, monthly.years.length * 48 + 80)}
                  colors={['#FF1744', '#1a1a2e', '#00C853']}
                  labelColor="#ffffff"
                  valueFormat={(v) => formatCapital(v)}
                />
              </div>
            )}
          </div>
        ) : null}
        {!selected && !pendingRunName && (
          <p className="text-xs text-fg-subtle">
            Run a backtest, or pick a completed run in the explorer below, to see its full results here.
          </p>
        )}
      </Panel>
    </Section>
  )
}

// ── Section 2: Backtest Results Explorer (strategy-filtered) ────────────────
function beats(row: BacktestSummary): boolean | null {
  if (row.total_return == null || row.benchmark_return == null) return null
  return Number.parseFloat(row.total_return) > Number.parseFloat(row.benchmark_return)
}

function ExplorerSection({
  strategies,
  backtests,
  loading,
  onSelect,
}: {
  strategies: Strategy[]
  backtests: BacktestSummary[]
  loading: boolean
  onSelect: (row: BacktestSummary) => void
}) {
  const runnable = strategies.filter((s) => RUNNABLE.has(s.name))
  const [strategyId, setStrategyId] = useState('')
  const [profitableOnly, setProfitableOnly] = useState(false)
  const [curveRow, setCurveRow] = useState<BacktestSummary | null>(null)

  const rows = useMemo(
    () =>
      backtests.filter(
        (b) =>
          (!strategyId || b.strategy_id === strategyId) &&
          (!profitableOnly || (b.total_return != null && Number.parseFloat(b.total_return) > 0)),
      ),
    [backtests, strategyId, profitableOnly],
  )

  const curveQuery = useEquityCurve(curveRow?.id ?? null)
  const curvePoints = (curveQuery.data ?? []).map((p) => ({
    label: formatTimestamp(p.ts),
    value: Number.parseFloat(p.portfolio_value),
  }))

  const columns: InstitutionalColumnDef<BacktestSummary>[] = useMemo(
    () => [
      {
        header: 'Asset',
        accessorKey: 'symbol',
        cell: (c) => {
          const s = c.getValue<string | null>()
          const beat = beats(c.row.original)
          return (
            <span className={cn('flex items-center gap-2 font-mono text-xs', beat && 'font-bold')}>
              {s && <CryptoIcon symbol={s} size={16} />} {s ?? '—'}
              {beat && <Badge variant="profit">beats BTC</Badge>}
            </span>
          )
        },
        meta: { width: '1.6fr' },
      },
      {
        header: 'Return',
        accessorKey: 'total_return',
        sortingFn: (a, b) =>
          Number.parseFloat(a.original.total_return ?? '-999') - Number.parseFloat(b.original.total_return ?? '-999'),
        cell: (c) => {
          const v = c.getValue<string | null>()
          if (v == null) return '—'
          const n = Number.parseFloat(v)
          return <span className={n >= 0 ? 'text-profit' : 'text-risk'}>{formatBacktestReturn(n)}</span>
        },
        meta: { numeric: true },
      },
      {
        header: 'vs BTC',
        accessorKey: 'benchmark_return',
        cell: (c) => {
          const v = c.getValue<string | null>()
          return v == null ? '—' : formatBacktestReturn(Number.parseFloat(v))
        },
        meta: { numeric: true, hideBelow: 'tablet' },
      },
      {
        header: 'Win rate',
        accessorKey: 'win_rate',
        cell: (c) => {
          const v = c.getValue<string | null>()
          return v == null ? '—' : formatWinRate(Number.parseFloat(v))
        },
        meta: { numeric: true, hideBelow: 'laptop' },
      },
      {
        header: 'Sharpe',
        accessorKey: 'sharpe_ratio',
        cell: (c) => {
          const v = c.getValue<string | null>()
          return v == null ? '—' : formatSharpe(Number.parseFloat(v))
        },
        meta: { numeric: true, hideBelow: 'laptop' },
      },
      {
        header: 'Max DD',
        accessorKey: 'max_drawdown_pct',
        cell: (c) => {
          const v = c.getValue<string | null>()
          return v == null ? '—' : <span className="text-risk">{`-${Math.abs(Number.parseFloat(v)).toFixed(2)}%`}</span>
        },
        meta: { numeric: true, hideBelow: 'desktop' },
      },
      {
        header: 'Trades',
        accessorKey: 'trade_count',
        cell: (c) => c.getValue<number | null>() ?? '—',
        meta: { numeric: true, hideBelow: 'tablet' },
      },
      {
        header: 'Date',
        accessorKey: 'created_at',
        cell: (c) => <span className="whitespace-nowrap text-fg-subtle">{formatTimestamp(c.getValue<string>())}</span>,
        meta: { hideBelow: 'desktop' },
      },
    ],
    [],
  )

  return (
    <Section
      icon={<Table2 size={16} />}
      title="Backtest Results Explorer"
      description="Pick a strategy to browse its runs — losers included. Bold rows beat the BTC buy-and-hold benchmark. Click a row for its equity curve."
      actions={
        <div className="flex items-center gap-2">
          <select className={selectCls} value={strategyId} onChange={(e) => setStrategyId(e.target.value)}>
            <option value="">All strategies</option>
            {runnable.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <Button variant="ghost" size="sm" onClick={() => setProfitableOnly((v) => !v)}>
            {profitableOnly ? 'Show all' : 'Profitable only'}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Fixed-height scroll container — scales to any number of runs. */}
        <div className="max-h-[500px] overflow-y-auto rounded-xl border border-border/60">
          <InstitutionalTable
            data={rows}
            columns={columns}
            getRowId={(r) => r.id}
            initialSorting={[{ id: 'total_return', desc: true }]}
            exportFilename="backtests"
            onRowClick={(row) => setCurveRow(row)}
            rowClassName={(r) => {
              const v = num(r.total_return)
              if (v == null) return ''
              return v >= 0 ? 'bg-profit/[0.04]' : 'bg-risk/[0.05]'
            }}
            emptyState={
              loading ? (
                <div className="skeleton h-24 w-full" />
              ) : (
                <EmptyState title="No backtests" description="Run one with the backtester above." />
              )
            }
          />
        </div>
        {curveRow && (
          <Panel className="space-y-2 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-fg-muted">
              <span>
                Equity curve — <span className="font-mono">{curveRow.strategy_name}</span> · {curveRow.symbol} ·{' '}
                <span className={cn('font-mono', num(curveRow.total_return) != null && num(curveRow.total_return)! >= 0 ? 'text-profit' : 'text-risk')}>
                  {curveRow.total_return != null ? formatBacktestReturn(Number.parseFloat(curveRow.total_return)) : '—'}
                </span>
              </span>
              <Button variant="ghost" size="sm" onClick={() => setCurveRow(null)}>Close</Button>
            </div>
            {curveQuery.isLoading ? (
              <div className="skeleton h-[220px] w-full" />
            ) : curvePoints.length >= 2 ? (
              <LineChart data={curvePoints} height={220} valueFormat={(v) => formatCapital(v)} />
            ) : (
              <EmptyState title="No equity curve" description="This run has no persisted curve." />
            )}
          </Panel>
        )}
      </div>
    </Section>
  )
}

// Horizontal stacked regime bar — segments proportional to time-in-regime,
// aligned and immediately readable (replaces the misaligned donut).
function StackedRegimeBar({ counts }: { counts: Record<string, number> }) {
  const order: Array<{ key: string; label: string; color: string }> = [
    { key: 'bear', label: 'Bear', color: '#FF1744' },
    { key: 'neutral', label: 'Neutral', color: '#6b7280' },
    { key: 'bull', label: 'Bull', color: '#00C853' },
  ]
  const total = order.reduce((s, o) => s + (counts[o.key] ?? 0), 0)
  if (total === 0) return null
  return (
    <div className="space-y-2">
      <div className="flex h-7 w-full overflow-hidden rounded-lg">
        {order.map((o) => {
          const v = counts[o.key] ?? 0
          const pct = (v / total) * 100
          if (pct === 0) return null
          return (
            <div
              key={o.key}
              className="flex items-center justify-center text-[10px] font-semibold text-white"
              style={{ width: `${pct}%`, backgroundColor: o.color }}
              title={`${o.label} ${pct.toFixed(1)}%`}
            >
              {pct >= 8 ? `${pct.toFixed(0)}%` : ''}
            </div>
          )
        })}
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-1 text-[11px]">
        {order.map((o) => {
          const v = counts[o.key] ?? 0
          const pct = ((v / total) * 100).toFixed(1)
          return (
            <span key={o.key} className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: o.color }} />
              <span className="text-fg-muted">{o.label}</span>
              <span className="font-mono text-fg">{pct}%</span>
              <span className="text-fg-subtle">· {v.toLocaleString()} bars</span>
            </span>
          )
        })}
      </div>
    </div>
  )
}

// HMM training results — 3 aligned cards, stacked regime bar, smooth posterior
// timeline. Consumes the extended metrics ml.py now stores.
function HmmResults({ metrics }: { metrics: NonNullable<ReturnType<typeof useTrainStatus>['data']>['metrics'] & Record<string, unknown> }) {
  const m = metrics as {
    current_regime_label?: string; current_regime_posterior?: number; current_confidence?: number
    avg_duration_hours?: Record<string, number>; avg_duration_bars?: number
    regime_change_prob_24h?: number; transition_entropy?: number
    regime_counts?: Record<string, number>; regime_distribution?: Record<string, number>
    regime_posteriors?: { ts: string; bear?: number; neutral?: number; bull?: number }[]
    bars_used?: number; symbol?: string; period_start?: string; period_end?: string; data_features?: string[]
  }
  const label = m.current_regime_label ?? '—'
  const posterior = m.current_regime_posterior ?? m.current_confidence ?? null
  const counts = m.regime_counts ?? (m.regime_distribution
    ? Object.fromEntries(Object.entries(m.regime_distribution).map(([k, v]) => [REGIME_NAME[k] ?? k, v]))
    : {})
  const total = Object.values(counts).reduce((s, v) => s + v, 0)
  const curCount = counts[label] ?? 0
  const avgDurHrs = m.avg_duration_hours?.[label]
  const dot = label === 'bull' ? '🟢' : label === 'bear' ? '🔴' : '⚪'

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <div className="rounded-xl border border-border/60 bg-surface/40 p-4">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-fg-subtle">Current regime</div>
          <div className={cn('mt-1 flex items-center gap-2 text-lg font-bold', regimeTone(label) === 'profit' ? 'text-profit' : regimeTone(label) === 'risk' ? 'text-risk' : 'text-fg')}>
            <span>{dot}</span>{label.toUpperCase()}
          </div>
          <dl className="mt-2 space-y-1 text-[11px] text-fg-muted">
            <div className="flex justify-between"><dt>Posterior</dt><dd className="font-mono text-fg">{posterior != null ? `${(posterior * 100).toFixed(0)}%` : '—'}</dd></div>
            <div className="flex justify-between"><dt>Avg duration</dt><dd className="font-mono text-fg">{avgDurHrs != null ? `${(avgDurHrs / 24).toFixed(1)} days` : '—'}</dd></div>
            <div className="flex justify-between"><dt>Change prob (24h)</dt><dd className="font-mono text-fg">{m.regime_change_prob_24h != null ? `${(m.regime_change_prob_24h * 100).toFixed(0)}%` : '—'}</dd></div>
            <div className="flex justify-between"><dt>Occurred</dt><dd className="font-mono text-fg">{curCount.toLocaleString()} / {total.toLocaleString()} ({total ? ((curCount / total) * 100).toFixed(1) : '0'}%)</dd></div>
          </dl>
        </div>

        <div className="rounded-xl border border-border/60 bg-surface/40 p-4">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-fg-subtle">Training data</div>
          <div className="mt-1 text-lg font-bold text-fg">{(m.bars_used ?? 0).toLocaleString()} bars</div>
          <p className="mt-2 text-[11px] leading-relaxed text-fg-muted">
            {yearsBetween(m.period_start, m.period_end)} ({fmtPeriod(m.period_start, m.period_end)}) {m.symbol} hourly.
            <br />Features: {(m.data_features ?? []).map(featureLabel).join(', ')}.
          </p>
        </div>

        <div className="rounded-xl border border-border/60 bg-surface/40 p-4">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-fg-subtle">Evaluation</div>
          <div className="mt-1 text-lg font-bold text-fg">Unsupervised</div>
          <dl className="mt-2 space-y-1 text-[11px] text-fg-muted">
            <div className="flex justify-between"><dt>Accuracy gate</dt><dd className="text-fg">none</dd></div>
            <div className="flex justify-between"><dt>Avg duration</dt><dd className="font-mono text-fg">{m.avg_duration_bars != null ? `${m.avg_duration_bars.toFixed(0)} bars` : '—'}</dd></div>
            <div className="flex justify-between"><dt>Transition entropy</dt><dd className="font-mono text-fg">{m.transition_entropy != null ? m.transition_entropy.toFixed(2) : '—'}</dd></div>
            <div className="text-[10px] text-fg-subtle">lower entropy = more stable regimes</div>
          </dl>
        </div>
      </div>

      <div>
        <p className="mb-2 text-[11px] uppercase tracking-wide text-fg-subtle">Regime distribution (time in each regime)</p>
        <StackedRegimeBar counts={counts} />
      </div>

      <div>
        <p className="mb-2 text-[11px] uppercase tracking-wide text-fg-subtle">Regime timeline (daily posterior)</p>
        {m.regime_posteriors && m.regime_posteriors.length > 1 ? (
          <RegimePosteriorTimeline posteriors={m.regime_posteriors} height={220} />
        ) : (
          <p className="text-xs text-fg-subtle">No posterior history recorded for this run.</p>
        )}
      </div>
    </div>
  )
}

// ── Section 3: Model Training (all 3 models) ────────────────────────────────
const MODEL_OPTIONS = [
  { value: 'XGBoost_MetaLabeler', label: 'XGBoost MetaLabeler', kind: 'xgboost' as const },
  { value: 'LSTM_Predictor', label: 'LSTM Predictor', kind: 'lstm' as const },
  { value: 'HMM_RegimeDetector', label: 'HMM Regime Detector', kind: 'hmm' as const },
]

function TrainingSection() {
  const [modelType, setModelType] = useState('XGBoost_MetaLabeler')
  const [instrumentType, setInstrumentType] = useState<'SPOT' | 'PERPETUAL'>('SPOT')
  const [hmmSymbol, setHmmSymbol] = useState('BTC/USDT')
  const [jobId, setJobId] = useState<string | null>(null)

  const trainMeta = useTrainMetalabeler()
  const trainLstm = useTrainLstm()
  const trainHmm = useTrainHmm()
  const statusQuery = useTrainStatus(jobId)
  const regimeQuery = useRegime()
  const mlQuery = useHermesMl()
  const models = mlQuery.data?.models ?? []
  const job = statusQuery.data ?? null
  const model = MODEL_OPTIONS.find((m) => m.value === modelType)!
  const busy = trainMeta.isPending || trainLstm.isPending || trainHmm.isPending
    || job?.status === 'RUNNING' || job?.status === 'PENDING'

  const onTrain = async () => {
    const res =
      model.kind === 'xgboost' ? await trainMeta.mutateAsync({ instrument_type: instrumentType })
      : model.kind === 'lstm' ? await trainLstm.mutateAsync({ instrument_type: instrumentType, seq_length: 20 })
      : await trainHmm.mutateAsync({ symbol: hmmSymbol })
    setJobId(res.job_id)
  }

  const metrics = job?.metrics as
    | {
        accuracy?: number; precision?: number; recall?: number; baseline?: number
        beats_baseline?: boolean; deployed?: boolean; not_deployed_reason?: string
        train_rows?: number; test_rows?: number
        period_start?: string; period_end?: string
        feature_importance?: Record<string, number>
        regime_distribution?: Record<string, number>
        regime_counts?: Record<string, number>
        regime_history?: { ts: string; regime: number }[]
        regime_posteriors?: { ts: string; bear?: number; neutral?: number; bull?: number }[]
        current_regime_label?: string; current_confidence?: number; current_regime_posterior?: number
        avg_duration_hours?: Record<string, number>; avg_duration_bars?: number
        transition_entropy?: number; regime_change_prob_24h?: number
        bars_used?: number; symbol?: string; data_features?: string[]
      }
    | null
  const isHmmJob = job?.model_type === 'HMM_RegimeDetector'

  return (
    <Section
      icon={<Brain size={16} />}
      title="Model Training"
      description="Train AI models that score your trading signals. XGBoost + LSTM predict if a signal will be profitable; HMM detects the current market regime (bear / neutral / bull). Deployed models attach confidence scores to live signals."
    >
      <Panel className="space-y-4 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-xs text-fg-muted">
            Model type
            <select className={selectCls} value={modelType} onChange={(e) => setModelType(e.target.value)}>
              {MODEL_OPTIONS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </label>
          {model.kind !== 'hmm' && (
            <label className="flex flex-col gap-1 text-xs text-fg-muted">
              Instrument type (feature set)
              <select
                className={selectCls}
                value={instrumentType}
                onChange={(e) => setInstrumentType(e.target.value as 'SPOT' | 'PERPETUAL')}
              >
                <option value="SPOT">SPOT — 6 features (no funding/OI)</option>
                <option value="PERPETUAL">PERPETUAL — 8 features</option>
              </select>
            </label>
          )}
          {model.kind === 'hmm' && (
            <label className="flex flex-col gap-1 text-xs text-fg-muted">
              Asset (bar returns)
              <input className={cn(selectCls, 'w-36 font-mono')} value={hmmSymbol} onChange={(e) => setHmmSymbol(e.target.value)} />
            </label>
          )}
          <Button onClick={onTrain} disabled={busy}>
            {busy ? 'Training…' : 'Train Model'}
          </Button>
          {model.kind === 'lstm' && (
            <span className="text-[11px] text-fg-subtle">LSTM needs 500+ labeled signals and trains slowly — leave the tab open.</span>
          )}
        </div>

        {job && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm">
              <Badge variant={job.status === 'COMPLETED' ? 'profit' : job.status === 'FAILED' ? 'risk' : 'info'}>
                {job.status}
              </Badge>
              {(job.status === 'RUNNING' || job.status === 'PENDING') && (
                <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-accent border-t-transparent" aria-label="training in progress" />
              )}
              <span className="font-mono text-xs text-fg-subtle">{job.job_id}</span>
              <span className="text-xs text-fg-subtle">{job.model_type}</span>
            </div>
            {job.status === 'FAILED' && <p className="text-xs text-risk">{job.error}</p>}

            {job.status === 'COMPLETED' && metrics && !isHmmJob && (
              <>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <StatCard
                    label="Held-out accuracy"
                    value={metrics.accuracy != null ? `${(metrics.accuracy * 100).toFixed(2)}%` : '—'}
                    tone={metrics.beats_baseline ? 'profit' : 'risk'}
                    hint={metrics.beats_baseline ? 'above baseline' : 'below baseline'}
                  />
                  <StatCard
                    label="Majority baseline"
                    value={metrics.baseline != null ? `${(metrics.baseline * 100).toFixed(2)}%` : '—'}
                    hint="always-predict-majority"
                  />
                  <StatCard
                    label="Precision / Recall"
                    value={`${metrics.precision != null ? (metrics.precision * 100).toFixed(1) : '—'}% / ${metrics.recall != null ? (metrics.recall * 100).toFixed(1) : '—'}%`}
                  />
                  <StatCard
                    label="Training period"
                    value={fmtPeriod(metrics.period_start, metrics.period_end)}
                    hint={`${(metrics.train_rows ?? 0).toLocaleString()} train · ${(metrics.test_rows ?? 0).toLocaleString()} test (20%)`}
                  />
                </div>

                {metrics.deployed ? (
                  <div className="flex items-start gap-3 rounded-xl border border-profit/30 bg-profit/[0.06] p-4">
                    <ShieldCheck size={18} className="mt-0.5 shrink-0 text-profit" />
                    <div>
                      <div className="text-sm font-semibold text-profit">Model deployed</div>
                      <p className="mt-0.5 text-xs text-fg-muted">
                        Held-out accuracy {metrics.accuracy != null ? `${(metrics.accuracy * 100).toFixed(2)}%` : '—'} beats the
                        {' '}{metrics.baseline != null ? `${(metrics.baseline * 100).toFixed(2)}%` : '—'} majority-class baseline — now scoring live signals.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start gap-3 rounded-xl border border-risk/40 bg-risk/[0.06] p-4">
                    <AlertTriangle size={18} className="mt-0.5 shrink-0 text-risk" />
                    <div>
                      <div className="text-sm font-semibold text-risk">Model not deployed</div>
                      <p className="mt-0.5 text-xs leading-relaxed text-fg-muted">
                        Accuracy {metrics.accuracy != null ? `${(metrics.accuracy * 100).toFixed(2)}%` : '—'} is below the
                        {' '}{metrics.baseline != null ? `${(metrics.baseline * 100).toFixed(2)}%` : '—'} majority-class baseline. This
                        model adds no predictive value over always guessing the majority outcome.
                        Suggestions: collect more signal data, try different hyperparameters, or wait for more diverse market conditions.
                      </p>
                    </div>
                  </div>
                )}

                {metrics.feature_importance && (
                  <div>
                    <p className="mb-1 text-[11px] uppercase tracking-wide text-fg-subtle">Feature importance</p>
                    <FeatureImportanceChart importance={relabelImportance(metrics.feature_importance)} height={200} />
                  </div>
                )}
              </>
            )}

            {job.status === 'COMPLETED' && metrics && isHmmJob && (
              <HmmResults metrics={metrics} />
            )}
          </div>
        )}

        {/* Persistent regime state (last trained HMM, any session) */}
        {!isHmmJob && regimeQuery.data && (
          <p className="text-[11px] text-fg-subtle">
            Last trained regime model: <span className="font-mono">{regimeQuery.data.symbol}</span> — currently{' '}
            <span className="font-medium text-fg-muted">{regimeQuery.data.current_regime_label?.toUpperCase()}</span>. Full view on the Strategy page's Market Regime section.
          </p>
        )}

        {/* Model version history — real registry rows (Hermes). */}
        <div>
          <p className="mb-2 text-[11px] uppercase tracking-wide text-fg-subtle">Model version history</p>
          {models.length === 0 ? (
            <p className="text-xs text-fg-subtle">No models registered yet.</p>
          ) : (
            <div className="max-h-[280px] overflow-y-auto rounded-lg border border-border/60">
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-surface-raised text-[10px] uppercase tracking-wide text-fg-subtle">
                  <tr>
                    <th className="px-3 py-2">Model</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2 text-right">Accuracy</th>
                    <th className="px-3 py-2 text-right">vs Baseline</th>
                    <th className="px-3 py-2">Period</th>
                    <th className="px-3 py-2 text-right">Trained</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {models.map((m) => {
                    const isHmm = m.model_type.startsWith('HMM')
                    // Below-baseline models read clearer as NOT DEPLOYED than TRAINED.
                    const belowBaseline = m.accuracy != null && m.baseline != null && m.accuracy <= m.baseline
                    const statusLabel = m.status === 'DEPLOYED' ? 'DEPLOYED' : belowBaseline || !isHmm ? 'NOT DEPLOYED' : m.status
                    const statusVariant = m.status === 'DEPLOYED' ? 'profit' : 'risk'
                    return (
                      <tr key={m.model_id}>
                        <td className="px-3 py-2 font-mono">{m.model_type}</td>
                        <td className="px-3 py-2"><Badge variant={statusVariant}>{statusLabel}</Badge></td>
                        <td className="px-3 py-2 text-right font-mono">
                          {isHmm ? (
                            <span className="text-fg-subtle" title="Unsupervised model — no accuracy metric applies">N/A</span>
                          ) : m.accuracy != null ? `${(m.accuracy * 100).toFixed(2)}%` : '—'}
                        </td>
                        <td className="px-3 py-2 text-right font-mono">{isHmm ? <span className="text-fg-subtle">—</span> : m.baseline != null ? `${(m.baseline * 100).toFixed(2)}%` : '—'}</td>
                        <td className="px-3 py-2 text-fg-muted">{m.period_start && m.period_end ? fmtPeriod(m.period_start, m.period_end) : '—'}</td>
                        <td className="px-3 py-2 text-right text-fg-subtle">{formatTimestamp(m.created_at)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Panel>
    </Section>
  )
}

// ── Section 4: Strategy Notes (local only) ──────────────────────────────────
function NotesSection({ strategies }: { strategies: Strategy[] }) {
  const [strategyId, setStrategyId] = useState('')
  const key = `quanthub-research-notes-${strategyId}`
  const [text, setText] = useState('')

  useEffect(() => {
    if (!strategyId) return
    setText(window.localStorage.getItem(key) ?? '')
  }, [key, strategyId])

  const onChange = (v: string) => {
    setText(v)
    if (strategyId) window.localStorage.setItem(key, v)
  }

  return (
    <Section
      icon={<NotebookPen size={16} />}
      title="Strategy Notes"
      description="Research observations per strategy."
      actions={<Badge variant="warning">local only — stored in this browser</Badge>}
    >
      <Panel className="space-y-3 p-4">
        <select className={selectCls} value={strategyId} onChange={(e) => setStrategyId(e.target.value)}>
          <option value="">Select strategy…</option>
          {strategies.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <textarea
          className="min-h-[140px] w-full resize-y rounded-lg border border-border bg-surface p-3 font-mono text-sm text-fg outline-none focus:border-accent"
          placeholder={strategyId ? 'Markdown notes — saved locally as you type…' : 'Pick a strategy first.'}
          value={text}
          disabled={!strategyId}
          onChange={(e) => onChange(e.target.value)}
        />
      </Panel>
    </Section>
  )
}

// ── Shell ───────────────────────────────────────────────────────────────────
export function ResearchShell() {
  const strategiesQuery = useStrategies()
  const strategies = strategiesQuery.data ?? []
  const backtestsQuery = useAllBacktests()
  const backtests = backtestsQuery.data ?? []
  const [selectedRun, setSelectedRun] = useState<BacktestSummary | null>(null)

  return (
    <div className="space-y-8">
      <PageHeader
        icon={<FlaskConical size={18} />}
        title="Research"
        subtitle="Backtesting, model training and results exploration — every figure engine-computed, losers included."
      />
      <BacktesterSection strategies={strategies} selectedRun={selectedRun} onSelectRun={setSelectedRun} />
      <ExplorerSection
        strategies={strategies}
        backtests={backtests}
        loading={backtestsQuery.isLoading}
        onSelect={(row) => {
          setSelectedRun(row)
          document.querySelector('#research-top')?.scrollIntoView({ behavior: 'smooth' })
        }}
      />
      <TrainingSection />
      <NotesSection strategies={strategies} />
    </div>
  )
}
