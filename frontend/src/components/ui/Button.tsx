// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Components: "Standardize buttons ... Every component should have a
//   reusable implementation." §Interaction Standards: "Clear primary
//   actions ... confirmation for destructive operations."
// Doc 08 §Component Standards: reusable design-system component, no
//   duplicated UI implementations — Doc 08 §Component Standards
// handbook/ui/visual_engineering/09_COMPONENT_BLUEPRINT_LIBRARY §Button
//   Specification: "Primary — Filled, Soft Glow, Hover Lift, Active
//   Compression. Secondary — Glass Surface, Thin Border, Soft Hover. Danger
//   — Controlled emphasis, Never bright red. Forbidden: Browser default
//   buttons, Flat buttons, No hover feedback."
// Per Doc 00 §14.11
'use client'

import type { ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils/cn'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type ButtonSize = 'sm' | 'md'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
}

// Doc 06 §Interaction Standards "clear primary actions" — `primary` is the
// one strong-emphasis action per view; `danger` is reserved for destructive
// operations, which Doc 06 requires a CONFIRMATION step for (that
// confirmation is the caller's responsibility — a Modal/Dialog component —
// not this Button's; Button only signals destructive intent visually via
// the `risk` token, same reuse as the P&L judgment call in globals.css: no
// separate "danger" hue is invented beyond `risk`).
//
// Every non-primary variant is a genuine glass surface (backdrop-blur +
// translucent fill + thin low-opacity border), not a flat filled rect —
// Doc 09 forbids "flat buttons" outright. `danger` stays translucent-red
// rather than a solid fill ("controlled emphasis, never bright red").
const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  // Filled + soft glow (Doc 09). `shadow-glow` is the same violet-halo token
  // Card uses for its `glow` elevation — reused here so the one strong CTA
  // on a view reads as unmistakably primary, hover intensifies the halo.
  primary:
    'bg-accent text-accent-fg shadow-glow hover:bg-accent/90 hover:shadow-glow-hover hover:enabled:-translate-y-px focus-visible:ring-accent',
  secondary:
    'border border-border/70 bg-surface/50 text-fg backdrop-blur-md hover:border-border-strong/80 hover:bg-surface-hover/70 hover:shadow-sm focus-visible:ring-border',
  ghost:
    'border border-transparent bg-transparent text-fg-muted backdrop-blur-md hover:border-border/50 hover:bg-surface-hover/50 hover:text-fg focus-visible:ring-border',
  danger:
    'border border-risk/30 bg-risk/15 text-risk backdrop-blur-md hover:border-risk/50 hover:bg-risk/25 focus-visible:ring-risk',
}

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-[13px]',
  md: 'h-10 px-4 text-btn',
}

// Doc 08 §Architecture: stateless presentation component.
export function Button({
  variant = 'secondary',
  size = 'md',
  className,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      suppressHydrationWarning
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium',
        // Doc 06 §Interaction Standards — subtle hover micro-animation
        // (brightness/elevation lift + press-scale), ≤150ms, disabled below
        // via the global prefers-reduced-motion guard in globals.css.
        'transition-[background-color,border-color,filter,transform,box-shadow] duration-150 ease-out',
        'hover:enabled:brightness-110 active:enabled:scale-[0.97]',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
        'disabled:opacity-50 disabled:pointer-events-none',
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className,
      )}
      disabled={disabled}
      {...props}
    />
  )
}
