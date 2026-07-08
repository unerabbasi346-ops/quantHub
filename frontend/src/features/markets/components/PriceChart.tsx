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
  IChartApi,
  ISeriesApi,
  SeriesMarker,
  Time,
  UTCTimestamp,
  createChart,
} from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import { useUIStore } from '@/lib/store/ui'
import type { OHLCVBar } from '../types'

// A real fill to overlay on the candles (owner request: BUY/SELL fill markers).
export interface FillMarker {
  time: number // unix seconds
  side: 'BUY' | 'SELL'
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

function chartOptions() {
  return {
    layout: {
      background: { type: ColorType.Solid, color: 'transparent' },
      textColor: token('--color-fg-muted', '#9ca3af'),
    },
    grid: {
      vertLines: { color: token('--color-border', '#26303f') },
      horzLines: { color: token('--color-border', '#26303f') },
    },
    timeScale: { timeVisible: true, borderColor: token('--color-border', '#26303f') },
    rightPriceScale: { borderColor: token('--color-border', '#26303f') },
    crosshair: { mode: CrosshairMode.Normal },
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
  const theme = useUIStore((s) => s.theme)

  // Create the chart once (autoSize keeps it responsive to its container —
  // Doc 06 §Layout "responsive grid" — without a manual ResizeObserver).
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const chart = createChart(container, { ...chartOptions(), autoSize: true })
    const series = chart.addCandlestickSeries(seriesColors())
    chartRef.current = chart
    seriesRef.current = series

    return () => {
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [])

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
  useEffect(() => {
    const series = seriesRef.current
    if (!series) return
    const up = token('--color-profit', '#16a34a')
    const down = token('--color-risk', '#dc2626')
    const sorted = [...markers].sort((a, b) => a.time - b.time)
    const seriesMarkers: SeriesMarker<Time>[] = sorted.map((m) => ({
      time: m.time as UTCTimestamp,
      position: m.side === 'BUY' ? 'belowBar' : 'aboveBar',
      color: m.side === 'BUY' ? up : down,
      shape: m.side === 'BUY' ? 'arrowUp' : 'arrowDown',
      text: m.side === 'BUY' ? 'B' : 'S',
    }))
    series.setMarkers(seriesMarkers)
  }, [markers, theme])

  // Re-apply resolved colors when the app theme toggles (dark <-> light).
  useEffect(() => {
    chartRef.current?.applyOptions(chartOptions())
    seriesRef.current?.applyOptions(seriesColors())
  }, [theme])

  return <div ref={containerRef} className="h-[420px] w-full" />
}
