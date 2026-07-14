// Governing specification: Doc 00 §14.5/§14.7 DATA HONESTY: cumulative P&L
//   is the running sum of real per-fill realized_pnl (migration
//   a2e4c7b1d6f9) — no slippage/TWAP/VWAP benchmarking (none of that data
//   exists). P&L by strategy is real, grouped by the order's resolved
//   strategy_name.
'use client'

import { LineChart as LineChartIcon, PieChart } from 'lucide-react'
import { Panel, Section } from '@/components/ui'
import { computeCumulativePnl, computePnlByStrategy } from '../analytics'
import type { Order } from '../types'
import type { Execution } from '../types'
import { CumulativePnlChart, PnlByStrategyChart } from './charts'

export function ExecutionQuality({ orders, executions }: { orders: Order[]; executions: Execution[] }) {
  const cumulative = computeCumulativePnl(executions)
  const byStrategy = computePnlByStrategy(orders)

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Section icon={<LineChartIcon size={16} />} title="P&L over time" description="Cumulative realized P&L from fills.">
        <Panel className="p-4">
          <CumulativePnlChart points={cumulative} />
        </Panel>
      </Section>

      <Section icon={<PieChart size={16} />} title="Strategy performance breakdown" description="Realized P&L per strategy.">
        <Panel className="p-4">
          <PnlByStrategyChart rows={byStrategy} />
        </Panel>
      </Section>
    </div>
  )
}
