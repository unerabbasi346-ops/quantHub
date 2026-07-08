// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Interaction Standards: "loading/success/error states." A skeleton is
//   the loading state that preserves layout (no content-shift pop-in) while
//   data resolves — Doc 08 §Performance (perceived performance).
// Per Doc 00 §14.11
import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils/cn'

// A single shimmering placeholder block. `.skeleton` (globals.css) carries
// the surface + shimmer keyframe (disabled under prefers-reduced-motion).
export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('skeleton', className)} {...props} />
}

// A table-shaped skeleton so a loading table holds its footprint instead of
// collapsing to a spinner and snapping back — used by data tables while their
// query is pending.
export function SkeletonTable({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div role="status" aria-live="polite" aria-label="Loading" className="w-full">
      <div className="mb-3 flex gap-4 border-b border-border pb-2.5">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 flex-1" />
        ))}
      </div>
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="flex gap-4">
            {Array.from({ length: cols }).map((_, c) => (
              <Skeleton
                key={c}
                className={cn('h-4 flex-1', c === 0 && 'max-w-[8rem]')}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

// A KPI-tile skeleton row for stat strips.
export function SkeletonStats({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4" role="status" aria-label="Loading">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-6 w-28" />
        </div>
      ))}
    </div>
  )
}
