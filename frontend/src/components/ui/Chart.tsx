// Governing specification: handbook/ui Doc 01 — Apache ECharts is the single
//   FROZEN analytics chart engine ("one responsibility, one library"). Doc 12
//   §Motion — progressive reveal, ease-out with no bounce, GPU-friendly. Doc 03
//   §Empty/Loading — skeleton while resolving, never a bare box.
// Per Doc 00 §14.11
//
// The ONE React↔ECharts bridge. Every analytical chart in QuantHub renders
// through this wrapper so they share: theme tokens (via chart-theme), the house
// easing, responsive resizing, disposal, and reduced-motion behavior. Higher-
// level charts (DonutChart, Treemap, Heatmap, Gauge…) build an ECharts option
// from the resolved theme and hand it here — they never touch the engine
// directly. Keeping the coupling in one file is what lets the whole platform
// swap or restyle charts as one instrument.
'use client'

import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import { cn } from '@/lib/utils/cn'
import { useReveal, DURATION } from '@/lib/motion'
import { useChartTheme, useChartAnimation, type ChartTheme } from './chart-theme'

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
  const instanceRef = useRef<echarts.ECharts | null>(null)

  // Init once the host exists; dispose on unmount.
  useEffect(() => {
    if (!hostRef.current) return
    const inst = echarts.init(hostRef.current, undefined, { renderer: 'canvas' })
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
    inst.setOption(
      {
        animation: animate,
        animationDuration: animate ? DURATION.chart * 1000 : 0,
        animationEasing: CHART_EASING,
        textStyle: { fontFamily: theme.fontMono },
        ...resolved,
      },
      { notMerge: true },
    )
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
