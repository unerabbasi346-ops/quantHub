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

import { memo, useMemo, type ReactNode } from 'react'
import { ArrowLeftRight, CandlestickChart, Gauge, LayoutDashboard, Radio, ShieldAlert, TrendingUp, Wallet } from 'lucide-react'
import { useQueries } from '@tanstack/react-query'
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CryptoIcon,
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
import { useAssets, useBars } from '@/features/markets/hooks/useMarkets'
import { useHermesHealth, useHermesStrategies } from '@/features/hermes/hooks/useHermes'
import { useStrategies } from '@/features/strategies/hooks/useStrategies'
import { strategiesService } from '@/features/strategies/services/strategies.service'
import { fmtReturnPct } from '@/features/strategies/components/tables'
import type { Backtest } from '@/features/strategies/types'
import { HeroSection } from './HeroSection'
import { StrategySection } from './StrategySection'

const PREFERRED_SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']

const fmtMoney = (v: string | null) => (v == null ? '—' : formatCapital(Number.parseFloat(v)))
const fmtSigned = (v: number) => (v > 0 ? '+' : '') + fmtMoney(String(v))
const fmtQty = (v: string) => Number.parseFloat(v).toLocaleString(undefined, { maximumFractionDigits: 8 })
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
            <SignalActivityWidget />
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
const AnalyticsGrid = memo(function AnalyticsGrid({ portfolioId: _portfolioId }: { portfolioId: string }) {
  // Backtest-centric redesign (UI wiring step, owner request): all 4 cards
  // now read from real backtest/strategy data instead of the live portfolio
  // — a single unlevered spot position ($25.25) made every card read nearly
  // identically before. `portfolioId` is kept in the signature (call site
  // still resolves it) but no longer used here.
  const strategiesQuery = useStrategies()
  const strategies = strategiesQuery.data ?? []
  const activeStrategies = strategies.filter((s) => s.status.toUpperCase() === 'ACTIVE')
  const backtestQueries = useQueries({
    queries: strategies.map((s) => ({
      queryKey: ['backtests', s.id],
      queryFn: () => strategiesService.getBacktests(s.id),
      enabled: Boolean(s.id),
    })),
  })
  const allBacktests: Backtest[] = backtestQueries.flatMap((q) => q.data ?? [])
  const completedBacktests = allBacktests.filter((b) => b.status === 'COMPLETED')

  // Best (highest total_return) COMPLETED backtest across every registered
  // strategy — drives both the Best Backtest and vs-BTC-Benchmark cards.
  const bestBacktest = completedBacktests
    .filter((b) => b.total_return != null)
    .reduce<Backtest | null>((best, b) => {
      const ret = Number.parseFloat(b.total_return!)
      const bestRet = best ? Number.parseFloat(best.total_return!) : -Infinity
      return ret > bestRet ? b : best
    }, null)
  const bestReturnPct = bestBacktest ? Number.parseFloat(bestBacktest.total_return!) : null
  const bestBenchmarkPct = bestBacktest?.benchmark_return != null ? Number.parseFloat(bestBacktest.benchmark_return) : null
  const bestStrategyName = bestBacktest?.strategy_id
    ? strategies.find((s) => s.id === bestBacktest.strategy_id)?.name ?? bestBacktest.name
    : bestBacktest?.name ?? null

  // Market card: BTC + ETH, Doc 10 §Analytics Grid's "Market Overview" —
  // fixed reference instruments, not the page's synced/selected asset
  // (which belongs to the Markets page).
  const assetsQuery = useAssets()
  const assets = assetsQuery.data ?? []
  const btcAsset = assets.find((a) => a.symbol === 'BTC/USDT') ?? null
  const ethAsset = assets.find((a) => a.symbol === 'ETH/USDT') ?? null
  const btcBarsQuery = useBars(btcAsset?.id ?? '', '1h')
  const ethBarsQuery = useBars(ethAsset?.id ?? '', '1h')

  const pctChange = (bars: { close: string }[]) => {
    const last = bars.at(-1)
    const first24 = bars.slice(-24)[0]
    if (!last || !first24) return null
    return ((Number.parseFloat(last.close) - Number.parseFloat(first24.close)) / Number.parseFloat(first24.close)) * 100
  }
  const btcBars = btcBarsQuery.data ?? []
  const ethBars = ethBarsQuery.data ?? []
  const btcLast = btcBars.at(-1)
  const ethLast = ethBars.at(-1)
  const btcChangePct = pctChange(btcBars)
  const ethChangePct = pctChange(ethBars)

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
  if (strategiesQuery.isLoading)
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
        <WidgetHead icon={<Wallet size={16} />} title="Active Strategies" />
        <CardContent>
          <div className="font-mono text-metric font-bold tabular-nums text-fg">{activeStrategies.length}</div>
          <div className="mt-1 text-[11px] text-fg-subtle">
            {activeStrategies.length === 1 ? '1 strategy running' : `${activeStrategies.length} strategies running`}
          </div>
        </CardContent>
      </Card>
      <Card elevation="elevated" className="col-span-12 md:col-span-6 xl:col-span-3">
        <WidgetHead icon={<TrendingUp size={16} />} title="Best Backtest" />
        <CardContent>
          {bestReturnPct != null ? (
            <>
              <div className={cn('font-mono text-metric font-bold tabular-nums', bestReturnPct >= 0 ? 'text-profit' : 'text-risk')}>
                {fmtReturnPct(bestBacktest!.total_return)}
              </div>
              <div className="mt-1 truncate text-[11px] text-fg-subtle">
                {bestStrategyName}
                {bestBacktest?.symbol && <> · {bestBacktest.symbol}</>}
              </div>
            </>
          ) : (
            <div className="text-sm text-fg-muted">No completed backtests yet.</div>
          )}
        </CardContent>
      </Card>
      <Card elevation="elevated" className="col-span-12 md:col-span-6 xl:col-span-3">
        <WidgetHead icon={<ShieldAlert size={16} />} title="vs BTC Benchmark" />
        <CardContent>
          {bestReturnPct != null && bestBenchmarkPct != null ? (
            <>
              <div className="flex items-baseline gap-1.5 font-mono font-bold tabular-nums">
                <span className={cn('text-metric', bestReturnPct >= 0 ? 'text-profit' : 'text-risk')}>{fmtReturnPct(bestBacktest!.total_return)}</span>
                <span className="text-sm text-fg-subtle">strategy</span>
              </div>
              <div className="mt-1 text-[11px] text-fg-subtle">
                vs <span className={cn('font-mono', bestBenchmarkPct >= 0 ? 'text-profit' : 'text-risk')}>{fmtReturnPct(bestBacktest!.benchmark_return)}</span> BTC buy-and-hold, same period
              </div>
            </>
          ) : (
            <div className="text-sm text-fg-muted">No benchmark comparison yet.</div>
          )}
        </CardContent>
      </Card>
      <Card elevation="elevated" className="col-span-12 md:col-span-6 xl:col-span-3">
        <WidgetHead icon={<CandlestickChart size={16} />} title="Market overview" />
        <CardContent className="space-y-2.5">
          {btcAsset && btcLast ? (
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <CryptoIcon symbol={btcAsset.symbol} size={16} />
                <span className="font-mono text-sm font-bold tabular-nums text-fg">{fmtMoney(btcLast.close)}</span>
              </div>
              {btcChangePct != null && (
                <span className={cn('text-[11px]', btcChangePct >= 0 ? 'text-profit' : 'text-risk')}>{formatReturn(btcChangePct / 100)}</span>
              )}
            </div>
          ) : (
            <div className="text-[11px] text-fg-muted">BTC not ingested yet.</div>
          )}
          {ethAsset && ethLast ? (
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <CryptoIcon symbol={ethAsset.symbol} size={16} />
                <span className="font-mono text-sm font-bold tabular-nums text-fg">{fmtMoney(ethLast.close)}</span>
              </div>
              {ethChangePct != null && (
                <span className={cn('text-[11px]', ethChangePct >= 0 ? 'text-profit' : 'text-risk')}>{formatReturn(ethChangePct / 100)}</span>
              )}
            </div>
          ) : (
            <div className="text-[11px] text-fg-muted">ETH not ingested yet.</div>
          )}
        </CardContent>
      </Card>
    </div>
  )
})

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
        title="Live position"
        right={query.isSuccess ? <Badge variant="neutral">{open.length} open</Badge> : null}
      />
      <p className="px-5 pt-1 text-[11px] text-fg-subtle">Paper trading — simulated position, not real capital.</p>
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

// Signal Activity (replaces the Allocation donut, which duplicated the
// Portfolio Summary next to it) — real Hermes lifecycle data: signals over
// the last 24h, the most recent signal timestamp, and which strategies are
// actively emitting.
function SignalActivityWidget() {
  const healthQuery = useHermesHealth()
  const strategiesQuery = useHermesStrategies()
  const health = healthQuery.data ?? null
  const lifecycles = strategiesQuery.data?.strategies ?? []
  const lastSignalTs = lifecycles
    .map((s) => s.last_signal_ts)
    .filter((ts): ts is string => ts != null)
    .sort()
    .at(-1) ?? null
  const activeNames = lifecycles.filter((s) => s.status.toUpperCase() === 'ACTIVE').map((s) => s.name)

  return (
    <Card elevation="elevated">
      <WidgetHead icon={<Radio size={16} />} title="Signal activity" />
      <CardContent className="space-y-3">
        {(healthQuery.isLoading || strategiesQuery.isLoading) && <div className="skeleton h-28 w-full" />}
        {healthQuery.isError && <ErrorState description="Could not load Hermes status." onRetry={() => healthQuery.refetch()} />}
        {health && strategiesQuery.isSuccess && (
          <>
            <div>
              <div className="font-mono text-metric font-bold tabular-nums text-fg">{health.strategy_engine.signals_24h}</div>
              <div className="mt-0.5 text-[11px] text-fg-subtle">signals generated · last 24h</div>
            </div>
            <div className="space-y-1.5 border-t border-border pt-3 text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="text-fg-subtle">Last signal</span>
                <span className="font-mono text-fg">{lastSignalTs ? fmtTime(lastSignalTs) : '—'}</span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-fg-subtle">Active strategies</span>
                <span className="truncate font-mono text-fg" title={activeNames.join(', ')}>
                  {activeNames.length === 0 ? '—' : activeNames.length === 1 ? activeNames[0] : `${activeNames.length} active`}
                </span>
              </div>
            </div>
            <SourceNote>Hermes strategy lifecycle (polled every 60s)</SourceNote>
          </>
        )}
      </CardContent>
    </Card>
  )
}

// Risk Snapshot (professional layout, owner request): the live position with
// entry/P&L/leverage from real portfolio data, plus an honest plain-language
// note for the metrics that still need return-series computation.
function RiskSnapshotWidget({ portfolioId }: { portfolioId: string }) {
  const query = useRiskSnapshot(portfolioId)
  const positionsQuery = usePositions(portfolioId)
  const snap = query.data ?? null
  const open = (positionsQuery.data ?? []).filter((p) => !p.is_closed)
  const pos = open[0] ?? null
  const qty = pos ? Number.parseFloat(pos.quantity) : null
  const entry = pos ? Number.parseFloat(pos.average_entry_price) : null
  const pnl = pos ? Number.parseFloat(pos.unrealized_pnl) : null
  const cost = qty != null && entry != null ? Math.abs(qty * entry) : null
  const pnlPct = pnl != null && cost != null && cost > 0 ? (pnl / cost) * 100 : null

  return (
    <Card elevation="elevated">
      <WidgetHead
        icon={<ShieldAlert size={16} />}
        title="Risk snapshot"
        right={snap ? <Badge variant={snap.breaches.length > 0 ? 'risk' : 'profit'}>● Live</Badge> : null}
      />
      <CardContent className="space-y-3">
        {(query.isLoading || positionsQuery.isLoading) && <div className="skeleton h-28 w-full" />}
        {query.isError && <ErrorState description="Could not load risk snapshot." onRetry={() => query.refetch()} />}
        {query.isSuccess && positionsQuery.isSuccess && !pos && (
          <EmptyState title="No open position" description="No open positions — nothing at risk right now." />
        )}
        {pos && (
          <>
            <div className="space-y-1.5 text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="text-fg-subtle">Position</span>
                <span className="font-mono font-medium text-fg">
                  {pos.symbol ?? '—'} <span className={cn(qty != null && qty < 0 ? 'text-risk' : 'text-profit')}>{qty != null && qty < 0 ? 'SHORT' : 'LONG'}</span>
                  {open.length > 1 && <span className="text-fg-subtle"> +{open.length - 1} more</span>}
                </span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-fg-subtle">Size</span>
                <span className="font-mono tabular-nums text-fg">{fmtMoney(pos.market_value)}</span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-fg-subtle">Entry price</span>
                <span className="font-mono tabular-nums text-fg">{fmtMoney(pos.average_entry_price)}</span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-fg-subtle">Current P&L</span>
                <span className={cn('font-mono tabular-nums', pnl != null && pnl < 0 ? 'text-risk' : 'text-profit')}>
                  {pnl != null ? fmtSigned(pnl) : '—'}
                  {pnlPct != null && <> ({pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%)</>}
                </span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-fg-subtle">Leverage</span>
                <span className="font-mono tabular-nums text-fg">
                  {pos.leverage != null ? `${Number.parseFloat(pos.leverage).toFixed(1)}x` : '1.0x (spot)'}
                </span>
              </div>
            </div>
            <p className="border-t border-border pt-3 text-[11px] leading-relaxed text-fg-subtle">
              Advanced metrics (VaR, CVaR, drawdown, beta) require return-series computation — not available yet.
            </p>
            {snap && <SourceNote>live positions + risk snapshot ({fmtTime(snap.snapshot_at)})</SourceNote>}
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
  const recent = [...(query.data ?? [])].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 10)

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
