// Governing specification: handbook/ui/visual_engineering/13_VISUAL_DNA —
//   real-data pill strip atop the workspace, same pattern as the Portfolio
//   page's strategy selector. Doc 00 §14.5/§14.7 DATA HONESTY.
'use client'

import { useEffect, useRef, useState } from 'react'
import { Check, ChevronDown, ShieldAlert } from 'lucide-react'
import { StatCard } from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import type { Portfolio, Position } from '@/features/portfolio/types'
import type { RiskLimit, RiskSnapshot } from '../types'
import { computeMarginUtilization } from '../analytics'

function PortfolioSelector({
  portfolios,
  current,
  onSelect,
}: {
  portfolios: Portfolio[]
  current: Portfolio | null
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
        <ShieldAlert size={16} className="shrink-0 text-fg-subtle" />
        <span className="min-w-0 flex-1 truncate font-medium text-fg">{current?.name ?? 'Select portfolio…'}</span>
        <ChevronDown size={16} className={cn('shrink-0 text-fg-subtle transition-transform duration-150', open && 'rotate-180')} />
      </button>
      {open && (
        <div
          role="listbox"
          className="absolute left-0 right-0 top-full z-40 mt-1.5 animate-slide-down overflow-hidden rounded-xl border border-border bg-surface-raised p-1.5 shadow-lg"
        >
          <p className="px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Portfolios</p>
          {portfolios.map((p) => {
            const selected = p.id === current?.id
            return (
              <button
                key={p.id}
                type="button"
                role="option"
                aria-selected={selected}
                onClick={() => {
                  setOpen(false)
                  onSelect(p.id)
                }}
                className={cn(
                  'flex w-full items-center justify-between gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors',
                  selected ? 'bg-accent-soft text-accent' : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
                )}
              >
                <span className="truncate">{p.name}</span>
                {selected && <Check size={15} className="shrink-0" />}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function RiskHeader({
  portfolios,
  activePortfolio,
  onSelect,
  snapshot,
  positions,
  limits,
}: {
  portfolios: Portfolio[]
  activePortfolio: Portfolio | null
  onSelect: (id: string) => void
  snapshot: RiskSnapshot | null | undefined
  positions: Position[]
  limits: RiskLimit[]
}) {
  const margin = activePortfolio ? computeMarginUtilization(positions, activePortfolio.configured_capital) : null

  return (
    <div className="space-y-4">
      <PortfolioSelector portfolios={portfolios} current={activePortfolio} onSelect={onSelect} />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <StatCard
          label="Gross exposure"
          value={snapshot ? Number.parseFloat(snapshot.gross_exposure).toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—'}
        />
        <StatCard
          label="Net exposure"
          value={snapshot ? Number.parseFloat(snapshot.net_exposure).toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—'}
          tone={snapshot ? (Number.parseFloat(snapshot.net_exposure) >= 0 ? 'profit' : 'risk') : 'default'}
        />
        <StatCard label="Leverage ratio" value={snapshot ? `${Number.parseFloat(snapshot.gross_leverage).toFixed(2)}x` : '—'} />
        <StatCard
          label="Margin used"
          value={margin ? `${margin.utilizationPct.toFixed(1)}%` : '—'}
          tone={margin ? (margin.utilizationPct > 80 ? 'risk' : margin.utilizationPct >= 50 ? 'warning' : 'profit') : 'default'}
          hint={!margin ? 'F-19: no capital configured' : undefined}
        />
        <StatCard label="Active limits" value={limits.length} />
      </div>
    </div>
  )
}
