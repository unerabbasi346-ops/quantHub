// Governing specification: Doc 04 — Analytics Component Library (blotter
//   pattern); Doc 00 §14.5/§14.7 DATA HONESTY: Direction is derived straight
//   from Order.side (BUY -> LONG, SELL -> SHORT; S-5 scoped-down model, see
//   api/v1/execution.py OrderOut.direction docstring) — no fabricated
//   position-aware short/cover distinction the schema doesn't model.
'use client'

import { useMemo, useState } from 'react'
import { ListOrdered } from 'lucide-react'
import {
  Badge,
  CryptoIcon,
  EmptyState,
  InstitutionalTable,
  Panel,
  Section,
  type InstitutionalColumnDef,
  pnlBadgeVariant,
} from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { num } from '../analytics'
import type { Order, OrderStatus } from '../types'

const fmtQty = (v: string) => Number.parseFloat(v).toLocaleString(undefined, { maximumFractionDigits: 8 })
const fmtPrice = (v: string | null) =>
  v === null ? '—' : Number.parseFloat(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const fmtAbsolute = (ts: string) => new Date(ts).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })

function fmtRelative(ts: string): string {
  const diffMs = Date.now() - new Date(ts).getTime()
  const s = Math.floor(diffMs / 1000)
  if (s < 60) return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  return `${d}d ago`
}

function isUtcToday(iso: string): boolean {
  const d = new Date(iso)
  const now = new Date()
  return d.getUTCFullYear() === now.getUTCFullYear() && d.getUTCMonth() === now.getUTCMonth() && d.getUTCDate() === now.getUTCDate()
}

const PENDING_STATUSES: OrderStatus[] = ['CREATED', 'VALIDATED']

function statusBadgeVariant(status: OrderStatus) {
  switch (status) {
    case 'FILLED': return 'profit' as const
    case 'REJECTED': return 'risk' as const
    case 'VALIDATED': return 'info' as const
    default: return 'neutral' as const
  }
}

type BlotterFilter = 'ALL' | 'TODAY' | 'FILLED' | 'PENDING' | 'REJECTED'

export function OrderBlotter({ orders }: { orders: Order[] }) {
  const [filter, setFilter] = useState<BlotterFilter>('ALL')

  const visible = useMemo(() => {
    switch (filter) {
      case 'TODAY': return orders.filter((o) => isUtcToday(o.created_at))
      case 'FILLED': return orders.filter((o) => o.status === 'FILLED')
      case 'PENDING': return orders.filter((o) => PENDING_STATUSES.includes(o.status))
      case 'REJECTED': return orders.filter((o) => o.status === 'REJECTED')
      default: return orders
    }
  }, [orders, filter])

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
          return <Badge variant={side === 'BUY' ? 'profit' : 'risk'}>{side}</Badge>
        },
      },
      {
        accessorKey: 'direction',
        header: 'Direction',
        cell: ({ getValue }) => {
          const direction = getValue<Order['direction']>()
          return <Badge variant={direction === 'LONG' ? 'profit' : 'risk'}>{direction}</Badge>
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
        id: 'average_price',
        header: 'Price',
        accessorFn: (o) => (o.average_price === null ? -Infinity : Number.parseFloat(o.average_price)),
        cell: ({ row }) => fmtPrice(row.original.average_price),
        meta: { numeric: true },
      },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ getValue }) => {
          const status = getValue<OrderStatus>()
          return <Badge variant={statusBadgeVariant(status)}>{status}</Badge>
        },
      },
      {
        id: 'realized_pnl',
        header: 'P&L',
        accessorFn: (o) => (o.realized_pnl === null ? -Infinity : Number.parseFloat(o.realized_pnl)),
        cell: ({ row }) => {
          const v = row.original.realized_pnl
          if (v === null) return <span className="text-fg-muted">—</span>
          const n = num(v)
          return <Badge variant={pnlBadgeVariant(n)}>{n >= 0 ? '+' : ''}{n.toFixed(4)}</Badge>
        },
        meta: { numeric: true },
      },
      {
        id: 'created_at',
        header: 'Timestamp',
        accessorFn: (o) => new Date(o.created_at).getTime(),
        cell: ({ row }) => (
          <span className="whitespace-nowrap text-fg-muted" title={fmtAbsolute(row.original.created_at)}>
            {fmtRelative(row.original.created_at)}
          </span>
        ),
      },
      {
        accessorKey: 'strategy_name',
        header: 'Strategy',
        cell: ({ getValue }) => {
          const name = getValue<Order['strategy_name']>()
          return name ? <span className="text-fg-muted">{name}</span> : <span className="text-fg-muted">—</span>
        },
        meta: { hideBelow: 'laptop' },
      },
    ],
    [],
  )

  return (
    <Section
      icon={<ListOrdered size={16} />}
      title="Order blotter"
      description="Real orders for the selected strategy."
      actions={
        <div className="flex items-center gap-1 rounded-lg border border-border bg-surface-raised p-0.5">
          {(['ALL', 'TODAY', 'FILLED', 'PENDING', 'REJECTED'] as BlotterFilter[]).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
                filter === f ? 'bg-accent text-accent-fg' : 'text-fg-muted hover:text-fg',
              )}
            >
              {f === 'ALL' ? 'All' : f.charAt(0) + f.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
      }
    >
      {orders.length === 0 ? (
        <EmptyState icon={<ListOrdered size={20} />} title="No orders" description="This strategy has generated no orders yet." />
      ) : visible.length === 0 ? (
        <EmptyState title="No orders in this state" description="Nothing matches the selected filter." />
      ) : (
        <Panel className="overflow-hidden">
          <InstitutionalTable
            data={visible}
            columns={columns}
            getRowId={(o) => o.id}
            searchPlaceholder="Search by asset symbol…"
            exportFilename="execution-orders"
            initialSorting={[{ id: 'created_at', desc: true }]}
          />
        </Panel>
      )}
    </Section>
  )
}
