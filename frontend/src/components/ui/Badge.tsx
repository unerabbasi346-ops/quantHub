// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Components: "Standardize ... badges ..."
//   §Visual Language: "Semantic colors: green=profit, red=risk,
//   blue=information, amber=warning."
// Per Doc 00 §14.11
import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils/cn'

// Doc 06 §Visual Language's four semantic hues, plus `neutral` for
// non-semantic labels (e.g. an instrument symbol, a plain status word).
//
// JUDGMENT CALL (Doc 00 §14.5/§14.7 — flagged, see globals.css for the
// full reasoning): Doc 06 names "red=risk", not "red=loss". A losing
// position/order P&L is nonetheless shown in red by convention — that is
// captured here by NOT adding a separate `loss` variant. Callers displaying
// a signed P&L number should pick `variant={value >= 0 ? 'profit' : 'risk'}`
// (see `pnlBadgeVariant` below) — reusing `risk`'s red, never inventing a
// second, visually-identical "loss" hue Doc 06 never specified.
export type BadgeVariant = 'profit' | 'risk' | 'info' | 'warning' | 'neutral'

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  profit: 'bg-profit-soft text-profit',
  risk: 'bg-risk-soft text-risk',
  info: 'bg-info-soft text-info',
  warning: 'bg-warning-soft text-warning',
  neutral: 'bg-surface-hover text-fg-muted',
}

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
}

// Doc 08 §Architecture: stateless presentation component.
export function Badge({ variant = 'neutral', className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        VARIANT_CLASSES[variant],
        className,
      )}
      {...props}
    />
  )
}

// Shared helper so every future P&L/signal-sign display (positions,
// executions, backtests) resolves the profit/risk judgment call the same
// way, instead of each feature re-deciding it — see the judgment-call
// comment above.
export function pnlBadgeVariant(value: number): BadgeVariant {
  return value >= 0 ? 'profit' : 'risk'
}
