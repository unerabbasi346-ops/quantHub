// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Components: "Standardize ... cards ... Every component should have a
//   reusable implementation." §Dashboards: "customizable widgets" render
//   inside cards — Card is the canonical widget container.
// Per Doc 00 §14.11
//
// VISUAL HIERARCHY (owner feedback): cards are no longer all one flat
// weight. `elevation` gives a deliberate ramp — `flat` (secondary content,
// hairline border only), `raised` (default card, subtle shadow + lighter
// surface), `elevated` (primary content, stronger shadow + top hairline
// highlight). Reserve bordered cards for content that truly needs grouping;
// prefer Section (headings + dividers) for the rest.
import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils/cn'

type Elevation = 'flat' | 'raised' | 'elevated'

const ELEVATION: Record<Elevation, string> = {
  flat: 'bg-surface border border-border',
  raised: 'bg-surface-raised border border-border shadow-sm',
  elevated:
    'bg-surface-raised border border-border-strong shadow-lg ' +
    // faint "lit from above" top highlight for the primary surface
    'before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:h-px ' +
    'before:bg-gradient-to-r before:from-transparent before:via-white/10 before:to-transparent',
}

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  elevation?: Elevation
  interactive?: boolean
}

// Doc 08 §Architecture: stateless presentation component.
export function Card({ className, elevation = 'raised', interactive, ...props }: CardProps) {
  return (
    <div
      className={cn(
        'relative rounded-xl',
        ELEVATION[elevation],
        interactive &&
          'transition-[transform,box-shadow,border-color] duration-150 hover:-translate-y-0.5 hover:shadow-lg hover:border-border-strong',
        className,
      )}
      {...props}
    />
  )
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-4 border-b border-border px-5 py-3.5',
        className,
      )}
      {...props}
    />
  )
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={cn('text-sm font-semibold tracking-tight text-fg', className)}
      {...props}
    />
  )
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-5', className)} {...props} />
}
