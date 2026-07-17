// Governing specification: handbook/ui Doc 01 — Apache ECharts is the single
//   FROZEN analytics engine; every chart here builds an option through the
//   shared `Chart` wrapper + `chart-theme` tokens (Doc 04/13_VISUAL_DNA
//   "Every chart must appear custom engineered. Default chart appearances are
//   prohibited."). Doc 00 §14.5/§14.7 — DATA HONESTY: every series below is a
//   deterministic transform of real signals; nothing here is fabricated.
//
// VISUAL UPGRADE PASS (owner request): premium ECharts styling — gradient
// fills, smooth curves, glow shadows — built entirely from theme tokens
// (theme.profit/risk/accent + theme.alpha) rather than literal hex/rgba, so
// every chart still recolors correctly across the light/dark toggle. The
// Chart wrapper already owns animation timing (lib/motion DURATION.chart) and
// dispose-on-unmount; charts here never touch echarts directly.
//
// Bespoke, page-specific compositions for the Strategy detail workspace.
// Kept feature-local rather than promoted to components/ui because they
// compose the generic primitives (Chart, chart-theme) for one page's exact
// shape, following the same pattern as markets/CorrelationMatrix building on
// the generic Heatmap.
'use client'

import { Chart } from '@/components/ui/Chart'
import { chartAxis, chartTooltip, type ChartTheme } from '@/components/ui/chart-theme'
import { EmptyState } from '@/components/ui/States'
import { formatRatio, formatSignalStrength } from '@/lib/utils/format'
import type { ConsecutiveRun, MLConfidencePoint, SignalPoint } from '../analytics'

const fmtTime = (ts: string) =>
  new Date(ts).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

// ── Equity/conviction split-area: signed signal values over time, shaded
//    profit-green above zero and risk-red below — an honest "equity proxy"
//    (Doc 00: real per-step equity tracking doesn't exist yet, F-21), never
//    presented as a real P&L curve. Primary line is the accent-violet
//    reference line (smooth, glowing) with the sign-colored fills beneath. ──
export function ConvictionEquityChart({
  points,
  height = 320,
}: {
  points: { label: string; value: number }[]
  height?: number
}) {
  if (points.length < 2) {
    return (
      <div style={{ height }}>
        <EmptyState title="Not enough signals" description="At least two signals are needed to plot the curve." />
      </div>
    )
  }

  const values = points.map((p) => p.value)
  const posData = values.map((v) => (v >= 0 ? v : 0))
  const negData = values.map((v) => (v < 0 ? v : 0))
  const dataMax = values.reduce((a, b) => Math.max(a, b), 0)
  const dataMin = values.reduce((a, b) => Math.min(a, b), 0)

  return (
    <Chart
      height={height}
      ariaLabel="Alpha Score equity curve with drawdown shading"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'axis',
            borderColor: theme.alpha('accent', 0.35),
            axisPointer: { type: 'line', lineStyle: { color: theme.alpha('accent', 0.4), width: 1 } },
            formatter: (params: unknown) => {
              const arr = params as { axisValue: string }[]
              const idx = points.findIndex((p) => p.label === arr[0]?.axisValue)
              const v = idx >= 0 ? values[idx] : 0
              return `${arr[0]?.axisValue}<br/><b style="color:${v >= 0 ? theme.profit : theme.risk}">${v >= 0 ? '+' : ''}${v.toFixed(4)}</b>`
            },
          }),
          grid: { left: 56, right: 16, top: 20, bottom: 28 },
          xAxis: {
            type: 'category',
            data: points.map((p) => p.label),
            boundaryGap: false,
            ...axis,
            splitLine: { show: false },
          },
          yAxis: {
            type: 'value',
            min: Math.min(dataMin * 1.1, -0.001),
            max: Math.max(dataMax * 1.1, 0.001),
            ...axis,
            splitLine: { lineStyle: { color: theme.alpha('border', 0.4), type: 'dashed' } },
          },
          series: [
            {
              name: 'Alpha Score',
              type: 'line',
              data: values,
              symbol: 'none',
              smooth: 0.25,
              lineStyle: {
                color: theme.accent,
                width: 3,
                shadowColor: theme.alpha('accent', 0.45),
                shadowBlur: 12,
              },
              areaStyle: {
                color: {
                  type: 'linear',
                  x: 0, y: 0, x2: 0, y2: 1,
                  colorStops: [
                    { offset: 0, color: theme.alpha('accent', 0.28) },
                    { offset: 1, color: theme.alpha('accent', 0) },
                  ],
                },
              },
              z: 3,
              markLine: {
                silent: true,
                symbol: 'none',
                lineStyle: { color: theme.alpha('fg', 0.2), type: 'dashed', width: 1 },
                data: [{ yAxis: 0 }],
                label: { show: false },
              },
            },
            {
              name: 'Above zero',
              type: 'line',
              data: posData,
              symbol: 'none',
              smooth: 0.25,
              lineStyle: { opacity: 0 },
              z: 1,
              areaStyle: {
                color: {
                  type: 'linear',
                  x: 0, y: 0, x2: 0, y2: 1,
                  colorStops: [
                    { offset: 0, color: theme.alpha('profit', 0.36) },
                    { offset: 1, color: theme.alpha('profit', 0.02) },
                  ],
                },
              },
            },
            {
              name: 'Below zero',
              type: 'line',
              data: negData,
              symbol: 'none',
              smooth: 0.25,
              lineStyle: { opacity: 0 },
              z: 1,
              areaStyle: {
                color: {
                  type: 'linear',
                  x: 0, y: 0, x2: 0, y2: 1,
                  colorStops: [
                    { offset: 0, color: theme.alpha('risk', 0.04) },
                    { offset: 1, color: theme.alpha('risk', 0.38) },
                  ],
                },
              },
            },
          ],
        }
      }}
    />
  )
}

// ── Signal timeline scatter: every recorded signal, x=time, y=conviction,
//    color + soft glow by sign, size by magnitude. ──
export function SignalTimelineScatter({ points, height = 260 }: { points: SignalPoint[]; height?: number }) {
  if (points.length === 0) {
    return (
      <div style={{ height }}>
        <EmptyState title="No signals" description="This strategy has emitted no signals yet." />
      </div>
    )
  }

  const maxAbs = points.reduce((m, p) => Math.max(m, Math.abs(p.value)), 1e-9)

  return (
    <Chart
      height={height}
      ariaLabel="Signal timeline scatter"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'item',
            formatter: (p: unknown) => {
              const d = p as { value: [number, number] }
              const v = d.value[1]
              return `${fmtTime(new Date(d.value[0]).toISOString())}<br/><b style="color:${v >= 0 ? theme.profit : theme.risk}">${formatSignalStrength(v)}</b>`
            },
          }),
          grid: { left: 56, right: 16, top: 20, bottom: 28 },
          xAxis: { type: 'time', ...axis, splitLine: { show: false } },
          yAxis: { type: 'value', scale: true, ...axis },
          series: [
            {
              type: 'scatter',
              data: points.map((p) => ({
                value: [new Date(p.ts).getTime(), p.value],
                itemStyle: {
                  color: p.value >= 0 ? theme.alpha('profit', 0.8) : theme.alpha('risk', 0.8),
                  shadowBlur: 8,
                  shadowColor: p.value >= 0 ? theme.alpha('profit', 0.4) : theme.alpha('risk', 0.4),
                },
              })),
              symbolSize: (val: number[]) => 4 + (Math.abs(val[1]) / maxAbs) * 14,
            },
          ],
        }
      }}
    />
  )
}

// ── ML confidence over time: X = signal time, Y = ml_confidence (0-1), dot
//    size = |signal strength|, color = direction_agreement (green true, red
//    false, neutral when the backend didn't resolve an agreement value).
//    Only ever fed points that already passed the ml_confidence != null
//    filter (analytics.ts's mlConfidencePoints) — never plots a fabricated
//    confidence for a pre-ML-deployment signal. ──
export function MLConfidenceScatterChart({ points, height = 260 }: { points: MLConfidencePoint[]; height?: number }) {
  if (points.length === 0) {
    return (
      <div style={{ height }}>
        <EmptyState title="No ML confidence data" description="No signals carry an ML confidence score yet — this appears once a deployed model scores new signals." />
      </div>
    )
  }

  return (
    <Chart
      height={height}
      ariaLabel="ML confidence over time"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'item',
            formatter: (p: unknown) => {
              const d = p as { value: [number, number, number, number] }
              const [tsMs, confidence, strength, agreementFlag] = d.value
              const agreementLabel = agreementFlag === 1 ? 'agrees' : agreementFlag === -1 ? 'disagrees' : 'n/a'
              return `${fmtTime(new Date(tsMs).toISOString())}<br/>confidence <b>${formatRatio(confidence)}</b><br/>strength <b>${formatSignalStrength(strength)}</b><br/>direction ${agreementLabel}`
            },
          }),
          grid: { left: 56, right: 16, top: 20, bottom: 28 },
          xAxis: { type: 'time', ...axis, splitLine: { show: false } },
          yAxis: { type: 'value', min: 0, max: 1, ...axis },
          series: [
            {
              type: 'scatter',
              data: points.map((p) => {
                const agreementFlag = p.agreement === true ? 1 : p.agreement === false ? -1 : 0
                const colorToken = p.agreement === true ? 'profit' : p.agreement === false ? 'risk' : 'fg'
                return {
                  value: [new Date(p.ts).getTime(), p.confidence, p.strength, agreementFlag],
                  itemStyle: { color: theme.alpha(colorToken, p.agreement == null ? 0.4 : 0.75) },
                }
              }),
              symbolSize: (val: number[]) => 4 + Math.min(val[2], 1) * 16,
            },
          ],
        }
      }}
    />
  )
}

// ── Consecutive signal direction: bar per run, height = run length, sign
//    keeps the strategy's "streakiness" honest and purely sign-derived. ──
export function ConsecutiveRunsChart({ runs, height = 220 }: { runs: ConsecutiveRun[]; height?: number }) {
  if (runs.length === 0) {
    return (
      <div style={{ height }}>
        <EmptyState title="No signals" description="This strategy has emitted no signals yet." />
      </div>
    )
  }

  return (
    <Chart
      height={height}
      ariaLabel="Consecutive signal direction runs"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'item',
            formatter: (p: unknown) => {
              const d = p as { dataIndex: number }
              const r = runs[d.dataIndex]
              return `${r.sign > 0 ? 'Positive' : 'Negative'} run · <b>${r.length}</b> signal${r.length === 1 ? '' : 's'}<br/>from ${fmtTime(r.startTs)}`
            },
          }),
          grid: { left: 44, right: 16, top: 16, bottom: 24 },
          xAxis: {
            type: 'category',
            data: runs.map((_, i) => String(i + 1)),
            ...axis,
            axisLabel: { ...axis.axisLabel, interval: Math.max(0, Math.floor(runs.length / 12)) },
            splitLine: { show: false },
          },
          yAxis: { type: 'value', minInterval: 1, ...axis },
          series: [
            {
              type: 'bar',
              barMaxWidth: 40,
              data: runs.map((r) => ({
                value: r.sign * r.length,
                itemStyle: {
                  color: {
                    type: 'linear',
                    x: 0, y: 0, x2: 0, y2: r.sign > 0 ? 1 : 0,
                    colorStops:
                      r.sign > 0
                        ? [
                            { offset: 0, color: theme.profit },
                            { offset: 1, color: theme.alpha('profit', 0.45) },
                          ]
                        : [
                            { offset: 0, color: theme.alpha('risk', 0.45) },
                            { offset: 1, color: theme.risk },
                          ],
                  },
                  borderRadius: r.sign > 0 ? [3, 3, 0, 0] : [0, 0, 3, 3],
                  shadowBlur: 6,
                  shadowColor: theme.alpha(r.sign > 0 ? 'profit' : 'risk', 0.3),
                },
              })),
              barCategoryGap: '18%',
            },
          ],
        }
      }}
    />
  )
}

// ── Signal strength distribution: page-specific richer take on the shared
//    Histogram primitive — bars colored by bin sign (zero bin neutral), plus
//    a smooth line overlay tracing the same counts so the shape of the
//    distribution reads at a glance. Binning matches Histogram's approach so
//    the underlying real data (signed signal values) is represented
//    identically, just styled for this page. Kept feature-local (not a
//    Histogram.tsx edit) since that shared primitive also renders on Markets/
//    PriceChart and shouldn't change shape for one page's aesthetic. ──
export function SignalStrengthDistributionChart({
  values,
  buckets = 11,
  height = 200,
}: {
  values: number[]
  buckets?: number
  height?: number
}) {
  if (values.length < 2) {
    return (
      <div style={{ height }}>
        <EmptyState title="Not enough data" description="At least two values are needed to plot a distribution." />
      </div>
    )
  }

  const min = values.reduce((a, b) => Math.min(a, b), Infinity)
  const max = values.reduce((a, b) => Math.max(a, b), -Infinity)
  const span = max - min || 1
  const w = span / buckets
  const bins = Array.from({ length: buckets }, (_, i) => ({ from: min + i * w, to: min + (i + 1) * w, count: 0 }))
  for (const v of values) {
    const idx = Math.min(buckets - 1, Math.floor((v - min) / w))
    bins[idx].count++
  }

  return (
    <Chart
      height={height}
      ariaLabel="Signal strength distribution"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        const mids = bins.map((b) => (b.from + b.to) / 2)
        const zeroBinIdx = mids.findIndex((m) => Math.abs(m) < w) // ~straddles zero
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'axis',
            formatter: (p: unknown) => {
              const arr = p as { dataIndex: number }[]
              const b = bins[arr[0].dataIndex]
              return `<b>${b.count}</b> ${b.count === 1 ? 'signal' : 'signals'}<br/>${b.from.toFixed(4)} … ${b.to.toFixed(4)}`
            },
          }),
          grid: { left: 40, right: 14, top: 12, bottom: 24 },
          xAxis: {
            type: 'category',
            data: mids.map((m) => m.toFixed(4)),
            ...axis,
            axisLabel: { ...axis.axisLabel, interval: Math.floor(buckets / 4) },
            splitLine: { show: false },
          },
          yAxis: { type: 'value', minInterval: 1, ...axis },
          series: [
            {
              type: 'bar',
              barMaxWidth: 40,
              data: bins.map((b, i) => ({
                value: b.count,
                itemStyle: {
                  color: i === zeroBinIdx ? theme.alpha('fg', 0.3) : mids[i] < 0 ? theme.risk : theme.profit,
                  borderRadius: [4, 4, 0, 0],
                },
              })),
              barCategoryGap: '12%',
              z: 2,
            },
            {
              type: 'line',
              data: bins.map((b) => b.count),
              smooth: true,
              symbol: 'none',
              lineStyle: { color: theme.alpha('fg', 0.4), width: 2 },
              z: 3,
            },
          ],
        }
      }}
    />
  )
}

// ── Regime timeline: step line of HMM regime states over time (0=bear,
//    1=neutral, 2=bull) — real train-time history from /api/ml/regime. ──
export function RegimeTimelineChart({ history, height = 160 }: { history: { ts: string; regime: number }[]; height?: number }) {
  if (history.length < 2) {
    return (
      <div style={{ height }}>
        <EmptyState title="No regime history" description="Train the HMM regime detector to build a history." />
      </div>
    )
  }
  const names = ['bear', 'neutral', 'bull']
  return (
    <Chart
      height={height}
      ariaLabel="Market regime timeline"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        const tone = [theme.risk, theme.borderStrong, theme.profit]
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'item',
            formatter: (p: unknown) => {
              const d = p as { value: [number, number] }
              return `${new Date(d.value[0]).toLocaleString()}<br/><b>${names[d.value[1]] ?? d.value[1]}</b>`
            },
          }),
          grid: { left: 64, right: 16, top: 12, bottom: 28 },
          xAxis: { type: 'time', ...axis, splitLine: { show: false } },
          yAxis: {
            type: 'value', min: 0, max: 2, interval: 1, ...axis,
            axisLabel: { ...axis.axisLabel, formatter: (v: number) => names[v] ?? String(v) },
          },
          series: [{
            type: 'line', step: 'end', showSymbol: false,
            lineStyle: { width: 1.5, color: theme.info },
            data: history.map((h) => {
              const v: [number, number] = [new Date(h.ts).getTime(), h.regime]
              return { value: v, itemStyle: { color: tone[h.regime] ?? theme.info } }
            }),
          }],
        }
      }}
    />
  )
}

// ── Feature importance: horizontal bars from a model's real
//    feature_importance metrics (XGBoost.evaluate) — never fabricated. ──
export function FeatureImportanceChart({ importance, height = 220 }: { importance: Record<string, number>; height?: number }) {
  const entries = Object.entries(importance).sort((a, b) => a[1] - b[1])
  if (entries.length === 0) {
    return (
      <div style={{ height }}>
        <EmptyState title="No feature importances" description="This model type does not report feature importance." />
      </div>
    )
  }
  return (
    <Chart
      height={height}
      ariaLabel="Feature importance"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            formatter: (p: unknown) => {
              const d = p as { name: string; value: number }
              return `${d.name}<br/><b>${d.value.toFixed(4)}</b>`
            },
          }),
          grid: { left: 110, right: 24, top: 8, bottom: 24 },
          xAxis: { type: 'value', ...axis },
          yAxis: { type: 'category', data: entries.map(([k]) => k), ...axis },
          series: [{
            type: 'bar',
            data: entries.map(([, v]) => v),
            itemStyle: { color: theme.info, borderRadius: [0, 3, 3, 0] },
            barMaxWidth: 16,
          }],
        }
      }}
    />
  )
}

// ── Regime posterior timeline: stacked area of daily-averaged HMM posterior
//    probabilities (bear=red / neutral=gray / bull=green), summing to 1 per
//    day — a smooth read of regime cycles, not the hourly flicker of discrete
//    states. Optional dashed "now" marker at the latest point. ──
export function RegimePosteriorTimeline({
  posteriors,
  height = 200,
}: {
  posteriors: { ts: string; bear?: number; neutral?: number; bull?: number }[]
  height?: number
}) {
  if (posteriors.length < 2) {
    return (
      <div style={{ height }}>
        <EmptyState title="No regime history" description="Train the HMM regime detector to build a posterior timeline." />
      </div>
    )
  }
  const nowTs = posteriors[posteriors.length - 1].ts
  return (
    <Chart
      height={height}
      ariaLabel="Regime posterior timeline"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        const band = (key: 'bear' | 'neutral' | 'bull', color: string) => ({
          name: key,
          type: 'line' as const,
          stack: 'posterior',
          areaStyle: { color, opacity: 0.85 },
          lineStyle: { width: 0 },
          symbol: 'none',
          emphasis: { disabled: true },
          data: posteriors.map((p) => [p.ts, p[key] ?? 0]),
        })
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'axis',
            formatter: (params: unknown) => {
              const arr = params as { seriesName: string; value: [string, number] }[]
              const day = new Date(arr[0].value[0]).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
              const lines = arr.map((s) => `${s.seriesName}: <b>${Math.round(s.value[1] * 100)}%</b>`).join('<br/>')
              return `${day}<br/>${lines}`
            },
          }),
          legend: { show: false },
          grid: { left: 44, right: 16, top: 12, bottom: 28 },
          xAxis: {
            type: 'time',
            ...axis,
            splitLine: { show: false },
            axisLabel: { ...axis.axisLabel, formatter: (v: number) => new Date(v).getFullYear().toString() },
          },
          yAxis: { type: 'value', min: 0, max: 1, ...axis, axisLabel: { ...axis.axisLabel, formatter: (v: number) => `${Math.round(v * 100)}%` } },
          series: [
            band('bear', theme.risk),
            band('neutral', theme.borderStrong),
            band('bull', theme.profit),
            {
              name: 'now',
              type: 'line',
              data: [[nowTs, 0], [nowTs, 1]],
              lineStyle: { color: theme.fgSubtle, width: 1, type: 'dashed' },
              symbol: 'none',
              silent: true,
              markPoint: {
                symbol: 'pin', symbolSize: 0,
                label: { show: true, formatter: 'now', position: 'top', color: theme.fgSubtle, fontSize: 10 },
                data: [{ name: 'now', coord: [nowTs, 1] }],
              },
            },
          ],
        }
      }}
    />
  )
}
