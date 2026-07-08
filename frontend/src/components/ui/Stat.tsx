// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Components / §Data Visualization: consistent metric presentation. One
//   canonical KPI/stat treatment reused across dashboard, portfolio, risk —
//   so a "gross exposure" figure looks the same everywhere.
// Per Doc 00 §14.11
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils/cn'

type Tone = 'default' | 'profit' | 'risk' | 'info' | 'warning'

const TONE: Record<Tone, string> = {
  default: 'text-fg',
  profit: 'text-profit',
  risk: 'text-risk',
  info: 'text-info',
  warning: 'text-warning',
}

interface StatProps {
  label: ReactNode
  value: ReactNode
  hint?: ReactNode
  tone?: Tone
  className?: string
}

// Inline stat (no box) — for use inside a Section or Card content region.
export function Stat({ label, value, hint, tone = 'default', className }: StatProps) {
  return (
    <div className={cn('min-w-0', className)}>
      <div className="truncate text-[11px] font-medium uppercase tracking-wider text-fg-subtle">
        {label}
      </div>
      <div className={cn('mt-1 font-mono text-xl font-semibold tabular-nums tracking-tight', TONE[tone])}>
        {value}
      </div>
      {hint && <div className="mt-0.5 text-xs text-fg-muted">{hint}</div>}
    </div>
  )
}

// Boxed KPI tile — the ONE case where a single stat earns its own bordered
// card (owner feedback: reserve bordered cards for content that truly needs
// grouping, e.g. a single KPI). A subtle raised surface, not flat.
export function StatCard({ label, value, hint, tone = 'default', className }: StatProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-surface-raised px-4 py-3.5 shadow-sm',
        className,
      )}
    >
      <Stat label={label} value={value} hint={hint} tone={tone} />
    </div>
  )
}
