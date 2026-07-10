// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Components: one reusable surface treatment. Per Doc 00 §14.11
//
// GLOW SURFACE (owner visual language, applied app-wide): the single source of
// truth for the violet-halo card treatment when a full <Card> (with header/
// title slots) is more than a content surface needs — e.g. a chart panel, a
// table wrapper, a KPI group. It mirrors Card elevation="glow" exactly (dark
// charcoal base + soft violet halo standing in for a border + a violet top
// hairline) so every glowing surface across Portfolio / Risk / Execution /
// Markets / Dashboard / Strategies reads as one system, not per-file variants.
//
// MOTION (digital materialization): self-reveals via useReveal('card') like a
// Card, so the shell forms first and its content cascades in — no orchestration.
'use client'

import { motion, type HTMLMotionProps } from 'framer-motion'
import { cn } from '@/lib/utils/cn'
import { useReveal } from '@/lib/motion'

interface PanelProps extends HTMLMotionProps<'div'> {
  /** Intensify the halo on hover (for clickable surfaces). */
  interactive?: boolean
}

export function Panel({ className, interactive, ...props }: PanelProps) {
  const reveal = useReveal('card')
  return (
    <motion.div
      {...reveal}
      whileHover={interactive ? { y: -2 } : undefined}
      className={cn(
        'relative rounded-xl bg-surface-raised shadow-glow',
        // violet top hairline replaces the neutral border (matches Card glow)
        'before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:h-px',
        'before:bg-gradient-to-r before:from-transparent before:via-accent/25 before:to-transparent',
        interactive && 'cursor-pointer transition-[box-shadow] duration-150 hover:shadow-glow-hover',
        className,
      )}
      {...props}
    />
  )
}
