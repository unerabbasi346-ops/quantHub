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

import { useState } from 'react'
import { ShieldAlert } from 'lucide-react'
import {
  Badge,
  EmptyState,
  ErrorState,
  PageHeader,
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
    <div className="space-y-8">
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

        <div className="min-w-0 space-y-8">
          {activePortfolio ? (
            <>
              <Snapshot portfolio={activePortfolio} />
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
                  VaR, CVaR, volatility, drawdown and beta require a return-series / equity-curve the platform does not accumulate yet — shown as deferred, never a fabricated 0 <span className="opacity-70">(F-18)</span>.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </Section>
  )
}

function Limits({ portfolio }: { portfolio: Portfolio }) {
  const query = useRiskLimits(portfolio.id)
  const limits = query.data ?? []
  return (
    <Section title="Risk limits" description="Governed limits (§11.5.7)." actions={query.isSuccess ? <Badge variant="neutral">{limits.length}</Badge> : null}>
      {query.isLoading && <SkeletonTable rows={3} cols={6} />}
      {query.isError && <ErrorState description="Could not load limits." onRetry={() => query.refetch()} />}
      {query.isSuccess && limits.length === 0 && (
        <EmptyState title="No risk limits" description="No governed risk limits are configured for this portfolio." />
      )}
      {query.isSuccess && limits.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-border bg-surface-raised shadow-sm">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Metric</TableHead><TableHead>Evaluation</TableHead><TableHead>Limit</TableHead>
                <TableHead>Warning</TableHead><TableHead>Current</TableHead><TableHead>Utilization</TableHead><TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {limits.map((limit) => (<LimitRow key={limit.limit_id} limit={limit} />))}
            </TableBody>
          </Table>
        </div>
      )}
    </Section>
  )
}

function LimitRow({ limit }: { limit: RiskLimit }) {
  const isPreTrade = limit.evaluation === 'pre_trade'
  return (
    <TableRow>
      <TableCell><span className="font-mono text-fg">{limit.metric_name}</span></TableCell>
      <TableCell><Badge variant={isPreTrade ? 'info' : 'neutral'}>{isPreTrade ? 'per-order' : 'continuous'}</Badge></TableCell>
      <TableCell numeric>{limit.limit_value}</TableCell>
      <TableCell numeric>{limit.warning_threshold}</TableCell>
      <TableCell numeric>{limit.current_value ?? '—'}</TableCell>
      <TableCell numeric>{fmtUtilPct(limit.utilization)}</TableCell>
      <TableCell>
        {limit.status ? <Badge variant={limitStatusVariant(limit.status)}>{limit.status}</Badge> : <span className="text-fg-muted" title="Evaluated per order (pre-trade)">—</span>}
      </TableCell>
    </TableRow>
  )
}

function Assessments({ portfolio }: { portfolio: Portfolio }) {
  const query = useRiskAssessments(portfolio.id)
  const assessments = query.data ?? []
  return (
    <Section title="Pre-trade assessments" description="Most recent gate evaluations (§10.7.5)." actions={query.isSuccess ? <Badge variant="neutral">{assessments.length}</Badge> : null}>
      {query.isLoading && <SkeletonTable rows={4} cols={4} />}
      {query.isError && <ErrorState description="Could not load assessments." onRetry={() => query.refetch()} />}
      {query.isSuccess && assessments.length === 0 && (
        <EmptyState title="No assessments" description="No pre-trade risk assessments have been recorded." />
      )}
      {query.isSuccess && assessments.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-border bg-surface-raised shadow-sm">
          <Table>
            <TableHeader>
              <TableRow><TableHead>Time</TableHead><TableHead>Order</TableHead><TableHead>Decision</TableHead><TableHead>Reason</TableHead></TableRow>
            </TableHeader>
            <TableBody>
              {assessments.map((a) => (
                <TableRow key={a.check_id}>
                  <TableCell className="whitespace-nowrap text-fg-muted">{fmtTime(a.assessed_at)}</TableCell>
                  <TableCell><span className="font-mono text-xs text-fg-muted" title={a.order_id}>{a.order_id.slice(0, 8)}…</span></TableCell>
                  <TableCell><Badge variant={a.authorized ? 'profit' : 'risk'}>{a.authorized ? 'APPROVED' : 'REJECTED'}</Badge></TableCell>
                  <TableCell>{a.rejection_reason ? <span className="text-sm text-fg">{a.rejection_reason}</span> : <span className="text-fg-muted">—</span>}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </Section>
  )
}
