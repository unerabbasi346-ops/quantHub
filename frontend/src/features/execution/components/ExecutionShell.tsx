// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Layout / §Data Visualization; §Interaction Standards.
// Doc 08 — Frontend Architecture (QH-008 v1.0) §Architecture / §State Management.
// Doc 14 §10.7.4 Order Lifecycle (CREATED/VALIDATED/REJECTED/FILLED); §10.7.3.
// Per Doc 00 §14.11
//
// REDESIGN (owner push): a KPI strip (orders / filled / rejected / fill-rate
// ring) anchors the blotter; Sections + thin dividers replace nested cards;
// asset rows carry a crypto icon; the signal-lineage column is preserved.
'use client'

import { useState } from 'react'
import { ArrowLeftRight } from 'lucide-react'
import {
  Badge,
  CryptoIcon,
  DonutChart,
  type DonutSlice,
  EmptyState,
  ErrorState,
  PageHeader,
  Panel,
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
import { useOrders } from '../hooks/useExecution'
import type { Order, OrderStatus } from '../types'

const fmtQty = (v: string) => Number.parseFloat(v).toLocaleString(undefined, { maximumFractionDigits: 8 })
const fmtPrice = (v: string | null) => (v === null ? '—' : Number.parseFloat(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }))

function orderStatusBadgeVariant(status: OrderStatus): BadgeVariant {
  switch (status) {
    case 'FILLED': return 'profit'
    case 'REJECTED': return 'risk'
    case 'VALIDATED': return 'info'
    default: return 'neutral'
  }
}

export function ExecutionShell() {
  const portfoliosQuery = usePortfolios()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const portfolios = portfoliosQuery.data ?? []
  const activeId = selectedId ?? portfolios[0]?.id ?? ''
  const activePortfolio = portfolios.find((p) => p.id === activeId) ?? null

  return (
    <div className="space-y-8">
      <PageHeader
        icon={<ArrowLeftRight size={18} />}
        title="Execution"
        subtitle="Order & execution blotter — Phase 3 order lifecycle."
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

        <div className="min-w-0">
          {activePortfolio ? (
            <Blotter portfolio={activePortfolio} />
          ) : (
            !portfoliosQuery.isLoading && !portfoliosQuery.isError && (
              <EmptyState icon={<ArrowLeftRight size={20} />} title="No portfolio selected" description="Select a portfolio to view its order blotter." />
            )
          )}
        </div>
      </div>
    </div>
  )
}

function Blotter({ portfolio }: { portfolio: Portfolio }) {
  const query = useOrders(portfolio.id)
  const orders = query.data ?? []
  const filled = orders.filter((o) => o.status === 'FILLED').length
  const rejected = orders.filter((o) => o.status === 'REJECTED').length
  const fillRate = orders.length ? filled / orders.length : 0

  // Real order-status distribution (Doc 04 "Order Distribution" donut). Counts
  // are genuine lifecycle states; tones are semantic (filled=profit, etc.).
  const STATUS_TONE: Partial<Record<OrderStatus, DonutSlice['tone']>> = {
    FILLED: 'profit',
    REJECTED: 'risk',
    VALIDATED: 'info',
    CREATED: 'accent',
  }
  const statusOrder: OrderStatus[] = ['FILLED', 'VALIDATED', 'CREATED', 'REJECTED']
  const statusDist: DonutSlice[] = statusOrder
    .map((s) => ({ name: s, value: orders.filter((o) => o.status === s).length, tone: STATUS_TONE[s] }))
    .filter((d) => d.value > 0)

  return (
    <div className="space-y-8">
      {query.isSuccess && orders.length > 0 && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_auto]">
          <div className="grid grid-cols-3 gap-4">
            <StatCard label="Orders" value={orders.length} />
            <StatCard label="Filled" value={filled} tone="profit" />
            <StatCard label="Rejected" value={rejected} tone={rejected ? 'risk' : 'default'} />
          </div>
          <Panel className="flex flex-col items-center justify-center gap-1.5 px-8 py-4">
            <Ring value={fillRate} size={92} thickness={9} tone="profit" centerLabel={`${Math.round(fillRate * 100)}%`} centerSub="filled" />
          </Panel>
        </div>
      )}

      {query.isSuccess && statusDist.length > 1 && (
        <Section title="Order distribution" description="Orders by lifecycle status.">
          <Panel className="p-4">
            <DonutChart
              data={statusDist}
              height={240}
              centerValue={String(orders.length)}
              centerLabel="orders"
              valueFormat={(v) => String(v)}
            />
          </Panel>
        </Section>
      )}

      <Section
        title={`${portfolio.name} · orders`}
        actions={query.isSuccess ? <Badge variant="neutral">{orders.length}</Badge> : null}
      >
        {query.isLoading && <SkeletonTable rows={6} cols={7} />}
        {query.isError && <ErrorState description="Could not load orders." onRetry={() => query.refetch()} />}
        {query.isSuccess && orders.length === 0 && (
          <EmptyState icon={<ArrowLeftRight size={20} />} title="No orders" description="This portfolio has placed no orders." />
        )}
        {query.isSuccess && orders.length > 0 && (
          <Panel className="overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Asset</TableHead><TableHead>Side</TableHead><TableHead>Status</TableHead>
                  <TableHead>Quantity</TableHead><TableHead>Filled</TableHead><TableHead>Avg Price</TableHead><TableHead>Signal</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((order) => (<OrderRow key={order.id} order={order} />))}
              </TableBody>
            </Table>
          </Panel>
        )}
      </Section>
    </div>
  )
}

function OrderRow({ order }: { order: Order }) {
  const symbol = order.symbol ?? order.asset_id
  return (
    <TableRow>
      <TableCell>
        <div className="flex items-center gap-2.5">
          <CryptoIcon symbol={symbol} size={20} />
          <span className="font-medium text-fg">{symbol}</span>
        </div>
      </TableCell>
      <TableCell>
        <span className={cn('font-medium', order.side === 'BUY' ? 'text-profit' : 'text-risk')}>{order.side}</span>
      </TableCell>
      <TableCell><Badge variant={orderStatusBadgeVariant(order.status)}>{order.status}</Badge></TableCell>
      <TableCell numeric>{fmtQty(order.quantity)}</TableCell>
      <TableCell numeric>{fmtQty(order.filled_quantity)}</TableCell>
      <TableCell numeric>{fmtPrice(order.average_price)}</TableCell>
      <TableCell>
        {order.signal_id ? (
          <span className="font-mono text-xs text-fg-muted" title={order.signal_id}>{order.signal_id.slice(0, 8)}…</span>
        ) : <span className="text-fg-muted">—</span>}
      </TableCell>
    </TableRow>
  )
}
