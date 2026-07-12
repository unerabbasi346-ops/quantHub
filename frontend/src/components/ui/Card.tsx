// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Components: "Standardize ... cards ... Every component should have a
//   reusable implementation." §Dashboards: "customizable widgets" render
//   inside cards — Card is the canonical widget container.
// handbook/ui/visual_engineering/05_GLASS_SURFACE_SYSTEM: every card/panel/
//   chart/modal surface is semi-transparent + backdrop-blur + a soft
//   low-opacity border + an inner highlight + a subtle gradient — "If any
//   card, panel, chart, modal, or workspace appears flat, opaque, or
//   inconsistent, the implementation is incomplete." §06_BORDER_ELEVATION
//   (card radius 16-20px, target 18px) and §09_COMPONENT_BLUEPRINT_LIBRARY
//   (border radius 16-20px, thin low-opacity border, glass surface, soft
//   gradient, soft ambient glow — required on every card, no exceptions).
// Per Doc 00 §14.11
//
// GLASS SURFACE — SINGLE SOURCE OF TRUTH (Phase 2): `glassSurface()` is the
// one glass recipe every bordered surface in QuantHub shares (native CSS
// backdrop-filter via Tailwind's backdrop-blur, no library). Every OTHER
// hand-rolled "glow panel" in the codebase (Panel.tsx, StatCard, the
// dashboard hero cards, the strategy carousel) used to duplicate this same
// class string inline; they now import and call this function so a future
// glass-recipe change updates every surface from one place, per the owner's
// instruction to "apply via Card.tsx so the fix is visible everywhere at
// once." `elevation` only changes shadow weight and highlight tint — every
// elevation is equally glass; Doc 05 draws no "some cards get glass"
// exception.
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

export type Elevation = 'flat' | 'raised' | 'elevated' | 'glow'

// Doc 06: card radius 16-20px, target 18px. One constant so charts/modals/
// panels stay pixel-identical to Card without re-typing the value.
export const CARD_RADIUS = 'rounded-[18px]'

// Translucent base + shadow ramp per elevation. Every tier is see-through
// (Doc 05 "semi-transparent background") — flat is the most transparent
// (secondary content), glow/elevated the least (primary content needs a
// touch more surface to stay readable under the ambient background).
const SURFACE: Record<Elevation, string> = {
  flat: 'bg-surface/50 shadow-none',
  raised: 'bg-surface-raised/55 shadow-sm',
  elevated: 'bg-surface-raised/65 shadow-lg',
  glow: 'bg-surface-raised/55 shadow-glow',
}

// Inner top highlight tint per elevation — glow gets the brand violet
// hairline, everything else a neutral foreground-tinted one so it still
// reads correctly in light mode (a hardcoded white highlight would vanish
// against a white card).
const HIGHLIGHT: Record<Elevation, string> = {
  flat: 'after:via-fg/[0.05]',
  raised: 'after:via-fg/[0.08]',
  elevated: 'after:via-fg/[0.12]',
  glow: 'after:via-accent/25',
}

// Interactive hover is elevation-aware: a glow card intensifies its halo; the
// others lift with the neutral shadow ramp they already use. The lift itself is
// driven by framer (whileHover y) rather than a Tailwind transform, because the
// card's own inline transform is owned by framer during/after the enter reveal.
const INTERACTIVE: Record<Elevation, string> = {
  flat: 'hover:shadow-md hover:border-border-strong/60',
  raised: 'hover:shadow-lg hover:border-border-strong/60',
  elevated: 'hover:shadow-lg hover:border-border-strong/60',
  glow: 'hover:shadow-glow-hover',
}

// Doc 05 Glass Surface System — the one glass recipe. `backdrop-blur-xl` is
// the native CSS `backdrop-filter: blur()` (no library). Border sits at 8%
// opacity (Doc 06's 6-10% range) — visual separation between surfaces comes
// from the shadow ramp + the ambient ("Dashboard Background: ambient radial
// lighting") page background showing through the blur, not from border
// contrast, which is the whole point of "glass" over a flat bordered box.
export function glassSurface(elevation: Elevation = 'raised'): string {
  return cn(
    'relative isolate overflow-hidden',
    CARD_RADIUS,
    'backdrop-blur-xl border border-border/[0.08]',
    SURFACE[elevation],
    // soft top-to-bottom sheen gradient (Doc 09: "Soft Background Gradient")
    'before:pointer-events-none before:absolute before:inset-0',
    'before:bg-gradient-to-b before:from-fg/[0.05] before:via-transparent before:to-transparent',
    // 1px inner top highlight (Doc 06: "inner highlight")
    'after:pointer-events-none after:absolute after:inset-x-0 after:top-0 after:h-px',
    'after:bg-gradient-to-r after:from-transparent after:to-transparent',
    HIGHLIGHT[elevation],
  )
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
        glassSurface(elevation),
        interactive && cn('cursor-pointer transition-[box-shadow,border-color] duration-150', INTERACTIVE[elevation]),
        className,
      )}
      {...props}
    />
  )
}

// Doc 09 §Header Specification: "Header Height 56-64px" — px-5 (20px each
// side) is Doc 09's card padding; py-[18px] brings a card-title-sized (19px,
// 1.2 line-height) header to ~59px total, inside the required range.
export function CardHeader({ className, ...props }: HTMLMotionProps<'div'>) {
  const reveal = useReveal('cardHeader')
  return (
    <motion.div
      {...reveal}
      className={cn(
        'flex items-center justify-between gap-4 border-b border-border px-5 py-[18px]',
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
      className={cn('text-card-title font-medium tracking-tight text-fg', className)}
      {...props}
    />
  )
}

export function CardContent({ className, ...props }: HTMLMotionProps<'div'>) {
  const reveal = useReveal('cardContent')
  return <motion.div {...reveal} className={cn('p-5 text-body text-fg', className)} {...props} />
}
