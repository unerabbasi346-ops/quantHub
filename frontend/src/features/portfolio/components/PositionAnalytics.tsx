// Governing specification: Doc 14 §10.6.6 — Position Management; Doc 00
//   §14.5/§14.7 DATA HONESTY. Section 3 — Position Analytics (3 columns):
//   current positions table, asset allocation donut, capital utilization
//   gauge. Every figure real; every gap (no linked portfolio, no configured
//   capital) shown as an explicit, honest state.
'use client'

import { useMemo } from 'react'
import { Info, ListChecks, PieChart as PieChartIcon, Wallet } from 'lucide-react'
import {
  Badge,
  CryptoIcon,
  DonutChart,
  EmptyState,
  ErrorState,
  Gauge,
  InstitutionalTable,
  type InstitutionalColumnDef,
  Panel,
  Section,
  SkeletonTable,
  pnlBadgeVariant,
} from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { formatCapital, formatReturn } from '@/lib/utils/format'
import { computeCapitalUtilization, num } from '../analytics'
import type { Portfolio, Position } from '../types'

const fmtMoney = (v: string | number) => formatCapital(Number(v))
const fmtQty = (v: string) => Number.parseFloat(v).toLocaleString(undefined, { maximumFractionDigits: 8 })
const fmtPnl = (v: string | number) => {
  const n = Number(v)
  return n > 0 ? `+${formatCapital(n)}` : formatCapital(n)
}

function NoLinkedPortfolio({ title }: { title: string }) {
  return (
    <Panel className="flex items-start gap-3 p-5">
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-warning-soft text-warning">
        <Info size={16} />
      </span>
      <div>
        <div className="text-sm font-medium text-fg">{title}</div>
        <p className="mt-1 text-xs leading-relaxed text-fg-muted">
          This strategy has no linked portfolio (<code className="font-mono">portfolio_id</code> is not set at registration) —
          live position data isn&apos;t available for it. See Backtest Analytics below for this strategy&apos;s real backtest performance.
        </p>
      </div>
    </Panel>
  )
}

function PositionsTable({ positions }: { positions: Position[] }) {
  const columns = useMemo<InstitutionalColumnDef<Position>[]>(
    () => [
      {
        id: 'asset',
        header: 'Asset',
        accessorFn: (p) => p.symbol ?? p.asset_id,
        cell: ({ row }) => {
          const p = row.original
          const symbol = p.symbol ?? p.asset_id
          return (
            <div className="flex items-center gap-2.5">
              <CryptoIcon symbol={symbol} size={22} />
              <div className="min-w-0">
                <div className="font-medium text-fg">{symbol}</div>
                {p.exchange && <div className="text-[11px] uppercase tracking-wide text-fg-subtle">{p.exchange}</div>}
              </div>
            </div>
          )
        },
      },
      {
        id: 'direction',
        header: 'Direction',
        accessorFn: (p) => num(p.quantity),
        cell: ({ row }) => {
          const q = num(row.original.quantity)
          return <Badge variant={q >= 0 ? 'profit' : 'risk'}>{q >= 0 ? 'LONG' : 'SHORT'}</Badge>
        },
      },
      {
        id: 'size',
        header: 'Size',
        accessorFn: (p) => Math.abs(num(p.quantity)),
        cell: ({ row }) => fmtQty(String(Math.abs(num(row.original.quantity)))),
        meta: { numeric: true },
      },
      {
        id: 'average_entry_price',
        header: 'Entry Price',
        accessorFn: (p) => num(p.average_entry_price),
        cell: ({ row }) => fmtMoney(row.original.average_entry_price),
        meta: { numeric: true, hideBelow: 'tablet' },
      },
      {
        id: 'last_price',
        header: 'Current Price',
        accessorFn: (p) => (p.last_price ? num(p.last_price) : -Infinity),
        cell: ({ row }) => (row.original.last_price ? fmtMoney(row.original.last_price) : '—'),
        meta: { numeric: true, hideBelow: 'tablet' },
      },
      {
        id: 'unrealized_pnl',
        header: 'P&L',
        accessorFn: (p) => num(p.unrealized_pnl),
        cell: ({ row }) => <Badge variant={pnlBadgeVariant(num(row.original.unrealized_pnl))}>{fmtPnl(row.original.unrealized_pnl)}</Badge>,
        meta: { numeric: true },
      },
      {
        id: 'pnl_pct',
        header: 'P&L %',
        accessorFn: (p) => {
          const costBasis = Math.abs(num(p.quantity)) * num(p.average_entry_price)
          return costBasis > 0 ? (num(p.unrealized_pnl) / costBasis) * 100 : 0
        },
        cell: ({ row }) => {
          const p = row.original
          const costBasis = Math.abs(num(p.quantity)) * num(p.average_entry_price)
          if (!(costBasis > 0)) return '—'
          const pct = (num(p.unrealized_pnl) / costBasis) * 100
          return <span className={cn('font-mono tabular-nums', pct >= 0 ? 'text-profit' : 'text-risk')}>{formatReturn(pct / 100)}</span>
        },
        meta: { numeric: true, hideBelow: 'laptop' },
      },
      {
        id: 'leverage',
        header: 'Leverage',
        accessorFn: (p) => (p.leverage ? num(p.leverage) : -Infinity),
        cell: ({ row }) => {
          const p = row.original
          if (p.instrument_type !== 'PERPETUAL') return <span className="text-fg-subtle">—</span>
          return p.leverage ? <span className="font-mono">{num(p.leverage).toFixed(1)}x</span> : <span className="text-fg-subtle">—</span>
        },
        meta: { numeric: true, hideBelow: 'laptop' },
      },
    ],
    [],
  )

  return <InstitutionalTable data={positions} columns={columns} getRowId={(p) => p.id} searchPlaceholder="Search positions…" exportFilename="portfolio-positions" />
}

export function PositionAnalytics({
  hasLinkedPortfolio,
  linkedPortfolio,
  positions,
  positionsLoading,
  positionsError,
  onRetry,
}: {
  hasLinkedPortfolio: boolean
  linkedPortfolio: Portfolio | null
  positions: Position[]
  positionsLoading: boolean
  positionsError: boolean
  onRetry: () => void
}) {
  const open = positions.filter((p) => !p.is_closed)
  const allocation = open
    .map((p) => ({ name: p.symbol ?? p.asset_id, value: Math.abs(num(p.market_value)) }))
    .filter((d) => d.value > 0)
    .sort((a, b) => b.value - a.value)
  const totalMarketValue = allocation.reduce((s, a) => s + a.value, 0)
  const utilization = hasLinkedPortfolio ? computeCapitalUtilization(positions, linkedPortfolio?.configured_capital ?? null) : null

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <Section icon={<ListChecks size={16} />} title="Current positions" actions={hasLinkedPortfolio ? <Badge variant="neutral">{open.length}</Badge> : null}>
        {!hasLinkedPortfolio ? (
          <NoLinkedPortfolio title="No open positions" />
        ) : positionsLoading ? (
          <SkeletonTable rows={4} cols={6} />
        ) : positionsError ? (
          <ErrorState description="Could not load positions." onRetry={onRetry} />
        ) : positions.length === 0 ? (
          <Panel className="p-6"><EmptyState icon={<Wallet size={20} />} title="No open positions" description="This portfolio holds no positions." /></Panel>
        ) : (
          <Panel className="overflow-hidden">
            <PositionsTable positions={positions} />
          </Panel>
        )}
      </Section>

      <Section icon={<PieChartIcon size={16} />} title="Asset allocation" description="Share of capital by open-position market value.">
        {!hasLinkedPortfolio ? (
          <NoLinkedPortfolio title="No allocation to show" />
        ) : positionsLoading ? (
          <div className="skeleton h-[280px] w-full" />
        ) : allocation.length > 0 ? (
          <Panel className="p-4">
            <DonutChart data={allocation} height={280} centerLabel="deployed" centerValue={fmtMoney(totalMarketValue)} valueFormat={(v) => fmtMoney(v)} />
          </Panel>
        ) : (
          <Panel className="p-6">
            <EmptyState icon={<Wallet size={20} />} title="No open positions to allocate" description="Allocation appears once this portfolio holds positions with a market value." />
          </Panel>
        )}
      </Section>

      <Section title="Capital utilization" description="Deployed vs. configured capital.">
        {!hasLinkedPortfolio ? (
          <NoLinkedPortfolio title="No capital utilization to show" />
        ) : positionsLoading ? (
          <div className="skeleton h-[280px] w-full" />
        ) : utilization ? (
          <Panel className="p-4">
            <Gauge value={utilization.utilizationPct} min={0} max={100} unit="%" invert height={200} valueFormat={(v) => v.toFixed(1)} />
            <div className="mt-2 flex items-center justify-between text-xs text-fg-muted">
              <span>{fmtMoney(utilization.deployed)} deployed</span>
              <span>{fmtMoney(utilization.configured)} configured</span>
            </div>
          </Panel>
        ) : (
          <Panel className="flex items-start gap-3 p-5">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-warning-soft text-warning">
              <Info size={16} />
            </span>
            <div>
              <div className="flex items-center gap-2 text-sm font-medium text-fg">
                Not configured <Badge variant="warning">F-19</Badge>
              </div>
              <p className="mt-1 text-xs leading-relaxed text-fg-muted">
                This portfolio has no operator-configured capital figure — utilization can&apos;t be computed without a denominator.
                Configure capital below to see it here.
              </p>
            </div>
          </Panel>
        )}
      </Section>
    </div>
  )
}
