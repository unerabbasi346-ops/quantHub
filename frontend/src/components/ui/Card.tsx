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
//
// MOTION (digital materialization): the card SHELL forms first (opacity+blur,
// its border/shadow defining), then — a beat later, driven purely by each
// piece's own positional cascade delay — the header, title and content
// materialize inside it. No orchestration wiring: every sub-part self-reveals
// via useReveal, so the shell-before-content ordering falls out of the per-kind
// `base` delays in the motion config.
'use client'

import { motion, type HTMLMotionProps } from 'framer-motion'
import { cn } from '@/lib/utils/cn'
import { useReveal } from '@/lib/motion'

type Elevation = 'flat' | 'raised' | 'elevated' | 'glow'

const ELEVATION: Record<Elevation, string> = {
  flat: 'bg-surface border border-border',
  raised: 'bg-surface-raised border border-border shadow-sm',
  elevated:
    'bg-surface-raised border border-border-strong shadow-lg ' +
    // faint "lit from above" top highlight for the primary surface
    'before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:h-px ' +
    'before:bg-gradient-to-r before:from-transparent before:via-white/10 before:to-transparent',
  // GLOW (owner visual language): dark charcoal base + a soft violet halo built
  // from the brand accent, no hard border (the halo's 0 0 0 1px ring stands in
  // for one). A violet-tinted top highlight replaces the neutral white one so
  // the whole card reads as brand-lit. Semantic P&L/status hues untouched.
  glow:
    'bg-surface-raised shadow-glow ' +
    'before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:h-px ' +
    'before:bg-gradient-to-r before:from-transparent before:via-accent/25 before:to-transparent',
}

// Interactive hover is elevation-aware: a glow card intensifies its halo; the
// others lift with the neutral shadow ramp they already use. The lift itself is
// driven by framer (whileHover y) rather than a Tailwind transform, because the
// card's own inline transform is owned by framer during/after the enter reveal.
const INTERACTIVE: Record<Elevation, string> = {
  flat: 'hover:shadow-md hover:border-border-strong',
  raised: 'hover:shadow-lg hover:border-border-strong',
  elevated: 'hover:shadow-lg hover:border-border-strong',
  glow: 'hover:shadow-glow-hover',
}

interface CardProps extends HTMLMotionProps<'div'> {
  elevation?: Elevation
  interactive?: boolean
}

// Doc 08 §Architecture: stateless presentation component.
export function Card({ className, elevation = 'raised', interactive, ...props }: CardProps) {
  const reveal = useReveal('card')
  return (
    <motion.div
      {...reveal}
      whileHover={interactive ? { y: -2 } : undefined}
      className={cn(
        'relative rounded-xl',
        ELEVATION[elevation],
        interactive && cn('cursor-pointer transition-[box-shadow,border-color] duration-150', INTERACTIVE[elevation]),
        className,
      )}
      {...props}
    />
  )
}

export function CardHeader({ className, ...props }: HTMLMotionProps<'div'>) {
  const reveal = useReveal('cardHeader')
  return (
    <motion.div
      {...reveal}
      className={cn(
        'flex items-center justify-between gap-4 border-b border-border px-5 py-3.5',
        className,
      )}
      {...props}
    />
  )
}

export function CardTitle({ className, ...props }: HTMLMotionProps<'h3'>) {
  const reveal = useReveal('title')
  return (
    <motion.h3
      {...reveal}
      className={cn('text-sm font-semibold tracking-tight text-fg', className)}
      {...props}
    />
  )
}

export function CardContent({ className, ...props }: HTMLMotionProps<'div'>) {
  const reveal = useReveal('cardContent')
  return <motion.div {...reveal} className={cn('p-5', className)} {...props} />
}
