// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout / §Data Visualization / §Interaction Standards.
// Doc 08 — Frontend Architecture (QH-008) §Architecture / §State Management.
// Doc 14 §10.2 Strategy Governance (§10.2.5 versioning F-9), §10.6.4 Signal
//   Recording, §10.3 Backtesting. Doc 15 §11.1.5 (signal value = conviction).
// Doc 00 §14.5/§14.7 — DATA HONESTY. Per Doc 00 §14.11
//
// Dedicated strategy detail page (owner request, points 7–8) at
// /strategies/[id]: a large primary chart, a side metadata panel (F-9 honest),
// supporting widgets from real data, and a top strategy SELECTOR whose dropdown
// slides down from the top and switches ALL page content to the chosen
// strategy (with a loading transition — nothing stays static).
'use client'

import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  Activity,
  BarChart3,
  Brain,
  Check,
  ChevronDown,
  Clock,
  Gauge,
  LineChart as LineChartIcon,
  ListChecks,
  Target,
  TerminalSquare,
} from 'lucide-react'
import {
  Badge,
  EmptyState,
  ErrorState,
  Histogram,
  LineChart,
  MultiLineChart,
  Panel,
  Ring,
  Section,
  SkeletonTable,
  StatCard,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  pnlBadgeVariant,
  type BadgeVariant,
  type LinePoint,
  type Series,
} from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { EASE_OUT } from '@/lib/motion'
import { useBacktests, useSignals, useStrategies } from '../hooks/useStrategies'
import type { Signal, Strategy } from '../types'
import { isReferenceStrategy, REFERENCE_BADGE, REFERENCE_CAPTION, REFERENCE_TOOLTIP } from '../labels'

const fmtReturnPct = (v: string | null) => (v === null ? '—' : `${(Number.parseFloat(v) * 100).toFixed(4)}%`)
const fmtMoney = (v: string | null) =>
  v === null ? '—' : Number.parseFloat(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const fmtSignal = (v: string) => {
  const n = Number.parseFloat(v)
  const s = n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 8 })
  return n > 0 ? `+${s}` : s
}
const fmtTime = (ts: string) => new Date(ts).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

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
      <div className="skeleton h-20 w-full" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_20rem]">
        <div className="skeleton h-80" />
        <div className="skeleton h-80" />
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="skeleton h-56" />
        <div className="skeleton h-56" />
      </div>
    </div>
  )
}

function StrategyDetailBody({ strategy }: { strategy: Strategy }) {
  const signalsQuery = useSignals(strategy.id)
  const backtestsQuery = useBacktests(strategy.id)
  const signals = signalsQuery.data ?? []
  const backtests = backtestsQuery.data ?? []
  const latest = backtests[0] ?? null

  const ordered = [...signals].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime())
  const points: LinePoint[] = ordered.map((s) => ({ label: fmtTime(s.ts), value: Number.parseFloat(s.value) }))
  const signalValues = signals.map((s) => Number.parseFloat(s.value))
  const validCount = signals.filter((s) => s.validation_status.toUpperCase() === 'VALID').length
  const validity = signals.length ? validCount / signals.length : 0
  const avgConviction = signalValues.length ? signalValues.reduce((a, b) => a + b, 0) / signalValues.length : null
  const latestSignal = ordered.at(-1) ?? null
  const indicator = indicatorSeries(signals)
  const results = latest?.results ?? null
  const fillRate = results && results.orders_created > 0 ? results.orders_filled / results.orders_created : null
  const reference = isReferenceStrategy(strategy.name)
  const active = strategy.status.toUpperCase() === 'ACTIVE'

  return (
    <>
      {/* Title row */}
      <Panel className="flex flex-wrap items-start justify-between gap-4 p-5">
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
        <div className="flex gap-3">
          <StatCard icon={<BarChart3 size={13} />} label="Recent signals" value={signals.length} />
          <StatCard icon={<Target size={13} />} label="Backtest return" value={latest ? fmtReturnPct(latest.total_return) : '—'} tone={latest?.total_return ? (Number.parseFloat(latest.total_return) >= 0 ? 'profit' : 'risk') : 'default'} />
        </div>
      </Panel>

      {/* Real-data metric strip — distinct icon per metric, every value computed
          from real signals/backtest results (no fabricated figures). */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-5">
        <StatCard icon={<Activity size={13} />} label="Signals" value={signals.length} hint="recorded events" />
        <StatCard
          icon={<Gauge size={13} />}
          label="Avg conviction"
          value={avgConviction != null ? fmtSignal(String(avgConviction)) : '—'}
          tone={avgConviction != null ? (avgConviction >= 0 ? 'profit' : 'risk') : 'default'}
          hint="mean signal value"
        />
        <StatCard icon={<Check size={13} />} label="Valid rate" value={`${Math.round(validity * 100)}%`} tone="profit" hint={`${validCount} of ${signals.length}`} />
        <StatCard
          icon={<Target size={13} />}
          label="Fill rate"
          value={fillRate != null ? `${Math.round(fillRate * 100)}%` : '—'}
          hint={results ? `${results.orders_filled} of ${results.orders_created} orders` : 'no backtest'}
        />
        <StatCard icon={<Clock size={13} />} label="Latest signal" value={latestSignal ? fmtTime(latestSignal.ts) : '—'} hint={latestSignal ? 'most recent' : 'none yet'} />
      </div>

      {/* Primary chart + metadata panel */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_20rem]">
        <Section title="Conviction curve" description="Signed conviction over time — the value each signal contributes to position sizing.">
          <Panel className="p-4">
            {signalsQuery.isLoading ? (
              <div className="skeleton h-[280px] w-full" />
            ) : points.length >= 2 ? (
              <LineChart data={points} tone="info" zeroBaseline height={280} />
            ) : (
              <div className="flex h-[280px] items-center justify-center text-sm text-fg-muted">Not enough signals to plot a curve yet.</div>
            )}
          </Panel>
        </Section>

        <MetadataPanel strategy={strategy} validity={validity} validCount={validCount} total={signals.length} active={active} />
      </div>

      {/* Distribution + indicator overlay (real data; honest states otherwise) */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Section title="Conviction distribution" description="How this strategy's signal values are spread — red below zero, green above.">
          <Panel className="p-4">
            {signalsQuery.isLoading ? (
              <div className="skeleton h-[200px] w-full" />
            ) : signalValues.length >= 2 ? (
              <>
                <Histogram values={signalValues} height={200} />
                <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-[11px] text-fg-subtle">
                  <span>min <span className="font-mono text-fg-muted">{fmtSignal(String(Math.min(...signalValues)))}</span></span>
                  <span>median <span className="font-mono text-fg-muted">{fmtSignal(String(median(signalValues)))}</span></span>
                  <span>max <span className="font-mono text-fg-muted">{fmtSignal(String(Math.max(...signalValues)))}</span></span>
                </div>
              </>
            ) : (
              <div className="flex h-[200px] items-center justify-center text-sm text-fg-muted">Not enough signals to show a distribution yet.</div>
            )}
          </Panel>
        </Section>

        <Section title="Indicator overlay" description="The numeric series this strategy records with each signal, over time.">
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
      </div>

      {/* Backtest order flow — real counts from the latest backtest run */}
      <OrderFlow query={backtestsQuery} results={results} />


      {/* Supporting widgets */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RecentSignals query={signalsQuery} signals={signals} />
        <BacktestPanel query={backtestsQuery} latest={latest} count={backtests.length} />
      </div>
    </>
  )
}

function MetadataPanel({
  strategy,
  validity,
  validCount,
  total,
  active,
}: {
  strategy: Strategy
  validity: number
  validCount: number
  total: number
  active: boolean
}) {
  const config = Object.entries(strategy.config)
  return (
    <Panel className="space-y-4 p-5">
      <div className="flex flex-col items-center gap-1.5">
        <Ring value={validity} tone="profit" centerLabel={`${Math.round(validity * 100)}%`} centerSub="valid" />
        <p className="text-xs text-fg-muted">Signal validity rate</p>
        <p className="text-[11px] text-fg-subtle">{validCount} of {total} recent</p>
      </div>

      <div className="space-y-2.5 border-t border-border pt-4 text-sm">
        <Meta label="Status" value={<Badge variant={statusVariant(strategy.status)}>{strategy.status}</Badge>} />
        <Meta label="Version" value={<span className="font-mono text-fg">v{strategy.version}</span>} />
        <Meta label="Engaged" value={<span className="text-fg-muted">{active ? 'emitting signals' : 'inactive'}</span>} />
      </div>

      <div className="border-t border-border pt-4">
        <div className="mb-2 flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-fg-subtle">
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
      </div>

      <p className="border-t border-border pt-3 text-[11px] leading-relaxed text-fg-subtle">
        Shows the current registration only — version history and rollback aren&apos;t available yet. Configuration is owned by the strategy and shown exactly as registered.
      </p>
    </Panel>
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

function RecentSignals({ query, signals }: { query: ReturnType<typeof useSignals>; signals: Signal[] }) {
  const recent = [...signals].sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime()).slice(0, 8)
  return (
    <Section
      title="Recent signals"
      description="Most recent signals emitted by this strategy."
      actions={query.isSuccess ? <Badge variant="neutral">{signals.length}</Badge> : null}
    >
      <Panel className="overflow-hidden">
        {query.isLoading && <div className="p-4"><SkeletonTable rows={5} cols={3} /></div>}
        {query.isError && <div className="p-4"><ErrorState description="Could not load signals." onRetry={() => query.refetch()} /></div>}
        {query.isSuccess && recent.length === 0 && <div className="p-6"><EmptyState icon={<ListChecks size={20} />} title="No signals" description="This strategy has emitted no signals yet." /></div>}
        {query.isSuccess && recent.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow><TableHead>Time</TableHead><TableHead>Conviction</TableHead><TableHead>Validation</TableHead></TableRow>
            </TableHeader>
            <TableBody>
              {recent.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="whitespace-nowrap text-fg-muted">{fmtTime(s.ts)}</TableCell>
                  <TableCell numeric><Badge variant={pnlBadgeVariant(Number.parseFloat(s.value))}>{fmtSignal(s.value)}</Badge></TableCell>
                  <TableCell><Badge variant={s.validation_status === 'VALID' ? 'profit' : 'warning'}>{s.validation_status}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Panel>
    </Section>
  )
}

function BacktestPanel({
  query,
  latest,
  count,
}: {
  query: ReturnType<typeof useBacktests>
  latest: import('../types').Backtest | null
  count: number
}) {
  return (
    <Section
      title="Backtest results"
      description="Results from replaying this strategy over historical data."
      actions={query.isSuccess ? <Badge variant="neutral">{count}</Badge> : null}
    >
      {query.isLoading && <div className="skeleton h-40 w-full" />}
      {query.isError && <ErrorState description="Could not load backtests." onRetry={() => query.refetch()} />}
      {query.isSuccess && !latest && (
        <Panel className="p-6">
          <EmptyState title="No backtest runs" description="This strategy has no backtest yet — return/fills are shown as “—”, never fabricated." />
        </Panel>
      )}
      {latest && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <StatCard label="Total return" value={fmtReturnPct(latest.total_return)} tone={latest.total_return && Number.parseFloat(latest.total_return) >= 0 ? 'profit' : 'risk'} />
            <StatCard label="Fills" value={latest.results?.orders_filled ?? latest.trade_count ?? '—'} />
            <StatCard label="Final capital" value={fmtMoney(latest.final_capital)} />
            <StatCard label="Realized P&L" value={latest.results ? fmtMoney(latest.results.realized_pnl) : '—'} tone={latest.results && Number.parseFloat(latest.results.realized_pnl) >= 0 ? 'profit' : 'risk'} />
          </div>
          {latest.reproducibility_hash && (
            <p className="rounded-lg border border-border bg-surface px-3 py-2 font-mono text-[11px] text-fg-subtle" title={latest.reproducibility_hash}>
              determinism hash · {latest.reproducibility_hash.slice(0, 20)}…
            </p>
          )}
        </div>
      )}
    </Section>
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
}: {
  query: ReturnType<typeof useBacktests>
  results: import('../types').BacktestResults | null
}) {
  const rpnl = results ? Number.parseFloat(results.realized_pnl) : 0
  const upnl = results ? Number.parseFloat(results.unrealized_pnl) : 0
  return (
    <Section title="Backtest order flow" description="What the latest backtest run did with its orders — created, filled and rejected.">
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
              <StatCard icon={<Gauge size={13} />} label="Unrealized P&L" value={fmtMoney(results.unrealized_pnl)} tone={upnl >= 0 ? 'profit' : 'risk'} hint="open at run end" />
            </div>
          </div>
        )}
      </Panel>
    </Section>
  )
}
