// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Data Visualization: "Support TradingView integration ... consistent
//   legends, tooltips, axis formatting, and efficient rendering for large
//   datasets." §Visual Language: green=profit / red=risk semantic colors.
// Doc 08 §Technology: "TradingView widgets where appropriate."
// Per Doc 00 §14.11
//
// Uses TradingView **Lightweight Charts** (open-source, Apache-2.0), NOT the
// licensed Advanced Charts library — the deliberate choice recorded in
// handbook S-6 to avoid a vendor licensing dependency.
'use client'

import {
  CandlestickData,
  ColorType,
  CrosshairMode,
  HistogramData,
  IChartApi,
  ISeriesApi,
  LineStyle,
  MouseEventParams,
  SeriesMarker,
  Time,
  UTCTimestamp,
  createChart,
} from 'lightweight-charts'
import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { useReveal } from '@/lib/motion'
import { useUIStore } from '@/lib/store/ui'
import { cn } from '@/lib/utils/cn'
import { formatCapital } from '@/lib/utils/format'
import type { OHLCVBar } from '../types'

// A real fill to overlay on the candles (owner request: BUY/SELL fill markers).
// The three `implied*` fields are the real GET .../signals response fields
// (direction/implied_size_usdt/implied_leverage — see
// domain/strategy_engine/implied_sizing.py) for the signal that produced this
// order's fill, joined in by the caller (MarketsShell). Undefined when the
// order carries no signal_id or the signal couldn't be resolved — the
// tooltip then simply omits that row rather than showing a fabricated value.
export interface FillMarker {
  time: number // unix seconds
  side: 'BUY' | 'SELL'
  direction?: string
  impliedSizeUsdt?: string | null
  impliedLeverage?: string
}

// Resolve a Doc 06 theme token (an HSL triplet CSS var, e.g. "152 60% 42%")
// to a concrete color Lightweight Charts can render. LWC renders to <canvas>
// so it can't consume Tailwind classes, AND its own color parser accepts
// only hex/rgb/named — NOT hsl() in any form. So we let the browser convert:
// a throwaway 2D canvas context normalizes any CSS color assigned to
// fillStyle into a hex string. Re-read on every theme change so the chart
// tracks the app's dark/light state.
let probeCtx: CanvasRenderingContext2D | null = null

function toHex(cssColor: string): string | null {
  if (typeof document === 'undefined') return null
  if (!probeCtx) probeCtx = document.createElement('canvas').getContext('2d')
  if (!probeCtx) return null
  // Assign a known-valid sentinel first; if `cssColor` is unparseable,
  // fillStyle keeps the sentinel and we can detect the failure.
  probeCtx.fillStyle = '#000000'
  probeCtx.fillStyle = cssColor
  const resolved = probeCtx.fillStyle
  if (resolved === '#000000' && cssColor !== '#000000') return null
  return resolved
}

function token(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  if (!value) return fallback
  return toHex(`hsl(${value})`) ?? fallback
}

// Same theme-token resolution as `token()`, but with an alpha channel — for
// the grid lines, which Doc 11 §Grid caps at 4-6% opacity (a plain `token()`
// border color at full alpha reads as "heavy grid lines", forbidden). Canvas's
// own CSS color parser accepts the modern `hsl(H S% L% / A)` slash-alpha form
// directly (unlike zrender's simplified parser — see chart-theme.ts), so no
// comma-conversion is needed here.
function tokenAlpha(name: string, alpha: number, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  if (!value) return fallback
  return toHex(`hsl(${value} / ${alpha})`) ?? fallback
}

function chartOptions() {
  // Doc 11 §Crosshair: "Smooth fade. High precision. Thin lines. Context-aware
  // highlighting." / Forbidden: "Static crosshair. Thick lines." — the library
  // default is a plain 1px solid line with no label styling; this replaces it
  // with a thin dashed line (reads as "precision instrument", not a ruler) and
  // a glass-toned label so it matches the rest of the app's overlay language
  // instead of Lightweight Charts' default black/white label chips.
  const crosshairLine = {
    width: 1 as const,
    color: tokenAlpha('--color-accent', 0.55, 'rgba(124,58,237,0.55)'),
    style: LineStyle.Dashed,
    labelBackgroundColor: token('--color-accent', '#7c3aed'),
  }
  return {
    layout: {
      background: { type: ColorType.Solid, color: 'transparent' },
      textColor: token('--color-fg-muted', '#9ca3af'),
    },
    grid: {
      // Doc 11 §Grid: "Grid opacity between 4% and 6%." — 0.05 sits mid-band.
      vertLines: { color: tokenAlpha('--color-border', 0.05, 'rgba(38,48,63,0.05)') },
      horzLines: { color: tokenAlpha('--color-border', 0.05, 'rgba(38,48,63,0.05)') },
    },
    timeScale: { timeVisible: true, borderColor: tokenAlpha('--color-border', 0.5, 'rgba(38,48,63,0.5)') },
    rightPriceScale: { borderColor: tokenAlpha('--color-border', 0.5, 'rgba(38,48,63,0.5)') },
    crosshair: { mode: CrosshairMode.Normal, vertLine: crosshairLine, horzLine: crosshairLine },
  }
}

function volumeColors() {
  // Doc 11 §Volume: "Rounded volume bars. Low visual dominance. Smooth
  // transitions." / Forbidden: "Flat rectangles. Bright saturated colors."
  // Lightweight Charts' histogram series has no rounded-cap primitive (no
  // custom series renderer in v4), so "rounded" is approximated the way the
  // rest of the app treats "soft" — reduced opacity rather than a hard-edged
  // saturated fill — and dominance is capped via the price-scale margins
  // below (~18% of chart height), not the bar color.
  return {
    up: tokenAlpha('--color-profit', 0.35, 'rgba(22,163,74,0.35)'),
    down: tokenAlpha('--color-risk', 0.35, 'rgba(220,38,38,0.35)'),
  }
}

function seriesColors() {
  // Doc 06 §Visual Language: green=profit (up bar), red=risk (down bar).
  const up = token('--color-profit', '#16a34a')
  const down = token('--color-risk', '#dc2626')
  return {
    upColor: up,
    downColor: down,
    borderUpColor: up,
    borderDownColor: down,
    wickUpColor: up,
    wickDownColor: down,
  }
}

export function PriceChart({ bars, markers = [] }: { bars: OHLCVBar[]; markers?: FillMarker[] }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const markersRef = useRef<FillMarker[]>(markers)
  // Half the gap between consecutive bars (seconds) — a marker's `time` is
  // the fill's exact timestamp (e.g. 21:32:52), NOT snapped to a bar
  // boundary, while the crosshair's `param.time` always snaps to the nearest
  // bar's exact time (e.g. 21:00:00). An exact-equality lookup would never
  // match, so the hover handler below buckets a marker to "the bar it falls
  // within" using this tolerance instead of requiring equality.
  const barSpacingRef = useRef(3600)
  const theme = useUIStore((s) => s.theme)
  // Hover tooltip for a marker's implied sizing (direction/implied_size_usdt/
  // implied_leverage) — LWC draws markers straight to canvas with no native
  // per-marker hover hook, so this tracks the crosshair's snapped time/point
  // and looks up any marker(s) whose real fill time falls within the hovered
  // bar (same coordinate space `setMarkers` already uses below).
  const [hoverInfo, setHoverInfo] = useState<{ x: number; y: number; markers: FillMarker[] } | null>(null)
  // Same 'cardContent' kind Chart.tsx's ECharts bridge uses for its own host —
  // this is the lightweight-charts engine's equivalent "Background" materialize
  // step (Doc 11 Animation Sequence), since LWC has no setOption-staging
  // equivalent to sequence its own grid/axis/candles internally.
  const reveal = useReveal('cardContent')

  // Create the chart once (autoSize keeps it responsive to its container —
  // Doc 06 §Layout "responsive grid" — without a manual ResizeObserver).
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const chart = createChart(container, { ...chartOptions(), autoSize: true })
    const series = chart.addCandlestickSeries(seriesColors())
    // Doc 11 Animation Sequence: "1 Background 2 Grid 3 Axis 4 Volume 5
    // Candles" — volume gets its own price scale pinned to the bottom ~18%
    // of the chart (scaleMargins) so it reads as a supporting strip beneath
    // the candles, never competing with them for vertical space.
    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    })
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } })
    chartRef.current = chart
    seriesRef.current = series
    volumeSeriesRef.current = volumeSeries

    const onCrosshairMove = (param: MouseEventParams) => {
      if (!param.time || !param.point) {
        setHoverInfo(null)
        return
      }
      const hoveredTime = param.time as number
      const tolerance = barSpacingRef.current / 2
      const nearby = markersRef.current.filter((m) => Math.abs(m.time - hoveredTime) <= tolerance)
      if (nearby.length === 0) {
        setHoverInfo(null)
        return
      }
      setHoverInfo({ x: param.point.x, y: param.point.y, markers: nearby })
    }
    chart.subscribeCrosshairMove(onCrosshairMove)

    return () => {
      chart.unsubscribeCrosshairMove(onCrosshairMove)
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
      volumeSeriesRef.current = null
    }
  }, [])

  // Keep the crosshair handler's marker lookup current without re-subscribing.
  useEffect(() => {
    markersRef.current = markers
  }, [markers])

  // Recompute the bar-bucketing tolerance whenever the series changes (a
  // timeframe switch changes the gap from 1h to 4h/1D).
  useEffect(() => {
    if (bars.length < 2) return
    const gap = Math.abs(Date.parse(bars[1].ts) - Date.parse(bars[0].ts)) / 1000
    if (gap > 0) barSpacingRef.current = gap
  }, [bars])

  // Feed data. parseFloat is deliberate: the API sends precision-preserving
  // Decimal STRINGS (shown exactly in the bars table), but a <canvas> plots
  // to pixels, so float precision is irrelevant for rendering. The precise
  // values remain authoritative in the table, never derived from these.
  useEffect(() => {
    const series = seriesRef.current
    if (!series) return
    const data: CandlestickData[] = bars.map((bar) => ({
      time: (Date.parse(bar.ts) / 1000) as UTCTimestamp,
      open: Number.parseFloat(bar.open),
      high: Number.parseFloat(bar.high),
      low: Number.parseFloat(bar.low),
      close: Number.parseFloat(bar.close),
    }))
    series.setData(data)

    // Real bar.volume — same field the Recent Bars table already renders,
    // never a derived/fabricated figure. Colored per bar direction so the
    // strip still reads as "this candle" at a glance.
    const volumeSeries = volumeSeriesRef.current
    if (volumeSeries) {
      const { up, down } = volumeColors()
      const volumeData: HistogramData[] = bars.map((bar) => ({
        time: (Date.parse(bar.ts) / 1000) as UTCTimestamp,
        value: Number.parseFloat(bar.volume),
        color: Number.parseFloat(bar.close) >= Number.parseFloat(bar.open) ? up : down,
      }))
      volumeSeries.setData(volumeData)
    }

    // Reset BOTH axes to the new series' data. A prior user pan/zoom on the
    // price axis disables its autoScale and pins a fixed price range; because
    // a different asset can have a wildly different magnitude (SOL ~77 vs BTC
    // ~62000), leaving that range makes the new candles render off-screen —
    // the "empty chart on asset switch" bug. Re-enabling autoScale refits the
    // price axis; fitContent() refits the time axis (clearing any prior zoom).
    const chart = chartRef.current
    if (chart) {
      chart.priceScale('right').applyOptions({ autoScale: true })
      chart.timeScale().fitContent()
    }
  }, [bars])

  // Overlay real BUY/SELL fill markers (Doc 06 green=profit/red=risk):
  // a BUY sits below its bar with an up-arrow, a SELL above with a down-arrow.
  // Doc 11 §Signal Markers: "Buy/Sell markers glow softly... Animated
  // appearance." Lightweight Charts draws markers straight to <canvas> with no
  // per-marker CSS filter hook, so the glow is built the way canvas glows
  // always are: a larger, translucent halo shape drawn first, the crisp arrow
  // drawn on top of it at the same point. DATA HONESTY: this is two draw calls
  // for ONE real fill, never a marker without a backing order — `markers` is
  // always the caller's real FILLED-order list (see MarketsShell), so an empty
  // list here means legitimately zero fills, not a hidden fake.
  useEffect(() => {
    const series = seriesRef.current
    if (!series) return
    const up = token('--color-profit', '#16a34a')
    const down = token('--color-risk', '#dc2626')
    const upGlow = tokenAlpha('--color-profit', 0.35, 'rgba(22,163,74,0.35)')
    const downGlow = tokenAlpha('--color-risk', 0.35, 'rgba(220,38,38,0.35)')
    const sorted = [...markers].sort((a, b) => a.time - b.time)
    const seriesMarkers: SeriesMarker<Time>[] = sorted.flatMap((m) => {
      const isBuy = m.side === 'BUY'
      const time = m.time as UTCTimestamp
      const position = isBuy ? 'belowBar' : 'aboveBar'
      return [
        // soft glow halo, drawn first so the arrow renders on top of it
        { time, position, color: isBuy ? upGlow : downGlow, shape: 'circle', size: 2.5 },
        { time, position, color: isBuy ? up : down, shape: isBuy ? 'arrowUp' : 'arrowDown', text: isBuy ? 'B' : 'S' },
      ]
    })
    series.setMarkers(seriesMarkers)
  }, [markers, theme])

  // Re-apply resolved colors when the app theme toggles (dark <-> light).
  useEffect(() => {
    chartRef.current?.applyOptions(chartOptions())
    seriesRef.current?.applyOptions(seriesColors())
    const volumeSeries = volumeSeriesRef.current
    if (volumeSeries) {
      const { up, down } = volumeColors()
      const volumeData: HistogramData[] = bars.map((bar) => ({
        time: (Date.parse(bar.ts) / 1000) as UTCTimestamp,
        value: Number.parseFloat(bar.volume),
        color: Number.parseFloat(bar.close) >= Number.parseFloat(bar.open) ? up : down,
      }))
      volumeSeries.setData(volumeData)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme])

  return (
    <motion.div {...reveal} className="relative h-[420px] w-full">
      <div ref={containerRef} className="h-full w-full" />
      {hoverInfo && (
        <div
          className="pointer-events-none absolute z-10 min-w-[11rem] rounded-lg border border-border/50 bg-surface-raised/90 px-3 py-2 text-xs shadow-lg backdrop-blur-md"
          style={{
            left: Math.min(hoverInfo.x + 12, (containerRef.current?.clientWidth ?? 400) - 180),
            top: Math.max(hoverInfo.y - 12, 8),
          }}
        >
          {hoverInfo.markers.map((m, i) => (
            <div key={i} className={cn(i > 0 && 'mt-2 border-t border-border/50 pt-2')}>
              <div className={cn('font-semibold', m.side === 'BUY' ? 'text-profit' : 'text-risk')}>
                {m.side === 'BUY' ? '▲ Buy fill' : '▼ Sell fill'}
                {m.direction && <span className="ml-1.5 font-normal text-fg-subtle">· {m.direction}</span>}
              </div>
              {m.impliedSizeUsdt != null ? (
                <div className="mt-0.5 font-mono text-fg-muted">
                  implied size <span className="text-fg">{formatCapital(Number.parseFloat(m.impliedSizeUsdt))}</span>
                </div>
              ) : (
                <div className="mt-0.5 text-fg-subtle">implied size — n/a</div>
              )}
              {m.impliedLeverage && (
                <div className="font-mono text-fg-muted">
                  leverage <span className="text-fg">{Number.parseFloat(m.impliedLeverage).toFixed(1)}x</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </motion.div>
  )
}
