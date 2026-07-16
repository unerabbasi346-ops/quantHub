// Governing specification: handbook/ui Doc 01 — Apache ECharts is the single
//   FROZEN analytics chart engine ("one responsibility, one library"). Doc 12
//   §Motion — progressive reveal, ease-out with no bounce, GPU-friendly. Doc 03
//   §Empty/Loading — skeleton while resolving, never a bare box.
// handbook/ui/visual_engineering/11_CHART_RENDERING_SPECIFICATION §Animation
//   Sequence: "Charts load in this order: 1. Background 2. Grid 3. Axis
//   4. Volume 5. Candles/Line 6. Indicators 7. Signal Markers 8. Live Updates.
//   Charts must never instantly appear."
// Per Doc 00 §14.11
//
// The ONE React↔ECharts bridge. Every analytical chart in QuantHub renders
// through this wrapper so they share: theme tokens (via chart-theme), the house
// easing, responsive resizing, disposal, and reduced-motion behavior. Higher-
// level charts (DonutChart, Treemap, Heatmap, Gauge…) build an ECharts option
// from the resolved theme and hand it here — they never touch the engine
// directly. Keeping the coupling in one file is what lets the whole platform
// swap or restyle charts as one instrument.
//
// STAGED LOAD (Doc 11): rather than a second, parallel animation system, this
// reuses lib/motion's own DURATION.chart as the one timing source. The
// enclosing `motion.div` below (useReveal('cardContent')) already supplies
// "Background" — the chart's card materializes before any pixel of the chart
// itself paints. Once mounted, this component then applies the option in TWO
// echarts.setOption passes: first the structural chrome only (grid/axis/
// tooltip, animation off, series stripped) — "Grid" + "Axis" appearing before
// any data — then, a beat later, the full option with series animation
// enabled, which is where ECharts' own progressive draw-in handles
// "Candles/Line" (and "Signal Markers", set by callers in a subsequent effect
// once the series exists, e.g. PriceChart's marker effect). Reduced-motion
// skips straight to the final state, per house convention.
'use client'

import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
// Tree-shaken ECharts: Turbopack resolves the full 'echarts' package entry in
// a way that skips its side-effect renderer registration ("Renderer 'undefined'
// is not imported"). Explicit echarts/core + use() registration is the
// build-tool-proof form. Every series/component any QuantHub chart uses must
// be registered HERE — this file is the single engine bridge.
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import {
  LineChart as EChartsLine,
  BarChart as EChartsBar,
  ScatterChart as EChartsScatter,
  GaugeChart as EChartsGauge,
  HeatmapChart as EChartsHeatmap,
  PieChart as EChartsPie,
} from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  VisualMapComponent,
  GraphicComponent,
  MarkLineComponent,
  MarkPointComponent,
  TitleComponent,
  DataZoomComponent,
} from 'echarts/components'
import type { EChartsOption } from 'echarts'
import type { EChartsType } from 'echarts/core'

echarts.use([
  CanvasRenderer,
  EChartsLine, EChartsBar, EChartsScatter, EChartsGauge, EChartsHeatmap, EChartsPie,
  GridComponent, TooltipComponent, LegendComponent, VisualMapComponent,
  GraphicComponent, MarkLineComponent, MarkPointComponent, TitleComponent,
  DataZoomComponent,
])
import { cn } from '@/lib/utils/cn'
import { useReveal, DURATION } from '@/lib/motion'
import { useChartTheme, useChartAnimation, type ChartTheme } from './chart-theme'

// Grid/axis settle before the series draws — a fraction of the existing
// "progressive line draw" duration, not a new timing constant.
const STRUCTURE_DELAY_MS = Math.round(DURATION.chart * 1000 * 0.15)

export interface ChartProps {
  /** ECharts option, or a builder given the live resolved theme. */
  option: EChartsOption | ((theme: ChartTheme) => EChartsOption)
  height?: number | string
  className?: string
  /** ECharts event handlers, e.g. { click: (params) => … }. */
  onEvents?: Record<string, (params: unknown) => void>
  /** Accessible description of what the chart shows. */
  ariaLabel?: string
}

// House ease-out feel (matches lib/motion EASE_OUT [0.16,1,0.3,1]) expressed as
// a built-in ECharts easing name — a fast start settling softly, no overshoot.
// ECharts expects a named easing string here, not a cubic-bezier array.
const CHART_EASING = 'quinticOut'

export function Chart({ option, height = 280, className, onEvents, ariaLabel }: ChartProps) {
  const theme = useChartTheme()
  const animate = useChartAnimation()
  const reveal = useReveal('cardContent')
  const hostRef = useRef<HTMLDivElement | null>(null)
  const instanceRef = useRef<EChartsType | null>(null)

  // Init once the host exists; dispose on unmount.
  useEffect(() => {
    if (!hostRef.current) return
    const inst = echarts.init(hostRef.current)
    instanceRef.current = inst
    const ro = new ResizeObserver(() => inst.resize())
    ro.observe(hostRef.current)
    return () => {
      ro.disconnect()
      inst.dispose()
      instanceRef.current = null
    }
  }, [])

  // (Re)apply option whenever the option or the resolved theme changes. notMerge
  // so switching datasets never leaves stale series behind.
  useEffect(() => {
    const inst = instanceRef.current
    if (!inst || !theme) return
    const resolved = typeof option === 'function' ? option(theme) : option
    const finalOption: EChartsOption = {
      animation: animate,
      animationDuration: animate ? DURATION.chart * 1000 : 0,
      animationEasing: CHART_EASING,
      textStyle: { fontFamily: theme.fontMono },
      ...resolved,
    }

    // Reduced motion: render the finished state immediately, no staging.
    if (!animate) {
      inst.setOption(finalOption, { notMerge: true })
      return
    }

    // Pass 1 — structural chrome only (Doc 11: "Grid" then "Axis" before any
    // data). Series stripped, animation off, so the grid/axis simply appear.
    const { series: _series, ...structure } = finalOption as typeof finalOption & {
      series?: unknown
    }
    inst.setOption({ ...structure, animation: false, series: [] }, { notMerge: true })

    // Pass 2 — the full option a beat later; ECharts' own animation draws the
    // series in (Doc 11: "Candles/Line"). Callers add signal markers in their
    // own effect once the series exists, which naturally lands after this.
    const timer = setTimeout(() => {
      if (!instanceRef.current) return
      instanceRef.current.setOption(finalOption, { notMerge: true })
    }, STRUCTURE_DELAY_MS)

    return () => clearTimeout(timer)
  }, [option, theme, animate])

  // Bind events once.
  useEffect(() => {
    const inst = instanceRef.current
    if (!inst || !onEvents) return
    for (const [name, handler] of Object.entries(onEvents)) {
      inst.on(name, handler as (params: unknown) => void)
    }
    return () => {
      for (const name of Object.keys(onEvents)) inst.off(name)
    }
  }, [onEvents])

  return (
    <motion.div
      {...reveal}
      className={cn('relative w-full', className)}
      style={{ height }}
      role="img"
      aria-label={ariaLabel}
    >
      {/* Skeleton until the theme resolves — holds size so nothing shifts. */}
      {!theme && <div className="skeleton absolute inset-0" />}
      <div ref={hostRef} className="h-full w-full" />
    </motion.div>
  )
}
