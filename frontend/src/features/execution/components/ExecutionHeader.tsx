// Governing specification: handbook/ui/visual_engineering — Image 1 (AI
//   Trading Bots) dense metric-card standard. Doc 00 §14.5/§14.7 DATA
//   HONESTY: every pill is a real, computed figure over the selected
//   strategy's orders/fills; "Realized P&L today" is a UTC calendar-day
//   filter over real fill timestamps, not a backend daily-reset field.
'use client'

import { useEffect, useRef, useState } from 'react'
import { ArrowLeftRight, Check, ChevronDown } from 'lucide-react'
import { StatCard } from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { formatCapital } from '@/lib/utils/format'
import type { Strategy } from '@/features/strategies/types'
import { num } from '../analytics'
import type { Execution, Order } from '../types'

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
        <ArrowLeftRight size={16} className="shrink-0 text-fg-subtle" />
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

function isUtcToday(iso: string): boolean {
  const d = new Date(iso)
  const now = new Date()
  return (
    d.getUTCFullYear() === now.getUTCFullYear() &&
    d.getUTCMonth() === now.getUTCMonth() &&
    d.getUTCDate() === now.getUTCDate()
  )
}

export function ExecutionHeader({
  strategies,
  activeStrategy,
  onSelect,
  orders,
  executions,
  loading,
}: {
  strategies: Strategy[]
  activeStrategy: Strategy | null
  onSelect: (id: string) => void
  orders: Order[]
  executions: Execution[]
  loading: boolean
}) {
  const filled = orders.filter((o) => o.status === 'FILLED')
  const fillRate = orders.length ? (filled.length / orders.length) * 100 : 0
  const avgFillSize = executions.length
    ? executions.reduce((s, e) => s + num(e.quantity) * num(e.price), 0) / executions.length
    : null
  // "Today" is judged off Execution.executed_at (the real bar/fill time),
  // not Order.created_at (the wall-clock backtest-insert time) — the latter
  // would compare "when the script ran" to today's UTC date, which is
  // consistently wrong for historical backtest data.
  const todaysFills = executions.filter((e) => isUtcToday(e.executed_at))
  const fillsTodayOrderIds = new Set(todaysFills.map((e) => e.order_id))
  const ordersToday = orders.filter((o) => fillsTodayOrderIds.has(o.id)).length
  const realizedToday = todaysFills.length
    ? todaysFills.reduce((s, e) => s + num(e.realized_pnl), 0)
    : null

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <StrategySelector strategies={strategies} current={activeStrategy} onSelect={onSelect} />
      </div>

      {loading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton h-20 w-full" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <StatCard label="Total orders" value={orders.length} />
          <StatCard
            label="Fill rate"
            value={orders.length ? `${fillRate.toFixed(1)}%` : '—'}
            tone={orders.length ? (fillRate > 95 ? 'profit' : 'default') : 'default'}
            hint={orders.length ? `${filled.length} filled` : 'no orders'}
          />
          <StatCard label="Total fills" value={executions.length} />
          <StatCard
            label="Avg fill size"
            value={avgFillSize != null ? formatCapital(avgFillSize) : '—'}
            hint={avgFillSize != null ? 'USDT' : 'no fills'}
          />
          <StatCard label="Orders today" value={ordersToday} hint="UTC calendar day" />
          <StatCard
            label="Realized P&L today"
            value={realizedToday != null ? `${realizedToday >= 0 ? '+' : ''}${formatCapital(realizedToday)}` : '—'}
            tone={realizedToday == null ? 'default' : realizedToday >= 0 ? 'profit' : 'risk'}
            hint={realizedToday == null ? 'no fills today' : 'fill-level, UTC day'}
          />
        </div>
      )}
    </div>
  )
}
