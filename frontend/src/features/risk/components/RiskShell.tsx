// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout / §Data Visualization; §Interaction Standards.
// Doc 08 — Frontend Architecture (QH-008 v1.0) §Architecture / §State Management.
// Doc 14 §10.7.5 — Pre-Trade Risk Check; Doc 15 §11.5.3/§11.5.7/§11.5.8.
// handbook/ui/10_RISK_ENGINEERING.md — aspirational institutional risk
//   terminal vision (Risk Hero/Exposure/Drawdown/Correlation/Leverage/
//   Scenario/Timeline/Intelligence) — scoped down to what's genuinely
//   computable from real data today, same discipline as every other page
//   rebuild this session. Per Doc 00 §14.11
//
// DENSE RISK REBUILD (owner request) — six sections: (1) portfolio selector
// + real-data pill strip; (2) exposure gauge + cross-asset correlation
// (moved here from Markets as its primary home, Markets keeps a compact
// copy); (3) 3-column position risk grid (concentration/leverage/funding);
// (4) NEW open-interest-vs-price monitor with divergence signals; (5) the
// existing pre-trade assessment master-detail inspector (verified, kept);
// (6) risk limits + needs-attention, with the F-18 deferred metrics shown as
// honest "Pending F-18" shells (same established pattern as Strategy/
// Portfolio — NOT "Computing…", which would imply progress that isn't
// happening; see metric-tiles.tsx's own docstring for why).
'use client'

import { useMemo, useState } from 'react'
import { AlertTriangle, Check, Gauge as GaugeIcon, ShieldAlert, ShieldCheck, X } from 'lucide-react'
import {
  Badge,
  EmptyState,
  ErrorState,
  InstitutionalTable,
  type InstitutionalColumnDef,
  PageHeader,
  Panel,
  Ring,
  Section,
  SkeletonTable,
  type BadgeVariant,
} from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { usePortfolios, usePositions } from '@/features/portfolio/hooks/usePortfolio'
import type { Portfolio } from '@/features/portfolio/types'
import { useStrategies } from '@/features/strategies/hooks/useStrategies'
import type { Strategy } from '@/features/strategies/types'
import { useRiskAssessments, useRiskLimits, useRiskSnapshot } from '../hooks/useRisk'
import type { PreTradeAssessment, RiskLimit, RiskSnapshot } from '../types'
import { RiskHeader } from './RiskHeader'
import { ExposureOverview } from './ExposureOverview'
import { PositionRiskGrid } from './PositionRiskGrid'
import { OpenInterestMonitor } from './OpenInterestMonitor'

// Includes seconds: a batch backtest re-runs its risk gate for many orders
// within the same second (real assessed_at values differing only at
// millisecond precision — see analytics.risk_assessments), so a
// minute-granularity timestamp made every row in a batch look identical even
// though the underlying data isn't.
const fmtTime = (ts: string) => new Date(ts).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })
const fmtUtilPct = (v: string | null) => (v === null ? '—' : `${(Number.parseFloat(v) * 100).toFixed(1)}%`)

function limitStatusVariant(status: string | null): BadgeVariant {
  switch (status) {
    case 'breach': return 'risk'
    case 'warning': return 'warning'
    case 'ok': return 'info'
    default: return 'neutral'
  }
}

export function RiskShell() {
  const strategiesQuery = useStrategies()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const strategies = strategiesQuery.data ?? []
  const activeId = selectedId ?? strategies[0]?.id ?? ''
  const activeStrategy = strategies.find((s) => s.id === activeId) ?? null

  // Resolve to the LIVE trading portfolio, not a throwaway backtest portfolio
  // (owner request). Backtest runs each spawn their own one-off BACKTEST
  // portfolio whose positions are $0 at read time — resolving the risk page to
  // one of those made every exposure read $0. Prefer a real LIVE/PAPER
  // portfolio instead; the strategy selector still scopes the pre-trade
  // assessment history below.
  const portfoliosQuery = usePortfolios()
  const portfolios = portfoliosQuery.data ?? []
  const livePortfolio = useMemo(() => {
    const trading = portfolios.filter((p) => p.portfolio_type !== 'BACKTEST')
    // LIVE first, then PAPER; skip obvious test rows.
    const ranked = trading
      .filter((p) => !p.name.startsWith('f21') && !p.name.startsWith('bt-'))
      .sort((a, b) => (a.portfolio_type === 'LIVE' ? -1 : 1) - (b.portfolio_type === 'LIVE' ? -1 : 1))
    return ranked[0] ?? trading[0] ?? null
  }, [portfolios])

  return (
    <div className="space-y-8">
      <PageHeader
        icon={<ShieldAlert size={18} />}
        title="Risk"
        subtitle="Exposure, concentration, open interest & pre-trade assessments — real recorded state."
      />

      {strategiesQuery.isLoading && <div className="skeleton h-24 w-full" />}
      {strategiesQuery.isError && <ErrorState description="Could not load strategies." onRetry={() => strategiesQuery.refetch()} />}
      {strategiesQuery.isSuccess && strategies.length === 0 && (
        <EmptyState icon={<ShieldAlert size={20} />} title="No strategies" description="No strategies are registered yet." />
      )}

      {portfoliosQuery.isSuccess && !livePortfolio && (
        <EmptyState
          icon={<ShieldAlert size={20} />}
          title="No live positions"
          description="No live or paper-trading portfolio exists yet — risk metrics need a real trading portfolio, not a backtest run."
        />
      )}
      {activeStrategy && livePortfolio && (
        <RiskBody
          portfolio={livePortfolio}
          strategies={strategies}
          activeStrategy={activeStrategy}
          onSelect={setSelectedId}
        />
      )}
    </div>
  )
}

function RiskBody({
  portfolio,
  strategies,
  activeStrategy,
  onSelect,
}: {
  portfolio: Portfolio
  strategies: Strategy[]
  activeStrategy: Strategy
  onSelect: (id: string) => void
}) {
  const snapshotQuery = useRiskSnapshot(portfolio.id)
  const limitsQuery = useRiskLimits(portfolio.id)
  const positionsQuery = usePositions(portfolio.id)
  const positions = positionsQuery.data ?? []
  const limits = limitsQuery.data ?? []

  return (
    <div className="space-y-8">
      <RiskHeader
        strategies={strategies}
        activeStrategy={activeStrategy}
        onSelect={onSelect}
        resolvedPortfolioName={portfolio.name}
        snapshot={snapshotQuery.data}
        positions={positions}
        limits={limits}
        configuredCapital={portfolio.configured_capital}
      />

      <ExposureOverview positions={positions} configuredCapital={portfolio.configured_capital} />

      <PositionRiskGrid positions={positions} limits={limits} />

      <OpenInterestMonitor positions={positions} />

      <DeferredMetricsPanel snapshot={snapshotQuery.data} />

      <Assessments portfolio={portfolio} />

      <NeedsAttention limits={limits} limitsLoading={limitsQuery.isLoading} />
      <Limits limits={limits} query={limitsQuery} />
    </div>
  )
}

// VaR/CVaR/volatility/drawdown/beta need a real return-series or
// equity-curve history this platform doesn't accumulate yet — one honest
// line, not a grid of empty tile shells for each metric name.
function DeferredMetricsPanel({ snapshot }: { snapshot: RiskSnapshot | null | undefined }) {
  if (!snapshot || snapshot.deferred_metrics.length === 0) return null

  return (
    <Section icon={<GaugeIcon size={16} />} title="Advanced risk metrics">
      <Panel className="flex items-center gap-3 p-4">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface text-fg-subtle">
          <GaugeIcon size={16} />
        </span>
        <p className="text-sm text-fg-muted">
          {snapshot.deferred_metrics.map((m) => m.name.replace(/_/g, ' ')).join(', ')} — requires return-series computation.
        </p>
      </Panel>
    </Section>
  )
}

function NeedsAttention({ limits, limitsLoading }: { limits: RiskLimit[]; limitsLoading: boolean }) {
  const flagged = limits
    .filter((l) => l.status === 'breach' || l.status === 'warning')
    .sort((a, b) => (a.status === b.status ? 0 : a.status === 'breach' ? -1 : 1))

  if (limitsLoading || limits.length === 0) return null

  return (
    <Section title="Needs attention" description="Governed limits currently at or beyond their warning threshold.">
      {flagged.length === 0 ? (
        <Panel className="flex items-center gap-3 p-5">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-profit-soft text-profit">
            <ShieldCheck size={16} />
          </span>
          <p className="text-sm text-fg-muted">All {limits.length} governed limits are within range.</p>
        </Panel>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {flagged.map((l) => (
            <Panel key={l.limit_id} className={cn('flex items-center gap-3 p-4', l.status === 'breach' && 'border-risk/30')}>
              <span
                className={cn(
                  'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
                  l.status === 'breach' ? 'bg-risk-soft text-risk' : 'bg-warning-soft text-warning',
                )}
              >
                <AlertTriangle size={16} />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate font-mono text-sm text-fg">{l.metric_name}</span>
                  <Badge variant={limitStatusVariant(l.status)}>{l.status}</Badge>
                </div>
                <div className="text-[11px] text-fg-subtle">
                  {l.current_value ?? '—'} of {l.limit_value} limit · {fmtUtilPct(l.utilization)} utilized
                </div>
              </div>
            </Panel>
          ))}
        </div>
      )}
    </Section>
  )
}

function Limits({ limits, query }: { limits: RiskLimit[]; query: ReturnType<typeof useRiskLimits> }) {
  return (
    <Section title="Risk limits" description="Governed limits for this portfolio." actions={query.isSuccess ? <Badge variant="neutral">{limits.length}</Badge> : null}>
      {query.isLoading && <SkeletonTable rows={3} cols={6} />}
      {query.isError && <ErrorState description="Could not load limits." onRetry={() => query.refetch()} />}
      {query.isSuccess && limits.length === 0 && (
        <EmptyState
          title="No risk limits configured"
          description="No governed risk limits are configured for this portfolio — shown honestly rather than a fabricated default set. Configurable metrics: gross/net exposure, leverage, position concentration, per-order notional."
        />
      )}
      {query.isSuccess && limits.length > 0 && (
        <Panel className="overflow-hidden">
          <LimitTable limits={limits} />
        </Panel>
      )}
    </Section>
  )
}

function LimitTable({ limits }: { limits: RiskLimit[] }) {
  const columns = useMemo<InstitutionalColumnDef<RiskLimit>[]>(
    () => [
      {
        accessorKey: 'metric_name',
        header: 'Metric',
        cell: ({ getValue }) => <span className="font-mono text-fg">{getValue<string>()}</span>,
      },
      {
        accessorKey: 'evaluation',
        header: 'Evaluation',
        cell: ({ getValue }) => {
          const isPreTrade = getValue<string>() === 'pre_trade'
          return <Badge variant={isPreTrade ? 'info' : 'neutral'}>{isPreTrade ? 'per-order' : 'continuous'}</Badge>
        },
      },
      {
        id: 'limit_value',
        header: 'Limit',
        accessorFn: (l) => Number.parseFloat(l.limit_value),
        cell: ({ row }) => row.original.limit_value,
        meta: { numeric: true },
      },
      {
        id: 'warning_threshold',
        header: 'Warning',
        accessorFn: (l) => Number.parseFloat(l.warning_threshold),
        cell: ({ row }) => row.original.warning_threshold,
        meta: { numeric: true, hideBelow: 'tablet' },
      },
      {
        id: 'current_value',
        header: 'Current',
        accessorFn: (l) => (l.current_value === null ? -Infinity : Number.parseFloat(l.current_value)),
        cell: ({ row }) => row.original.current_value ?? '—',
        meta: { numeric: true },
      },
      {
        id: 'utilization',
        header: 'Utilization',
        accessorFn: (l) => (l.utilization === null ? -Infinity : Number.parseFloat(l.utilization)),
        cell: ({ row }) => fmtUtilPct(row.original.utilization),
        meta: { numeric: true, hideBelow: 'laptop' },
      },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ getValue }) => {
          const status = getValue<string | null>()
          return status ? (
            <Badge variant={limitStatusVariant(status)}>{status}</Badge>
          ) : (
            <span className="text-fg-muted" title="Evaluated per order (pre-trade)">—</span>
          )
        },
      },
    ],
    [],
  )

  return (
    <InstitutionalTable
      data={limits}
      columns={columns}
      getRowId={(l) => l.limit_id}
      searchPlaceholder="Search limits…"
      exportFilename="risk-limits"
    />
  )
}

// REDESIGNED (Doc 10 §Pre-Trade Risk Assessment) — master-detail inspector,
// verified still working after the Portfolio page's positions/leverage
// changes (kept as-is, per task instruction — no changes needed).
function Assessments({ portfolio }: { portfolio: Portfolio }) {
  const query = useRiskAssessments(portfolio.id)
  const assessments = query.data ?? []
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selected = assessments.find((a) => a.check_id === selectedId) ?? assessments[0] ?? null

  return (
    <Section
      title="Pre-trade assessments"
      description="Every pre-trade risk-gate evaluation, with its full checklist — click a row to inspect."
      actions={query.isSuccess ? <Badge variant="neutral">{assessments.length}</Badge> : null}
    >
      {query.isLoading && <SkeletonTable rows={4} cols={4} />}
      {query.isError && <ErrorState description="Could not load assessments." onRetry={() => query.refetch()} />}
      {query.isSuccess && assessments.length === 0 && (
        <EmptyState title="No assessments" description="No pre-trade risk assessments have been recorded." />
      )}
      {query.isSuccess && assessments.length > 0 && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_20rem]">
          <Panel className="overflow-hidden">
            <AssessmentTable assessments={assessments} selectedId={selected?.check_id ?? null} onSelect={(a) => setSelectedId(a.check_id)} />
          </Panel>
          <AssessmentDetail assessment={selected} />
        </div>
      )}
    </Section>
  )
}

function AssessmentTable({
  assessments,
  selectedId,
  onSelect,
}: {
  assessments: PreTradeAssessment[]
  selectedId: string | null
  onSelect: (a: PreTradeAssessment) => void
}) {
  const columns = useMemo<InstitutionalColumnDef<PreTradeAssessment>[]>(
    () => [
      {
        id: 'assessed_at',
        header: 'Time',
        accessorFn: (a) => new Date(a.assessed_at).getTime(),
        cell: ({ row }) => <span className="whitespace-nowrap text-fg-muted">{fmtTime(row.original.assessed_at)}</span>,
      },
      {
        accessorKey: 'order_id',
        header: 'Order',
        enableSorting: false,
        cell: ({ getValue }) => {
          const orderId = getValue<string>()
          return <span className="font-mono text-xs text-fg-muted" title={orderId}>{orderId.slice(0, 8)}…</span>
        },
      },
      {
        id: 'authorized',
        header: 'Decision',
        accessorFn: (a) => (a.authorized ? 'APPROVED' : 'REJECTED'),
        cell: ({ row }) => (
          <Badge variant={row.original.authorized ? 'profit' : 'risk'}>
            {row.original.authorized ? 'APPROVED' : 'REJECTED'}
          </Badge>
        ),
      },
      {
        id: 'checks',
        header: 'Checks passed',
        enableSorting: false,
        accessorFn: (a) => a.individual_checks.filter((c) => c.passed).length,
        cell: ({ row }) => {
          const checks = row.original.individual_checks
          if (checks.length === 0) return <span className="text-fg-muted">—</span>
          const passed = checks.filter((c) => c.passed).length
          return (
            <span className={passed === checks.length ? 'text-fg-muted' : 'text-risk'}>
              {passed}/{checks.length}
            </span>
          )
        },
      },
    ],
    [],
  )

  return (
    <InstitutionalTable
      data={assessments}
      columns={columns}
      getRowId={(a) => a.check_id}
      searchPlaceholder="Search assessments…"
      exportFilename="risk-assessments"
      initialSorting={[{ id: 'assessed_at', desc: true }]}
      onRowClick={onSelect}
      isRowSelected={(a) => a.check_id === selectedId}
    />
  )
}

function AssessmentDetail({ assessment }: { assessment: PreTradeAssessment | null }) {
  if (!assessment) {
    return (
      <Panel className="flex items-center justify-center p-6 text-sm text-fg-muted">Select an assessment to inspect its checklist.</Panel>
    )
  }
  const checks = assessment.individual_checks
  const passed = checks.filter((c) => c.passed).length
  const rate = checks.length ? passed / checks.length : 0

  return (
    <Panel className="space-y-4 p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="font-mono text-xs text-fg-subtle" title={assessment.order_id}>{assessment.order_id.slice(0, 8)}…</div>
          <div className="text-[11px] text-fg-subtle">{fmtTime(assessment.assessed_at)}</div>
        </div>
        <Badge variant={assessment.authorized ? 'profit' : 'risk'}>{assessment.authorized ? 'APPROVED' : 'REJECTED'}</Badge>
      </div>

      {assessment.rejection_reason && (
        <p className="rounded-lg border border-risk/25 bg-risk-soft/30 px-3 py-2 text-xs leading-relaxed text-fg">
          {assessment.rejection_reason}
        </p>
      )}

      {checks.length > 0 && (
        <div className="flex items-center gap-3 border-t border-border pt-4">
          <Ring value={rate} size={56} thickness={6} tone={rate === 1 ? 'profit' : 'warning'} centerLabel={`${passed}/${checks.length}`} />
          <div>
            <div className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Checks passed</div>
            <div className="text-xs text-fg-muted">every gate this order was evaluated against</div>
          </div>
        </div>
      )}

      <div className="space-y-2 border-t border-border pt-4">
        {checks.length === 0 ? (
          <p className="text-sm text-fg-muted">No individual checks were recorded for this assessment.</p>
        ) : (
          checks.map((c) => (
            <div key={c.check_name} className="flex items-start gap-2.5">
              <span
                className={cn(
                  'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full',
                  c.passed ? 'bg-profit-soft text-profit' : 'bg-risk-soft text-risk',
                )}
              >
                {c.passed ? <Check size={12} /> : <X size={12} />}
              </span>
              <div className="min-w-0">
                <div className="font-mono text-xs text-fg">{c.check_name}</div>
                {c.detail && <div className="text-[11px] text-fg-subtle">{c.detail}</div>}
              </div>
            </div>
          ))
        )}
      </div>
    </Panel>
  )
}
