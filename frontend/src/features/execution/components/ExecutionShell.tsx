// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout: sidebar + workspace; §Components: cards, tables, badges;
//   §Visual Language: semantic colors (green/red/blue/amber);
//   §Interaction Standards: loading/success/error/empty states.
// Doc 08 — Frontend Architecture (QH-008 v1.0)
//   §Architecture: feature module composes the shared design system + hooks;
//   §State Management: TanStack Query.
// Doc 14 §10.7.4 Order Lifecycle (CREATED/VALIDATED/REJECTED/FILLED) — the
//   statuses the blotter renders; §10.7.3 Order Model (side/qty/price).
// Per Doc 00 §14.11
//
// JUDGMENT CALLS (Doc 00 §14.5/§14.7 — flagged):
//  1. PORTFOLIO SELECTOR REUSE: orders belong to a portfolio, so this blotter
//     needs the portfolio list to pick one. Rather than duplicate the
//     portfolio API contract, it reuses the portfolio feature's usePortfolios
//     hook + Portfolio type — a one-directional execution→portfolio domain
//     dependency (orders reference portfolios, never the reverse). Promote the
//     portfolio-list concern to a shared module if a third feature needs it.
//  2. STATUS COLOR MAPPING: Doc 06 names green=profit / red=risk / blue=info /
//     amber=warning. Order status is mapped onto those existing hues (no new
//     colors invented) — FILLED reuses profit-green as a "successful terminal
//     fill" success color, REJECTED reuses risk-red — the same kind of
//     beyond-literal reuse Badge.tsx already documents for loss=risk-red. This
//     makes FILLED (green) and REJECTED (red) maximally distinguishable, which
//     is the blotter's core job.
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
import { useOrders } from '../hooks/useExecution'
import type { Order, OrderStatus } from '../types'

// Display formatters. The authoritative precise values are the API's Decimal
// strings; these are display-only (nothing downstream consumes them).
function fmtQty(value: string): string {
  return Number.parseFloat(value).toLocaleString(undefined, { maximumFractionDigits: 8 })
}

function fmtPrice(value: string | null): string {
  if (value === null) return '—'
  return Number.parseFloat(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

// Judgment call #2 (module docstring): map the four modeled lifecycle states
// onto Doc 06's existing semantic hues so FILLED and REJECTED are clearly
// distinguishable at a glance.
function orderStatusBadgeVariant(status: OrderStatus): BadgeVariant {
  switch (status) {
    case 'FILLED':
      return 'profit'
    case 'REJECTED':
      return 'risk'
    case 'VALIDATED':
      return 'info'
    default:
      return 'neutral' // CREATED
  }
}

export function ExecutionShell() {
  const portfoliosQuery = usePortfolios()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const portfolios = portfoliosQuery.data ?? []
  const activeId = selectedId ?? portfolios[0]?.id ?? ''
  const activePortfolio = portfolios.find((p) => p.id === activeId) ?? null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-fg">Execution</h1>
        <p className="mt-1 text-sm text-fg-muted">
          Order &amp; execution blotter — Phase 3 order lifecycle.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[18rem_1fr]">
        <PortfolioList
          query={portfoliosQuery}
          portfolios={portfolios}
          activeId={activeId}
          onSelect={setSelectedId}
        />
        <div className="min-w-0">
          {activePortfolio ? (
            <Blotter portfolio={activePortfolio} />
          ) : (
            !portfoliosQuery.isLoading &&
            !portfoliosQuery.isError && (
              <Card>
                <CardContent>
                  <EmptyState
                    title="No portfolio selected"
                    description="Select a portfolio to view its order blotter."
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

function Blotter({ portfolio }: { portfolio: Portfolio }) {
  const ordersQuery = useOrders(portfolio.id)
  const orders = ordersQuery.data ?? []

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {portfolio.name}
          <span className="ml-2 font-normal text-fg-muted">Orders</span>
        </CardTitle>
        {ordersQuery.isSuccess && <Badge variant="neutral">{orders.length}</Badge>}
      </CardHeader>
      <CardContent>
        {ordersQuery.isLoading && <LoadingState label="Loading orders…" />}
        {ordersQuery.isError && (
          <ErrorState description="Could not load orders." onRetry={() => ordersQuery.refetch()} />
        )}
        {ordersQuery.isSuccess && orders.length === 0 && (
          <EmptyState title="No orders" description="This portfolio has placed no orders." />
        )}
        {ordersQuery.isSuccess && orders.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Asset</TableHead>
                <TableHead>Side</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Quantity</TableHead>
                <TableHead>Filled</TableHead>
                <TableHead>Avg Price</TableHead>
                <TableHead>Signal</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {orders.map((order) => (
                <OrderRow key={order.id} order={order} />
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}

function OrderRow({ order }: { order: Order }) {
  return (
    <TableRow>
      <TableCell>
        <span className="font-medium text-fg">{order.symbol ?? order.asset_id}</span>
        {order.exchange && (
          <span className="ml-2 text-xs uppercase text-fg-muted">{order.exchange}</span>
        )}
      </TableCell>
      <TableCell>
        <span className="font-medium text-fg">{order.side}</span>
      </TableCell>
      <TableCell>
        <Badge variant={orderStatusBadgeVariant(order.status)}>{order.status}</Badge>
      </TableCell>
      <TableCell numeric>{fmtQty(order.quantity)}</TableCell>
      <TableCell numeric>{fmtQty(order.filled_quantity)}</TableCell>
      <TableCell numeric>{fmtPrice(order.average_price)}</TableCell>
      <TableCell>
        {order.signal_id ? (
          <span className="font-mono text-xs text-fg-muted" title={order.signal_id}>
            {order.signal_id.slice(0, 8)}…
          </span>
        ) : (
          <span className="text-fg-muted">—</span>
        )}
      </TableCell>
    </TableRow>
  )
}
