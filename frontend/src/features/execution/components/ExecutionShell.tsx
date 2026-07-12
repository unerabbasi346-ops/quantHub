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

import { useMemo, useState } from 'react'
import { ArrowLeftRight } from 'lucide-react'
import {
  Badge,
  CryptoIcon,
  DonutChart,
  type DonutSlice,
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
import { useExecutions, useOrders } from '../hooks/useExecution'
import type { Execution, Order, OrderStatus } from '../types'

const fmtQty = (v: string) => Number.parseFloat(v).toLocaleString(undefined, { maximumFractionDigits: 8 })
const fmtPrice = (v: string | null) => (v === null ? '—' : Number.parseFloat(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }))
const fmtTime = (ts: string) => new Date(ts).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })

// "What's pending" — created or risk-validated but not yet filled/rejected
// (Doc 14 §10.7.4 lifecycle: CREATED -> VALIDATED -> FILLED | REJECTED).
const PENDING_STATUSES: OrderStatus[] = ['CREATED', 'VALIDATED']

type StatusFilter = 'ALL' | 'PENDING' | 'FILLED' | 'REJECTED'

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
    <div className="space-y-14">
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
  const pending = orders.filter((o) => PENDING_STATUSES.includes(o.status)).length
  const fillRate = orders.length ? filled / orders.length : 0

  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null)
  const visibleOrders =
    statusFilter === 'ALL'
      ? orders
      : statusFilter === 'PENDING'
        ? orders.filter((o) => PENDING_STATUSES.includes(o.status))
        : orders.filter((o) => o.status === statusFilter)
  const selectedOrder = orders.find((o) => o.id === selectedOrderId) ?? null

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
    <div className="space-y-14">
      {query.isSuccess && orders.length > 0 && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_auto]">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="Orders" value={orders.length} />
            <StatCard label="Filled" value={filled} tone="profit" />
            <StatCard label="Pending" value={pending} tone={pending ? 'warning' : 'default'} />
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
        description="Click a row to see its real fills below."
        actions={
          query.isSuccess ? (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 rounded-lg border border-border bg-surface-raised p-0.5">
                {(['ALL', 'PENDING', 'FILLED', 'REJECTED'] as StatusFilter[]).map((s) => (
                  <button
                    key={s}
                    onClick={() => setStatusFilter(s)}
                    className={cn(
                      'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
                      statusFilter === s ? 'bg-accent text-accent-fg' : 'text-fg-muted hover:text-fg',
                    )}
                  >
                    {s === 'ALL' ? 'All' : s === 'PENDING' ? 'Pending' : s === 'FILLED' ? 'Filled' : 'Rejected'}
                  </button>
                ))}
              </div>
              <Badge variant="neutral">{visibleOrders.length}</Badge>
            </div>
          ) : null
        }
      >
        {query.isLoading && <SkeletonTable rows={6} cols={7} />}
        {query.isError && <ErrorState description="Could not load orders." onRetry={() => query.refetch()} />}
        {query.isSuccess && orders.length === 0 && (
          <EmptyState icon={<ArrowLeftRight size={20} />} title="No orders" description="This portfolio has placed no orders." />
        )}
        {query.isSuccess && orders.length > 0 && visibleOrders.length === 0 && (
          <EmptyState title="No orders in this state" description="Nothing matches the selected status filter." />
        )}
        {query.isSuccess && visibleOrders.length > 0 && (
          <OrderTable orders={visibleOrders} selectedOrderId={selectedOrderId} onSelectOrder={(o) => setSelectedOrderId(o.id === selectedOrderId ? null : o.id)} />
        )}
      </Section>

      {selectedOrder && <OrderFills order={selectedOrder} onClose={() => setSelectedOrderId(null)} />}
    </div>
  )
}

// Real fill-level detail for the selected order — the `useExecutions` hook
// already existed but was never called anywhere; wiring it here is what makes
// "what filled" genuinely readable instead of just an aggregate status badge.
function OrderFills({ order, onClose }: { order: Order; onClose: () => void }) {
  const query = useExecutions(order.id)
  const executions = query.data ?? []
  const symbol = order.symbol ?? order.asset_id

  return (
    <Section
      title={`Fills for ${symbol} · ${order.side} ${fmtQty(order.quantity)}`}
      description="Individual executions recorded against this order."
      actions={
        <button onClick={onClose} className="text-xs text-fg-muted transition-colors hover:text-fg">
          Close
        </button>
      }
    >
      <Panel className="overflow-hidden">
        {query.isLoading && <SkeletonTable rows={2} cols={5} />}
        {query.isError && <ErrorState description="Could not load fills." onRetry={() => query.refetch()} />}
        {query.isSuccess && executions.length === 0 && (
          <EmptyState title="No fills recorded" description="This order has no execution records yet." />
        )}
        {query.isSuccess && executions.length > 0 && <ExecutionTable executions={executions} />}
      </Panel>
    </Section>
  )
}

function ExecutionTable({ executions }: { executions: Execution[] }) {
  const columns = useMemo<InstitutionalColumnDef<Execution>[]>(
    () => [
      {
        id: 'executed_at',
        header: 'Time',
        accessorFn: (e) => new Date(e.executed_at).getTime(),
        cell: ({ row }) => <span className="whitespace-nowrap text-fg-muted">{fmtTime(row.original.executed_at)}</span>,
      },
      {
        id: 'quantity',
        header: 'Quantity',
        accessorFn: (e) => Number.parseFloat(e.quantity),
        cell: ({ row }) => fmtQty(row.original.quantity),
        meta: { numeric: true },
      },
      {
        id: 'price',
        header: 'Price',
        accessorFn: (e) => Number.parseFloat(e.price),
        cell: ({ row }) => fmtPrice(row.original.price),
        meta: { numeric: true },
      },
      {
        id: 'commission',
        header: 'Commission',
        accessorFn: (e) => Number.parseFloat(e.commission),
        cell: ({ row }) => fmtPrice(row.original.commission),
        meta: { numeric: true, hideBelow: 'tablet' },
      },
      {
        id: 'net_amount',
        header: 'Net Amount',
        accessorFn: (e) => Number.parseFloat(e.net_amount),
        cell: ({ row }) => fmtPrice(row.original.net_amount),
        meta: { numeric: true },
      },
      {
        accessorKey: 'venue',
        header: 'Venue',
        cell: ({ getValue }) => <span className="uppercase text-fg-muted">{getValue<string>()}</span>,
        meta: { hideBelow: 'laptop' },
      },
    ],
    [],
  )
  return <InstitutionalTable data={executions} columns={columns} getRowId={(e) => e.id} />
}

function OrderTable({
  orders,
  selectedOrderId,
  onSelectOrder,
}: {
  orders: Order[]
  selectedOrderId: string | null
  onSelectOrder: (order: Order) => void
}) {
  const columns = useMemo<InstitutionalColumnDef<Order>[]>(
    () => [
      {
        id: 'asset',
        header: 'Asset',
        accessorFn: (o) => o.symbol ?? o.asset_id,
        cell: ({ getValue }) => (
          <div className="flex items-center gap-2.5">
            <CryptoIcon symbol={String(getValue())} size={20} />
            <span className="font-medium text-fg">{String(getValue())}</span>
          </div>
        ),
      },
      {
        accessorKey: 'side',
        header: 'Side',
        cell: ({ getValue }) => {
          const side = getValue<Order['side']>()
          return <span className={cn('font-medium', side === 'BUY' ? 'text-profit' : 'text-risk')}>{side}</span>
        },
      },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ getValue }) => {
          const status = getValue<OrderStatus>()
          return <Badge variant={orderStatusBadgeVariant(status)}>{status}</Badge>
        },
      },
      {
        id: 'quantity',
        header: 'Quantity',
        accessorFn: (o) => Number.parseFloat(o.quantity),
        cell: ({ row }) => fmtQty(row.original.quantity),
        meta: { numeric: true },
      },
      {
        id: 'filled_quantity',
        header: 'Filled',
        accessorFn: (o) => Number.parseFloat(o.filled_quantity),
        cell: ({ row }) => fmtQty(row.original.filled_quantity),
        meta: { numeric: true, hideBelow: 'tablet' },
      },
      {
        id: 'average_price',
        header: 'Avg Price',
        accessorFn: (o) => (o.average_price === null ? -Infinity : Number.parseFloat(o.average_price)),
        cell: ({ row }) => fmtPrice(row.original.average_price),
        meta: { numeric: true, hideBelow: 'laptop' },
      },
      {
        accessorKey: 'signal_id',
        header: 'Signal',
        enableSorting: false,
        cell: ({ getValue }) => {
          const signalId = getValue<Order['signal_id']>()
          return signalId ? (
            <span className="font-mono text-xs text-fg-muted" title={signalId}>{signalId.slice(0, 8)}…</span>
          ) : (
            <span className="text-fg-muted">—</span>
          )
        },
        meta: { hideBelow: 'laptop' },
      },
    ],
    [],
  )

  return (
    <Panel className="overflow-hidden">
      <InstitutionalTable
        data={orders}
        columns={columns}
        getRowId={(o) => o.id}
        searchPlaceholder="Search orders…"
        exportFilename="execution-orders"
        onRowClick={onSelectOrder}
        isRowSelected={(o) => o.id === selectedOrderId}
      />
    </Panel>
  )
}
