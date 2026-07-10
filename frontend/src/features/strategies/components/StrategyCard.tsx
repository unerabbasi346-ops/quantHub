// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Components (cards), §Data Visualization (inline sparkline).
// Doc 14 §10.2 (Strategy Governance), §10.3 (Backtesting). Doc 00 §14.5/§14.7
//   — DATA HONESTY: every number real; uncomputed metrics show an explicit
//   "Not yet computed" state (F-18 risk metrics / F-21 equity-curve), never a
//   fabricated value. Per Doc 00 §14.11
//
// One glowing card per registered strategy (owner request, point 4). Clicking
// it navigates to the dedicated detail route /strategies/[id] (point 6). Scales
// to any number of strategies via the caller's responsive grid.
'use client'

import Link from 'next/link'
import { ArrowUpRight, Brain } from 'lucide-react'
import { Badge, Card, Sparkline } from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import type { StrategyPerformance } from '../hooks/useStrategyPerformance'
import { isReferenceStrategy, REFERENCE_BADGE, REFERENCE_CAPTION, REFERENCE_TOOLTIP } from '../labels'

function returnPct(v: string | null): { text: string; tone: 'profit' | 'risk' | 'muted' } {
  if (v === null) return { text: '—', tone: 'muted' }
  const n = Number.parseFloat(v) * 100
  return { text: `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`, tone: n >= 0 ? 'profit' : 'risk' }
}

// Honest "not computed" chip — real per-step equity-curve tracking does not
// exist yet, so drawdown / win-rate cannot be computed (F-18/F-21). We say so
// rather than invent a number.
function NotComputed({ label }: { label: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-wide text-fg-subtle">{label}</span>
      <span
        title="Not yet computed — this needs a per-step equity curve, which the platform doesn't track yet. Shown honestly rather than as a fabricated number."
        className="inline-flex w-fit items-center gap-1 rounded-md border border-border bg-surface px-1.5 py-0.5 text-[11px] font-medium text-fg-subtle"
      >
        <span aria-hidden className="h-1 w-1 rounded-full bg-fg-subtle" />
        Not yet computed
      </span>
    </div>
  )
}

export function StrategyCard({ perf }: { perf: StrategyPerformance }) {
  const { strategy, sparkline, latestReturn, hasBacktest, loading } = perf
  const ret = returnPct(latestReturn)
  const reference = isReferenceStrategy(strategy.name)
  const active = strategy.status.toUpperCase() === 'ACTIVE'

  return (
    <Card elevation="glow" interactive className="group h-full">
      <Link href={`/strategies/${strategy.id}`} className="flex h-full flex-col gap-4 p-5" aria-label={`Open ${strategy.name} detail`}>
        {/* Header: name + status/reference badges */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-2.5">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
              <Brain size={16} />
            </span>
            <div className="min-w-0">
              <h3 className="truncate text-sm font-semibold tracking-tight text-fg">{strategy.name}</h3>
              <p className="mt-0.5 truncate text-[11px] text-fg-subtle">
                {reference ? REFERENCE_CAPTION : <>v{strategy.version}</>}
              </p>
            </div>
          </div>
          <ArrowUpRight size={16} className="shrink-0 text-fg-subtle transition-colors group-hover:text-accent" />
        </div>

        {/* Status row */}
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant={active ? 'profit' : 'neutral'}>{strategy.status}</Badge>
          {reference && (
            <Badge variant="warning" title={REFERENCE_TOOLTIP}>
              {REFERENCE_BADGE}
            </Badge>
          )}
        </div>

        {/* Sparkline of signed conviction (real signal values) */}
        <div className="flex items-end justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-wide text-fg-subtle">Return (backtest)</div>
            <div
              className={cn(
                'mt-0.5 font-mono text-2xl font-semibold tabular-nums',
                ret.tone === 'profit' ? 'text-profit' : ret.tone === 'risk' ? 'text-risk' : 'text-fg-muted',
              )}
            >
              {ret.text}
            </div>
            <div className="text-[11px] text-fg-subtle">{hasBacktest ? 'latest backtest total return' : 'no backtest run yet'}</div>
          </div>
          <div className="shrink-0">
            {loading ? (
              <div className="skeleton h-8 w-24" />
            ) : sparkline.length > 1 ? (
              <Sparkline data={sparkline} tone="info" width={104} height={34} />
            ) : (
              <div className="flex h-[34px] w-[104px] items-center justify-center text-[11px] text-fg-subtle">no signals</div>
            )}
          </div>
        </div>

        {/* Honest deferred metrics */}
        <div className="mt-auto grid grid-cols-2 gap-3 border-t border-border/60 pt-3">
          <NotComputed label="Max drawdown" />
          <NotComputed label="Win rate" />
        </div>
      </Link>
    </Card>
  )
}
