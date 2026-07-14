// Governing specification: Image 4 (EchoFi) — multi-widget grid, varied
//   chart types. Doc 00 §14.5/§14.7 DATA HONESTY: no slippage, TWAP/VWAP, or
//   latency widgets — none of those benchmarks/timing data exist in this
//   schema (Doc 14 §10.7 simulated immediate fill, no routing round-trip).
'use client'

import { BarChart3, Clock, Waypoints } from 'lucide-react'
import { Panel, Section } from '@/components/ui'
import type { Signal } from '@/features/strategies/types'
import { computeFillNotionals, computeOrdersByHour, computeSignalFunnel } from '../analytics'
import type { Execution, Order } from '../types'
import { FillSizeHistogram, OrdersByHourChart, SignalExecutionFunnel } from './charts'

export function AnalyticsGrid({
  orders,
  executions,
  signals,
}: {
  orders: Order[]
  executions: Execution[]
  signals: Signal[]
}) {
  const notionals = computeFillNotionals(executions)
  const hourBuckets = computeOrdersByHour(executions)
  const funnel = computeSignalFunnel(signals, orders)
  const hourTotal = hourBuckets.reduce((s, b) => s + b.count, 0)
  const maxBucket = hourBuckets.reduce((m, b) => Math.max(m, b.count), 0)
  const batchConcentrated = hourTotal > 0 && maxBucket / hourTotal > 0.6

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <Section icon={<BarChart3 size={16} />} title="Fill size distribution" description="Real fill notionals (quantity × price), USDT.">
        <Panel className="p-4">
          <FillSizeHistogram notionals={notionals} />
        </Panel>
      </Section>

      <Section icon={<Clock size={16} />} title="Fill activity by hour" description="24h breakdown of fill time (executed_at), UTC. Current hour highlighted.">
        <Panel className="p-4">
          <OrdersByHourChart buckets={hourBuckets} />
          {batchConcentrated && (
            <p className="mt-3 border-t border-border pt-3 text-[11px] leading-relaxed text-fg-subtle">
              Concentrated in one hour — this strategy backtests on daily bars, so every fill lands at that bar&apos;s
              00:00 UTC timestamp. Real intraday hour-of-day patterns require hourly-interval fills.
            </p>
          )}
        </Panel>
      </Section>

      <Section icon={<Waypoints size={16} />} title="Signal to execution flow" description="Real lineage counts; drop-off % between stages.">
        <Panel className="p-4">
          <SignalExecutionFunnel stages={funnel} />
        </Panel>
      </Section>
    </div>
  )
}
