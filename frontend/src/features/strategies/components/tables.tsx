// Shared InstitutionalTable column sets reused across the Strategies list
// (StrategiesShell) and the dedicated Strategy Workspace (StrategyDetailShell)
// — Doc 06 "The user must be capable of understanding every aspect of a
// strategy without navigating away from the workspace" means the same real
// backtest-run history belongs on both surfaces, not duplicated ad hoc.
// Per Doc 00 §14.11 DATA HONESTY — every column reads a real field; no
// derived/fabricated metrics.
'use client'

import { useMemo } from 'react'
import { Badge, InstitutionalTable, type InstitutionalColumnDef, type BadgeVariant, pnlBadgeVariant } from '@/components/ui'
import { formatCapital } from '@/lib/utils/format'
import type { Backtest } from '../types'

// Backtest total returns render as a full-precision percentage, never the
// generic bps rounding formatReturn applies below 0.1% — "+0.016%" is clearer
// than "+1.61 bps" in a backtest context (owner request).
export const fmtReturnPct = (v: string | null) => {
  if (v === null) return '—'
  const value = Number.parseFloat(v)
  if (!Number.isFinite(value)) return '—'
  const pct = value * 100
  const sign = value > 0 ? '+' : value < 0 ? '-' : ''
  return `${sign}${Math.abs(pct).toFixed(Math.abs(pct) >= 0.1 ? 2 : 3)}%`
}
export const fmtMoney = (v: string | null) => (v === null ? '—' : formatCapital(Number.parseFloat(v)))

export function backtestStatusVariant(status: string): BadgeVariant {
  switch (status.toUpperCase()) {
    case 'COMPLETED':
      return 'profit'
    case 'RUNNING':
      return 'info'
    case 'FAILED':
      return 'risk'
    default:
      return 'neutral'
  }
}

export function BacktestRunsTable({ backtests, exportFilename = 'strategy-backtests' }: { backtests: Backtest[]; exportFilename?: string }) {
  const columns = useMemo<InstitutionalColumnDef<Backtest>[]>(
    () => [
      {
        accessorKey: 'name',
        header: 'Run',
        cell: ({ getValue }) => <span className="font-medium text-fg">{getValue<string>()}</span>,
      },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ getValue }) => <Badge variant={backtestStatusVariant(getValue<string>())}>{getValue<string>()}</Badge>,
      },
      {
        id: 'fills',
        header: 'Fills',
        accessorFn: (b) => b.results?.orders_filled ?? b.trade_count ?? -Infinity,
        cell: ({ row }) => row.original.results?.orders_filled ?? row.original.trade_count ?? '—',
        meta: { numeric: true },
      },
      {
        id: 'total_return',
        header: 'Total Return',
        accessorFn: (b) => (b.total_return === null ? -Infinity : Number.parseFloat(b.total_return)),
        cell: ({ row }) => {
          const b = row.original
          return b.total_return === null ? (
            '—'
          ) : (
            <Badge variant={pnlBadgeVariant(Number.parseFloat(b.total_return))}>{fmtReturnPct(b.total_return)}</Badge>
          )
        },
        meta: { numeric: true },
      },
      {
        id: 'final_capital',
        header: 'Final Capital',
        accessorFn: (b) => (b.final_capital === null ? -Infinity : Number.parseFloat(b.final_capital)),
        cell: ({ row }) => fmtMoney(row.original.final_capital),
        meta: { numeric: true, hideBelow: 'tablet' },
      },
      {
        accessorKey: 'reproducibility_hash',
        header: 'Determinism Hash',
        enableSorting: false,
        cell: ({ getValue }) => {
          const hash = getValue<string | null>()
          return hash ? (
            <span className="font-mono text-xs text-fg-muted" title={hash}>{hash.slice(0, 12)}…</span>
          ) : (
            <span className="text-fg-muted">—</span>
          )
        },
        meta: { hideBelow: 'laptop' },
      },
    ],
    [],
  )

  return <InstitutionalTable data={backtests} columns={columns} getRowId={(b) => b.id} searchPlaceholder="Search runs…" exportFilename={exportFilename} />
}
