// Governing specification: Doc 03 §Strategy Cards ("miniature research reports":
//   Status, mini equity curve, Signal Count, Current Conviction, Current Asset,
//   Last Signal + the risk metrics), Doc 04 §Strategy Performance Card.
// Doc 00 §14.5/§14.7 — DATA HONESTY: every number real; uncomputed metrics show
//   an explicit "Not yet computed" state (F-18 risk metrics / F-21 equity-curve),
//   never a fabricated value. Per Doc 00 §14.11
//
// One glowing card per registered strategy. Clicking it opens /strategies/[id].
// The card packs the Doc 03 field set that REAL data supports (signals-derived:
// count, current conviction, asset, last signal) and honestly defers the metrics
// the platform does not compute yet (drawdown / win rate / Sharpe).
'use client'

import Link from 'next/link'
import { ArrowUpRight, Brain } from 'lucide-react'
import { Badge, Card, Sparkline } from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { formatReturn, formatSignalStrength, formatTimestamp } from '@/lib/utils/format'
import { useSyncStore } from '@/lib/store/sync'
import type { StrategyPerformance } from '../hooks/useStrategyPerformance'
import { isReferenceStrategy, REFERENCE_BADGE, REFERENCE_CAPTION, REFERENCE_TOOLTIP } from '../labels'

function returnPct(v: string | null): { text: string; tone: 'profit' | 'risk' | 'muted' } {
  if (v === null) return { text: '—', tone: 'muted' }
  const n = Number.parseFloat(v)
  return { text: formatReturn(n), tone: n >= 0 ? 'profit' : 'risk' }
}

function fmtSignalTime(iso: string): string {
  return formatTimestamp(iso)
}

// Honest "not computed" chip — real per-step equity-curve tracking does not
// exist yet, so drawdown / win-rate / Sharpe cannot be computed (F-18/F-21).
function NotComputed({ label }: { label: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-wide text-fg-subtle">{label}</span>
      <span
        title="Not yet computed — this needs a per-step equity curve, which the platform doesn't track yet. Shown honestly rather than as a fabricated number."
        className="inline-flex w-fit items-center gap-1 rounded-md border border-border bg-surface px-1.5 py-0.5 text-[11px] font-medium text-fg-subtle"
      >
        <span aria-hidden className="h-1 w-1 rounded-full bg-fg-subtle" />
        Not computed
      </span>
    </div>
  )
}

// A real, computed metric cell.
function Metric({ label, value, tone = 'default' }: { label: string; value: string; tone?: 'default' | 'profit' | 'risk' }) {
  return (
    <div className="flex flex-col gap-1 min-w-0">
      <span className="truncate text-[11px] uppercase tracking-wide text-fg-subtle">{label}</span>
      <span
        className={cn(
          'truncate font-mono text-sm font-semibold tabular-nums',
          tone === 'profit' ? 'text-profit' : tone === 'risk' ? 'text-risk' : 'text-fg',
        )}
      >
        {value}
      </span>
    </div>
  )
}

export function StrategyCard({ perf }: { perf: StrategyPerformance }) {
  const { strategy, signals, sparkline, latestReturn, hasBacktest, loading } = perf
  const ret = returnPct(latestReturn)
  const reference = isReferenceStrategy(strategy.name)

  // Real, signals-derived fields (no fetch beyond what the card already has).
  const ordered = [...signals].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime())
  const last = ordered.at(-1)
  const conviction = last ? Number.parseFloat(last.value) : null
  const asset = typeof strategy.config?.symbol === 'string' ? (strategy.config.symbol as string) : null
  // Global Synchronization (Doc 11): opening a strategy from anywhere makes
  // it the default selection everywhere else (e.g. the /strategies list).
  const setSyncedStrategyId = useSyncStore((s) => s.setSelectedStrategyId)

  return (
    <Card elevation="elevated" interactive className="group h-full">
      <Link
        href={`/strategies/${strategy.id}`}
        className="flex h-full flex-col gap-4 p-5"
        aria-label={`Open ${strategy.name} detail`}
        onClick={() => setSyncedStrategyId(strategy.id)}
      >
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
          <Badge variant={strategy.status.toUpperCase() === 'ACTIVE' ? 'profit' : 'neutral'}>{strategy.status}</Badge>
          {reference && (
            <Badge variant="warning" title={REFERENCE_TOOLTIP}>
              {REFERENCE_BADGE}
            </Badge>
          )}
        </div>

        {/* Return + mini conviction curve */}
        <div className="flex items-end justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-wide text-fg-subtle">Return (backtest)</div>
            <div
              className={cn(
                'mt-0.5 font-mono text-metric font-bold tabular-nums',
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

        {/* Real, signals-derived metrics (Doc 03 field set that data supports) */}
        <div className="grid grid-cols-3 gap-3 border-t border-border/60 pt-3">
          <Metric label="Signals" value={String(signals.length)} />
          <Metric
            label="Conviction"
            value={conviction != null ? formatSignalStrength(conviction) : '—'}
            tone={conviction == null ? 'default' : conviction >= 0 ? 'profit' : 'risk'}
          />
          <Metric label="Asset" value={asset ?? '—'} />
        </div>

        {/* Honestly deferred risk metrics */}
        <div className="mt-auto grid grid-cols-3 gap-3">
          <NotComputed label="Max drawdown" />
          <NotComputed label="Win rate" />
          <NotComputed label="Sharpe" />
        </div>

        {/* Last signal footer */}
        <div className="text-[11px] text-fg-subtle">
          {last ? <>Last signal · {fmtSignalTime(last.ts)}</> : 'No signals recorded yet'}
        </div>
      </Link>
    </Card>
  )
}
