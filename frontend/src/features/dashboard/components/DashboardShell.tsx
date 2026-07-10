// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: "responsive grid, modular widgets"; §Dashboards.
// Doc 08 — Frontend Architecture (QH-008 v1.0) §Architecture: the dashboard
//   COMPOSES feature hooks — no data logic is reimplemented here.
// Per Doc 00 §14.11
//
// DASHBOARD REBUILD (owner request):
//   - The strategy hero (StrategySection) is the new centerpiece: an
//     auto-rotating conviction chart + one glowing card per registered
//     strategy (points 4–6).
//   - ALL market-data widgets are REMOVED (top movers, watchlist) — that
//     content lives on the Markets page, unchanged (point 3).
//   - The old flat "Strategies & signals" and "Signal activity" widgets are
//     removed too — the strategy hero supersedes them.
// The remaining widgets are the real, non-market operational overview
// (portfolio, execution, risk). Every number is real and cites its source.
'use client'

import type { ReactNode } from 'react'
import { ArrowLeftRight, Gauge, LayoutDashboard, ShieldAlert, Wallet } from 'lucide-react'
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CryptoIcon,
  EmptyState,
  ErrorState,
  PageHeader,
  Ring,
  StatCard,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  pnlBadgeVariant,
  type BadgeVariant,
} from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { usePortfolios, usePositions } from '@/features/portfolio/hooks/usePortfolio'
import type { Portfolio } from '@/features/portfolio/types'
import { useOrders } from '@/features/execution/hooks/useExecution'
import type { Order } from '@/features/execution/types'
import { useRiskSnapshot } from '@/features/risk/hooks/useRisk'
import { StrategySection } from './StrategySection'

const fmtMoney = (v: string | null) =>
  v == null ? '—' : Number.parseFloat(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const fmtSigned = (v: number) => (v > 0 ? '+' : '') + fmtMoney(String(v))
const fmtQty = (v: string) => Number.parseFloat(v).toLocaleString(undefined, { maximumFractionDigits: 8 })
const fmtLeverage = (v: string) => `${Number.parseFloat(v).toLocaleString(undefined, { maximumFractionDigits: 6 })}×`
const fmtTime = (iso: string | null) =>
  !iso ? '—' : new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

function WidgetHead({ icon, title, right }: { icon: ReactNode; title: string; right?: ReactNode }) {
  return (
    <CardHeader>
      <div className="flex items-center gap-2 min-w-0">
        <span className="shrink-0 text-fg-muted">{icon}</span>
        <CardTitle className="truncate">{title}</CardTitle>
      </div>
      {right}
    </CardHeader>
  )
}

// Honest data-provenance line — every widget states the real table / endpoint
// it reads (Doc 00 §14.5/§14.7: no fabricated numbers, sources are cited).
function SourceNote({ children }: { children: ReactNode }) {
  return <p className="mt-3 text-[11px] leading-relaxed text-fg-subtle">Source: {children}</p>
}

export function DashboardShell() {
  const portfoliosQuery = usePortfolios()
  const portfolios = portfoliosQuery.data ?? []
  const activePortfolio: Portfolio | null = portfolios[0] ?? null
  const portfolioId = activePortfolio?.id ?? ''

  return (
    <div className="space-y-8">
      <PageHeader
        icon={<LayoutDashboard size={18} />}
        title="Dashboard"
        subtitle={
          activePortfolio ? (
            <>Strategy performance & operational overview — portfolio <span className="font-medium text-fg">{activePortfolio.name}</span>.</>
          ) : (
            'Strategy performance & operational overview.'
          )
        }
      />

      {/* Strategy hero — always shown (reads the strategy registry directly, not
          gated on a portfolio existing). */}
      <StrategySection />

      {portfoliosQuery.isLoading && <div className="skeleton h-24 w-full" />}
      {portfoliosQuery.isError && (
        <ErrorState description="Could not load portfolios." onRetry={() => portfoliosQuery.refetch()} />
      )}
      {portfoliosQuery.isSuccess && portfolios.length === 0 && (
        <EmptyState icon={<LayoutDashboard size={20} />} title="No portfolios" description="No portfolios exist yet — nothing to summarize." />
      )}

      {portfoliosQuery.isSuccess && activePortfolio && (
        <>
          <KpiStrip portfolioId={portfolioId} />
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <PortfolioSummaryWidget portfolioId={portfolioId} className="lg:col-span-2" />
            <RiskSnapshotWidget portfolioId={portfolioId} />
            <RecentExecutionsWidget portfolioId={portfolioId} className="lg:col-span-2" />
            <ExecutionSummaryWidget portfolioId={portfolioId} />
          </div>
        </>
      )}
    </div>
  )
}

function KpiStrip({ portfolioId }: { portfolioId: string }) {
  const positionsQuery = usePositions(portfolioId)
  const riskQuery = useRiskSnapshot(portfolioId)
  const open = (positionsQuery.data ?? []).filter((p) => !p.is_closed)
  const unrealized = open.reduce((s, p) => s + Number.parseFloat(p.unrealized_pnl), 0)
  const realized = open.reduce((s, p) => s + Number.parseFloat(p.realized_pnl_today), 0)
  const snap = riskQuery.data

  if (positionsQuery.isLoading)
    return (
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="skeleton h-20" />
        <div className="skeleton h-20" />
        <div className="skeleton h-20" />
        <div className="skeleton h-20" />
      </div>
    )

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <StatCard label="Unrealized P&L" value={fmtSigned(unrealized)} tone={unrealized >= 0 ? 'profit' : 'risk'} />
      <StatCard label="Realized today" value={fmtSigned(realized)} tone={realized >= 0 ? 'profit' : 'risk'} />
      <StatCard label="Gross exposure" value={snap ? fmtMoney(snap.gross_exposure) : '—'} hint={snap ? `lev ${fmtLeverage(snap.gross_leverage)}` : undefined} />
      <StatCard label="Open positions" value={open.length} />
    </div>
  )
}

function PortfolioSummaryWidget({ portfolioId, className }: { portfolioId: string; className?: string }) {
  const query = usePositions(portfolioId)
  const open = (query.data ?? []).filter((p) => !p.is_closed)
  const top = [...open].sort((a, b) => a.sequence_number - b.sequence_number).slice(0, 5)

  return (
    <Card elevation="glow" className={className}>
      <WidgetHead
        icon={<Wallet size={16} />}
        title="Portfolio summary"
        right={query.isSuccess ? <Badge variant="neutral">{open.length} open</Badge> : null}
      />
      <CardContent>
        {query.isLoading && <div className="skeleton h-32 w-full" />}
        {query.isError && <ErrorState description="Could not load positions." onRetry={() => query.refetch()} />}
        {query.isSuccess && open.length === 0 && <EmptyState title="No open positions" description="This portfolio holds no open positions." />}
        {query.isSuccess && open.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow><TableHead>Symbol</TableHead><TableHead>Qty</TableHead><TableHead>Market value</TableHead><TableHead>Unrealized</TableHead></TableRow>
            </TableHeader>
            <TableBody>
              {top.map((p) => (
                <TableRow key={p.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <CryptoIcon symbol={p.symbol ?? '?'} size={20} />
                      <span className="font-medium text-fg">{p.symbol ?? '—'}</span>
                    </div>
                  </TableCell>
                  <TableCell numeric>{fmtQty(p.quantity)}</TableCell>
                  <TableCell numeric>{fmtMoney(p.market_value)}</TableCell>
                  <TableCell numeric><Badge variant={pnlBadgeVariant(Number.parseFloat(p.unrealized_pnl))}>{fmtSigned(Number.parseFloat(p.unrealized_pnl))}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        {query.isSuccess && open.length > 0 && (
          <SourceNote>live portfolio positions</SourceNote>
        )}
      </CardContent>
    </Card>
  )
}

function RiskSnapshotWidget({ portfolioId }: { portfolioId: string }) {
  const query = useRiskSnapshot(portfolioId)
  const snap = query.data ?? null
  return (
    <Card elevation="glow">
      <WidgetHead
        icon={<ShieldAlert size={16} />}
        title="Risk snapshot"
        right={snap ? (snap.breaches.length > 0 ? <Badge variant="risk">{snap.breaches.length} breach</Badge> : <Badge variant="profit">OK</Badge>) : null}
      />
      <CardContent className="space-y-4">
        {query.isLoading && <div className="skeleton h-28 w-full" />}
        {query.isError && <ErrorState description="Could not load risk snapshot." onRetry={() => query.refetch()} />}
        {query.isSuccess && !snap && <EmptyState title="No snapshot" description="No risk snapshot computed yet." />}
        {snap && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <div><div className="text-[11px] uppercase tracking-wide text-fg-subtle">Gross exp.</div><div className="mt-0.5 font-mono text-lg font-semibold tabular-nums text-fg">{fmtMoney(snap.gross_exposure)}</div></div>
              <div><div className="text-[11px] uppercase tracking-wide text-fg-subtle">Gross lev.</div><div className="mt-0.5 font-mono text-lg font-semibold tabular-nums text-fg">{fmtLeverage(snap.gross_leverage)}</div></div>
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-wide text-fg-subtle">Deferred metrics</div>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {snap.deferred_metrics.map((m) => (<Badge key={m.name} variant="warning" title={m.reason}>{m.name}</Badge>))}
              </div>
            </div>
            <p className="text-xs text-fg-subtle">As of {fmtTime(snap.snapshot_at)}</p>
            <SourceNote>the portfolio's live risk snapshot</SourceNote>
          </>
        )}
      </CardContent>
    </Card>
  )
}

function orderStatusVariant(status: Order['status']): BadgeVariant {
  if (status === 'FILLED') return 'profit'
  if (status === 'REJECTED') return 'risk'
  return 'info'
}

function RecentExecutionsWidget({ portfolioId, className }: { portfolioId: string; className?: string }) {
  const query = useOrders(portfolioId)
  const recent = [...(query.data ?? [])].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 6)
  return (
    <Card elevation="glow" className={className}>
      <WidgetHead
        icon={<ArrowLeftRight size={16} />}
        title="Recent executions"
        right={query.isSuccess ? <Badge variant="neutral">{(query.data ?? []).length} orders</Badge> : null}
      />
      <CardContent>
        {query.isLoading && <div className="skeleton h-32 w-full" />}
        {query.isError && <ErrorState description="Could not load orders." onRetry={() => query.refetch()} />}
        {query.isSuccess && recent.length === 0 && <EmptyState title="No orders" description="No orders placed for this portfolio." />}
        {query.isSuccess && recent.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow><TableHead>Time</TableHead><TableHead>Symbol</TableHead><TableHead>Side</TableHead><TableHead>Qty</TableHead><TableHead>Avg price</TableHead><TableHead>Status</TableHead></TableRow>
            </TableHeader>
            <TableBody>
              {recent.map((o) => (
                <TableRow key={o.id}>
                  <TableCell className="whitespace-nowrap text-fg-muted">{fmtTime(o.created_at)}</TableCell>
                  <TableCell className="font-medium text-fg">{o.symbol ?? '—'}</TableCell>
                  <TableCell><span className={cn('font-medium', o.side === 'BUY' ? 'text-profit' : 'text-risk')}>{o.side}</span></TableCell>
                  <TableCell numeric>{fmtQty(o.quantity)}</TableCell>
                  <TableCell numeric>{fmtMoney(o.average_price)}</TableCell>
                  <TableCell><Badge variant={orderStatusVariant(o.status)}>{o.status}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        {query.isSuccess && recent.length > 0 && (
          <SourceNote>the portfolio's live order history</SourceNote>
        )}
      </CardContent>
    </Card>
  )
}

// Execution summary: TODAY's order lifecycle for the active portfolio — fill
// rate and approval rate (approved = anything not REJECTED). Real order rows
// only; "today" is the local calendar day, and an empty day says so.
function ExecutionSummaryWidget({ portfolioId }: { portfolioId: string }) {
  const query = useOrders(portfolioId)
  const all = query.data ?? []
  const startOfDay = new Date()
  startOfDay.setHours(0, 0, 0, 0)
  const today = all.filter((o) => new Date(o.created_at).getTime() >= startOfDay.getTime())
  const filled = today.filter((o) => o.status === 'FILLED').length
  const rejected = today.filter((o) => o.status === 'REJECTED').length
  const approved = today.length - rejected
  const fillRate = today.length ? filled / today.length : 0
  const approvalRate = today.length ? approved / today.length : 0

  return (
    <Card elevation="glow">
      <WidgetHead
        icon={<Gauge size={16} />}
        title="Execution summary"
        right={query.isSuccess ? <Badge variant="neutral">today</Badge> : null}
      />
      <CardContent className="space-y-4">
        {query.isLoading && <div className="skeleton h-28 w-full" />}
        {query.isError && <ErrorState description="Could not load orders." onRetry={() => query.refetch()} />}
        {query.isSuccess && today.length === 0 && (
          <EmptyState icon={<Gauge size={20} />} title="No orders today" description="No orders were placed on the current calendar day." />
        )}
        {query.isSuccess && today.length > 0 && (
          <>
            <div className="flex items-center gap-5">
              <Ring value={approvalRate} size={88} thickness={9} tone={rejected ? 'warning' : 'profit'} centerLabel={`${Math.round(approvalRate * 100)}%`} centerSub="approved" />
              <div className="grid flex-1 grid-cols-2 gap-3">
                <div><div className="text-[11px] uppercase tracking-wide text-fg-subtle">Orders</div><div className="font-mono text-lg font-semibold tabular-nums text-fg">{today.length}</div></div>
                <div><div className="text-[11px] uppercase tracking-wide text-fg-subtle">Filled</div><div className="font-mono text-lg font-semibold tabular-nums text-profit">{filled}</div></div>
                <div><div className="text-[11px] uppercase tracking-wide text-fg-subtle">Rejected</div><div className={cn('font-mono text-lg font-semibold tabular-nums', rejected ? 'text-risk' : 'text-fg')}>{rejected}</div></div>
                <div><div className="text-[11px] uppercase tracking-wide text-fg-subtle">Fill rate</div><div className="font-mono text-lg font-semibold tabular-nums text-fg">{Math.round(fillRate * 100)}%</div></div>
              </div>
            </div>
            <SourceNote>orders placed today</SourceNote>
          </>
        )}
      </CardContent>
    </Card>
  )
}
