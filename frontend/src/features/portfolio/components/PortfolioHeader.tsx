// Governing specification: handbook/ui/visual_engineering/13_VISUAL_DNA —
//   Voltrex/Finor summary strip: dense real-data pills atop the workspace.
// Doc 00 §14.5/§14.7 DATA HONESTY: NAV/P&L/utilization are real when a
//   portfolio is linked to the selected strategy; every figure that depends
//   on a missing link is shown as an honest "n/a", never fabricated.
'use client'

import { useEffect, useRef, useState } from 'react'
import { Brain, Check, ChevronDown } from 'lucide-react'
import { Badge, StatCard } from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { formatCapital } from '@/lib/utils/format'
import type { Strategy } from '@/features/strategies/types'
import { computeCapitalUtilization, num, utilizationTone } from '../analytics'
import type { Portfolio, Position } from '../types'

function statusVariant(status: string) {
  return status.toUpperCase() === 'ACTIVE' ? 'profit' : 'neutral'
}

// Same selector pattern as the Strategy detail page's StrategySelector —
// kept feature-local (a small ~40-line component) rather than exported
// cross-feature, matching how MarketChartSection has its own AssetDropdown.
function StrategySelector({
  strategies,
  current,
  onSelect,
}: {
  strategies: Strategy[]
  current: Strategy | null
  onSelect: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onClick = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false)
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  return (
    <div className="relative w-full max-w-sm" ref={ref}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'flex h-10 w-full items-center gap-2.5 rounded-lg border bg-surface-raised/50 px-3 text-left text-sm transition-colors',
          open ? 'border-border-strong bg-surface-raised' : 'border-border hover:border-border-strong',
        )}
      >
        <Brain size={16} className="shrink-0 text-fg-subtle" />
        <span className="min-w-0 flex-1 truncate font-medium text-fg">{current?.name ?? 'Select strategy…'}</span>
        <ChevronDown size={16} className={cn('shrink-0 text-fg-subtle transition-transform duration-150', open && 'rotate-180')} />
      </button>
      {open && (
        <div
          role="listbox"
          className="absolute left-0 right-0 top-full z-40 mt-1.5 animate-slide-down overflow-hidden rounded-xl border border-border bg-surface-raised p-1.5 shadow-lg"
        >
          <p className="px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Registered strategies</p>
          {strategies.map((s) => {
            const selected = s.id === current?.id
            return (
              <button
                key={s.id}
                type="button"
                role="option"
                aria-selected={selected}
                onClick={() => {
                  setOpen(false)
                  onSelect(s.id)
                }}
                className={cn(
                  'flex w-full items-center justify-between gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors',
                  selected ? 'bg-accent-soft text-accent' : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
                )}
              >
                <span className="truncate">{s.name}</span>
                {selected && <Check size={15} className="shrink-0" />}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function PortfolioHeader({
  strategies,
  activeStrategy,
  onSelect,
  linkedPortfolio,
  positions,
  positionsLoading,
  backtestTotalReturn,
  backtestRealizedPnl,
  backtestUnrealizedPnl,
}: {
  strategies: Strategy[]
  activeStrategy: Strategy | null
  onSelect: (id: string) => void
  linkedPortfolio: Portfolio | null
  positions: Position[]
  positionsLoading: boolean
  backtestTotalReturn: string | null
  backtestRealizedPnl: string | null
  backtestUnrealizedPnl: string | null
}) {
  const open = positions.filter((p) => !p.is_closed)
  const hasPortfolio = linkedPortfolio != null

  // Total P&L: real open-position realized-today + unrealized when a
  // portfolio is linked (true live figure); otherwise falls back to the
  // real backtest's realized + unrealized P&L, labeled "(backtest)" so the
  // source is never ambiguous.
  const livePnl = hasPortfolio
    ? open.reduce((s, p) => s + num(p.realized_pnl_today) + num(p.unrealized_pnl), 0)
    : null
  const backtestPnl =
    backtestRealizedPnl != null && backtestUnrealizedPnl != null
      ? Number.parseFloat(backtestRealizedPnl) + Number.parseFloat(backtestUnrealizedPnl)
      : null
  const totalPnl = livePnl ?? backtestPnl
  const pnlSourceLabel = livePnl != null ? 'live positions' : backtestPnl != null ? '(backtest)' : undefined

  const utilization = hasPortfolio ? computeCapitalUtilization(positions, linkedPortfolio.configured_capital) : null

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <StrategySelector strategies={strategies} current={activeStrategy} onSelect={onSelect} />
        {activeStrategy && <Badge variant={statusVariant(activeStrategy.status)}>{activeStrategy.status}</Badge>}
      </div>

      {positionsLoading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="skeleton h-20 w-full" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
          <StatCard
            label="Portfolio NAV"
            value={hasPortfolio && linkedPortfolio.configured_capital ? formatCapital(Number(linkedPortfolio.configured_capital)) : '—'}
            hint={hasPortfolio ? 'configured capital' : 'no linked portfolio'}
          />
          <StatCard
            label="Total P&L"
            value={totalPnl != null ? `${totalPnl >= 0 ? '+' : ''}${formatCapital(totalPnl)}` : '—'}
            tone={totalPnl == null ? 'default' : totalPnl >= 0 ? 'profit' : 'risk'}
            hint={pnlSourceLabel}
          />
          <StatCard label="Open positions" value={hasPortfolio ? open.length : '—'} hint={hasPortfolio ? `${positions.length} total` : 'no linked portfolio'} />
          <StatCard label="Active strategy" value={activeStrategy?.name ?? '—'} hint={activeStrategy ? `v${activeStrategy.version}` : undefined} />
          <StatCard
            label="Capital utilization"
            value={utilization ? `${utilization.utilizationPct.toFixed(1)}%` : '—'}
            tone={utilization ? utilizationTone(utilization.utilizationPct) : 'default'}
            hint={utilization ? `${formatCapital(utilization.deployed)} deployed` : 'F-19: no capital configured'}
          />
        </div>
      )}
    </div>
  )
}
