// Governing specification: handbook/ui Doc 01 (Technology Standard) — Apache
//   ECharts is the FROZEN engine for every analytical chart; Doc 03/11 §Color
//   Philosophy — charts must use the platform's semantic hues, never arbitrary
//   colors; Doc 12 §Motion — one easing language across the app.
// Per Doc 00 §14.11
//
// WHY THIS EXISTS: our theme is expressed as CSS custom properties holding HSL
// TRIPLETS (e.g. `--color-profit: 152 60% 42%`) so Tailwind opacity modifiers
// work. ECharts renders to <canvas>, which cannot read `hsl(var(--x))` — it
// needs concrete color strings. This hook resolves the live computed values off
// <html> and, crucially, RE-RESOLVES them when the `data-theme` attribute flips
// (light/dark), so every chart recolors with the rest of the UI. It is the one
// bridge between the token system and the canvas engine — no chart hardcodes a
// color.
'use client'

import { useEffect, useState } from 'react'
import { useReducedMotion } from 'framer-motion'

/** Resolved, canvas-ready colors pulled from the active theme's CSS tokens. */
export interface ChartTheme {
  fg: string
  fgMuted: string
  fgSubtle: string
  border: string
  borderStrong: string
  surface: string
  surfaceRaised: string
  profit: string
  risk: string
  info: string
  warning: string
  accent: string
  /** Categorical series palette — semantic + brand hues, ordered for contrast. */
  palette: string[]
  fontMono: string
  fontSans: string
  /** `hsl(<triplet> / a)` for any resolved token, for gradients/soft fills. */
  alpha: (color: keyof Omit<ChartTheme, 'palette' | 'alpha' | 'fontMono' | 'fontSans'>, a: number) => string
}

const TOKENS = {
  fg: '--color-fg',
  fgMuted: '--color-fg-muted',
  fgSubtle: '--color-fg-subtle',
  border: '--color-border',
  borderStrong: '--color-border-strong',
  surface: '--color-surface',
  surfaceRaised: '--color-surface-raised',
  profit: '--color-profit',
  risk: '--color-risk',
  info: '--color-info',
  warning: '--color-warning',
  accent: '--color-accent',
} as const

// Our CSS tokens hold space-separated HSL triplets ("220 6% 24%") — the modern
// CSS Color-4 syntax. ECharts' color parser (zrender) does NOT understand the
// space form; it needs the classic comma form. Convert here so every canvas
// color is parseable (otherwise colors silently resolve to nothing → black).
function toHsl(triplet: string): string {
  return `hsl(${triplet.split(/\s+/).join(', ')})`
}
function toHsla(triplet: string, a: number): string {
  return `hsla(${triplet.split(/\s+/).join(', ')}, ${a})`
}

function readTheme(): ChartTheme {
  const cs = getComputedStyle(document.documentElement)
  const triplets = {} as Record<keyof typeof TOKENS, string>
  const solid = {} as Record<keyof typeof TOKENS, string>
  for (const [key, varName] of Object.entries(TOKENS) as [keyof typeof TOKENS, string][]) {
    const t = cs.getPropertyValue(varName).trim() || '0 0% 50%'
    triplets[key] = t
    solid[key] = toHsl(t)
  }
  return {
    ...solid,
    palette: [
      toHsl(triplets.info),
      toHsl(triplets.profit),
      toHsl(triplets.accent),
      toHsl(triplets.warning),
      toHsl(triplets.risk),
      toHsl(triplets.fgMuted),
    ],
    fontMono: cs.getPropertyValue('--font-mono').trim() || 'monospace',
    fontSans: cs.getPropertyValue('--font-sans').trim() || 'sans-serif',
    alpha: (color, a) => toHsla(triplets[color as keyof typeof TOKENS], a),
  }
}

/**
 * Live chart theme resolved from CSS tokens, re-read whenever the theme toggles.
 * Returns `null` on the server / first paint (no `document`), so callers should
 * render the chart only once a theme exists.
 */
export function useChartTheme(): ChartTheme | null {
  const [theme, setTheme] = useState<ChartTheme | null>(null)

  useEffect(() => {
    setTheme(readTheme())
    const target = document.documentElement
    const obs = new MutationObserver(() => setTheme(readTheme()))
    obs.observe(target, { attributes: true, attributeFilter: ['data-theme'] })
    return () => obs.disconnect()
  }, [])

  return theme
}

/** Whether chart animations should run (respects prefers-reduced-motion). */
export function useChartAnimation(): boolean {
  return !useReducedMotion()
}

// ── Shared option fragments so every chart inherits ONE look (Doc 11: "no page
//    invents its own chart language"). Components spread these into their option.

/** Base text style — mono figures, themed foreground. */
export function chartTextStyle(theme: ChartTheme) {
  return { fontFamily: theme.fontMono, color: theme.fgMuted, fontSize: 11 }
}

// Doc 05 Glass Surface System / Doc 11 Chart Rendering §Tooltip: "Glass
// surface. Soft blur. Rounded corners." ECharts tooltips render as a real
// positioned <div> (not canvas), so — unlike series colors — native CSS
// `backdrop-filter` works here directly via extraCssText.
/** Institutional tooltip: translucent glass surface, hairline border, mono body. */
export function chartTooltip(theme: ChartTheme, extra: Record<string, unknown> = {}) {
  return {
    backgroundColor: theme.alpha('surfaceRaised', 0.72),
    borderColor: theme.alpha('border', 0.5),
    borderWidth: 1,
    padding: [8, 10],
    textStyle: { color: theme.fg, fontFamily: theme.fontMono, fontSize: 12 },
    extraCssText: 'border-radius:12px;box-shadow:var(--shadow-md);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);',
    ...extra,
  }
}

// Doc 11 Chart Rendering §Grid: "Grid opacity between 4% and 6%." §Axis:
// "Minimal styling. Low opacity." 0.05 (5%) sits mid-range for split lines;
// the axis line itself isn't numerically specified but is softened too so it
// stays secondary to the data, never "bright axis labels" (forbidden).
/** Themed category/value axis fragment (subtle grid, hairline axis). */
export function chartAxis(theme: ChartTheme) {
  return {
    axisLine: { lineStyle: { color: theme.alpha('border', 0.5) } },
    axisTick: { show: false },
    axisLabel: { color: theme.fgSubtle, fontFamily: theme.fontMono, fontSize: 10 },
    splitLine: { lineStyle: { color: theme.alpha('border', 0.05), type: 'dashed' as const } },
  }
}
