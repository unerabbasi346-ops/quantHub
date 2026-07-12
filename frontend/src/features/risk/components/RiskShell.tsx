// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout / §Data Visualization; §Interaction Standards.
// Doc 08 — Frontend Architecture (QH-008 v1.0) §Architecture / §State Management.
// Doc 14 §10.7.5 — Pre-Trade Risk Check; Doc 15 §11.5.3/§11.5.7/§11.5.8.
// Per Doc 00 §14.11
//
// REDESIGN + FEATURES (owner push): a ring gauge for directional exposure and
// stat tiles for the REAL computed §11.5.3 exposure/leverage; the honest F-18
// deferred-metrics panel is retained (never faked as 0); and the standalone
// price-correlation matrix is composed at the bottom — explicitly labeled as
// market correlation, NOT portfolio risk (unrelated to F-18).
'use client'

import { useMemo, useState } from 'react'
import { AlertTriangle, Check, ShieldAlert, ShieldCheck, X } from 'lucide-react'
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
  StatCard,
  type BadgeVariant,
} from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { usePortfolios } from '@/features/portfolio/hooks/usePortfolio'
import type { Portfolio } from '@/features/portfolio/types'
import { CorrelationMatrix } from '@/features/markets/components/CorrelationMatrix'
import { useRiskAssessments, useRiskLimits, useRiskSnapshot } from '../hooks/useRisk'
import type { PreTradeAssessment, RiskLimit, RiskSnapshot } from '../types'

const fmtMoney = (v: string) => Number.parseFloat(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const fmtLeverage = (v: string) => `${Number.parseFloat(v).toLocaleString(undefined, { maximumFractionDigits: 6 })}×`
const fmtUtilPct = (v: string | null) => (v === null ? '—' : `${(Number.parseFloat(v) * 100).toFixed(1)}%`)
const fmtTime = (ts: string) => new Date(ts).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

function limitStatusVariant(status: string | null): BadgeVariant {
  switch (status) {
    case 'breach': return 'risk'
    case 'warning': return 'warning'
    case 'ok': return 'info'
    default: return 'neutral'
  }
}

export function RiskShell() {
  const portfoliosQuery = usePortfolios()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const portfolios = portfoliosQuery.data ?? []
  const activeId = selectedId ?? portfolios[0]?.id ?? ''
  const activePortfolio = portfolios.find((p) => p.id === activeId) ?? null

  return (
    <div className="space-y-14">
      <PageHeader
        icon={<ShieldAlert size={18} />}
        title="Risk"
        subtitle="Exposure, limits, pre-trade assessments & market correlation — Phase 3 data."
      />

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[16rem_1fr]">
        <Section title="Portfolios" actions={portfoliosQuery.isSuccess ? <Badge variant="neutral">{portfolios.length}</Badge> : null}>
          {portfoliosQuery.isLoading && <div className="skeleton h-24 w-full" />}
          {portfoliosQuery.isError && <ErrorState description="Could not load portfolios." onRetry={() => portfoliosQuery.refetch()} />}
          <div className="space-y-1">
            {portfolios.map((p) => {
              const selected = p.id === activeId
              return (
                <button
                  key={p.id}
                  onClick={() => setSelectedId(p.id)}
                  className={cn(
                    'flex w-full flex-col gap-0.5 rounded-lg border px-3 py-2.5 text-left transition-colors duration-150',
                    selected ? 'border-accent/40 bg-accent-soft text-accent' : 'border-transparent text-fg-muted hover:bg-surface-hover hover:text-fg',
                  )}
                >
                  <span className="truncate text-sm font-medium">{p.name}</span>
                  <span className="text-[11px] uppercase tracking-wide text-fg-subtle">{p.portfolio_type} · {p.base_currency}</span>
                </button>
              )
            })}
          </div>
        </Section>

        <div className="min-w-0 space-y-14">
          {activePortfolio ? (
            <>
              <Snapshot portfolio={activePortfolio} />
              <NeedsAttention portfolio={activePortfolio} />
              <Limits portfolio={activePortfolio} />
              <Assessments portfolio={activePortfolio} />
              <CorrelationMatrix />
            </>
          ) : (
            !portfoliosQuery.isLoading && !portfoliosQuery.isError && (
              <EmptyState icon={<ShieldAlert size={20} />} title="No portfolio selected" description="Select a portfolio to view its risk." />
            )
          )}
        </div>
      </div>
    </div>
  )
}

function Snapshot({ portfolio }: { portfolio: Portfolio }) {
  const query = useRiskSnapshot(portfolio.id)
  const snapshot: RiskSnapshot | null | undefined = query.data

  const gross = snapshot ? Number.parseFloat(snapshot.gross_exposure) : 0
  const net = snapshot ? Number.parseFloat(snapshot.net_exposure) : 0
  const directional = gross > 0 ? Math.abs(net) / gross : 0

  return (
    <Section
      title="Risk snapshot"
      description={snapshot ? `As of ${fmtTime(snapshot.snapshot_at)}` : undefined}
      actions={snapshot ? (snapshot.breaches.length > 0 ? <Badge variant="risk">{snapshot.breaches.length} breach</Badge> : <Badge variant="profit">OK</Badge>) : null}
    >
      {query.isLoading && <div className="skeleton h-40 w-full" />}
      {query.isError && <ErrorState description="Could not load snapshot." onRetry={() => query.refetch()} />}
      {query.isSuccess && !snapshot && (
        <EmptyState icon={<ShieldAlert size={20} />} title="No risk snapshot" description="No snapshot has been computed for this portfolio yet." />
      )}
      {snapshot && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[auto_1fr]">
          <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-border-strong bg-surface-raised px-8 py-6 shadow-lg">
            <Ring value={directional} tone="info" centerLabel={`${Math.round(directional * 100)}%`} centerSub="directional" />
            <p className="text-xs text-fg-muted">|net| / gross exposure</p>
            <p className="text-[11px] text-fg-subtle">Gross leverage {fmtLeverage(snapshot.gross_leverage)}</p>
          </div>

          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <StatCard label="Gross exposure" value={fmtMoney(snapshot.gross_exposure)} />
              <StatCard label="Net exposure" value={fmtMoney(snapshot.net_exposure)} />
              <StatCard label="Gross leverage" value={fmtLeverage(snapshot.gross_leverage)} />
              <StatCard label="Net leverage" value={fmtLeverage(snapshot.net_leverage)} />
            </div>

            {snapshot.deferred_metrics.length > 0 && (
              <div className="rounded-xl border border-warning/25 bg-warning-soft/30 p-4">
                <div className="mb-2 flex items-center gap-2 text-sm font-medium text-fg">
                  Deferred metrics <Badge variant="warning">Not computed</Badge>
                </div>
                <div className="flex flex-wrap gap-2">
                  {snapshot.deferred_metrics.map((m) => (
                    <span key={m.name} title={m.reason} className="inline-flex items-center gap-1 rounded-md border border-border bg-surface px-2.5 py-1 font-mono text-xs text-fg-muted">
                      {m.name}<span className="opacity-60">— deferred</span>
                    </span>
                  ))}
                </div>
                <p className="mt-2 text-xs leading-relaxed text-fg-muted">
                  VaR, CVaR, volatility, drawdown and beta require a return-series / equity-curve the platform does not accumulate yet — shown as deferred, never a fabricated 0.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </Section>
  )
}

// "What requires attention" — real limits currently in breach or warning,
// surfaced immediately instead of requiring a scan of the full limits table.
function NeedsAttention({ portfolio }: { portfolio: Portfolio }) {
  const query = useRiskLimits(portfolio.id)
  const limits = query.data ?? []
  const flagged = limits
    .filter((l) => l.status === 'breach' || l.status === 'warning')
    .sort((a, b) => (a.status === b.status ? 0 : a.status === 'breach' ? -1 : 1))

  if (query.isLoading || query.isError || limits.length === 0) return null

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

function Limits({ portfolio }: { portfolio: Portfolio }) {
  const query = useRiskLimits(portfolio.id)
  const limits = query.data ?? []
  return (
    <Section title="Risk limits" description="Governed limits for this portfolio." actions={query.isSuccess ? <Badge variant="neutral">{limits.length}</Badge> : null}>
      {query.isLoading && <SkeletonTable rows={3} cols={6} />}
      {query.isError && <ErrorState description="Could not load limits." onRetry={() => query.refetch()} />}
      {query.isSuccess && limits.length === 0 && (
        <EmptyState title="No risk limits" description="No governed risk limits are configured for this portfolio." />
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

// REDESIGNED (Doc 10 §Pre-Trade Risk Assessment: "SHALL be completely
// redesigned. The current implementation SHALL NOT be reused.") — a flat
// table was the forbidden pattern; this is a master-detail inspector.
// Selecting an assessment reveals its full Risk Checklist (every individual
// gate the order was evaluated against, previously fetched but only ever
// summarized as a tooltip) and a real Checks-Passed ratio. What the doc also
// asks for — a multi-factor Trade Approval Score, Exposure Simulation,
// Capital Impact waterfall, and an AI Risk Report — would require inputs
// (projected post-trade exposure, a capital ledger, a real AI backend) this
// platform doesn't compute; per Data Honesty those are left out rather than
// faked, not silently renamed into something they aren't.
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

// The real Risk Checklist — one row per gate the order was actually
// evaluated against, not a summary count.
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
