// Governing specification: Doc 00 §14.11 DATA HONESTY — every field below
//   reads a real value off Backtest/Signal; nothing derived or fabricated.
// VISUAL UPGRADE PASS (owner request): a card-grid presentation of backtest
//   runs and a rich per-row presentation of recent signals, for the Strategy
//   detail workspace specifically. The shared InstitutionalTable-backed
//   BacktestRunsTable (tables.tsx) stays untouched and keeps serving the
//   Strategies list page (StrategiesShell) and its own search/export chrome —
//   this is a page-specific alternate view, not a replacement of the shared
//   table engine.
'use client'

import { Hash, TrendingDown, TrendingUp, Wallet } from 'lucide-react'
import { Badge, CryptoIcon, Panel, type BadgeVariant } from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { formatSignalStrength, formatTimestamp } from '@/lib/utils/format'
import type { Backtest, Signal } from '../types'
import { backtestStatusVariant, fmtMoney, fmtReturnPct } from './tables'

const fmtDate = (ts: string | null) => (ts ? formatTimestamp(ts) : '—')

// ── Backtest run cards — glass tiles, 2/row on desktop, replacing the flat
//    table for this page's dense visual layout. ──
export function BacktestRunCards({ backtests }: { backtests: Backtest[] }) {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {backtests.map((b, i) => {
        const ret = b.total_return === null ? null : Number.parseFloat(b.total_return)
        const fills = b.results?.orders_filled ?? b.trade_count ?? null
        return (
          <Panel key={b.id} interactive className="space-y-3 p-4">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Badge variant="neutral">Run #{backtests.length - i}</Badge>
                <span className="truncate text-xs text-fg-subtle">{b.name}</span>
              </div>
              <Badge variant={backtestStatusVariant(b.status) as BadgeVariant}>{b.status}</Badge>
            </div>

            <div className="flex items-baseline justify-between gap-2">
              <div className={cn('font-mono text-metric font-bold tabular-nums', ret == null ? 'text-fg-muted' : ret >= 0 ? 'text-profit' : 'text-risk')}>
                {fmtReturnPct(b.total_return)}
              </div>
              {ret != null && (ret >= 0 ? <TrendingUp size={16} className="text-profit" /> : <TrendingDown size={16} className="text-risk" />)}
            </div>

            <div className="grid grid-cols-3 gap-3 border-t border-border/60 pt-3 text-xs">
              <div className="flex flex-col gap-1">
                <span className="flex items-center gap-1 text-[10px] uppercase tracking-wide text-fg-subtle">
                  <Hash size={10} /> Trades
                </span>
                <span className="font-mono text-fg">{fills ?? '—'}</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="flex items-center gap-1 text-[10px] uppercase tracking-wide text-fg-subtle">
                  <TrendingUp size={10} /> Realized P&L
                </span>
                <span className={cn('font-mono', b.results && Number.parseFloat(b.results.realized_pnl) >= 0 ? 'text-profit' : 'text-risk')}>
                  {b.results ? fmtMoney(b.results.realized_pnl) : '—'}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="flex items-center gap-1 text-[10px] uppercase tracking-wide text-fg-subtle">
                  <Wallet size={10} /> Final capital
                </span>
                <span className="font-mono text-fg">{fmtMoney(b.final_capital)}</span>
              </div>
            </div>

            <div className="flex items-center justify-between gap-2 border-t border-border/60 pt-2.5 text-[10px] text-fg-subtle">
              <span>{fmtDate(b.completed_at ?? b.created_at)}</span>
              {b.reproducibility_hash && (
                <span className="truncate font-mono" title={b.reproducibility_hash}>
                  {b.reproducibility_hash.slice(0, 12)}…
                </span>
              )}
            </div>
          </Panel>
        )
      })}
    </div>
  )
}

// ── Recent signals — rich row: a sign/magnitude-proportional colored edge
//    bar, the strategy's instrument icon, a large colored strength value,
//    relative time, validation badge, and up to two metadata pairs. ──
export function RecentSignalRows({ signals, symbol }: { signals: Signal[]; symbol: string | null }) {
  const maxAbs = signals.reduce((m, s) => Math.max(m, Math.abs(Number.parseFloat(s.value))), 1e-9)

  return (
    <Panel className="divide-y divide-border/60 overflow-hidden">
      {signals.map((s) => {
        const v = Number.parseFloat(s.value)
        const pct = Math.min(100, (Math.abs(v) / maxAbs) * 100)
        const metadataEntries = Object.entries(s.metadata ?? {}).slice(0, 2)
        return (
          <div key={s.id} className="flex items-stretch gap-3 px-3 py-2.5">
            <span
              className={cn('w-1 shrink-0 rounded-full', v >= 0 ? 'bg-profit' : 'bg-risk')}
              style={{ opacity: 0.35 + (pct / 100) * 0.65 }}
              aria-hidden
            />
            <div className="flex min-w-0 flex-1 items-center gap-3">
              {symbol && <CryptoIcon symbol={symbol} size={22} />}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className={cn('font-mono text-sm font-semibold tabular-nums', v >= 0 ? 'text-profit' : 'text-risk')}>
                    {formatSignalStrength(v)}
                  </span>
                  <Badge variant={s.validation_status === 'VALID' ? 'profit' : 'warning'}>{s.validation_status}</Badge>
                </div>
                {metadataEntries.length > 0 && (
                  <div className="mt-0.5 flex flex-wrap gap-x-3 font-mono text-[10px] text-fg-subtle">
                    {metadataEntries.map(([k, mv]) => (
                      <span key={k}>
                        {k}=<span className="text-fg-muted">{mv}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <span className="shrink-0 text-[11px] text-fg-subtle">{formatTimestamp(s.ts)}</span>
            </div>
          </div>
        )
      })}
    </Panel>
  )
}
