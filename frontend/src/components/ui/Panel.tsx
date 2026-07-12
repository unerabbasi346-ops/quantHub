// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Components: one reusable surface treatment.
// handbook/ui/visual_engineering/05_GLASS_SURFACE_SYSTEM / 09_COMPONENT_
//   BLUEPRINT_LIBRARY: same glass recipe as Card — see Card.tsx's
//   `glassSurface()`, the single source of truth this Panel now calls
//   instead of duplicating the class string.
// Per Doc 00 §14.11
//
// GLASS SURFACE (owner visual language, applied app-wide): the single source
// of truth for a chart panel / table wrapper / KPI group surface when a full
// <Card> (with header/title slots) is more than a content surface needs. It
// calls the same `glassSurface()` recipe as Card so every surface across
// Portfolio / Risk / Execution / Markets / Dashboard / Strategies reads as
// one system, not per-file variants.
//
// GLOW (VE_13 Design Authority, "Lighting": restrained glows, avoid excessive
// bloom — glow is reserved for the Hero Chart, the AI/Intelligence Workspace,
// active controls, and focus states, not every standard surface). Panel
// therefore defaults to `elevated` — the same non-glow top tier Card uses for
// primary content — and only glows when a caller explicitly opts in via
// `elevation="glow"` for one of those reserved contexts.
//
// MOTION (digital materialization): self-reveals via useReveal('card') like a
// Card, so the shell forms first and its content cascades in — no orchestration.
'use client'

import { motion, type HTMLMotionProps } from 'framer-motion'
import { cn } from '@/lib/utils/cn'
import { useReveal } from '@/lib/motion'
import { glassSurface, type Elevation } from './Card'

interface PanelProps extends HTMLMotionProps<'div'> {
  /** Intensify the halo on hover (for clickable surfaces). */
  interactive?: boolean
  /** Reserved for Hero Chart / AI Workspace / active controls / focus states — see VE_13. */
  elevation?: Elevation
}

export function Panel({ className, interactive, elevation = 'elevated', ...props }: PanelProps) {
  const reveal = useReveal('card')
  return (
    <motion.div
      {...reveal}
      whileHover={interactive ? { y: -2 } : undefined}
      className={cn(
        glassSurface(elevation),
        interactive &&
          cn(
            'cursor-pointer transition-[box-shadow] duration-150',
            elevation === 'glow' ? 'hover:shadow-glow-hover' : 'hover:shadow-lg',
          ),
        className,
      )}
      {...props}
    />
  )
}
