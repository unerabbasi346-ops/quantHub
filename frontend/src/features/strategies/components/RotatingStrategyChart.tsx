// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Data Visualization, §Interaction Standards (motion conveys state; pause on
//   hover/focus). Doc 15 §11.1.5 (signal value = signed conviction).
//   Doc 00 §14.11 / §14.5 (data honesty: charts plot real signals only).
//
// Auto-rotating chart panel (owner request, point 5): cycles through each
// strategy's OWN conviction chart on a fixed interval, looping. Pauses on
// hover/focus. Correct for 1 strategy (no rotation, no dots), 2, or many.
'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Brain, Pause } from 'lucide-react'
import { Badge, LineChart, glassSurface } from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { useReveal } from '@/lib/motion'
import type { StrategyPerformance } from '../hooks/useStrategyPerformance'
import { isReferenceStrategy, REFERENCE_BADGE, REFERENCE_TOOLTIP } from '../labels'

const ROTATE_MS = 12_000 // within the requested 10–15s window

export function RotatingStrategyChart({ items }: { items: StrategyPerformance[] }) {
  const count = items.length
  const [index, setIndex] = useState(0)
  const [paused, setPaused] = useState(false)

  // Keep the index valid if the strategy list changes length.
  useEffect(() => {
    if (index >= count && count > 0) setIndex(0)
  }, [count, index])

  // Advance one slide per interval; the timer is keyed on `index` so a manual
  // jump (dot click) restarts a full interval, and `paused` halts it. Single
  // strategy never rotates.
  useEffect(() => {
    if (paused || count <= 1) return
    const t = setTimeout(() => setIndex((i) => (i + 1) % count), ROTATE_MS)
    return () => clearTimeout(t)
  }, [index, paused, count])

  if (count === 0) return null

  const current = items[Math.min(index, count - 1)]
  const reference = isReferenceStrategy(current.strategy.name)
  const canPlot = current.convictionPoints.length >= 2

  // Same 'card' kind Card/Panel/HeroSection's shells use — a glass surface
  // self-reveals as a shell, its content cascading in a beat later.
  // Non-glow (VE_13: glow reserved for the Hero Chart / AI Workspace / active
  // controls / focus states — this carousel is a secondary chart below the
  // Hero, and giving it the same halo would create a competing focal point).
  const reveal = useReveal('card')
  return (
    <motion.div
      {...reveal}
      className={cn(glassSurface('elevated'), 'flex h-full flex-col p-5')}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
      role="group"
      aria-label="Strategy performance carousel"
      aria-roledescription="carousel"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <Brain size={16} />
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="truncate text-sm font-semibold tracking-tight text-fg">{current.strategy.name}</h2>
              {reference && (
                <Badge variant="warning" title={REFERENCE_TOOLTIP}>
                  {REFERENCE_BADGE}
                </Badge>
              )}
            </div>
            <p className="mt-0.5 text-[11px] text-fg-subtle">Signed Alpha Score over time · signals feed</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-fg-subtle">
          {count > 1 && (
            <span className="tabular-nums">
              {index + 1} / {count}
            </span>
          )}
          {paused && count > 1 && (
            <span className="inline-flex items-center gap-1 text-fg-muted" title="Rotation paused (hover/focus)">
              <Pause size={12} /> paused
            </span>
          )}
        </div>
      </div>

      <div className="mt-4 flex-1">
        {canPlot ? (
          // key forces a fresh mount per strategy so nothing from the previous
          // slide lingers (crossfade in on each rotation).
          <div key={current.strategy.id} className="animate-fade-in">
            <LineChart data={current.convictionPoints} tone="info" zeroBaseline height={240} />
          </div>
        ) : (
          <div className="flex h-[240px] items-center justify-center rounded-lg border border-dashed border-border text-sm text-fg-muted">
            {current.strategy.name} has too few signals to plot a curve yet.
          </div>
        )}
      </div>

      {/* Rotation controls: progress bar + jump dots (only when >1 strategy) */}
      {count > 1 && (
        <div className="mt-4 space-y-3">
          <div className="h-0.5 w-full overflow-hidden rounded-full bg-border">
            <div
              key={`${index}-${paused}`}
              className="h-full rounded-full bg-accent animate-progress"
              style={{ animationDuration: `${ROTATE_MS}ms`, animationPlayState: paused ? 'paused' : 'running' }}
            />
          </div>
          <div className="flex items-center justify-center gap-2" role="tablist" aria-label="Select strategy">
            {items.map((it, i) => (
              <button
                key={it.strategy.id}
                type="button"
                role="tab"
                aria-selected={i === index}
                aria-label={`Show ${it.strategy.name}`}
                onClick={() => setIndex(i)}
                className={cn(
                  'h-2 rounded-full transition-all duration-200',
                  i === index ? 'w-6 bg-accent' : 'w-2 bg-border-strong hover:bg-fg-subtle',
                )}
              />
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}
