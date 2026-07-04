// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: sidebar + workspace; §Components: cards, tables, badges;
//   §Visual Language: semantic colors; §Interaction Standards: state handling.
// Doc 08 — Frontend Architecture (QH-008 v1.0)
//   §Architecture: feature module composes the shared design system + hooks;
//   §State Management: TanStack Query.
// Doc 14 §10.7.5 — Pre-Trade Risk Check (the assessment history).
// Doc 15 §11.5.3 Risk Measurement, §11.5.7 Limits, §11.5.8 Continuous Monitoring.
// Per Doc 00 §14.11
//
// JUDGMENT CALLS (Doc 00 §14.5/§14.7 — flagged):
//  1. HONEST F-18 DEFERRED METRICS (the one to get right — same discipline as
//     Step 4.5's F-9). The snapshot shows gross/net exposure and gross/net
//     leverage as REAL computed values, and lists VaR/CVaR/volatility/drawdown/
//     beta in a distinct "Deferred (F-18)" panel — each with a "Not computed"
//     badge and the reason — NEVER as a real 0. Nothing implies these are
//     measured when they are not.
//  2. HONEST UTILIZATION. A pre-trade limit (position_size / gross_exposure,
//     evaluated per order at §10.7.5) has no standing portfolio utilization, so
//     the limits table shows "—" with a "per-order" evaluation badge rather
//     than a fabricated bar. Continuous limits show real utilization/status.
//  3. PORTFOLIO SELECTOR REUSE: risk is portfolio-scoped, so this reuses the
//     portfolio feature's usePortfolios/Portfolio — a one-directional
//     risk→portfolio domain dependency (same as the execution blotter).
'use client'

import { useState } from 'react'
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  LoadingState,
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
import { useRiskAssessments, useRiskLimits, useRiskSnapshot } from '../hooks/useRisk'
import type { PreTradeAssessment, RiskLimit, RiskSnapshot } from '../types'

// ── formatters (display-only; API strings are the source of truth) ──
function fmtMoney(value: string): string {
  return Number.parseFloat(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function fmtLeverage(value: string): string {
  return `${Number.parseFloat(value).toLocaleString(undefined, { maximumFractionDigits: 6 })}×`
}

function fmtUtilPct(value: string | null): string {
  if (value === null) return '—'
  return `${(Number.parseFloat(value) * 100).toFixed(1)}%`
}

function fmtTime(ts: string): string {
  return new Date(ts).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function limitStatusVariant(status: string | null): BadgeVariant {
  switch (status) {
    case 'breach':
      return 'risk'
    case 'warning':
      return 'warning'
    case 'ok':
      return 'info'
    default:
      return 'neutral'
  }
}

export function RiskShell() {
  const portfoliosQuery = usePortfolios()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const portfolios = portfoliosQuery.data ?? []
  const activeId = selectedId ?? portfolios[0]?.id ?? ''
  const activePortfolio = portfolios.find((p) => p.id === activeId) ?? null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-fg">Risk</h1>
        <p className="mt-1 text-sm text-fg-muted">
          Limits, pre-trade assessments &amp; portfolio risk snapshot — Phase 3 data.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[18rem_1fr]">
        <PortfolioList
          query={portfoliosQuery}
          portfolios={portfolios}
          activeId={activeId}
          onSelect={setSelectedId}
        />
        <div className="min-w-0 space-y-6">
          {activePortfolio ? (
            <>
              <Snapshot portfolio={activePortfolio} />
              <Limits portfolio={activePortfolio} />
              <Assessments portfolio={activePortfolio} />
            </>
          ) : (
            !portfoliosQuery.isLoading &&
            !portfoliosQuery.isError && (
              <Card>
                <CardContent>
                  <EmptyState
                    title="No portfolio selected"
                    description="Select a portfolio to view its risk."
                  />
                </CardContent>
              </Card>
            )
          )}
        </div>
      </div>
    </div>
  )
}

function PortfolioList({
  query,
  portfolios,
  activeId,
  onSelect,
}: {
  query: ReturnType<typeof usePortfolios>
  portfolios: Portfolio[]
  activeId: string
  onSelect: (id: string) => void
}) {
  return (
    <Card className="h-fit">
      <CardHeader>
        <CardTitle>Portfolios</CardTitle>
        {query.isSuccess && <Badge variant="neutral">{portfolios.length}</Badge>}
      </CardHeader>
      <CardContent className="p-2">
        {query.isLoading && <LoadingState label="Loading portfolios…" />}
        {query.isError && (
          <ErrorState description="Could not load portfolios." onRetry={() => query.refetch()} />
        )}
        {query.isSuccess && portfolios.length === 0 && (
          <EmptyState title="No portfolios" description="No active portfolios exist yet." />
        )}
        {query.isSuccess &&
          portfolios.map((portfolio) => {
            const selected = portfolio.id === activeId
            return (
              <button
                key={portfolio.id}
                onClick={() => onSelect(portfolio.id)}
                aria-current={selected ? 'true' : undefined}
                className={cn(
                  'flex w-full flex-col gap-1 rounded-md px-3 py-2 text-left transition-colors',
                  selected
                    ? 'bg-info-soft text-info'
                    : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
                )}
              >
                <span className="truncate text-sm font-medium">{portfolio.name}</span>
                <span className="text-xs uppercase tracking-wide text-fg-muted">
                  {portfolio.portfolio_type} · {portfolio.base_currency}
                </span>
              </button>
            )
          })}
      </CardContent>
    </Card>
  )
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-fg-muted">{label}</div>
      <div className="mt-1 text-lg font-semibold tabular-nums text-fg">{value}</div>
    </div>
  )
}

function Snapshot({ portfolio }: { portfolio: Portfolio }) {
  const snapshotQuery = useRiskSnapshot(portfolio.id)
  const snapshot: RiskSnapshot | null | undefined = snapshotQuery.data

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Risk Snapshot
          <span className="ml-2 font-normal text-fg-muted">{portfolio.name}</span>
        </CardTitle>
        {snapshot && (
          <span className="text-xs text-fg-muted">as of {fmtTime(snapshot.snapshot_at)}</span>
        )}
      </CardHeader>
      <CardContent>
        {snapshotQuery.isLoading && <LoadingState label="Loading snapshot…" />}
        {snapshotQuery.isError && (
          <ErrorState description="Could not load snapshot." onRetry={() => snapshotQuery.refetch()} />
        )}
        {snapshotQuery.isSuccess && !snapshot && (
          <EmptyState
            title="No risk snapshot"
            description="No portfolio risk snapshot has been computed for this portfolio yet."
          />
        )}
        {snapshot && (
          <div className="space-y-5">
            {/* COMPUTED metrics — real values from positions (§11.5.3). */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatTile label="Gross Exposure" value={fmtMoney(snapshot.gross_exposure)} />
              <StatTile label="Net Exposure" value={fmtMoney(snapshot.net_exposure)} />
              <StatTile label="Gross Leverage" value={fmtLeverage(snapshot.gross_leverage)} />
              <StatTile label="Net Leverage" value={fmtLeverage(snapshot.net_leverage)} />
            </div>

            {/* DEFERRED metrics — named honestly (F-18), never shown as real 0. */}
            {snapshot.deferred_metrics.length > 0 && (
              <div>
                <div className="mb-2 flex items-center gap-2 text-sm font-medium text-fg">
                  Deferred metrics
                  <Badge variant="warning">Not computed</Badge>
                </div>
                <div className="flex flex-wrap gap-2">
                  {snapshot.deferred_metrics.map((m) => (
                    <span
                      key={m.name}
                      title={m.reason}
                      className="inline-flex items-center gap-1 rounded-md border border-border bg-surface px-2.5 py-1 text-xs text-fg-muted"
                    >
                      <span className="font-mono">{m.name}</span>
                      <span className="opacity-70">— deferred</span>
                    </span>
                  ))}
                </div>
                <p className="mt-2 text-xs leading-relaxed text-fg-muted">
                  VaR, CVaR, volatility, drawdown and beta are not yet computed — they
                  require return-series / equity-curve history the platform does not
                  accumulate yet. They are shown here as deferred rather than as a
                  fabricated 0. <span className="opacity-70">(F-18)</span>
                </p>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function Limits({ portfolio }: { portfolio: Portfolio }) {
  const limitsQuery = useRiskLimits(portfolio.id)
  const limits = limitsQuery.data ?? []

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Risk Limits
          <span className="ml-2 font-normal text-fg-muted">governed</span>
        </CardTitle>
        {limitsQuery.isSuccess && <Badge variant="neutral">{limits.length}</Badge>}
      </CardHeader>
      <CardContent>
        {limitsQuery.isLoading && <LoadingState label="Loading limits…" />}
        {limitsQuery.isError && (
          <ErrorState description="Could not load limits." onRetry={() => limitsQuery.refetch()} />
        )}
        {limitsQuery.isSuccess && limits.length === 0 && (
          <EmptyState
            title="No risk limits"
            description="No governed risk limits are configured for this portfolio."
          />
        )}
        {limitsQuery.isSuccess && limits.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Metric</TableHead>
                <TableHead>Evaluation</TableHead>
                <TableHead>Limit</TableHead>
                <TableHead>Warning</TableHead>
                <TableHead>Current</TableHead>
                <TableHead>Utilization</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {limits.map((limit) => (
                <LimitRow key={limit.limit_id} limit={limit} />
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}

function LimitRow({ limit }: { limit: RiskLimit }) {
  const isPreTrade = limit.evaluation === 'pre_trade'
  return (
    <TableRow>
      <TableCell>
        <span className="font-mono text-sm text-fg">{limit.metric_name}</span>
      </TableCell>
      <TableCell>
        <Badge variant={isPreTrade ? 'info' : 'neutral'}>
          {isPreTrade ? 'per-order' : 'continuous'}
        </Badge>
      </TableCell>
      <TableCell numeric>{limit.limit_value}</TableCell>
      <TableCell numeric>{limit.warning_threshold}</TableCell>
      <TableCell numeric>{limit.current_value ?? '—'}</TableCell>
      <TableCell numeric>{fmtUtilPct(limit.utilization)}</TableCell>
      <TableCell>
        {limit.status ? (
          <Badge variant={limitStatusVariant(limit.status)}>{limit.status}</Badge>
        ) : (
          <span className="text-fg-muted" title="Evaluated per order (pre-trade), not against a standing snapshot">
            —
          </span>
        )}
      </TableCell>
    </TableRow>
  )
}

function Assessments({ portfolio }: { portfolio: Portfolio }) {
  const assessmentsQuery = useRiskAssessments(portfolio.id)
  const assessments = assessmentsQuery.data ?? []

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Pre-Trade Assessments
          <span className="ml-2 font-normal text-fg-muted">most recent</span>
        </CardTitle>
        {assessmentsQuery.isSuccess && <Badge variant="neutral">{assessments.length}</Badge>}
      </CardHeader>
      <CardContent>
        {assessmentsQuery.isLoading && <LoadingState label="Loading assessments…" />}
        {assessmentsQuery.isError && (
          <ErrorState
            description="Could not load assessments."
            onRetry={() => assessmentsQuery.refetch()}
          />
        )}
        {assessmentsQuery.isSuccess && assessments.length === 0 && (
          <EmptyState
            title="No assessments"
            description="No pre-trade risk assessments have been recorded for this portfolio."
          />
        )}
        {assessmentsQuery.isSuccess && assessments.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Order</TableHead>
                <TableHead>Decision</TableHead>
                <TableHead>Reason</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {assessments.map((assessment) => (
                <AssessmentRow key={assessment.check_id} assessment={assessment} />
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}

function AssessmentRow({ assessment }: { assessment: PreTradeAssessment }) {
  return (
    <TableRow>
      <TableCell className="whitespace-nowrap text-fg-muted">
        {fmtTime(assessment.assessed_at)}
      </TableCell>
      <TableCell>
        <span className="font-mono text-xs text-fg-muted" title={assessment.order_id}>
          {assessment.order_id.slice(0, 8)}…
        </span>
      </TableCell>
      <TableCell>
        <Badge variant={assessment.authorized ? 'profit' : 'risk'}>
          {assessment.authorized ? 'APPROVED' : 'REJECTED'}
        </Badge>
      </TableCell>
      <TableCell>
        {assessment.rejection_reason ? (
          <span className="text-sm text-fg">{assessment.rejection_reason}</span>
        ) : (
          <span className="text-fg-muted">—</span>
        )}
      </TableCell>
    </TableRow>
  )
}
