// Governing specification: Doc 15 §11.5.3/§11.5.7 Risk Measurement/Limits;
//   Doc 14 §10.9.5 Financing Costs. Section 3 — 3-column position risk grid:
//   concentration, leverage utilization, funding rate monitor. Doc 00
//   §14.5/§14.7 DATA HONESTY.
'use client'

import { useMemo } from 'react'
import { BarChart3, Layers, Sigma } from 'lucide-react'
import { Badge, Panel, Section } from '@/components/ui'
import { useAssets, useFundingRates } from '@/features/markets/hooks/useMarkets'
import { FundingRateHistoryChart } from '@/features/markets/components/charts'
import type { Position } from '@/features/portfolio/types'
import type { RiskLimit } from '../types'
import { computeConcentration, computeLeverageRows, num } from '../analytics'
import { ConcentrationChart, LeverageUtilizationChart } from './charts'

// BTC/USDT:USDT funding is 8h-cadence on Binance — 6 observations = 48h,
// exactly the task-specified window. Real data, not a fabricated resample.
const FUNDING_WINDOW_COUNT = 6

function FundingRateMonitor() {
  const assetsQuery = useAssets()
  const btcPerp = (assetsQuery.data ?? []).find((a) => a.symbol === 'BTC/USDT:USDT')
  const fundingQuery = useFundingRates(btcPerp?.id ?? '', Boolean(btcPerp))
  const allRates = fundingQuery.data ?? []
  const recent = allRates.slice(-FUNDING_WINDOW_COUNT)
  const latest = recent.at(-1)
  const latestPct = latest ? num(latest.funding_rate) * 100 : null

  return (
    <Section icon={<Sigma size={16} />} title="Funding rate monitor" description="BTC/USDT:USDT, last 48h of 8h funding periods.">
      <Panel className="p-4">
        {!btcPerp ? (
          <div className="flex h-[220px] items-center justify-center text-sm text-fg-muted">BTC/USDT:USDT is not registered.</div>
        ) : fundingQuery.isLoading ? (
          <div className="skeleton h-[220px] w-full" />
        ) : (
          <>
            {latestPct != null && (
              <div className="mb-3 flex items-center justify-between">
                <span className="text-[11px] uppercase tracking-wide text-fg-subtle">Latest rate</span>
                <span className={`font-mono text-lg font-bold tabular-nums ${latestPct >= 0 ? 'text-risk' : 'text-profit'}`}>
                  {latestPct >= 0 ? '+' : ''}
                  {latestPct.toFixed(4)}%
                </span>
              </div>
            )}
            <FundingRateHistoryChart rates={recent} height={180} />
          </>
        )}
      </Panel>
    </Section>
  )
}

export function PositionRiskGrid({ positions, limits }: { positions: Position[]; limits: RiskLimit[] }) {
  const concentration = useMemo(() => computeConcentration(positions), [positions])
  const leverageRows = useMemo(() => computeLeverageRows(positions), [positions])

  // Real threshold, only when a limit genuinely configures one — never a
  // fabricated line (current data has no configured limits, per task; this
  // simply renders nothing extra in that honest case).
  const leverageLimit = limits.find((l) => l.metric_name.toLowerCase().includes('leverage'))
  const maxLeverage = leverageLimit ? num(leverageLimit.limit_value) : null

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <Section icon={<Layers size={16} />} title="Concentration risk" description="Each open position's share of total portfolio value.">
        <Panel className="p-4">
          <ConcentrationChart rows={concentration} height={260} />
        </Panel>
      </Section>

      <Section
        icon={<BarChart3 size={16} />}
        title="Leverage utilization"
        description="Real leverage per position — 1.0x for spot."
        actions={maxLeverage ? <Badge variant="warning">limit {maxLeverage}x</Badge> : null}
      >
        <Panel className="p-4">
          <LeverageUtilizationChart rows={leverageRows} maxLeverage={maxLeverage} height={260} />
        </Panel>
      </Section>

      <FundingRateMonitor />
    </div>
  )
}
