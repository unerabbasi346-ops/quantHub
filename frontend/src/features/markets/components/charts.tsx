// Governing specification: handbook/ui Doc 01 — Apache ECharts is the single
//   FROZEN analytics engine; every chart here builds an option through the
//   shared `Chart` wrapper + `chart-theme` tokens. Doc 00 §14.5/§14.7 — DATA
//   HONESTY: every series below is a deterministic transform of real ingested
//   bars/funding rows; nothing here is fabricated.
//
// Bespoke, page-specific compositions for the Markets workspace (volume
// ranking, 24h performance ranking, funding-rate history) — feature-local,
// composing the generic Chart/chart-theme primitives the same way
// strategies/components/charts.tsx and markets/CorrelationMatrix do.
'use client'

import { Chart } from '@/components/ui/Chart'
import { chartAxis, chartTooltip, type ChartTheme } from '@/components/ui/chart-theme'
import { EmptyState } from '@/components/ui/States'
import { fmtCompactVolume, type RankedAsset } from '../analytics'
import type { FundingRate } from '../types'

const fmtDate = (ts: string) =>
  new Date(ts).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit' })

// ── Horizontal bar: 24h volume ranking, highest at top; selected asset
//    highlighted violet, everyone else a muted neutral. ──
export function VolumeRankingChart({
  ranked,
  selectedAssetId,
  height = 320,
}: {
  ranked: RankedAsset[]
  selectedAssetId: string | null
  height?: number
}) {
  if (ranked.length === 0) {
    return (
      <div style={{ height }}>
        <EmptyState title="No volume data" description="No bars ingested yet for any instrument." />
      </div>
    )
  }

  return (
    <Chart
      height={height}
      ariaLabel="24h volume ranking"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'item',
            formatter: (p: unknown) => {
              const d = p as { dataIndex: number }
              const r = ranked[d.dataIndex]
              return `${r.symbol}<br/><b>${fmtCompactVolume(r.value)}</b>`
            },
          }),
          grid: { left: 78, right: 40, top: 8, bottom: 8 },
          xAxis: { type: 'value', ...axis, axisLabel: { ...axis.axisLabel, formatter: (v: number) => fmtCompactVolume(v) } },
          yAxis: {
            type: 'category',
            data: ranked.map((r) => r.symbol.split('/')[0]),
            inverse: true,
            ...axis,
            splitLine: { show: false },
          },
          series: [
            {
              type: 'bar',
              data: ranked.map((r) => ({
                value: r.value,
                itemStyle: {
                  color: r.assetId === selectedAssetId ? theme.accent : theme.alpha('fg', 0.25),
                  borderRadius: [0, 3, 3, 0],
                },
              })),
              barMaxWidth: 16,
              label: {
                show: true,
                position: 'right',
                color: theme.fgMuted,
                fontFamily: theme.fontMono,
                fontSize: 10,
                formatter: (p: unknown) => fmtCompactVolume((p as { value: number }).value),
              },
            },
          ],
        }
      }}
    />
  )
}

// ── Horizontal bar: 24h performance ranking, sorted by |return| descending;
//    green/red by sign, selected asset gets a brighter fill. ──
export function PerformanceRankingChart({
  ranked,
  selectedAssetId,
  height = 320,
}: {
  ranked: RankedAsset[]
  selectedAssetId: string | null
  height?: number
}) {
  if (ranked.length === 0) {
    return (
      <div style={{ height }}>
        <EmptyState title="No performance data" description="No bars ingested yet for any instrument." />
      </div>
    )
  }

  return (
    <Chart
      height={height}
      ariaLabel="24h performance ranking"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'item',
            formatter: (p: unknown) => {
              const d = p as { dataIndex: number }
              const r = ranked[d.dataIndex]
              return `${r.symbol}<br/><b style="color:${r.value >= 0 ? theme.profit : theme.risk}">${r.value >= 0 ? '+' : ''}${r.value.toFixed(2)}%</b>`
            },
          }),
          grid: { left: 78, right: 40, top: 8, bottom: 8 },
          xAxis: { type: 'value', ...axis, axisLabel: { ...axis.axisLabel, formatter: (v: number) => `${v}%` } },
          yAxis: {
            type: 'category',
            data: ranked.map((r) => r.symbol.split('/')[0]),
            inverse: true,
            ...axis,
            splitLine: { show: false },
          },
          series: [
            {
              type: 'bar',
              data: ranked.map((r) => ({
                value: r.value,
                itemStyle: {
                  color: theme.alpha(
                    r.value >= 0 ? 'profit' : 'risk',
                    r.assetId === selectedAssetId ? 0.95 : 0.45,
                  ),
                  borderRadius: r.value >= 0 ? [0, 3, 3, 0] : [3, 0, 0, 3],
                },
              })),
              barMaxWidth: 16,
              label: {
                show: true,
                position: 'right',
                color: theme.fgMuted,
                fontFamily: theme.fontMono,
                fontSize: 10,
                formatter: (p: unknown) => `${(p as { value: number }).value >= 0 ? '+' : ''}${(p as { value: number }).value.toFixed(1)}%`,
              },
            },
          ],
        }
      }}
    />
  )
}

// ── Funding rate history: positive rates (longs pay -> bearish) in red,
//    negative (shorts pay -> bullish) in green, zero line marked. ──
export function FundingRateHistoryChart({ rates, height = 260 }: { rates: FundingRate[]; height?: number }) {
  if (rates.length < 2) {
    return (
      <div style={{ height }}>
        <EmptyState title="Not enough funding history" description="At least two funding observations are needed to plot a trend." />
      </div>
    )
  }

  const values = rates.map((r) => Number.parseFloat(r.funding_rate) * 100) // display as %
  const posData = values.map((v) => (v >= 0 ? v : 0))
  const negData = values.map((v) => (v < 0 ? v : 0))

  return (
    <Chart
      height={height}
      ariaLabel="Funding rate history"
      option={(theme: ChartTheme) => {
        const axis = chartAxis(theme)
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'axis',
            formatter: (params: unknown) => {
              const arr = params as { axisValue: string }[]
              const idx = rates.findIndex((r) => fmtDate(r.funding_time) === arr[0]?.axisValue)
              const v = idx >= 0 ? values[idx] : 0
              return `${arr[0]?.axisValue}<br/><b style="color:${v >= 0 ? theme.risk : theme.profit}">${v >= 0 ? '+' : ''}${v.toFixed(4)}%</b>`
            },
          }),
          grid: { left: 56, right: 16, top: 20, bottom: 28 },
          xAxis: {
            type: 'category',
            data: rates.map((r) => fmtDate(r.funding_time)),
            boundaryGap: false,
            ...axis,
            splitLine: { show: false },
          },
          yAxis: { type: 'value', ...axis, axisLabel: { ...axis.axisLabel, formatter: (v: number) => `${v}%` } },
          series: [
            {
              name: 'Funding rate',
              type: 'line',
              data: values,
              symbol: 'none',
              lineStyle: { color: theme.fg, width: 1.5 },
              markLine: {
                silent: true,
                symbol: 'none',
                lineStyle: { color: theme.alpha('fg', 0.25), type: 'dashed', width: 1 },
                data: [{ yAxis: 0 }],
                label: { show: false },
              },
            },
            {
              // positive funding = longs pay = bearish -> risk red
              type: 'line',
              data: posData,
              symbol: 'none',
              lineStyle: { opacity: 0 },
              areaStyle: {
                color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
                  { offset: 0, color: theme.alpha('risk', 0.32) },
                  { offset: 1, color: theme.alpha('risk', 0.02) },
                ] },
              },
            },
            {
              // negative funding = shorts pay = bullish -> profit green
              type: 'line',
              data: negData,
              symbol: 'none',
              lineStyle: { opacity: 0 },
              areaStyle: {
                color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
                  { offset: 0, color: theme.alpha('profit', 0.04) },
                  { offset: 1, color: theme.alpha('profit', 0.34) },
                ] },
              },
            },
          ],
        }
      }}
    />
  )
}
