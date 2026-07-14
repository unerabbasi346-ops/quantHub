// Governing specification: Doc 14 §10.2 Strategy Governance; Doc 00 §14.5/
//   §14.7 DATA HONESTY. Section 5 — a comparison table across every
//   registered strategy's real latest backtest, shown only when 2+ strategies
//   are registered (a comparison of one thing isn't a comparison).
'use client'

import { useMemo } from 'react'
import { useQueries } from '@tanstack/react-query'
import { GitCompare } from 'lucide-react'
import { Badge, InstitutionalTable, type InstitutionalColumnDef, Panel, Section, pnlBadgeVariant } from '@/components/ui'
import { strategiesService } from '@/features/strategies/services/strategies.service'
import type { Backtest, Strategy } from '@/features/strategies/types'

const fmtReturnPct = (v: string | null) => (v === null ? '—' : `${(Number.parseFloat(v) * 100).toFixed(4)}%`)
const fmtMoney = (v: string | null) =>
  v === null ? '—' : Number.parseFloat(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

interface ComparisonRow {
  strategy: Strategy
  latest: Backtest | null
}

function statusVariant(status: string) {
  return status.toUpperCase() === 'ACTIVE' ? 'profit' : 'neutral'
}

export function StrategyComparison({ strategies }: { strategies: Strategy[] }) {
  const backtestQueries = useQueries({
    queries: strategies.map((s) => ({
      queryKey: ['backtests', s.id],
      queryFn: () => strategiesService.getBacktests(s.id),
      enabled: Boolean(s.id),
    })),
  })

  const rows: ComparisonRow[] = useMemo(
    () => strategies.map((strategy, i) => ({ strategy, latest: backtestQueries[i]?.data?.[0] ?? null })),
    [strategies, backtestQueries],
  )

  if (strategies.length < 2) return null

  const columns: InstitutionalColumnDef<ComparisonRow>[] = [
    {
      id: 'name',
      header: 'Strategy',
      accessorFn: (r) => r.strategy.name,
      cell: ({ row }) => <span className="font-medium text-fg">{row.original.strategy.name}</span>,
    },
    {
      id: 'status',
      header: 'Status',
      accessorFn: (r) => r.strategy.status,
      cell: ({ row }) => <Badge variant={statusVariant(row.original.strategy.status)}>{row.original.strategy.status}</Badge>,
    },
    {
      id: 'total_return',
      header: 'Return',
      accessorFn: (r) => (r.latest?.total_return != null ? Number.parseFloat(r.latest.total_return) : -Infinity),
      cell: ({ row }) => {
        const v = row.original.latest?.total_return ?? null
        if (v === null) return '—'
        return <Badge variant={pnlBadgeVariant(Number.parseFloat(v))}>{fmtReturnPct(v)}</Badge>
      },
      meta: { numeric: true },
    },
    {
      id: 'trade_count',
      header: 'Trade Count',
      accessorFn: (r) => r.latest?.trade_count ?? r.latest?.results?.trade_count ?? -Infinity,
      cell: ({ row }) => row.original.latest?.trade_count ?? row.original.latest?.results?.trade_count ?? '—',
      meta: { numeric: true },
    },
    {
      id: 'pnl',
      header: 'P&L',
      accessorFn: (r) => (r.latest?.results ? Number.parseFloat(r.latest.results.realized_pnl) : -Infinity),
      cell: ({ row }) => {
        const results = row.original.latest?.results
        if (!results) return '—'
        return <span className={Number.parseFloat(results.realized_pnl) >= 0 ? 'text-profit' : 'text-risk'}>{fmtMoney(results.realized_pnl)}</span>
      },
      meta: { numeric: true },
    },
  ]

  return (
    <Section icon={<GitCompare size={16} />} title="Strategy performance comparison" actions={<Badge variant="neutral">{strategies.length}</Badge>}>
      <Panel className="overflow-hidden">
        <InstitutionalTable data={rows} columns={columns} getRowId={(r) => r.strategy.id} exportFilename="strategy-comparison" />
      </Panel>
    </Section>
  )
}
