// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout / §Data Visualization; §Interaction Standards (governed write).
// Doc 08 — Frontend Architecture (QH-008 v1.0) §Architecture / §State Management.
// Doc 14 §10.2 Strategy Governance (§10.2.5 versioning F-9, §10.2.6 lifecycle),
//   §10.6.4 Signal Recording, §10.3 Backtesting.
// Doc 15 §11.1.5 — the signal `value` is the signed conviction sizing consumes.
// Per Doc 00 §14.11
//
// REDESIGN + FEATURES (owner push): the flat one-table page is restructured
// into a sectioned/tabbed detail (Overview / Performance / Signals / Backtest),
// each with a focused visual — a signal-validity RING, a signed-conviction
// CURVE (LineChart over the signal values that already exist), and the backtest
// results — instead of one long table of everything. Adds the Activate/
// Deactivate control: the first real FRONTEND WRITE (governed §10.2.6
// transition via PATCH /strategies/{id}/status).
//
// HONEST F-9 (unchanged discipline): `version` is the CURRENT registration
// only — no history/rollback is offered because none exists; a caption says so.
'use client'

import { useState } from 'react'
import { Brain, Power } from 'lucide-react'
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  LineChart,
  PageHeader,
  Ring,
  Section,
  SkeletonTable,
  Stat,
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
} from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { useBacktests, useSetStrategyStatus, useSignals, useStrategies } from '../hooks/useStrategies'
import type { Backtest, Signal, Strategy } from '../types'

// ── formatters (display-only; API strings are the source of truth) ──
const fmtReturnPct = (v: string | null) => (v === null ? '—' : `${(Number.parseFloat(v) * 100).toFixed(4)}%`)
const fmtMoney = (v: string | null) =>
  v === null ? '—' : Number.parseFloat(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const fmtSignal = (v: string) => {
  const n = Number.parseFloat(v)
  const s = n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 8 })
  return n > 0 ? `+${s}` : s
}
const fmtTime = (ts: string) =>
  new Date(ts).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

function strategyStatusVariant(status: string): BadgeVariant {
  switch (status.toUpperCase()) {
    case 'ACTIVE':
    case 'LIVE':
      return 'profit'
    case 'PAPER':
      return 'warning'
    case 'INACTIVE':
      return 'neutral'
    default:
      return 'neutral'
  }
}
function backtestStatusVariant(status: string): BadgeVariant {
  switch (status.toUpperCase()) {
    case 'COMPLETED':
      return 'profit'
    case 'RUNNING':
      return 'info'
    case 'FAILED':
      return 'risk'
    default:
      return 'neutral'
  }
}

type TabKey = 'overview' | 'performance' | 'signals' | 'backtest'
const TABS: { key: TabKey; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'performance', label: 'Performance' },
  { key: 'signals', label: 'Signals' },
  { key: 'backtest', label: 'Backtest' },
]

export function StrategiesShell() {
  const strategiesQuery = useStrategies()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const strategies = strategiesQuery.data ?? []
  const activeId = selectedId ?? strategies[0]?.id ?? ''
  const activeStrategy = strategies.find((s) => s.id === activeId) ?? null

  return (
    <div className="space-y-8">
      <PageHeader
        icon={<Brain size={18} />}
        title="Strategies"
        subtitle="Registry, signal feed & backtest results — Phase 2/3 data."
      />

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[19rem_1fr]">
        <Section title="Registry" actions={strategiesQuery.isSuccess ? <Badge variant="neutral">{strategies.length}</Badge> : null}>
          {strategiesQuery.isLoading && <div className="skeleton h-28 w-full" />}
          {strategiesQuery.isError && (
            <ErrorState description="Could not load strategies." onRetry={() => strategiesQuery.refetch()} />
          )}
          {strategiesQuery.isSuccess && strategies.length === 0 && (
            <EmptyState icon={<Brain size={20} />} title="No strategies" description="No strategies are registered yet." />
          )}
          <div className="space-y-1">
            {strategies.map((strategy) => {
              const selected = strategy.id === activeId
              return (
                <button
                  key={strategy.id}
                  onClick={() => setSelectedId(strategy.id)}
                  aria-current={selected ? 'true' : undefined}
                  className={cn(
                    'flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-2.5 text-left transition-colors duration-150',
                    selected
                      ? 'border-accent/40 bg-accent-soft text-accent'
                      : 'border-transparent text-fg-muted hover:bg-surface-hover hover:text-fg',
                  )}
                >
                  <span className="flex min-w-0 flex-col gap-0.5">
                    <span className="truncate text-sm font-medium">{strategy.name}</span>
                    <span className="text-[11px] text-fg-subtle">v{strategy.version}</span>
                  </span>
                  <Badge variant={strategyStatusVariant(strategy.status)}>{strategy.status}</Badge>
                </button>
              )
            })}
          </div>
          {strategiesQuery.isSuccess && strategies.length > 0 && (
            <p className="text-xs leading-relaxed text-fg-subtle">
              Shows the current registration only — version history and rollback aren&apos;t available yet.
            </p>
          )}
        </Section>

        <div className="min-w-0">
          {activeStrategy ? (
            <StrategyDetail strategy={activeStrategy} />
          ) : (
            !strategiesQuery.isLoading &&
            !strategiesQuery.isError && (
              <EmptyState icon={<Brain size={20} />} title="No strategy selected" description="Select a strategy to view its detail." />
            )
          )}
        </div>
      </div>
    </div>
  )
}

function StrategyDetail({ strategy }: { strategy: Strategy }) {
  const [tab, setTab] = useState<TabKey>('overview')
  const signalsQuery = useSignals(strategy.id)
  const backtestsQuery = useBacktests(strategy.id)
  const signals = signalsQuery.data ?? []
  const backtests = backtestsQuery.data ?? []

  return (
    <div className="space-y-6">
      {/* Detail header with the governed Activate/Deactivate write */}
      <div className="flex flex-wrap items-start justify-between gap-4 rounded-xl border border-border-strong bg-surface-raised p-5 shadow-lg">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5">
            <h2 className="truncate text-lg font-semibold tracking-tight text-fg">{strategy.name}</h2>
            <Badge variant={strategyStatusVariant(strategy.status)}>{strategy.status}</Badge>
          </div>
          <p className="mt-1 text-sm text-fg-muted">
            {strategy.description ?? 'No description.'} · <span className="font-mono">v{strategy.version}</span>
          </p>
        </div>
        <ActivateControl strategy={strategy} />
      </div>

      {/* Tab bar */}
      <div className="flex items-center gap-1 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              'relative px-3.5 py-2 text-sm font-medium transition-colors',
              tab === t.key ? 'text-fg' : 'text-fg-muted hover:text-fg',
            )}
          >
            {t.label}
            {tab === t.key && <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-accent" />}
          </button>
        ))}
      </div>

      {tab === 'overview' && <OverviewTab strategy={strategy} signals={signals} backtests={backtests} />}
      {tab === 'performance' && <PerformanceTab signals={signals} loading={signalsQuery.isLoading} />}
      {tab === 'signals' && <SignalsTab query={signalsQuery} signals={signals} />}
      {tab === 'backtest' && <BacktestTab query={backtestsQuery} backtests={backtests} />}
    </div>
  )
}

function ActivateControl({ strategy }: { strategy: Strategy }) {
  const mutation = useSetStrategyStatus()
  const isActive = strategy.status.toUpperCase() === 'ACTIVE'
  const next = isActive ? 'INACTIVE' : 'ACTIVE'

  return (
    <div className="flex flex-col items-end gap-1">
      <Button
        size="sm"
        variant={isActive ? 'secondary' : 'primary'}
        disabled={mutation.isPending}
        onClick={() => mutation.mutate({ id: strategy.id, status: next })}
      >
        <Power size={15} />
        {mutation.isPending ? 'Saving…' : isActive ? 'Deactivate' : 'Activate'}
      </Button>
      {mutation.isError && <span className="text-xs text-risk">Transition failed</span>}
      <span className="text-[11px] text-fg-subtle">Governed status change</span>
    </div>
  )
}

// ── validity ring shared by Overview/Performance ──
function validityStats(signals: Signal[]) {
  const total = signals.length
  const valid = signals.filter((s) => s.validation_status.toUpperCase() === 'VALID').length
  return { total, valid, rate: total ? valid / total : 0 }
}

function OverviewTab({ strategy, signals, backtests }: { strategy: Strategy; signals: Signal[]; backtests: Backtest[] }) {
  const { valid, total, rate } = validityStats(signals)
  const latest = backtests[0] ?? null
  const configKeys = Object.entries(strategy.config)

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_auto]">
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard label="Signals (recent)" value={total} />
          <StatCard label="Valid" value={valid} tone="profit" />
          <StatCard label="Backtests" value={backtests.length} />
          <StatCard
            label="Latest return"
            value={latest ? fmtReturnPct(latest.total_return) : '—'}
            tone={latest?.total_return ? (Number.parseFloat(latest.total_return) >= 0 ? 'profit' : 'risk') : 'default'}
          />
        </div>

        <Section title="Configuration">
          {configKeys.length === 0 ? (
            <p className="text-sm text-fg-muted">No configuration parameters.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {configKeys.map(([k, v]) => (
                <span key={k} className="rounded-lg border border-border bg-surface px-2.5 py-1.5 font-mono text-xs text-fg-muted">
                  <span className="text-fg-subtle">{k}</span>=<span className="text-fg">{String(v)}</span>
                </span>
              ))}
            </div>
          )}
          <p className="mt-2 text-xs text-fg-subtle">Configuration is owned by the strategy — shown exactly as registered, never interpreted.</p>
        </Section>
      </div>

      <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-border bg-surface-raised p-6 shadow-sm">
        <Ring value={rate} tone="profit" centerLabel={`${Math.round(rate * 100)}%`} centerSub="valid" />
        <p className="text-xs text-fg-muted">Signal validity rate</p>
        <p className="text-[11px] text-fg-subtle">{valid} of {total} recent</p>
      </div>
    </div>
  )
}

function PerformanceTab({ signals, loading }: { signals: Signal[]; loading: boolean }) {
  // conviction curve: oldest -> newest signed signal value
  const ordered = [...signals].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime())
  const points: LinePoint[] = ordered.map((s) => ({ label: fmtTime(s.ts), value: Number.parseFloat(s.value) }))
  const values = points.map((p) => p.value)
  const { valid, total, rate } = validityStats(signals)
  const avg = values.length ? values.reduce((s, v) => s + v, 0) / values.length : 0

  if (loading) return <div className="skeleton h-64 w-full" />

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_16rem]">
        <Section title="Conviction curve" description="Signed conviction over time.">
          <div className="rounded-xl border border-border bg-surface-raised p-4 shadow-sm">
            {points.length >= 2 ? (
              <LineChart data={points} tone="info" zeroBaseline height={240} />
            ) : (
              <div className="flex h-[240px] items-center justify-center text-sm text-fg-muted">
                Not enough signals to plot a curve.
              </div>
            )}
          </div>
        </Section>
        <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-border bg-surface-raised p-6 shadow-sm">
          <Ring value={rate} tone="profit" centerLabel={`${Math.round(rate * 100)}%`} centerSub="valid" />
          <p className="text-xs text-fg-muted">Validity rate</p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Recent signals" value={total} />
        <StatCard label="Valid" value={valid} tone="profit" />
        <StatCard label="Avg conviction" value={fmtSignal(String(avg))} tone={avg >= 0 ? 'profit' : 'risk'} />
        <StatCard label="Max |conviction|" value={fmtSignal(String(values.length ? Math.max(...values.map(Math.abs)) : 0))} />
      </div>
    </div>
  )
}

function SignalsTab({ query, signals }: { query: ReturnType<typeof useSignals>; signals: Signal[] }) {
  return (
    <Section title="Signal feed" description="Most recent signals (immutable event log)." actions={query.isSuccess ? <Badge variant="neutral">{signals.length}</Badge> : null}>
      {query.isLoading && <SkeletonTable rows={5} cols={4} />}
      {query.isError && <ErrorState description="Could not load signals." onRetry={() => query.refetch()} />}
      {query.isSuccess && signals.length === 0 && (
        <EmptyState title="No signals" description="This strategy has emitted no signals." />
      )}
      {query.isSuccess && signals.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-border bg-surface-raised shadow-sm">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Value (conviction)</TableHead>
                <TableHead>Validation</TableHead>
                <TableHead>Detail</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {signals.map((signal) => {
                const meta = Object.entries(signal.metadata)
                return (
                  <TableRow key={signal.id}>
                    <TableCell className="whitespace-nowrap text-fg-muted">{fmtTime(signal.ts)}</TableCell>
                    <TableCell numeric>
                      <Badge variant={pnlBadgeVariant(Number.parseFloat(signal.value))}>{fmtSignal(signal.value)}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={signal.validation_status === 'VALID' ? 'profit' : 'warning'}>{signal.validation_status}</Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-fg-muted">
                      {meta.length === 0 ? '—' : meta.map(([k, v]) => `${k}=${v}`).join('  ')}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </Section>
  )
}

function BacktestTab({ query, backtests }: { query: ReturnType<typeof useBacktests>; backtests: Backtest[] }) {
  const latest = backtests[0] ?? null
  return (
    <div className="space-y-6">
      {latest?.results && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard label="Total return" value={fmtReturnPct(latest.total_return)} tone={latest.total_return && Number.parseFloat(latest.total_return) >= 0 ? 'profit' : 'risk'} />
          <StatCard label="Fills" value={latest.results.orders_filled} />
          <StatCard label="Final capital" value={fmtMoney(latest.final_capital)} />
          <StatCard label="Realized P&L" value={fmtMoney(latest.results.realized_pnl)} tone={Number.parseFloat(latest.results.realized_pnl) >= 0 ? 'profit' : 'risk'} />
        </div>
      )}
      <Section title="Backtest runs" actions={query.isSuccess ? <Badge variant="neutral">{backtests.length}</Badge> : null}>
        {query.isLoading && <SkeletonTable rows={3} cols={5} />}
        {query.isError && <ErrorState description="Could not load backtests." onRetry={() => query.refetch()} />}
        {query.isSuccess && backtests.length === 0 && (
          <EmptyState title="No backtests" description="This strategy has no backtest runs." />
        )}
        {query.isSuccess && backtests.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-border bg-surface-raised shadow-sm">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Run</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Fills</TableHead>
                  <TableHead>Total Return</TableHead>
                  <TableHead>Final Capital</TableHead>
                  <TableHead>Determinism Hash</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {backtests.map((b) => (
                  <TableRow key={b.id}>
                    <TableCell className="font-medium text-fg">{b.name}</TableCell>
                    <TableCell><Badge variant={backtestStatusVariant(b.status)}>{b.status}</Badge></TableCell>
                    <TableCell numeric>{b.results?.orders_filled ?? b.trade_count ?? '—'}</TableCell>
                    <TableCell numeric>
                      {b.total_return === null ? '—' : (
                        <Badge variant={pnlBadgeVariant(Number.parseFloat(b.total_return))}>{fmtReturnPct(b.total_return)}</Badge>
                      )}
                    </TableCell>
                    <TableCell numeric>{fmtMoney(b.final_capital)}</TableCell>
                    <TableCell>
                      {b.reproducibility_hash ? (
                        <span className="font-mono text-xs text-fg-muted" title={b.reproducibility_hash}>
                          {b.reproducibility_hash.slice(0, 12)}…
                        </span>
                      ) : <span className="text-fg-muted">—</span>}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Section>
    </div>
  )
}
