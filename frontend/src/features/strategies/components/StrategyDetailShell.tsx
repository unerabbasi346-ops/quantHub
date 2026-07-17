// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout / §Data Visualization / §Interaction Standards.
// Doc 08 — Frontend Architecture (QH-008) §Architecture / §State Management.
// Doc 14 §10.2 Strategy Governance (§10.2.5 versioning F-9), §10.6.4 Signal
//   Recording, §10.3 Backtesting. Doc 15 §11.1.5 (signal value = conviction).
// Doc 00 §14.5/§14.7 — DATA HONESTY. Per Doc 00 §14.11
// handbook/ui/06_STRATEGY_ENGINEERING + visual_engineering/13_VISUAL_DNA —
//   dense institutional quantitative analytics hub. Six sections: (1) selector
//   + real-data stat pill strip, (2) equity/conviction curve + performance
//   metrics grid, (3) full-width monthly signal-performance heatmap, (4)
//   conviction distribution + signal timeline scatter, (5) backtest order flow
//   + trade P&L distribution + consecutive-direction runs, (6) strategy
//   configuration + metadata card. Every figure is real (signals/backtest) or
//   an explicit "Pending"/"Not computed" disclosure — nothing fabricated.
//
// Dedicated strategy detail page (owner request, points 7–8) at
// /strategies/[id]: a large primary chart, a side metadata panel (F-9 honest),
// supporting widgets from real data, and a top strategy SELECTOR whose dropdown
// slides down from the top and switches ALL page content to the chosen
// strategy (with a loading transition — nothing stays static).
'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  Activity,
  BarChart3,
  Brain,
  CalendarClock,
  CalendarRange,
  Check,
  ChevronDown,
  Clock,
  FileText,
  Gauge as GaugeIcon,
  Hash,
  LineChart as LineChartIcon,
  ListChecks,
  Percent,
  ShieldQuestion,
  Sigma,
  Target,
  TerminalSquare,
  Waves,
  Zap,
} from 'lucide-react'
import {
  Badge,
  CryptoIcon,
  EmptyState,
  ErrorState,
  Heatmap,
  MultiLineChart,
  Panel,
  Section,
  SkeletonTable,
  StatCard,
  type BadgeVariant,
  type Series,
} from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { formatMaxDrawdownPct, formatReturn, formatSharpe, formatSignalStrength, formatTimestamp } from '@/lib/utils/format'
import { EASE_OUT } from '@/lib/motion'
import { useSyncStore } from '@/lib/store/sync'
import { useAssets, useBars } from '@/features/markets/hooks/useMarkets'
import { useBacktests, useMonthlyReturns, useSignals, useStrategies, useStrategyMetrics } from '../hooks/useStrategies'
import type { Signal, Strategy } from '../types'
import { isReferenceStrategy, REFERENCE_BADGE, REFERENCE_CAPTION, REFERENCE_TOOLTIP } from '../labels'
import { consecutiveRuns, monthlyConvictionGrid, monthlyReturnsGrid, signalPoints } from '../analytics'
import { ConsecutiveRunsChart, ConvictionEquityChart, SignalStrengthDistributionChart, SignalTimelineScatter } from './charts'
import { MLIntelligenceSection } from './MLIntelligence'
import { BacktestReturnTile, PendingMetricTile, RealMetricTile, RealRingTile } from './metric-tiles'
import { BacktestRunCards, RecentSignalRows } from './rich-lists'
import { MultiAssetBacktestSection, SimCapitalInput, TradePnlDistributionSection, useSimCapital } from './multi-asset'
import { fmtMoney, fmtReturnPct } from './tables'

// Signal history depth for the detail workspace's derived analytics (monthly
// heatmap, timeline scatter, streaks) — the backend caps at 1000; the flat
// /strategies list and dashboard cards keep their own lighter default.
const SIGNAL_HISTORY_LIMIT = 1000

const fmtSignal = (v: string) => formatSignalStrength(Number.parseFloat(v))
const fmtTime = (ts: string) => formatTimestamp(ts)
const fmtDate = (ts: string | null) => (ts ? formatTimestamp(ts) : '—')

function statusVariant(status: string): BadgeVariant {
  return status.toUpperCase() === 'ACTIVE' ? 'profit' : 'neutral'
}

const median = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b)
  const m = Math.floor(s.length / 2)
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2
}

const prettyKey = (k: string) =>
  k
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bMa\b/g, 'MA')

// Indicator overlay data — REAL only: pulls the numeric series a strategy chose
// to record in each signal's metadata (e.g. the MA-crossover plugin records
// long_ma / short_ma). Keeps only keys that are numeric in EVERY signal and
// actually VARY over time (so constants like `window` / `scale` are excluded),
// then plots them on a shared time axis. Strategies whose signals carry no such
// series (or that have <2 signals) yield nothing — the caller shows that state.
function indicatorSeries(signals: Signal[]): { labels: string[]; series: Series[] } {
  const ordered = [...signals].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime())
  if (ordered.length < 2) return { labels: [], series: [] }

  let keys = Object.keys(ordered[0].metadata ?? {})
  for (const s of ordered) {
    const md = s.metadata ?? {}
    keys = keys.filter((k) => k in md && md[k] !== '' && !Number.isNaN(Number(md[k])))
  }
  const labels = ordered.map((s) => fmtTime(s.ts))
  const series: Series[] = []
  for (const k of keys) {
    const values = ordered.map((s) => Number((s.metadata ?? {})[k]))
    if (new Set(values).size > 1) series.push({ name: prettyKey(k), values })
  }
  return { labels, series }
}

// ── Strategy selector: transparent rounded bar matching the search-input look;
//    dropdown slides down from the top; selecting switches the whole page ──
function StrategySelector({
  strategies,
  current,
  onSelect,
}: {
  strategies: Strategy[]
  current: Strategy | null
  onSelect: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onClick = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false)
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div className="relative w-full max-w-sm" ref={ref}>
      <button
        type="button"
        suppressHydrationWarning
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'flex h-10 w-full items-center gap-2.5 rounded-lg border bg-surface-raised/50 px-3 text-left text-sm transition-colors',
          open ? 'border-border-strong bg-surface-raised' : 'border-border hover:border-border-strong',
        )}
      >
        <Brain size={16} className="shrink-0 text-fg-subtle" />
        <span className="min-w-0 flex-1 truncate font-medium text-fg">{current?.name ?? 'Select strategy…'}</span>
        <ChevronDown size={16} className={cn('shrink-0 text-fg-subtle transition-transform duration-150', open && 'rotate-180')} />
      </button>
      {open && (
        <div
          role="listbox"
          className="absolute left-0 right-0 top-full z-40 mt-1.5 animate-slide-down overflow-hidden rounded-xl border border-border bg-surface-raised p-1.5 shadow-lg"
        >
          <p className="px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Available strategies</p>
          {strategies.map((s) => {
            const selected = s.id === current?.id
            return (
              <button
                key={s.id}
                type="button"
                suppressHydrationWarning
                role="option"
                aria-selected={selected}
                onClick={() => {
                  setOpen(false) // close immediately on selection
                  onSelect(s.id)
                }}
                className={cn(
                  'flex w-full items-center justify-between gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors',
                  selected ? 'bg-accent-soft text-accent' : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
                )}
              >
                <span className="truncate">{s.name}</span>
                {selected && <Check size={15} className="shrink-0" />}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function StrategyDetailShell({ id }: { id: string }) {
  const router = useRouter()
  const strategiesQuery = useStrategies()
  const strategies = strategiesQuery.data ?? []
  const strategy = strategies.find((s) => s.id === id) ?? null

  // Switching state: set on selection, cleared when the route param actually
  // updates — guarantees a visible loading transition even if the target's
  // data is cached, so nothing stays static from the previous selection.
  const [pendingId, setPendingId] = useState<string | null>(null)
  useEffect(() => setPendingId(null), [id])

  // Global Synchronization (Doc 11): whichever strategy this page lands on
  // (direct link or in-page switch) becomes the shared selection, so the
  // /strategies list and Dashboard reflect it on the next visit.
  const setSyncedStrategyId = useSyncStore((s) => s.setSelectedStrategyId)
  useEffect(() => setSyncedStrategyId(id), [id, setSyncedStrategyId])

  const select = (nextId: string) => {
    if (nextId === id) return
    setPendingId(nextId)
    router.push(`/strategies/${nextId}`)
  }

  return (
    <div className="space-y-6">
      {/* Header: back link + selector */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link href="/strategies" className="text-sm text-fg-muted transition-colors hover:text-fg">
            ← Strategies
          </Link>
          <span className="text-fg-subtle">/</span>
          <span className="text-sm font-medium text-fg">Detail</span>
        </div>
        {strategiesQuery.isSuccess && strategies.length > 0 && (
          <StrategySelector strategies={strategies} current={strategy} onSelect={select} />
        )}
      </div>

      {strategiesQuery.isLoading && <DetailSkeleton />}
      {strategiesQuery.isError && (
        <ErrorState description="Could not load strategies." onRetry={() => strategiesQuery.refetch()} />
      )}
      {strategiesQuery.isSuccess && !strategy && !pendingId && (
        <EmptyState
          icon={<Brain size={20} />}
          title="Strategy not found"
          description="No strategy with this id is registered. Pick one from the selector above."
        />
      )}

      {/* While switching, show the skeleton (not the previous strategy). */}
      {pendingId && <DetailSkeleton />}

      {!pendingId && strategy && (
        // key on id -> the whole content region remounts with a fade on switch.
        <div key={strategy.id} className="animate-fade-in space-y-6">
          <StrategyDetailBody strategy={strategy} />
        </div>
      )}
    </div>
  )
}

function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="skeleton h-24 w-full" />
      <div className="flex gap-2.5">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="skeleton h-9 w-32 shrink-0 rounded-full" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[3fr_2fr]">
        <div className="skeleton h-80" />
        <div className="skeleton h-80" />
      </div>
      <div className="skeleton h-64 w-full" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="skeleton h-56" />
        <div className="skeleton h-56" />
      </div>
    </div>
  )
}

// ── Section 1: real-data stat pill strip — horizontal scroll, one pill per
//    headline metric (Status, Total Signals, Valid Rate, Backtest Return,
//    Last Signal), matching the reference's Voltrex asset-pill styling. ──
function StatPill({
  icon,
  label,
  value,
  tone = 'default',
}: {
  icon: React.ReactNode
  label: string
  value: React.ReactNode
  tone?: 'default' | 'profit' | 'risk'
}) {
  return (
    <div className="flex shrink-0 items-center gap-2 rounded-full border border-border/60 bg-surface-raised/50 px-3.5 py-2 backdrop-blur-sm">
      <span className="text-fg-subtle">{icon}</span>
      <span className="text-[10px] font-medium uppercase tracking-wider text-fg-subtle">{label}</span>
      <span
        className={cn(
          'font-mono text-xs font-semibold tabular-nums',
          tone === 'profit' ? 'text-profit' : tone === 'risk' ? 'text-risk' : 'text-fg',
        )}
      >
        {value}
      </span>
    </div>
  )
}

function StatPillStrip({
  strategy,
  totalSignals,
  validity,
  latest,
  latestSignal,
}: {
  strategy: Strategy
  totalSignals: number
  validity: number
  latest: import('../types').Backtest | null
  latestSignal: Signal | null
}) {
  const active = strategy.status.toUpperCase() === 'ACTIVE'
  const ret = latest?.total_return != null ? Number.parseFloat(latest.total_return) : null
  return (
    <div className="flex gap-2.5 overflow-x-auto pb-1">
      <StatPill icon={<Zap size={13} />} label="Status" value={strategy.status} tone={active ? 'profit' : 'default'} />
      <StatPill icon={<Activity size={13} />} label="Total signals" value={totalSignals} />
      <StatPill icon={<Percent size={13} />} label="Valid rate" value={`${Math.round(validity * 100)}%`} tone="profit" />
      <StatPill
        icon={<Target size={13} />}
        label="Backtest return"
        value={fmtReturnPct(latest?.total_return ?? null)}
        tone={ret == null ? 'default' : ret >= 0 ? 'profit' : 'risk'}
      />
      <StatPill icon={<Clock size={13} />} label="Last signal" value={latestSignal ? fmtTime(latestSignal.ts) : '—'} />
    </div>
  )
}

function StrategyDetailBody({ strategy }: { strategy: Strategy }) {
  const signalsQuery = useSignals(strategy.id, SIGNAL_HISTORY_LIMIT)
  const backtestsQuery = useBacktests(strategy.id)
  const metricsQuery = useStrategyMetrics(strategy.id)
  const metrics = metricsQuery.data
  const signals = signalsQuery.data ?? []
  const backtests = backtestsQuery.data ?? []
  const latest = backtests[0] ?? null

  const ordered = [...signals].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime())
  const points = ordered.map((s) => ({ label: fmtTime(s.ts), value: Number.parseFloat(s.value) }))
  const signalValues = signals.map((s) => Number.parseFloat(s.value))
  const validCount = signals.filter((s) => s.validation_status.toUpperCase() === 'VALID').length
  const validity = signals.length ? validCount / signals.length : 0
  const avgConviction = signalValues.length ? signalValues.reduce((a, b) => a + b, 0) / signalValues.length : null
  const latestSignal = ordered.at(-1) ?? null
  const indicator = indicatorSeries(signals)
  const results = latest?.results ?? null
  const fillRate = results && results.orders_created > 0 ? results.orders_filled / results.orders_created : null
  const reference = isReferenceStrategy(strategy.name)

  const monthlyReturnsQuery = useMonthlyReturns(strategy.id)
  const monthlyRows = monthlyReturnsQuery.data ?? []
  // Prefer the REAL realized-P&L calendar (server-side, from executions);
  // fall back to the signal-mean proxy only when no execution history exists.
  const monthlyPnl = useMemo(() => monthlyReturnsGrid(monthlyRows), [monthlyRows])
  const monthlyProxy = useMemo(() => monthlyConvictionGrid(signals), [signals])
  const monthlyIsPnl = monthlyPnl.years.length > 0
  const monthly = monthlyIsPnl ? monthlyPnl : monthlyProxy
  const timelinePoints = useMemo(() => signalPoints(signals), [signals])
  const runs = useMemo(() => consecutiveRuns(signals), [signals])

  const tradeCount = latest?.trade_count ?? results?.trade_count ?? null
  const retNum = latest?.total_return != null ? Number.parseFloat(latest.total_return) : null
  const [capital, setCapital] = useSimCapital(strategy.id)

  return (
    <>
      {/* ── Section 1: title + real-data pill strip + simulated capital ── */}
      <Panel className="space-y-4 p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="truncate text-lg font-semibold tracking-tight text-fg">{strategy.name}</h1>
              <Badge variant={statusVariant(strategy.status)}>{strategy.status}</Badge>
              {reference && (
                <Badge variant="warning" title={REFERENCE_TOOLTIP}>
                  {REFERENCE_BADGE}
                </Badge>
              )}
            </div>
            <p className="mt-1 text-sm text-fg-muted">
              {strategy.description ?? (reference ? REFERENCE_CAPTION : 'No description.')} · <span className="font-mono">v{strategy.version}</span>
            </p>
          </div>
          <SimCapitalInput capital={capital} onChange={setCapital} />
        </div>
        <StatPillStrip strategy={strategy} totalSignals={signals.length} validity={validity} latest={latest} latestSignal={latestSignal} />
      </Panel>

      {/* ── Multi-asset backtest view (owner request): the strategy page's
          default backtest presentation — never a single asset only. ── */}
      <MultiAssetBacktestSection strategy={strategy} capital={capital} />

      {/* ── ML Intelligence — prominent, placed right after the header per
          owner request (see MLIntelligence.tsx's module docstring for why
          this is a Section rather than a page-wide tab). ── */}
      <MLIntelligenceSection signals={signals} symbol={typeof strategy.config?.symbol === 'string' ? (strategy.config.symbol as string) : null} capital={capital} />

      {/* ── Section 2: equity/conviction curve (60%) + performance metrics grid (40%) ── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[3fr_2fr]">
        <Section
          icon={<LineChartIcon size={16} />}
          title="Equity curve"
          description="Signed Alpha Score over time — an honest equity proxy (per-step P&L isn't tracked yet). Green above zero, red drawdown shading below."
        >
          <Panel className="p-4">
            {signalsQuery.isLoading ? (
              <div className="skeleton h-[320px] w-full" />
            ) : (
              <>
                <ConvictionEquityChart points={points} height={320} />
                {(latest?.total_return != null || (latest?.start_date && latest?.end_date)) && (
                  <div className="mt-3 flex flex-wrap justify-end gap-2">
                    {latest?.start_date && latest?.end_date && (
                      <Badge variant="neutral">
                        Backtest period · {fmtDate(latest.start_date)} → {fmtDate(latest.end_date)}
                      </Badge>
                    )}
                    {latest?.total_return != null && (
                      <Badge variant={retNum != null && retNum >= 0 ? 'profit' : 'risk'}>
                        Latest backtest return · {fmtReturnPct(latest.total_return)}
                      </Badge>
                    )}
                  </div>
                )}
              </>
            )}
          </Panel>
        </Section>

        <Section icon={<GaugeIcon size={16} />} title="Performance metrics" description="Real where computable; honestly deferred otherwise.">
          <Panel className="grid grid-cols-2 gap-3 p-4">
            {metrics?.win_rate != null ? (
              <RealRingTile label="Win rate" value={Number.parseFloat(metrics.win_rate)} />
            ) : (
              <PendingMetricTile label="Win rate" shell="ring" />
            )}
            {metrics?.sharpe_ratio != null ? (
              <RealMetricTile label="Sharpe ratio" value={formatSharpe(Number.parseFloat(metrics.sharpe_ratio))} />
            ) : (
              <PendingMetricTile label="Sharpe ratio" shell="number" />
            )}
            {metrics?.max_drawdown_pct != null ? (
              <RealMetricTile
                label="Max drawdown"
                value={formatMaxDrawdownPct(Number.parseFloat(metrics.max_drawdown_pct))}
                tone="risk"
              />
            ) : (
              <PendingMetricTile label="Max drawdown" shell="bar" />
            )}
            <RealMetricTile icon={<Activity size={11} />} label="Total signals" value={signals.length} />
            <RealRingTile label="Valid rate" value={validity} hint={`${validCount}/${signals.length}`} />
            <RealMetricTile icon={<Hash size={11} />} label="Trade count" value={tradeCount ?? '—'} />
            {metrics?.profit_factor != null ? (
              <RealMetricTile label="Profit factor" value={Number.parseFloat(metrics.profit_factor).toFixed(2)} />
            ) : (
              <PendingMetricTile label="Profit factor" shell="number" />
            )}
            <BacktestReturnTile
              label="Backtest return"
              valueText={fmtReturnPct(latest?.total_return ?? null)}
              positive={retNum == null ? null : retNum >= 0}
              sparkline={points.map((p) => p.value)}
              hint={latest ? 'latest run' : 'no backtest yet'}
            />
          </Panel>
        </Section>
      </div>

      {/* ── Section 3: monthly signal performance heatmap (full width) ── */}
      <Section
        icon={<CalendarRange size={16} />}
        title={monthlyIsPnl ? 'Monthly realized P&L' : 'Monthly signal performance'}
        description={
          monthlyIsPnl
            ? 'Realized trading P&L per calendar month, aggregated from this strategy’s real executions.'
            : 'Average signed Alpha Score by month — an honest proxy for strategy lean, not a realized P&L calendar.'
        }
      >
        <Panel className="p-4">
          {signalsQuery.isLoading || monthlyReturnsQuery.isLoading ? (
            <div className="skeleton h-[240px] w-full" />
          ) : monthly.years.length === 0 ? (
            <div className="flex h-[200px] items-center justify-center text-sm text-fg-muted">Not enough signals to build a monthly grid yet.</div>
          ) : (
            <Heatmap
              xLabels={monthly.months}
              yLabels={monthly.years}
              values={monthly.grid}
              mode="diverging"
              min={-monthly.maxAbs}
              max={monthly.maxAbs}
              // Vivid P&L palette (owner request): #FF1744 loss → dark
              // neutral → #00C853 gain; white labels for readability.
              colors={['#FF1744', '#1a1a2e', '#00C853']}
              labelColor="#ffffff"
              height={Math.max(180, monthly.years.length * 70 + 90)}
              valueFormat={(v) => (monthlyIsPnl ? fmtMoney(String(v)) : formatSignalStrength(v))}
            />
          )}
        </Panel>
      </Section>

      {/* ── Section 4: signal intelligence — distribution + timeline scatter ── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Section
          icon={<BarChart3 size={16} />}
          title="Signal strength distribution"
          description="How this strategy's signal strength is spread — red below zero, green above."
        >
          <Panel className="p-4">
            {signalsQuery.isLoading ? (
              <div className="skeleton h-[200px] w-full" />
            ) : signalValues.length >= 2 ? (
              <>
                <SignalStrengthDistributionChart values={signalValues} height={200} />
                <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-[11px] text-fg-subtle">
                  <span>min <span className="font-mono text-fg-muted">{fmtSignal(String(signalValues.reduce((a, b) => Math.min(a, b), Infinity)))}</span></span>
                  <span>median <span className="font-mono text-fg-muted">{fmtSignal(String(median(signalValues)))}</span></span>
                  <span>max <span className="font-mono text-fg-muted">{fmtSignal(String(signalValues.reduce((a, b) => Math.max(a, b), -Infinity)))}</span></span>
                  <span>mean <span className="font-mono text-fg-muted">{avgConviction != null ? fmtSignal(String(avgConviction)) : '—'}</span></span>
                </div>
              </>
            ) : (
              <div className="flex h-[200px] items-center justify-center text-sm text-fg-muted">Not enough signals to show a distribution yet.</div>
            )}
          </Panel>
        </Section>

        <Section icon={<Waves size={16} />} title="Signal timeline" description="Every recorded signal — color by direction, size by magnitude.">
          <Panel className="p-4">
            {signalsQuery.isLoading ? <div className="skeleton h-[260px] w-full" /> : <SignalTimelineScatter points={timelinePoints} height={260} />}
          </Panel>
        </Section>
      </div>

      {/* Strategy indicators — real recorded metadata series (kept from the prior
          layout; the new spec doesn't remove it and it's genuine data). */}
      <Section icon={<LineChartIcon size={16} />} title="Strategy indicators" description="The numeric series this strategy records with each signal, over time.">
        <Panel className="p-4">
          {signalsQuery.isLoading ? (
            <div className="skeleton h-[240px] w-full" />
          ) : indicator.series.length > 0 ? (
            <MultiLineChart labels={indicator.labels} series={indicator.series} height={240} />
          ) : (
            <div className="flex h-[240px] flex-col items-center justify-center gap-1 px-6 text-center text-sm text-fg-muted">
              <LineChartIcon size={18} className="text-fg-subtle" />
              This strategy&apos;s signals don&apos;t carry an indicator series to overlay.
            </div>
          )}
        </Panel>
      </Section>

      {/* ── Section 5: backtest analytics ── */}
      <OrderFlow query={backtestsQuery} results={results} fillRate={fillRate} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <TradePnlDistributionSection strategyId={strategy.id} />

        <Section
          icon={<Activity size={16} />}
          title="Consecutive signal direction"
          description="Streaks of same-direction signals, time-ordered — computed purely from signal sign."
        >
          <Panel className="p-4">
            {signalsQuery.isLoading ? <div className="skeleton h-[220px] w-full" /> : <ConsecutiveRunsChart runs={runs} height={220} />}
          </Panel>
        </Section>
      </div>

      {/* ── Section 6: strategy configuration + metadata ── */}
      <Section icon={<TerminalSquare size={16} />} title="Strategy configuration" description="Registered configuration and metadata for this strategy.">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <ConfigChipsCard strategy={strategy} />
          <StrategyMetadataCard strategy={strategy} />
        </div>
      </Section>

      {/* Full run history — Doc 06 "Backtest Analytics": every run, not just
          the latest, browsable in place (no navigating away from the workspace). */}
      <Section
        title="Backtest runs"
        description="Every backtest recorded for this strategy."
        actions={backtestsQuery.isSuccess ? <Badge variant="neutral">{backtests.length}</Badge> : null}
      >
        {backtestsQuery.isLoading && <SkeletonTable rows={3} cols={5} />}
        {backtestsQuery.isError && <ErrorState description="Could not load backtests." onRetry={() => backtestsQuery.refetch()} />}
        {backtestsQuery.isSuccess && backtests.length === 0 && (
          <EmptyState title="No backtests" description="This strategy has no backtest runs." />
        )}
        {backtestsQuery.isSuccess && backtests.length > 0 && <BacktestRunCards backtests={backtests} />}
      </Section>

      {/* Market Analytics — real instrument context. (Risk Analytics
          removed permanently, owner request: per-strategy risk attribution
          belongs to the Risk workspace, not a deferred card here.) */}
      <MarketContext symbol={typeof strategy.config?.symbol === 'string' ? (strategy.config.symbol as string) : null} />

      {/* Signals grouped by source (owner request): live signals emitted
          since the strategy was registered vs historical backtest-replay
          signals — never mixed without context. */}
      <GroupedSignals
        query={signalsQuery}
        signals={signals}
        strategy={strategy}
        symbol={typeof strategy.config?.symbol === 'string' ? (strategy.config.symbol as string) : null}
      />
    </>
  )
}

// ── Section 6a: config parameters as labeled chips (kept from the prior
//    layout, relocated into the dedicated configuration section). ──
function ConfigChipsCard({ strategy }: { strategy: Strategy }) {
  const config = Object.entries(strategy.config)
  return (
    <Panel className="p-5">
      <div className="mb-3 flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-fg-subtle">
        <TerminalSquare size={13} /> Configuration
      </div>
      {config.length === 0 ? (
        <p className="text-sm text-fg-muted">No configuration parameters.</p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {config.map(([k, v]) => (
            <span key={k} className="rounded-md border border-border bg-surface px-2 py-1 font-mono text-[11px] text-fg-muted">
              <span className="text-fg-subtle">{k}</span>=<span className="text-fg">{String(v)}</span>
            </span>
          ))}
        </div>
      )}
      <p className="mt-4 border-t border-border pt-3 text-[11px] leading-relaxed text-fg-subtle">
        Shows the current registration only — version history and rollback aren&apos;t available yet. Configuration
        is owned by the strategy and shown exactly as registered.
      </p>
    </Panel>
  )
}

// ── Section 6b: strategy metadata card — description, version, registered
//    date, last modified. Clean glass card, not a settings form. ──
function StrategyMetadataCard({ strategy }: { strategy: Strategy }) {
  return (
    <Panel className="space-y-3 p-5">
      <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-fg-subtle">
        <FileText size={13} /> Metadata
      </div>
      <p className="text-sm leading-relaxed text-fg-muted">
        {strategy.description ?? 'No description registered for this strategy.'}
      </p>
      <div className="space-y-2 border-t border-border pt-3 text-sm">
        <Meta label="Version" value={<span className="font-mono text-fg">v{strategy.version}</span>} />
        <Meta label="Status" value={<Badge variant={statusVariant(strategy.status)}>{strategy.status}</Badge>} />
        <Meta
          label="Registered"
          value={
            <span className="flex items-center gap-1.5 font-mono text-fg-muted">
              <CalendarClock size={12} className="text-fg-subtle" /> {fmtDate(strategy.created_at)}
            </span>
          }
        />
        <Meta label="Last modified" value={<span className="font-mono text-fg-muted">{fmtDate(strategy.updated_at)}</span>} />
      </div>
    </Panel>
  )
}

// ── Market Analytics: the strategy's configured instrument, real price/24h
//    change from the same feed Markets renders — ties Strategy ↔ Market
//    together as one connected surface (VE_16) instead of an isolated card. ──
function MarketContext({ symbol }: { symbol: string | null }) {
  const assetsQuery = useAssets()
  const assets = assetsQuery.data ?? []
  const asset = symbol ? assets.find((a) => a.symbol === symbol) : undefined
  const barsQuery = useBars(asset?.id ?? '', '1h')
  const bars = barsQuery.data ?? []
  const last = bars.at(-1)
  const prev = bars.at(-2)
  const change = last && prev ? Number.parseFloat(last.close) - Number.parseFloat(prev.close) : null
  const changePct = change != null && prev ? (change / Number.parseFloat(prev.close)) * 100 : null

  return (
    <Section
      title="Market context"
      description={
        symbol
          ? `Strategy instrument: ${symbol} — live from the same feed Markets renders. Only this instrument shows because it's the one this strategy trades.`
          : "The strategy's configured instrument, live from the same feed Markets renders."
      }
    >
      <Panel className="p-5">
        {!symbol ? (
          <div className="flex h-24 items-center justify-center text-sm text-fg-muted">
            This strategy&apos;s configuration doesn&apos;t name a single symbol.
          </div>
        ) : assetsQuery.isLoading || barsQuery.isLoading ? (
          <div className="skeleton h-24 w-full" />
        ) : !asset ? (
          <div className="flex h-24 items-center justify-center text-sm text-fg-muted">
            {symbol} isn&apos;t a registered instrument yet.
          </div>
        ) : (
          <div className="flex items-center gap-4">
            <CryptoIcon symbol={asset.symbol} size={32} />
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium text-fg">{asset.symbol}</div>
              <div className="text-[11px] uppercase tracking-wide text-fg-subtle">{asset.exchange} · 1h</div>
            </div>
            {last ? (
              <div className="text-right">
                <div className="font-mono text-lg font-semibold tabular-nums text-fg">
                  {Number.parseFloat(last.close).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
                {changePct != null && (
                  <div className={cn('font-mono text-xs tabular-nums', change! >= 0 ? 'text-profit' : 'text-risk')}>
                    {formatReturn(changePct / 100)}
                  </div>
                )}
              </div>
            ) : (
              <span className="text-xs text-fg-subtle">no bars yet</span>
            )}
          </div>
        )}
      </Panel>
    </Section>
  )
}

function Meta({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-fg-subtle">{label}</span>
      {value}
    </div>
  )
}

// Signals grouped by source (owner request): "live" = emitted at-or-after the
// strategy's registration timestamp (the strategy was actually running);
// "backtest" = historical replay timestamps before registration. Deterministic
// rule from real fields, no heuristics on gaps.
function GroupedSignals({
  query,
  signals,
  strategy,
  symbol,
}: {
  query: ReturnType<typeof useSignals>
  signals: Signal[]
  strategy: Strategy
  symbol: string | null
}) {
  const registeredAt = strategy.created_at ? new Date(strategy.created_at).getTime() : null
  const ordered = [...signals].sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime())
  const live = registeredAt != null ? ordered.filter((s) => new Date(s.ts).getTime() >= registeredAt) : []
  const backtest = registeredAt != null ? ordered.filter((s) => new Date(s.ts).getTime() < registeredAt) : ordered
  const fmtRange = (xs: Signal[]) => {
    if (xs.length === 0) return null
    const f = (ts: string) => new Date(ts).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
    const newest = f(xs[0].ts)
    const oldest = f(xs[xs.length - 1].ts)
    return newest === oldest ? newest : `${oldest} – ${newest}`
  }

  if (query.isLoading) return <div className="rounded-xl border border-border/60 p-4"><SkeletonTable rows={5} cols={3} /></div>
  if (query.isError) return <ErrorState description="Could not load signals." onRetry={() => query.refetch()} />
  if (signals.length === 0)
    return (
      <Panel className="p-6"><EmptyState icon={<ListChecks size={20} />} title="No signals" description="This strategy has emitted no signals yet." /></Panel>
    )

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Section
        title="Live signals"
        description={`Signals emitted since this strategy was registered (${fmtDate(strategy.created_at)}).`}
        actions={<Badge variant="profit">{live.length}</Badge>}
      >
        {live.length === 0 ? (
          <Panel className="p-6"><EmptyState title="No live signals yet" description="Nothing emitted since registration — everything below is backtest replay." /></Panel>
        ) : (
          <RecentSignalRows signals={live.slice(0, 8)} symbol={symbol} />
        )}
      </Section>
      <Section
        title="Backtest signals"
        description={backtest.length > 0 ? `Historical simulation signals — ${fmtRange(backtest)} period.` : 'Historical simulation signals.'}
        actions={<Badge variant="neutral">{backtest.length}</Badge>}
      >
        {backtest.length === 0 ? (
          <Panel className="p-6"><EmptyState title="No backtest signals" description="No replay signals recorded." /></Panel>
        ) : (
          <RecentSignalRows signals={backtest.slice(0, 8)} symbol={symbol} />
        )}
      </Section>
    </div>
  )
}

// Real backtest order flow: created → filled → rejected, as proportion bars,
// plus the run's realized / unrealized P&L. Every figure is a literal count or
// amount from the backtest results — never fabricated; no run ⇒ honest state.
function FlowBar({ label, value, total, tone }: { label: string; value: number; total: number; tone: 'info' | 'profit' | 'risk' }) {
  const pct = total > 0 ? (value / total) * 100 : 0
  const bar = tone === 'profit' ? 'bg-profit' : tone === 'risk' ? 'bg-risk' : 'bg-info'
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-fg-muted">{label}</span>
        <span className="font-mono tabular-nums text-fg">{value} <span className="text-fg-subtle">· {Math.round(pct)}%</span></span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-surface">
        <motion.div
          className={cn('h-full rounded-full', bar)}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: EASE_OUT }}
        />
      </div>
    </div>
  )
}

function OrderFlow({
  query,
  results,
  fillRate,
}: {
  query: ReturnType<typeof useBacktests>
  results: import('../types').BacktestResults | null
  fillRate: number | null
}) {
  const rpnl = results ? Number.parseFloat(results.realized_pnl) : 0
  const upnl = results ? Number.parseFloat(results.unrealized_pnl) : 0
  return (
    <Section icon={<Zap size={16} />} title="Backtest order flow" description="What the latest backtest run did with its orders — created, filled and rejected.">
      <Panel className="p-5">
        {query.isLoading ? (
          <div className="skeleton h-28 w-full" />
        ) : !results ? (
          <div className="flex h-28 items-center justify-center text-sm text-fg-muted">No backtest run yet — nothing to break down.</div>
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_18rem]">
            <div className="space-y-3.5">
              <FlowBar label="Created" value={results.orders_created} total={results.orders_created} tone="info" />
              <FlowBar label="Filled" value={results.orders_filled} total={results.orders_created} tone="profit" />
              <FlowBar label="Rejected" value={results.orders_rejected} total={results.orders_created} tone="risk" />
            </div>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-1">
              <StatCard icon={<Activity size={13} />} label="Realized P&L" value={fmtMoney(results.realized_pnl)} tone={rpnl >= 0 ? 'profit' : 'risk'} hint="closed positions" />
              <StatCard icon={<GaugeIcon size={13} />} label="Unrealized P&L" value={fmtMoney(results.unrealized_pnl)} tone={upnl >= 0 ? 'profit' : 'risk'} hint="open at run end" />
              {fillRate != null && (
                <StatCard icon={<Percent size={13} />} label="Fill rate" value={`${Math.round(fillRate * 100)}%`} hint={`${results.orders_filled} of ${results.orders_created} orders`} />
              )}
            </div>
          </div>
        )}
      </Panel>
    </Section>
  )
}
