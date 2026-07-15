// Governing specification: Image 1 (AI Trading Bots) — trade ratio split bar
//   with large % numbers + colored win/loss labels. Doc 00 §14.5/§14.7 DATA
//   HONESTY: the status donut shows ONLY the four real OrderStatus values
//   (CREATED/VALIDATED/REJECTED/FILLED, domain/execution/entities.py) — no
//   fabricated PENDING/EXPIRED bucket the schema doesn't model. "Win"/"loss"
//   is explicitly fill-level realized P&L sign, not strategy-level P&L.
'use client'

import { ListChecks, Percent } from 'lucide-react'
import { DonutChart, Panel, Section, Stat } from '@/components/ui'
import { cn } from '@/lib/utils/cn'
import { formatCapital, formatCount } from '@/lib/utils/format'
import { computeStatusDistribution, computeTradeRatio } from '../analytics'
import type { Execution, Order } from '../types'

const STATUS_TONE: Record<string, 'profit' | 'risk' | 'info' | 'accent'> = {
  FILLED: 'profit',
  REJECTED: 'risk',
  VALIDATED: 'info',
  CREATED: 'accent',
}

export function ExecutionOverview({ orders, executions }: { orders: Order[]; executions: Execution[] }) {
  const statusDist = computeStatusDistribution(orders)
  const ratio = computeTradeRatio(executions)
  const decided = ratio.wins + ratio.losses
  const allFilled = statusDist.length === 1 && statusDist[0].status === 'FILLED'

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Section icon={<ListChecks size={16} />} title="Order status breakdown" description="Real lifecycle-state distribution.">
        <Panel className="p-4">
          {statusDist.length > 0 ? (
            <>
              <DonutChart
                data={statusDist.map((s) => ({ name: s.status, value: s.count, tone: STATUS_TONE[s.status] }))}
                height={260}
                centerValue={String(orders.length)}
                centerLabel="orders"
                valueFormat={(v) => String(v)}
              />
              {allFilled && (
                <p className="mt-3 border-t border-border pt-3 text-center text-[11px] text-fg-subtle">
                  All orders filled (simulation) — this strategy&apos;s risk gate never rejected an order and every fill
                  is a deterministic backtest replay, not a live venue response.
                </p>
              )}
            </>
          ) : (
            <div style={{ height: 260 }} className="flex items-center justify-center text-sm text-fg-muted">
              No orders yet for this strategy.
            </div>
          )}
        </Panel>
      </Section>

      <Section icon={<Percent size={16} />} title="Trade ratio" description="Fill-level realized P&L sign — not strategy P&L.">
        <Panel className="p-4">
          {decided > 0 ? (
            <>
              <div className="flex h-3 w-full overflow-hidden rounded-full bg-surface-hover">
                <div className="bg-profit transition-all" style={{ width: `${ratio.winPct}%` }} />
                <div className="bg-risk transition-all" style={{ width: `${ratio.lossPct}%` }} />
              </div>
              <div className="mt-3 flex items-baseline justify-between">
                <span className="font-mono text-2xl font-semibold text-profit tabular-nums">{ratio.winPct.toFixed(1)}%</span>
                <span className="font-mono text-2xl font-semibold text-risk tabular-nums">{ratio.lossPct.toFixed(1)}%</span>
              </div>
              <div className="mt-1 flex items-center justify-between text-xs">
                <span className="font-medium text-profit">{ratio.wins} Positive</span>
                <span className="font-medium text-risk">{ratio.losses} Negative</span>
              </div>

              <div className="mt-5 grid grid-cols-2 gap-3">
                <div className={cn('rounded-lg border border-border bg-surface-raised/50 p-3')}>
                  <Stat label="Avg win" value={ratio.avgWin != null ? `+${formatCapital(ratio.avgWin)}` : '—'} tone={ratio.avgWin != null ? 'profit' : 'default'} />
                </div>
                <div className={cn('rounded-lg border border-border bg-surface-raised/50 p-3')}>
                  <Stat label="Avg loss" value={ratio.avgLoss != null ? formatCapital(ratio.avgLoss) : '—'} tone={ratio.avgLoss != null ? 'risk' : 'default'} />
                </div>
                <div className={cn('rounded-lg border border-border bg-surface-raised/50 p-3')}>
                  <Stat label="Total wins" value={formatCount(ratio.wins)} tone="profit" />
                </div>
                <div className={cn('rounded-lg border border-border bg-surface-raised/50 p-3')}>
                  <Stat label="Total losses" value={formatCount(ratio.losses)} tone="risk" />
                </div>
              </div>
            </>
          ) : (
            <div style={{ height: 260 }} className="flex items-center justify-center text-center text-sm text-fg-muted">
              No wins/losses yet — every fill so far opened or added to a position (0 realized P&L).
            </div>
          )}
        </Panel>
      </Section>
    </div>
  )
}
