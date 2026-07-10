// Governing specification: handbook/ui Doc 04 (Analytics Component Library) —
//   Asset Allocation / Order Distribution / Exchange Distribution are donut
//   charts; Doc 05 §Donut; Doc 11 — legend + tooltip mandatory. Doc 03 — one
//   question per chart. Per Doc 00 §14.11
//
// Reusable donut for compositional breakdowns (portfolio allocation, order
// status, exchange split). Every slice is REAL — the caller supplies genuine
// values (position market values, order-state counts). A center label shows the
// total so the chart answers "how is X divided AND how big is X". Colors come
// from the theme palette unless the caller assigns semantic hues (e.g. filled vs
// rejected orders → profit/risk).
'use client'

import { Chart } from './Chart'
import { chartTooltip, type ChartTheme } from './chart-theme'

export interface DonutSlice {
  name: string
  value: number
  /** Optional explicit theme color key for semantic slices. */
  tone?: 'profit' | 'risk' | 'info' | 'warning' | 'accent'
}

interface DonutChartProps {
  data: DonutSlice[]
  height?: number
  /** Big number rendered in the hole (already formatted). Defaults to the sum. */
  centerValue?: string
  centerLabel?: string
  /** Value formatter for tooltips/legend (e.g. money, percent). */
  valueFormat?: (v: number) => string
  className?: string
}

export function DonutChart({
  data,
  height = 260,
  centerValue,
  centerLabel,
  valueFormat = (v) => v.toLocaleString(undefined, { maximumFractionDigits: 2 }),
  className,
}: DonutChartProps) {
  const total = data.reduce((s, d) => s + d.value, 0)
  const center = centerValue ?? valueFormat(total)

  return (
    <Chart
      className={className}
      height={height}
      ariaLabel={`Donut chart: ${data.map((d) => d.name).join(', ')}`}
      option={(theme: ChartTheme) => {
        const toneColor: Record<NonNullable<DonutSlice['tone']>, string> = {
          profit: theme.profit,
          risk: theme.risk,
          info: theme.info,
          warning: theme.warning,
          accent: theme.accent,
        }
        return {
          tooltip: chartTooltip(theme, {
            trigger: 'item',
            formatter: (p: unknown) => {
              const d = p as { name: string; value: number; percent: number }
              return `${d.name}<br/><b>${valueFormat(d.value)}</b> &nbsp; ${d.percent.toFixed(1)}%`
            },
          }),
          legend: {
            type: 'scroll',
            orient: 'vertical',
            right: 8,
            top: 'middle',
            icon: 'circle',
            itemWidth: 8,
            itemHeight: 8,
            textStyle: { color: theme.fgMuted, fontFamily: theme.fontMono, fontSize: 11 },
            pageTextStyle: { color: theme.fgMuted },
          },
          graphic: {
            type: 'group',
            left: '32%',
            top: 'middle',
            children: [
              {
                type: 'text',
                style: {
                  text: center,
                  textAlign: 'center',
                  fill: theme.fg,
                  font: `600 18px ${theme.fontMono}`,
                },
              },
              centerLabel
                ? {
                    type: 'text',
                    top: 24,
                    style: {
                      text: centerLabel.toUpperCase(),
                      textAlign: 'center',
                      fill: theme.fgSubtle,
                      font: `500 10px ${theme.fontSans}`,
                    },
                  }
                : { type: 'text', style: { text: '' } },
            ],
          },
          series: [
            {
              type: 'pie',
              radius: ['58%', '82%'],
              center: ['34%', '50%'],
              avoidLabelOverlap: true,
              itemStyle: { borderColor: theme.surfaceRaised, borderWidth: 2, borderRadius: 3 },
              label: { show: false },
              labelLine: { show: false },
              data: data.map((d, i) => ({
                name: d.name,
                value: d.value,
                itemStyle: d.tone ? { color: toneColor[d.tone] } : { color: theme.palette[i % theme.palette.length] },
              })),
            },
          ],
        }
      }}
    />
  )
}
