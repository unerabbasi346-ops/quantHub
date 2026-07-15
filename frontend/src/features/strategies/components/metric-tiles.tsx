// Governing specification: Doc 00 §14.5/§14.7 — DATA HONESTY: a metric that
//   isn't genuinely computed shows an inert, grayed shell + explicit "Pending"
//   label — never a plausible-looking fabricated reading. Matches the
//   established "Not computed" chip in StrategyCard.tsx (F-18/F-21) at higher
//   density for the detail workspace's metrics grid.
// handbook/ui/visual_engineering/13_VISUAL_DNA — "Every visual element must
//   have a functional purpose"; restrained glows, no decoration for its own sake.
//
// VISUAL UPGRADE PASS (owner request): richer real-metric presentation
// (sparkline-backed return tile) and a more premium pending-metric shell
// (subtle pulse). Deliberately NOT adopting the "Computing…" / lock-icon
// framing requested alongside this: these metrics aren't mid-computation,
// they're deferred behind unbuilt backend work (F-21/F-18) — "Computing"
// would imply progress that isn't happening, the exact fabrication Doc 00
// exists to prevent. Kept the honest "Pending {ticket}" label; used a Clock
// icon (deferred-in-time) rather than a Lock (implies a permissions gate,
// the wrong metaphor for "not built yet").
'use client'

import type { ReactNode } from 'react'
import { Clock } from 'lucide-react'
import { Ring } from '@/components/ui/Ring'
import { Badge } from '@/components/ui/Badge'
import { Sparkline } from '@/components/ui/Sparkline'
import { cn } from '@/lib/utils/cn'

interface RealMetricTileProps {
  icon?: ReactNode
  label: string
  value: ReactNode
  hint?: ReactNode
  tone?: 'default' | 'profit' | 'risk'
}

const TONE_TEXT: Record<NonNullable<RealMetricTileProps['tone']>, string> = {
  default: 'text-fg',
  profit: 'text-profit',
  risk: 'text-risk',
}

// A genuinely computed metric — dense tile for the Performance Metrics Grid.
export function RealMetricTile({ icon, label, value, hint, tone = 'default' }: RealMetricTileProps) {
  return (
    <div className="flex min-w-0 flex-col gap-1 rounded-xl border border-border/60 bg-surface/40 px-3 py-3 transition-colors hover:border-border-strong/60">
      <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-fg-subtle">
        {icon}
        <span className="truncate">{label}</span>
      </div>
      <div className={cn('truncate font-mono text-metric-sm font-semibold tabular-nums', TONE_TEXT[tone])}>{value}</div>
      {hint && <div className="truncate text-[10px] text-fg-subtle">{hint}</div>}
    </div>
  )
}

// A ring-backed real metric (e.g. Valid Rate) — real progress fill, not a shell.
export function RealRingTile({ label, value, hint }: { label: string; value: number; hint?: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col items-center gap-1.5 rounded-xl border border-border/60 bg-surface/40 px-3 py-3 text-center">
      <Ring value={value} size={56} thickness={6} tone="profit" centerLabel={`${Math.round(value * 100)}%`} />
      <span className="truncate text-[10px] font-medium uppercase tracking-wider text-fg-subtle">{label}</span>
      {hint && <div className="truncate text-[10px] text-fg-subtle">{hint}</div>}
    </div>
  )
}

// Backtest return, given real weight: a large colored figure plus a real
// sparkline of the underlying signal values (the same series the equity
// curve plots) so the number sits next to the shape that produced it.
export function BacktestReturnTile({
  label,
  valueText,
  positive,
  sparkline,
  hint,
}: {
  label: string
  valueText: string
  positive: boolean | null
  sparkline: number[]
  hint?: ReactNode
}) {
  return (
    <div className="col-span-2 flex items-center justify-between gap-3 rounded-xl border border-border/60 bg-surface/40 px-3 py-3">
      <div className="min-w-0">
        <div className="text-[10px] font-medium uppercase tracking-wider text-fg-subtle">{label}</div>
        <div className={cn('mt-1 truncate font-mono text-metric-sm font-semibold tabular-nums', positive == null ? 'text-fg' : positive ? 'text-profit' : 'text-risk')}>
          {valueText}
        </div>
        {hint && <div className="mt-0.5 truncate text-[10px] text-fg-subtle">{hint}</div>}
      </div>
      {sparkline.length > 1 && (
        <div className="shrink-0">
          <Sparkline data={sparkline} tone={positive == null ? 'info' : positive ? 'profit' : 'risk'} width={88} height={32} />
        </div>
      )}
    </div>
  )
}

type PendingShell = 'ring' | 'bar' | 'number'

// Not genuinely computed yet — shell rendered inert (track only, no fabricated
// fill/reading) at low opacity with a subtle pulse (it reads as "deferred",
// not "broken"), plus a plain "Pending" badge so the deferral reads as
// deliberate without leaking an internal tracking code.
export function PendingMetricTile({
  label,
  shell = 'number',
}: {
  label: string
  shell?: PendingShell
}) {
  return (
    <div className="flex min-w-0 flex-col items-center gap-1.5 rounded-xl border border-dashed border-border/60 bg-surface/20 px-3 py-3 text-center">
      <div className="animate-pulse opacity-40 grayscale">
        {shell === 'ring' ? (
          <Ring value={0} size={56} thickness={6} tone="info" centerLabel="—" />
        ) : shell === 'bar' ? (
          <div className="flex h-14 w-full flex-col justify-end gap-1.5 px-1">
            <div className="h-2 w-full rounded-full bg-fg-subtle/30" />
            <span className="font-mono text-metric-sm font-semibold text-fg-subtle">—</span>
          </div>
        ) : (
          <span className="font-mono text-metric-sm font-semibold text-fg-subtle">—</span>
        )}
      </div>
      <span className="flex items-center gap-1 truncate text-[10px] font-medium uppercase tracking-wider text-fg-subtle">
        <Clock size={10} className="shrink-0" /> {label}
      </span>
      <Badge variant="warning" className="text-[9px]" title="Not yet computed — shown honestly rather than as a fabricated number.">
        Pending
      </Badge>
    </div>
  )
}
