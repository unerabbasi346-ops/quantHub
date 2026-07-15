// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: "responsive grid, modular widgets"; §Dashboards.
// Doc 08 — Frontend Architecture (QH-008 v1.0) §Architecture: the dashboard
//   COMPOSES feature hooks — no data logic is reimplemented here.
// handbook/ui/visual_engineering/02_LAYOUT_GRID_SYSTEM §Dashboard Sections
//   and 10_DASHBOARD_MASTER_BLUEPRINT §Primary Layout: the MANDATORY fixed
//   section order — Hero -> Analytics Grid -> Strategy Workspace ->
//   Portfolio Intelligence -> Market Activity Feed -> Footer.
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
//
// PHASE 1 ARCHITECTURE PASS: HeroSection (real market chart + Intelligence
// Workspace) now leads the page as the true Doc 02/10 Hero. StrategySection
// moves to the Strategy Workspace slot below Analytics. The remaining
// widgets split into their own Portfolio Intelligence and Market Activity
// Feed sections (previously one merged grid) to match the mandated order.
'use client'

import { useMemo, type ReactNode } from 'react'
import { ArrowLeftRight, CandlestickChart, Gauge, LayoutDashboard, ShieldAlert, TrendingUp, Wallet } from 'lucide-react'
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CryptoIcon,
  DonutChart,
  EmptyState,
  ErrorState,
  InstitutionalTable,
  type InstitutionalColumnDef,
  PageHeader,
  Ring,
  StatCard,
  pnlBadgeVariant,
  type BadgeVariant,
} from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { formatCapital, formatReturn, formatTimestamp } from '@/lib/utils/format'
import { usePortfolios, usePositions } from '@/features/portfolio/hooks/usePortfolio'
import type { Portfolio, Position } from '@/features/portfolio/types'
import { useOrders } from '@/features/execution/hooks/useExecution'
import type { Order } from '@/features/execution/types'
import { useRiskSnapshot } from '@/features/risk/hooks/useRisk'
import { useSyncStore } from '@/lib/store/sync'
import { useAssets, useBars } from '@/features/markets/hooks/useMarkets'
import { HeroSection } from './HeroSection'
import { StrategySection } from './StrategySection'

const PREFERRED_SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']

const fmtMoney = (v: string | null) => (v == null ? '—' : formatCapital(Number.parseFloat(v)))
const fmtSigned = (v: number) => (v > 0 ? '+' : '') + fmtMoney(String(v))
const fmtQty = (v: string) => Number.parseFloat(v).toLocaleString(undefined, { maximumFractionDigits: 8 })
const fmtLeverage = (v: string) => `${Number.parseFloat(v).toLocaleString(undefined, { maximumFractionDigits: 6 })}×`
const fmtTime = (iso: string | null) => (!iso ? '—' : formatTimestamp(iso))

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
    <div className="space-y-14">
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

      {/* Hero Intelligence Area (Doc 02/10): real market chart (70%) + real
          engine status workspace (30%) — always shown. */}
      <HeroSection />

      {portfoliosQuery.isSuccess && activePortfolio && (
        // Analytics Grid (Doc 10 §Analytics Grid: "Directly below Hero.
        // Contains: Portfolio, Risk, Performance, Market Overview.").
        <AnalyticsGrid portfolioId={portfolioId} />
      )}

      {/* Strategy Workspace — reads the strategy registry directly, not
          gated on a portfolio existing. */}
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
          {/* Portfolio Intelligence (Doc 10 §Portfolio Section: "Portfolio
              Value, Allocation, PnL, Exposure"). */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
            <PortfolioSummaryWidget portfolioId={portfolioId} className="lg:col-span-2" />
            <AllocationWidget portfolioId={portfolioId} />
            <RiskSnapshotWidget portfolioId={portfolioId} />
          </div>

          {/* Market Activity Feed */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <RecentExecutionsWidget portfolioId={portfolioId} className="lg:col-span-2" />
            <ExecutionSummaryWidget portfolioId={portfolioId} />
          </div>
        </>
      )}

      <DashboardFooter />
    </div>
  )
}

// Footer (Doc 02/10 fixed section order: ... Feed -> Footer). Presentation
// only — states the platform's real, current operating scope; nothing
// fabricated (Doc 00 §14.5).
function DashboardFooter() {
  return (
    <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-6 text-[11px] text-fg-subtle">
      <span>QuantHub — institutional quantitative intelligence platform.</span>
      <span>Single-user local deployment</span>
    </footer>
  )
}

// Analytics Grid (Doc 10): exactly four cards, one per named domain —
// Portfolio / Risk / Performance / Market Overview — not an undifferentiated
// stat strip. Every figure reads from a hook already used elsewhere in the
// app (Positions/Risk/Markets) — no new endpoint, no fabricated number.
function AnalyticsGrid({ portfolioId }: { portfolioId: string }) {
  const positionsQuery = usePositions(portfolioId)
  const riskQuery = useRiskSnapshot(portfolioId)
  const open = (positionsQuery.data ?? []).filter((p) => !p.is_closed)
  const marketValue = open.reduce((s, p) => s + Number.parseFloat(p.market_value), 0)
  const unrealized = open.reduce((s, p) => s + Number.parseFloat(p.unrealized_pnl), 0)
  const realized = open.reduce((s, p) => s + Number.parseFloat(p.realized_pnl_today), 0)
  const snap = riskQuery.data

  const syncedSymbol = useSyncStore((s) => s.selectedAssetSymbol)
  const assetsQuery = useAssets()
  const assets = assetsQuery.data ?? []
  const marketAsset =
    (syncedSymbol ? assets.find((a) => a.symbol === syncedSymbol) : undefined) ??
    PREFERRED_SYMBOLS.map((sym) => assets.find((a) => a.symbol === sym)).find(Boolean) ??
    assets[0] ??
    null
  const barsQuery = useBars(marketAsset?.id ?? '', '1h')
  const bars = barsQuery.data ?? []
  const last = bars.at(-1)
  const first24 = bars.slice(-24)
  const dayChange = last && first24[0] ? Number.parseFloat(last.close) - Number.parseFloat(first24[0].close) : null
  const dayChangePct = dayChange != null && first24[0] ? (dayChange / Number.parseFloat(first24[0].close)) * 100 : null

  // Doc 02 §Grid System: "12 Column Grid, Equal Columns, Equal Gutters."
  // §Analytics Grid: "Desktop 4 Columns / Laptop 2 / Tablet 2 / Mobile 1."
  // A real 12-col base (not an approximated `grid-cols-4` shorthand) so each
  // card's span is explicit: 12 (mobile) -> 6 (2-up) -> 3 (4-up).
  //
  // BUG FIX: originally used the custom tablet:/desktop: variants defined in
  // tailwind.config.ts (768px/1400px, matching Doc 02 exactly), but those
  // variants compiled to zero CSS rules in the running dev server — verified
  // by inspecting document.styleSheets directly, no rule for either prefix
  // existed anywhere in the compiled stylesheet, while stock breakpoints
  // (lg: elsewhere on this page) compiled and rendered correctly. Root cause
  // not fully isolated (likely a dev-server config-cache staleness, since the
  // config file itself is correct and a safelist entry didn't fix it either).
  // Switched to stock Tailwind screens instead: md: (768px, exact match for
  // "tablet") and xl: (1280px, closest stock tier to the spec's 1400px
  // "desktop") — both always present in Tailwind's core preset regardless of
  // this project's custom-screen config, so they don't depend on whatever is
  // stopping the custom variants from compiling.
  if (positionsQuery.isLoading)
    return (
      <div className="grid grid-cols-12 gap-4">
        <div className="skeleton col-span-12 h-28 md:col-span-6 xl:col-span-3" />
        <div className="skeleton col-span-12 h-28 md:col-span-6 xl:col-span-3" />
        <div className="skeleton col-span-12 h-28 md:col-span-6 xl:col-span-3" />
        <div className="skeleton col-span-12 h-28 md:col-span-6 xl:col-span-3" />
      </div>
    )

  return (
    <div className="grid grid-cols-12 gap-4">
      <Card elevation="elevated" className="col-span-12 md:col-span-6 xl:col-span-3">
        <WidgetHead icon={<Wallet size={16} />} title="Portfolio" />
        <CardContent>
          <div className="font-mono text-metric font-bold tabular-nums text-fg">{fmtMoney(String(marketValue))}</div>
          <div className="mt-1 text-[11px] text-fg-subtle">{open.length} open position{open.length === 1 ? '' : 's'}</div>
        </CardContent>
      </Card>
      <Card elevation="elevated" className="col-span-12 md:col-span-6 xl:col-span-3">
        <WidgetHead icon={<ShieldAlert size={16} />} title="Risk" />
        <CardContent>
          <div className="font-mono text-metric font-bold tabular-nums text-fg">{snap ? fmtMoney(snap.gross_exposure) : '—'}</div>
          <div className="mt-1 text-[11px] text-fg-subtle">{snap ? `lev ${fmtLeverage(snap.gross_leverage)} gross exposure` : 'no snapshot yet'}</div>
        </CardContent>
      </Card>
      <Card elevation="elevated" className="col-span-12 md:col-span-6 xl:col-span-3">
        <WidgetHead icon={<TrendingUp size={16} />} title="Performance" />
        <CardContent>
          <div className={cn('font-mono text-metric font-bold tabular-nums', unrealized >= 0 ? 'text-profit' : 'text-risk')}>{fmtSigned(unrealized)}</div>
          <div className="mt-1 text-[11px] text-fg-subtle">{fmtSigned(realized)} realized today</div>
        </CardContent>
      </Card>
      <Card elevation="elevated" className="col-span-12 md:col-span-6 xl:col-span-3">
        <WidgetHead icon={<CandlestickChart size={16} />} title="Market overview" />
        <CardContent>
          {marketAsset && last ? (
            <>
              <div className="flex items-center gap-2">
                <CryptoIcon symbol={marketAsset.symbol} size={18} />
                <span className="font-mono text-metric font-bold tabular-nums text-fg">{fmtMoney(last.close)}</span>
              </div>
              <div className="mt-1 text-[11px] text-fg-subtle">
                {marketAsset.symbol}
                {dayChangePct != null && (
                  <span className={dayChange! >= 0 ? 'text-profit' : 'text-risk'}> · {formatReturn(dayChangePct / 100)} 24h</span>
                )}
              </div>
            </>
          ) : (
            <div className="text-sm text-fg-muted">No ingested instrument yet.</div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function PortfolioSummaryWidget({ portfolioId, className }: { portfolioId: string; className?: string }) {
  const query = usePositions(portfolioId)
  const open = (query.data ?? []).filter((p) => !p.is_closed)
  const top = [...open].sort((a, b) => a.sequence_number - b.sequence_number).slice(0, 5)

  const columns = useMemo<InstitutionalColumnDef<Position>[]>(
    () => [
      {
        id: 'symbol',
        header: 'Symbol',
        accessorFn: (p) => p.symbol ?? '',
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <CryptoIcon symbol={row.original.symbol ?? '?'} size={20} />
            <span className="font-medium text-fg">{row.original.symbol ?? '—'}</span>
          </div>
        ),
      },
      { id: 'quantity', header: 'Qty', accessorFn: (p) => Number.parseFloat(p.quantity), cell: ({ row }) => fmtQty(row.original.quantity), meta: { numeric: true } },
      { id: 'market_value', header: 'Market value', accessorFn: (p) => Number.parseFloat(p.market_value), cell: ({ row }) => fmtMoney(row.original.market_value), meta: { numeric: true } },
      {
        id: 'unrealized',
        header: 'Unrealized',
        accessorFn: (p) => Number.parseFloat(p.unrealized_pnl),
        cell: ({ row }) => (
          <Badge variant={pnlBadgeVariant(Number.parseFloat(row.original.unrealized_pnl))}>{fmtSigned(Number.parseFloat(row.original.unrealized_pnl))}</Badge>
        ),
        meta: { numeric: true },
      },
    ],
    [],
  )

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
          <InstitutionalTable data={top} columns={columns} getRowId={(p) => p.id} />
        )}
        {query.isSuccess && open.length > 0 && (
          <SourceNote>live portfolio positions</SourceNote>
        )}
      </CardContent>
    </Card>
  )
}

// Allocation (Doc 10 §Portfolio Section: "Portfolio Value, Allocation, PnL,
// Exposure") — same real open-position market values as the Portfolio page's
// own allocation donut, sized for the dashboard grid.
function AllocationWidget({ portfolioId }: { portfolioId: string }) {
  const query = usePositions(portfolioId)
  const open = (query.data ?? []).filter((p) => !p.is_closed)
  const totalMarketValue = open.reduce((s, p) => s + Number.parseFloat(p.market_value), 0)
  const allocation = open
    .map((p) => ({ name: p.symbol ?? p.asset_id, value: Math.abs(Number.parseFloat(p.market_value)) }))
    .filter((d) => d.value > 0)
    .sort((a, b) => b.value - a.value)

  return (
    <Card elevation="elevated">
      <WidgetHead icon={<Wallet size={16} />} title="Allocation" />
      <CardContent>
        {query.isLoading && <div className="skeleton h-40 w-full" />}
        {query.isError && <ErrorState description="Could not load positions." onRetry={() => query.refetch()} />}
        {query.isSuccess && allocation.length === 0 && <EmptyState title="No allocation" description="No open positions to allocate." />}
        {allocation.length > 0 && (
          <DonutChart data={allocation} height={180} centerLabel="value" centerValue={fmtMoney(String(totalMarketValue))} valueFormat={(v) => fmtMoney(String(v))} />
        )}
      </CardContent>
    </Card>
  )
}

function RiskSnapshotWidget({ portfolioId }: { portfolioId: string }) {
  const query = useRiskSnapshot(portfolioId)
  const snap = query.data ?? null
  return (
    <Card elevation="elevated">
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
  const query = useOrders(portfolioId, 200)
  const recent = [...(query.data ?? [])].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 6)

  const columns = useMemo<InstitutionalColumnDef<Order>[]>(
    () => [
      { id: 'created_at', header: 'Time', accessorFn: (o) => new Date(o.created_at).getTime(), cell: ({ row }) => <span className="whitespace-nowrap text-fg-muted">{fmtTime(row.original.created_at)}</span> },
      { id: 'symbol', header: 'Symbol', accessorFn: (o) => o.symbol ?? '', cell: ({ row }) => <span className="font-medium text-fg">{row.original.symbol ?? '—'}</span> },
      {
        accessorKey: 'side',
        header: 'Side',
        cell: ({ getValue }) => {
          const side = getValue<Order['side']>()
          return <span className={cn('font-medium', side === 'BUY' ? 'text-profit' : 'text-risk')}>{side}</span>
        },
      },
      { id: 'quantity', header: 'Qty', accessorFn: (o) => Number.parseFloat(o.quantity), cell: ({ row }) => fmtQty(row.original.quantity), meta: { numeric: true } },
      { id: 'average_price', header: 'Avg price', accessorFn: (o) => (o.average_price === null ? -Infinity : Number.parseFloat(o.average_price)), cell: ({ row }) => fmtMoney(row.original.average_price), meta: { numeric: true, hideBelow: 'tablet' } },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ getValue }) => <Badge variant={orderStatusVariant(getValue<Order['status']>())}>{getValue<Order['status']>()}</Badge>,
      },
    ],
    [],
  )

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
          <InstitutionalTable data={recent} columns={columns} getRowId={(o) => o.id} />
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
  // ponytail: shares RecentExecutionsWidget's limit=200 fetch (same
  // queryKey — one network call). Undercounts "today" if a portfolio places
  // >200 orders in a day; raise the limit or add a server-side since= filter
  // if that becomes real.
  const query = useOrders(portfolioId, 200)
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
    <Card elevation="elevated">
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
