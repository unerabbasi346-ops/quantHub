// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Data Visualization / §Components: a small asset mark next to a symbol
//   (owner request: real crypto asset icon on watchlist/asset rows). Marks
//   are drawn as inline SVG (self-contained — no network image, renders
//   offline and in the screenshot harness) keyed off the base symbol, with a
//   deterministic colored initial-badge fallback for anything unmapped.
// Per Doc 00 §14.11
import { cn } from '@/lib/utils/cn'

// base asset = the part before the quote currency ("BTC/USDT" -> "BTC")
function baseOf(symbol: string): string {
  return (symbol.split(/[/\-:]/)[0] || symbol).toUpperCase()
}

const BRAND: Record<string, string> = {
  BTC: '#f7931a',
  ETH: '#627eea',
  USDT: '#26a17b',
  USDC: '#2775ca',
  SOL: '#14f195',
  BNB: '#f3ba2f',
  REGTEST: '#8b8f9c',
}

function hashHue(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 360
  return h
}

function BtcGlyph() {
  return (
    <text x="12" y="16.5" textAnchor="middle" fontSize="12" fontWeight="700" fill="#fff">
      ₿
    </text>
  )
}

function EthGlyph() {
  return (
    <g fill="#fff">
      <path d="M12 4l5 8-5 3-5-3 5-8z" opacity="0.9" />
      <path d="M12 20l5-7-5 3-5-3 5 7z" opacity="0.7" />
    </g>
  )
}

interface CryptoIconProps {
  symbol: string
  size?: number
  className?: string
}

// Doc 08 §Architecture: stateless presentation component.
export function CryptoIcon({ symbol, size = 22, className }: CryptoIconProps) {
  const base = baseOf(symbol)
  const brand = BRAND[base]
  const bg = brand ?? `hsl(${hashHue(base)} 45% 42%)`

  return (
    <span
      className={cn('inline-flex shrink-0 items-center justify-center rounded-full', className)}
      style={{ width: size, height: size, background: bg, boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.18)' }}
      aria-hidden="true"
      title={base}
    >
      <svg width={size} height={size} viewBox="0 0 24 24">
        {base === 'BTC' ? (
          <BtcGlyph />
        ) : base === 'ETH' ? (
          <EthGlyph />
        ) : (
          <text
            x="12"
            y="16"
            textAnchor="middle"
            fontSize={base.length > 3 ? 7.5 : 9}
            fontWeight="700"
            fill="#fff"
            fontFamily="var(--font-sans)"
          >
            {base.slice(0, 4)}
          </text>
        )}
      </svg>
    </span>
  )
}
