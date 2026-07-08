// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Visual Language: a small, consistent brand mark shown in the sidebar
//   (even when collapsed) and the top bar (owner request). Inline SVG — a
//   stylized candlestick "Q" motif, self-contained, theme-aware via the
//   violet brand-accent token (deliberately off all four semantic hues).
// Per Doc 00 §14.11
interface BrandMarkProps {
  size?: number
  className?: string
}

export function BrandMark({ size = 26, className }: BrandMarkProps) {
  return (
    <span
      className={className}
      style={{ width: size, height: size, display: 'inline-flex' }}
      aria-label="QuantHub"
    >
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
        <rect x="1" y="1" width="30" height="30" rx="8" fill="hsl(var(--color-surface-raised))" stroke="hsl(var(--color-border-strong))" />
        {/* candlestick trio — brand violet accent */}
        <g stroke="hsl(var(--color-accent))" strokeWidth="2.2" strokeLinecap="round">
          <line x1="10" y1="8" x2="10" y2="24" />
          <line x1="16" y1="6" x2="16" y2="26" />
          <line x1="22" y1="10" x2="22" y2="22" />
        </g>
        <g fill="hsl(var(--color-accent))">
          <rect x="8" y="12" width="4" height="8" rx="1.2" />
          <rect x="14" y="10" width="4" height="7" rx="1.2" fill="hsl(var(--color-profit))" />
          <rect x="20" y="13" width="4" height="6" rx="1.2" />
        </g>
      </svg>
    </span>
  )
}
