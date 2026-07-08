// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: "responsive grid, modular widgets"; §Dashboards.
// Doc 08 — Frontend Architecture (QH-008 v1.0) §Architecture: the dashboard
//   COMPOSES the five slices' hooks — no data logic is reimplemented here.
// Per Doc 00 §14.11
//
// REDESIGN (owner push): a top KPI strip anchors the page; primary widgets
// (portfolio, executions) read as ELEVATED, secondary ones (risk, watchlist)
// flatter — a real visual hierarchy. The watchlist gains crypto icons + inline
// sparklines. Data logic is unchanged (assembly only, S-6 fixed layout).
'use client'

import type { ReactNode } from 'react'
import { useQueries } from '@tanstack/react-query'
import {
  ArrowLeftRight,
  Brain,
  Eye,
  Gauge,
  LayoutDashboard,
  Radio,
  ShieldAlert,
  TrendingUp,
  Wallet,
} from 'lucide-react'
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
  Sparkline,
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
import { useStrategies, useSignals } from '@/features/strategies/hooks/useStrategies'
import type { Strategy } from '@/features/strategies/types'
import { useAssets, useBars } from '@/features/markets/hooks/useMarkets'
import { marketsService } from '@/features/markets/services/markets.service'
import type { Asset } from '@/features/markets/types'

const fmtMoney = (v: string | null) =>
  v == null ? '—' : Number.parseFloat(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const fmtSigned = (v: number) => (v > 0 ? '+' : '') + fmtMoney(String(v))
const fmtQty = (v: string) => Number.parseFloat(v).toLocaleString(undefined, { maximumFractionDigits: 8 })
const fmtLeverage = (v: string) => `${Number.parseFloat(v).toLocaleString(undefined, { maximumFractionDigits: 6 })}×`
const fmtTime = (iso: string | null) =>
  !iso ? '—' : new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

// Every widget header carries a distinct lucide icon (same icon language as
// the sidebar) in the resting neutral tone, plus the standard right-slot for
// a count/status badge.
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
            <>Live overview across markets, portfolio, execution, strategies & risk — portfolio <span className="font-medium text-fg">{activePortfolio.name}</span>.</>
          ) : (
            'Live overview across markets, portfolio, execution, strategies & risk.'
          )
        }
      />

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
            <TopMoversWidget />
            <ExecutionSummaryWidget portfolioId={portfolioId} />
            <SignalActivityWidget />
            <RecentExecutionsWidget portfolioId={portfolioId} className="lg:col-span-2" />
            <MarketsWatchlistWidget />
            <StrategiesSignalsWidget className="lg:col-span-3" />
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

  if (positionsQuery.isLoading) return <div className="grid grid-cols-2 gap-4 sm:grid-cols-4"><div className="skeleton h-20" /><div className="skeleton h-20" /><div className="skeleton h-20" /><div className="skeleton h-20" /></div>

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
    <Card elevation="elevated" className={className}>
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
          <SourceNote>core.positions · GET /v1/portfolios/{'{id}'}/positions</SourceNote>
        )}
      </CardContent>
    </Card>
  )
}

function RiskSnapshotWidget({ portfolioId }: { portfolioId: string }) {
  const query = useRiskSnapshot(portfolioId)
  const snap = query.data ?? null
  return (
    <Card elevation="flat">
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
              <div className="text-[11px] uppercase tracking-wide text-fg-subtle">Deferred (F-18)</div>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {snap.deferred_metrics.map((m) => (<Badge key={m.name} variant="warning" title={m.reason}>{m.name}</Badge>))}
              </div>
            </div>
            <p className="text-xs text-fg-subtle">As of {fmtTime(snap.snapshot_at)}</p>
            <SourceNote>analytics risk snapshot · GET /v1/portfolios/{'{id}'}/risk/snapshot</SourceNote>
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
    <Card elevation="elevated" className={className}>
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
          <SourceNote>core.orders · GET /v1/portfolios/{'{id}'}/orders</SourceNote>
        )}
      </CardContent>
    </Card>
  )
}

function MarketsWatchlistWidget() {
  const query = useAssets()
  const assets = query.data ?? []
  return (
    <Card elevation="flat">
      <WidgetHead
        icon={<Eye size={16} />}
        title="Watchlist"
        right={query.isSuccess ? <Badge variant="neutral">{assets.length}</Badge> : null}
      />
      <CardContent className="space-y-1 p-2">
        {query.isLoading && <div className="skeleton h-28 w-full" />}
        {query.isError && <ErrorState description="Could not load assets." onRetry={() => query.refetch()} />}
        {query.isSuccess && assets.length === 0 && <EmptyState title="No assets" description="No tradable assets registered." />}
        {query.isSuccess && assets.map((asset) => <WatchlistRow key={asset.id} asset={asset} />)}
        {query.isSuccess && assets.length > 0 && (
          <div className="px-2"><SourceNote>market_data.assets + ohlcv_bars · GET /v1/assets, /v1/assets/{'{id}'}/bars</SourceNote></div>
        )}
      </CardContent>
    </Card>
  )
}

function WatchlistRow({ asset }: { asset: Asset }) {
  const barsQuery = useBars(asset.id, '1h')
  const bars = barsQuery.data ?? []
  const closes = bars.slice(-24).map((b) => Number.parseFloat(b.close))
  const last = bars.at(-1)
  const prev = bars.at(-2)
  const change = last && prev ? Number.parseFloat(last.close) - Number.parseFloat(prev.close) : null
  const changePct = change != null && prev ? (change / Number.parseFloat(prev.close)) * 100 : null

  return (
    <div className="flex items-center gap-2.5 rounded-lg px-2 py-2 transition-colors hover:bg-surface-hover/50">
      <CryptoIcon symbol={asset.symbol} size={24} />
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium text-fg">{asset.symbol}</div>
        <div className="text-[11px] uppercase text-fg-subtle">{asset.exchange}</div>
      </div>
      {closes.length > 1 && <Sparkline data={closes} width={56} height={22} />}
      <div className="text-right">
        {last ? (
          <>
            <div className="font-mono text-sm font-semibold tabular-nums text-fg">{fmtMoney(last.close)}</div>
            {changePct != null && (
              <div className={cn('font-mono text-[11px] tabular-nums', change! >= 0 ? 'text-profit' : 'text-risk')}>
                {change! >= 0 ? '+' : ''}{changePct.toFixed(2)}%
              </div>
            )}
          </>
        ) : <span className="text-xs text-fg-subtle">…</span>}
      </div>
    </div>
  )
}

function StrategiesSignalsWidget({ className }: { className?: string }) {
  const query = useStrategies()
  const strategies = query.data ?? []
  const firstId = strategies[0]?.id ?? ''
  const signalsQuery = useSignals(firstId)
  const signals = signalsQuery.data ?? []
  const latest = signals.length > 0 ? [...signals].sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime())[0] : null

  return (
    <Card elevation="raised" className={className}>
      <WidgetHead
        icon={<Brain size={16} />}
        title="Strategies & signals"
        right={query.isSuccess ? <Badge variant="neutral">{strategies.length}</Badge> : null}
      />
      <CardContent>
        {query.isLoading && <div className="skeleton h-28 w-full" />}
        {query.isError && <ErrorState description="Could not load strategies." onRetry={() => query.refetch()} />}
        {query.isSuccess && strategies.length === 0 && <EmptyState title="No strategies" description="No strategies registered yet." />}
        {query.isSuccess && strategies.length > 0 && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Table>
                <TableHeader>
                  <TableRow><TableHead>Strategy</TableHead><TableHead>Status</TableHead><TableHead>Version</TableHead></TableRow>
                </TableHeader>
                <TableBody>
                  {strategies.slice(0, 6).map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="font-medium text-fg">{s.name}</TableCell>
                      <TableCell><Badge variant={s.status === 'ACTIVE' ? 'profit' : 'neutral'}>{s.status}</Badge></TableCell>
                      <TableCell className="font-mono">{s.version}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <p className="mt-2 text-xs text-fg-subtle">Version shown is the current registration only — no history (F-9).</p>
            </div>
            <div className="rounded-xl border border-border bg-surface p-4">
              <div className="text-[11px] uppercase tracking-wide text-fg-subtle">Latest signal · {strategies[0]?.name}</div>
              {signalsQuery.isLoading && <p className="mt-2 text-sm text-fg-muted">Loading…</p>}
              {signalsQuery.isSuccess && !latest && <p className="mt-2 text-sm text-fg-muted">No signals yet.</p>}
              {latest && (
                <div className="mt-2 space-y-1">
                  <div className="font-mono text-2xl font-semibold tabular-nums text-fg">
                    {Number.parseFloat(latest.value).toLocaleString(undefined, { maximumFractionDigits: 4 })}
                  </div>
                  <Badge variant={latest.validation_status === 'VALID' ? 'profit' : 'warning'}>{latest.validation_status}</Badge>
                  <p className="text-xs text-fg-muted">{fmtTime(latest.ts)}</p>
                  <p className="text-xs text-fg-subtle">{signals.length} recent signals</p>
                </div>
              )}
            </div>
          </div>
        )}
        {query.isSuccess && strategies.length > 0 && (
          <SourceNote>core.strategies + core.signals · GET /v1/strategies, /v1/strategies/{'{id}'}/signals</SourceNote>
        )}
      </CardContent>
    </Card>
  )
}

// ── NEW WIDGETS (owner request) — all read EXISTING data only; no new backend
//    compute. Each cites its real source and fabricates nothing. ──────────────

// Top movers: 24h % change per asset, computed from the same 1h OHLCV bars the
// watchlist already loads (24 one-hour bars back vs latest close). useQueries
// shares the ['bars', id, '1h'] cache with the watchlist rows — no extra round
// trips. Ranks the full active universe into best/worst 3.
function TopMoversWidget() {
  const assetsQuery = useAssets()
  const assets = assetsQuery.data ?? []
  const barsResults = useQueries({
    queries: assets.map((a) => ({
      queryKey: ['bars', a.id, '1h'],
      queryFn: () => marketsService.getBars(a.id, '1h'),
      enabled: Boolean(a.id),
    })),
  })

  const movers = assets
    .map((asset, i) => {
      const bars = barsResults[i]?.data ?? []
      const last = bars.at(-1)
      const ref = bars.length > 24 ? bars[bars.length - 25] : bars[0]
      if (!last || !ref) return null
      const lastC = Number.parseFloat(last.close)
      const refC = Number.parseFloat(ref.close)
      if (!refC) return null
      const pct = ((lastC - refC) / refC) * 100
      const closes = bars.slice(-24).map((b) => Number.parseFloat(b.close))
      return { asset, pct, last: lastC, closes }
    })
    .filter((m): m is { asset: Asset; pct: number; last: number; closes: number[] } => m !== null)
    .sort((a, b) => b.pct - a.pct)

  const anyLoading = barsResults.some((r) => r.isLoading)
  const gainers = movers.slice(0, 3)
  const losers = movers.slice(-3).reverse().filter((l) => !gainers.includes(l))

  return (
    <Card elevation="flat">
      <WidgetHead
        icon={<TrendingUp size={16} />}
        title="Top movers"
        right={movers.length ? <Badge variant="neutral">24h</Badge> : null}
      />
      <CardContent className="space-y-3">
        {(assetsQuery.isLoading || (anyLoading && movers.length === 0)) && <div className="skeleton h-28 w-full" />}
        {assetsQuery.isError && <ErrorState description="Could not load assets." onRetry={() => assetsQuery.refetch()} />}
        {!anyLoading && movers.length === 0 && assetsQuery.isSuccess && (
          <EmptyState title="No price history" description="Not enough bars to compute movers yet." />
        )}
        {movers.length > 0 && (
          <>
            <MoverGroup label="Leaders" rows={gainers} />
            {losers.length > 0 && <MoverGroup label="Laggards" rows={losers} />}
            <SourceNote>market_data.ohlcv_bars · GET /v1/assets/{'{id}'}/bars (1h)</SourceNote>
          </>
        )}
      </CardContent>
    </Card>
  )
}

function MoverGroup({ label, rows }: { label: string; rows: { asset: Asset; pct: number; last: number; closes: number[] }[] }) {
  return (
    <div>
      <div className="mb-1 text-[11px] uppercase tracking-wide text-fg-subtle">{label}</div>
      <div className="space-y-0.5">
        {rows.map(({ asset, pct, last, closes }) => (
          <div key={asset.id} className="flex items-center gap-2.5 rounded-lg px-1.5 py-1.5">
            <CryptoIcon symbol={asset.symbol} size={20} />
            <span className="min-w-0 flex-1 truncate text-sm font-medium text-fg">{asset.symbol}</span>
            {closes.length > 1 && <Sparkline data={closes} width={48} height={18} />}
            <span className="w-20 text-right font-mono text-xs tabular-nums text-fg-muted">{fmtMoney(String(last))}</span>
            <span className={cn('w-16 text-right font-mono text-xs font-semibold tabular-nums', pct >= 0 ? 'text-profit' : 'text-risk')}>
              {pct >= 0 ? '+' : ''}{pct.toFixed(2)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Execution summary: TODAY's order lifecycle for the active portfolio —
// fill rate and approval rate (approved = anything not REJECTED). Real order
// rows only; "today" is the local calendar day, and an empty day says so.
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
    <Card elevation="flat">
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
            <SourceNote>core.orders · GET /v1/portfolios/{'{id}'}/orders (created today)</SourceNote>
          </>
        )}
      </CardContent>
    </Card>
  )
}

// Signal activity across ACTIVE strategies: per active strategy, how many
// signals it has emitted and how many validated, plus its latest emission.
// Only active strategies are shown (honest — inactive ones aren't "active").
function SignalActivityWidget() {
  const query = useStrategies()
  const strategies = query.data ?? []
  const active = strategies.filter((s) => s.status === 'ACTIVE')

  return (
    <Card elevation="flat">
      <WidgetHead
        icon={<Radio size={16} />}
        title="Signal activity"
        right={query.isSuccess ? <Badge variant={active.length ? 'profit' : 'neutral'}>{active.length} active</Badge> : null}
      />
      <CardContent className="space-y-2">
        {query.isLoading && <div className="skeleton h-28 w-full" />}
        {query.isError && <ErrorState description="Could not load strategies." onRetry={() => query.refetch()} />}
        {query.isSuccess && active.length === 0 && (
          <EmptyState icon={<Radio size={20} />} title="No active strategies" description="No strategy is currently active to emit signals." />
        )}
        {active.map((s) => <SignalActivityRow key={s.id} strategy={s} />)}
        {active.length > 0 && <SourceNote>core.signals · GET /v1/strategies/{'{id}'}/signals</SourceNote>}
      </CardContent>
    </Card>
  )
}

function SignalActivityRow({ strategy }: { strategy: Strategy }) {
  const query = useSignals(strategy.id)
  const signals = query.data ?? []
  const valid = signals.filter((s) => s.validation_status === 'VALID').length
  const latest = signals.length > 0 ? [...signals].sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime())[0] : null

  return (
    <div className="flex items-center gap-3 rounded-lg border border-border bg-surface/60 px-3 py-2.5">
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium text-fg">{strategy.name}</div>
        <div className="text-[11px] text-fg-subtle">
          {query.isLoading ? 'loading…' : latest ? `latest ${fmtTime(latest.ts)}` : 'no signals yet'}
        </div>
      </div>
      <div className="text-right">
        <div className="font-mono text-lg font-semibold tabular-nums text-fg">{signals.length}</div>
        <div className="text-[11px] text-fg-subtle">{valid} valid</div>
      </div>
    </div>
  )
}
