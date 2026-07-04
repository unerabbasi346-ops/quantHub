// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: "responsive grid, modular widgets"; §Dashboards: widgets for
//   "portfolio, positions, orders, signals, watchlists, risk metrics".
// Doc 08 — Frontend Architecture (QH-008 v1.0)
//   §Architecture: the dashboard COMPOSES presentation from the shared design
//   system + the five vertical slices' feature hooks — it does NOT reimplement
//   any data logic (this is assembly, Step 4.7); §State Management: TanStack Query.
// Per Doc 00 §14.11
//
// SCOPE (S-6): FIXED widget layout — customizable/draggable widgets are
// deferred. This is a responsive CSS grid of modular Card widgets, not a
// user-arrangeable dashboard.
//
// JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged): the portfolio-scoped widgets
// (summary, executions, risk) follow ONE active portfolio — the first active
// portfolio (portfolios[0]), the same "default to the first item" convention
// every other shell uses (MarketsShell's assets[0], etc.). A portfolio switcher
// on the dashboard would be a new interaction, not assembly, so it is deferred;
// the active portfolio's name is shown in the header so the context is explicit,
// never hidden. Markets and strategies widgets are global (not portfolio-scoped).
'use client'

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
  pnlBadgeVariant,
} from '@/components/ui'
import type { BadgeVariant } from '@/components/ui'
import { cn } from '@/lib/utils/cn'
// Reuse the REAL feature hooks/types from all five vertical slices — no new
// data logic is introduced here (Doc 08 §Architecture; Step 4.7 = assembly).
import { usePortfolios, usePositions } from '@/features/portfolio/hooks/usePortfolio'
import type { Portfolio } from '@/features/portfolio/types'
import { useOrders } from '@/features/execution/hooks/useExecution'
import type { Order } from '@/features/execution/types'
import { useRiskSnapshot } from '@/features/risk/hooks/useRisk'
import { useStrategies, useSignals } from '@/features/strategies/hooks/useStrategies'
import { useAssets, useBars } from '@/features/markets/hooks/useMarkets'
import type { Asset } from '@/features/markets/types'

// ── display formatting (Doc 06 §Data Visualization: consistent formatting) ──
// The authoritative precise values are the API's Decimal strings; these helpers
// are for readable presentation only — nothing downstream consumes them.
function fmtMoney(value: string | null): string {
  if (value == null) return '—'
  return Number.parseFloat(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function fmtSignedMoney(value: string): string {
  const n = Number.parseFloat(value)
  const sign = n > 0 ? '+' : ''
  return sign + fmtMoney(value)
}

function fmtQty(value: string): string {
  return Number.parseFloat(value).toLocaleString(undefined, {
    maximumFractionDigits: 8,
  })
}

// Leverage keeps fine precision (matches the Risk slice's fmtLeverage) so a
// small-but-nonzero ratio like 0.000252 is NOT rounded to a misleading 0.00.
function fmtLeverage(value: string): string {
  return `${Number.parseFloat(value).toLocaleString(undefined, { maximumFractionDigits: 6 })}×`
}

function fmtTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// A small labelled metric, reused across the summary widgets (Doc 06
// §Components — consistent metric presentation).
function Stat({ label, value, variant }: { label: string; value: string; variant?: BadgeVariant }) {
  const tone =
    variant === 'profit'
      ? 'text-profit'
      : variant === 'risk'
        ? 'text-risk'
        : 'text-fg'
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-fg-muted">{label}</div>
      <div className={cn('mt-0.5 text-lg font-semibold tabular-nums', tone)}>{value}</div>
    </div>
  )
}

export function DashboardShell() {
  const portfoliosQuery = usePortfolios()
  const portfolios = portfoliosQuery.data ?? []
  // Default to the first active portfolio (see JUDGMENT CALL header note).
  const activePortfolio: Portfolio | null = portfolios[0] ?? null
  const portfolioId = activePortfolio?.id ?? ''

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-fg">Dashboard</h1>
        <p className="mt-1 text-sm text-fg-muted">
          Live overview across markets, portfolio, execution, strategies, and risk
          {activePortfolio && (
            <>
              {' '}
              — portfolio <span className="font-medium text-fg">{activePortfolio.name}</span>
            </>
          )}
          .
        </p>
      </div>

      {portfoliosQuery.isLoading && (
        <Card>
          <CardContent>
            <LoadingState label="Loading portfolios…" />
          </CardContent>
        </Card>
      )}
      {portfoliosQuery.isError && (
        <Card>
          <CardContent>
            <ErrorState
              description="Could not load portfolios."
              onRetry={() => portfoliosQuery.refetch()}
            />
          </CardContent>
        </Card>
      )}
      {portfoliosQuery.isSuccess && portfolios.length === 0 && (
        <Card>
          <CardContent>
            <EmptyState
              title="No portfolios"
              description="No portfolios exist yet — nothing to summarize."
            />
          </CardContent>
        </Card>
      )}

      {/* Fixed responsive grid of modular widgets (Doc 06 §Layout / §Dashboards;
          draggable arrangement deferred per S-6). */}
      {portfoliosQuery.isSuccess && activePortfolio && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <PortfolioSummaryWidget portfolioId={portfolioId} className="lg:col-span-2" />
          <RiskSnapshotWidget portfolioId={portfolioId} />
          <RecentExecutionsWidget portfolioId={portfolioId} className="lg:col-span-2" />
          <MarketsWatchlistWidget />
          <StrategiesSignalsWidget className="lg:col-span-3" />
        </div>
      )}
    </div>
  )
}

// ── Widget: portfolio summary (positions + P&L) — Doc 06 §Dashboards ────────
function PortfolioSummaryWidget({
  portfolioId,
  className,
}: {
  portfolioId: string
  className?: string
}) {
  const query = usePositions(portfolioId)
  const positions = query.data ?? []
  const open = positions.filter((p) => !p.is_closed)

  // Aggregate P&L from the real position rows (parse the Decimal strings only
  // for the readable total; the per-row strings stay authoritative).
  const totalUnrealized = open.reduce((s, p) => s + Number.parseFloat(p.unrealized_pnl), 0)
  const totalRealizedToday = open.reduce(
    (s, p) => s + Number.parseFloat(p.realized_pnl_today),
    0,
  )
  const topPositions = [...open]
    .sort((a, b) => a.sequence_number - b.sequence_number)
    .slice(0, 5)

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Portfolio summary</CardTitle>
        {query.isSuccess && <Badge variant="neutral">{open.length} open</Badge>}
      </CardHeader>
      <CardContent className="space-y-4">
        {query.isLoading && <LoadingState label="Loading positions…" />}
        {query.isError && (
          <ErrorState description="Could not load positions." onRetry={() => query.refetch()} />
        )}
        {query.isSuccess && open.length === 0 && (
          <EmptyState title="No open positions" description="This portfolio holds no open positions." />
        )}
        {query.isSuccess && open.length > 0 && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Stat
                label="Unrealized P&L"
                value={fmtSignedMoney(totalUnrealized.toString())}
                variant={pnlBadgeVariant(totalUnrealized)}
              />
              <Stat
                label="Realized today"
                value={fmtSignedMoney(totalRealizedToday.toString())}
                variant={pnlBadgeVariant(totalRealizedToday)}
              />
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Qty</TableHead>
                  <TableHead>Market value</TableHead>
                  <TableHead>Unrealized</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {topPositions.map((p) => {
                  const pnl = Number.parseFloat(p.unrealized_pnl)
                  return (
                    <TableRow key={p.id}>
                      <TableCell className="font-medium text-fg">{p.symbol ?? '—'}</TableCell>
                      <TableCell numeric>{fmtQty(p.quantity)}</TableCell>
                      <TableCell numeric>{fmtMoney(p.market_value)}</TableCell>
                      <TableCell numeric>
                        <Badge variant={pnlBadgeVariant(pnl)}>{fmtSignedMoney(p.unrealized_pnl)}</Badge>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </>
        )}
      </CardContent>
    </Card>
  )
}

// ── Widget: risk snapshot (exposure/leverage + honest deferred F-18) ────────
function RiskSnapshotWidget({ portfolioId }: { portfolioId: string }) {
  const query = useRiskSnapshot(portfolioId)
  const snapshot = query.data ?? null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk snapshot</CardTitle>
        {snapshot && snapshot.breaches.length > 0 && (
          <Badge variant="risk">{snapshot.breaches.length} breach</Badge>
        )}
        {snapshot && snapshot.breaches.length === 0 && <Badge variant="profit">OK</Badge>}
      </CardHeader>
      <CardContent className="space-y-4">
        {query.isLoading && <LoadingState label="Loading risk snapshot…" />}
        {query.isError && (
          <ErrorState description="Could not load risk snapshot." onRetry={() => query.refetch()} />
        )}
        {query.isSuccess && !snapshot && (
          <EmptyState
            title="No snapshot"
            description="No risk snapshot has been computed for this portfolio yet."
          />
        )}
        {snapshot && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Stat label="Gross exposure" value={fmtMoney(snapshot.gross_exposure)} />
              <Stat label="Net exposure" value={fmtMoney(snapshot.net_exposure)} />
              <Stat label="Gross leverage" value={fmtLeverage(snapshot.gross_leverage)} />
              <Stat label="Net leverage" value={fmtLeverage(snapshot.net_leverage)} />
            </div>
            {/* Honest F-18 representation: the deferred §11.5.3 metrics are NAMED
                as not-yet-computed, never fabricated as a real 0. */}
            <div>
              <div className="text-xs uppercase tracking-wide text-fg-muted">
                Deferred metrics (F-18)
              </div>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {snapshot.deferred_metrics.map((m) => (
                  <Badge key={m.name} variant="warning" title={m.reason}>
                    {m.name}
                  </Badge>
                ))}
              </div>
            </div>
            <p className="text-xs text-fg-muted">As of {fmtTime(snapshot.snapshot_at)}</p>
          </>
        )}
      </CardContent>
    </Card>
  )
}

// ── Widget: recent executions (order blotter excerpt) — Doc 06 §Dashboards ──
function orderStatusVariant(status: Order['status']): BadgeVariant {
  if (status === 'FILLED') return 'profit'
  if (status === 'REJECTED') return 'risk'
  return 'info' // CREATED / VALIDATED
}

function RecentExecutionsWidget({
  portfolioId,
  className,
}: {
  portfolioId: string
  className?: string
}) {
  const query = useOrders(portfolioId)
  const orders = query.data ?? []
  // Most recent first — this is a blotter EXCERPT (Doc 06 §Dashboards "orders");
  // the full blotter lives in the Execution slice.
  const recent = [...orders]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 6)

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Recent executions</CardTitle>
        {query.isSuccess && <Badge variant="neutral">{orders.length} orders</Badge>}
      </CardHeader>
      <CardContent>
        {query.isLoading && <LoadingState label="Loading orders…" />}
        {query.isError && (
          <ErrorState description="Could not load orders." onRetry={() => query.refetch()} />
        )}
        {query.isSuccess && orders.length === 0 && (
          <EmptyState title="No orders" description="No orders have been placed for this portfolio." />
        )}
        {query.isSuccess && recent.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Symbol</TableHead>
                <TableHead>Side</TableHead>
                <TableHead>Qty</TableHead>
                <TableHead>Avg price</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recent.map((o) => (
                <TableRow key={o.id}>
                  <TableCell>{fmtTime(o.created_at)}</TableCell>
                  <TableCell className="font-medium text-fg">{o.symbol ?? '—'}</TableCell>
                  <TableCell>
                    <Badge variant="neutral">{o.side}</Badge>
                  </TableCell>
                  <TableCell numeric>{fmtQty(o.quantity)}</TableCell>
                  <TableCell numeric>{fmtMoney(o.average_price)}</TableCell>
                  <TableCell>
                    <Badge variant={orderStatusVariant(o.status)}>{o.status}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}

// ── Widget: markets watchlist — Doc 06 §Dashboards "watchlists" ─────────────
function MarketsWatchlistWidget() {
  const query = useAssets()
  const assets = query.data ?? []

  return (
    <Card>
      <CardHeader>
        <CardTitle>Watchlist</CardTitle>
        {query.isSuccess && <Badge variant="neutral">{assets.length}</Badge>}
      </CardHeader>
      <CardContent className="p-2">
        {query.isLoading && <LoadingState label="Loading assets…" />}
        {query.isError && (
          <ErrorState description="Could not load assets." onRetry={() => query.refetch()} />
        )}
        {query.isSuccess && assets.length === 0 && (
          <EmptyState title="No assets" description="No tradable assets are registered." />
        )}
        {query.isSuccess &&
          assets.map((asset) => <WatchlistRow key={asset.id} asset={asset} />)}
      </CardContent>
    </Card>
  )
}

// One watchlist row owns its own bars query (each asset = its own component, so
// the hook is called unconditionally). Reuses the Markets slice's 1h price path.
function WatchlistRow({ asset }: { asset: Asset }) {
  const barsQuery = useBars(asset.id, '1h')
  const bars = barsQuery.data ?? []
  const last = bars.length > 0 ? bars[bars.length - 1] : null
  const prev = bars.length > 1 ? bars[bars.length - 2] : null
  const change =
    last && prev ? Number.parseFloat(last.close) - Number.parseFloat(prev.close) : null
  const changePct =
    change != null && prev ? (change / Number.parseFloat(prev.close)) * 100 : null

  return (
    <div className="flex items-center justify-between rounded-md px-3 py-2">
      <div>
        <div className="text-sm font-medium text-fg">{asset.symbol}</div>
        <div className="text-xs uppercase text-fg-muted">{asset.exchange}</div>
      </div>
      <div className="text-right">
        {barsQuery.isLoading && <span className="text-xs text-fg-muted">…</span>}
        {barsQuery.isSuccess && !last && <span className="text-xs text-fg-muted">no bars</span>}
        {last && (
          <>
            <div className="text-sm font-semibold tabular-nums text-fg">{fmtMoney(last.close)}</div>
            {change != null && changePct != null && (
              <Badge variant={pnlBadgeVariant(change)}>
                {change >= 0 ? '+' : ''}
                {changePct.toFixed(2)}%
              </Badge>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ── Widget: strategies + signals — Doc 06 §Dashboards "signals" ─────────────
function StrategiesSignalsWidget({ className }: { className?: string }) {
  const query = useStrategies()
  const strategies = query.data ?? []
  // Latest signal is shown for the first strategy as a live sample of the
  // §10.3 signal stream (the full per-strategy view lives in the Strategies slice).
  const firstStrategyId = strategies[0]?.id ?? ''
  const signalsQuery = useSignals(firstStrategyId)
  const signals = signalsQuery.data ?? []
  const latestSignal =
    signals.length > 0
      ? [...signals].sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime())[0]
      : null

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Strategies &amp; signals</CardTitle>
        {query.isSuccess && <Badge variant="neutral">{strategies.length}</Badge>}
      </CardHeader>
      <CardContent className="space-y-4">
        {query.isLoading && <LoadingState label="Loading strategies…" />}
        {query.isError && (
          <ErrorState description="Could not load strategies." onRetry={() => query.refetch()} />
        )}
        {query.isSuccess && strategies.length === 0 && (
          <EmptyState title="No strategies" description="No strategies are registered yet." />
        )}
        {query.isSuccess && strategies.length > 0 && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Strategy</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Version</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {strategies.slice(0, 6).map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="font-medium text-fg">{s.name}</TableCell>
                      <TableCell>
                        <Badge variant={s.status === 'ACTIVE' ? 'profit' : 'neutral'}>
                          {s.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{s.version}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {/* Honest F-9 representation: `version` is the CURRENT registration
                  only — no version history exists, so we don't imply one. */}
              <p className="mt-2 text-xs text-fg-muted opacity-70">
                Version shown is the current registration only — no version history (F-9).
              </p>
            </div>
            <div className="rounded-md border border-border bg-surface-hover/40 p-3">
              <div className="text-xs uppercase tracking-wide text-fg-muted">
                Latest signal · {strategies[0]?.name}
              </div>
              {signalsQuery.isLoading && <p className="mt-2 text-sm text-fg-muted">Loading…</p>}
              {signalsQuery.isSuccess && !latestSignal && (
                <p className="mt-2 text-sm text-fg-muted">No signals generated yet.</p>
              )}
              {latestSignal && (
                <div className="mt-2 space-y-1">
                  <div className="text-2xl font-semibold tabular-nums text-fg">
                    {Number.parseFloat(latestSignal.value).toLocaleString(undefined, {
                      maximumFractionDigits: 4,
                    })}
                  </div>
                  <Badge variant={latestSignal.validation_status === 'VALID' ? 'profit' : 'warning'}>
                    {latestSignal.validation_status}
                  </Badge>
                  <p className="text-xs text-fg-muted">{fmtTime(latestSignal.ts)}</p>
                  <p className="text-xs text-fg-muted">{signals.length} signals total</p>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
