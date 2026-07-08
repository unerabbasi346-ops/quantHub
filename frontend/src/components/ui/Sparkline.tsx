// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Data Visualization: dense inline visualization. A sparkline conveys a
//   recent price trajectory next to a symbol far better than a lone number
//   (owner request: watchlist rows get an inline mini price sparkline).
//   Pure SVG, no dependency, deterministic.
// Per Doc 00 §14.11
import { cn } from '@/lib/utils/cn'

interface SparklineProps {
  data: number[]
  width?: number
  height?: number
  /** Tone override; defaults to profit/risk by first→last direction. */
  tone?: 'profit' | 'risk' | 'info' | 'auto'
  className?: string
}

// Doc 08 §Architecture: stateless presentation component.
export function Sparkline({
  data,
  width = 88,
  height = 28,
  tone = 'auto',
  className,
}: SparklineProps) {
  if (!data || data.length < 2) {
    return <div style={{ width, height }} className={cn('inline-block', className)} aria-hidden />
  }

  const min = Math.min(...data)
  const max = Math.max(...data)
  const span = max - min || 1
  const pad = 2
  const stepX = (width - pad * 2) / (data.length - 1)

  const points = data.map((v, i) => {
    const x = pad + i * stepX
    const y = pad + (1 - (v - min) / span) * (height - pad * 2)
    return [x, y] as const
  })

  const line = points.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(2)} ${y.toFixed(2)}`).join(' ')
  const area = `${line} L${points[points.length - 1][0].toFixed(2)} ${height - pad} L${points[0][0].toFixed(2)} ${height - pad} Z`

  const up = data[data.length - 1] >= data[0]
  const resolved = tone === 'auto' ? (up ? 'profit' : 'risk') : tone
  const stroke =
    resolved === 'profit'
      ? 'hsl(var(--color-profit))'
      : resolved === 'risk'
        ? 'hsl(var(--color-risk))'
        : 'hsl(var(--color-info))'
  const gid = `spark-${resolved}`

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={cn('inline-block align-middle', className)}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.22" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gid})`} />
      <path d={line} fill="none" stroke={stroke} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}
