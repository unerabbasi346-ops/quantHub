// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Components: "Standardize buttons ... Every component should have a
//   reusable implementation." §Interaction Standards: "Clear primary
//   actions ... confirmation for destructive operations."
// Doc 08 §Component Standards: reusable design-system component, no
//   duplicated UI implementations — Doc 08 §Component Standards
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
// confirmation is the caller's responsibility — a dialog/AlertDialog
// component — not this Button's; Button only signals destructive intent
// visually via the `risk` token, same reuse as the P&L judgment call in
// globals.css: no separate "danger" hue is invented beyond `risk`).
const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: 'bg-info text-white hover:bg-info/90 focus-visible:ring-info',
  secondary:
    'bg-surface text-fg border border-border hover:bg-surface-hover focus-visible:ring-border',
  ghost: 'bg-transparent text-fg hover:bg-surface-hover focus-visible:ring-border',
  danger: 'bg-risk text-white hover:bg-risk/90 focus-visible:ring-risk',
}

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-sm',
  md: 'h-10 px-4 text-sm',
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
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-md font-medium',
        'transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
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
