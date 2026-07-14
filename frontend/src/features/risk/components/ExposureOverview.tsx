// Governing specification: Doc 15 §11.5.3 Risk Measurement. Section 2 —
//   exposure gauge (left) + cross-asset correlation (right, full-size — its
//   primary home per owner instruction, Markets keeps a compact copy).
'use client'

import { Gauge as GaugeIcon, Grid3x3 } from 'lucide-react'
import { Panel, Section } from '@/components/ui'
import { CorrelationMatrix } from '@/features/markets/components/CorrelationMatrix'
import type { Position } from '@/features/portfolio/types'
import { computeExposureSplit, num } from '../analytics'
import { ExposureGauge } from './charts'

const fmtMoney = (v: number) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export function ExposureOverview({ positions, configuredCapital }: { positions: Position[]; configuredCapital: string | null }) {
  const split = computeExposureSplit(positions)
  const capital = configuredCapital != null ? num(configuredCapital) : null
  const utilizationPct = capital && capital > 0 ? (split.gross / capital) * 100 : null

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Section icon={<GaugeIcon size={16} />} title="Exposure gauge" description="Gross exposure as a share of configured capital.">
        <Panel className="p-4">
          <ExposureGauge utilizationPct={utilizationPct} height={220} />
          <div className="mt-4 grid grid-cols-2 gap-3 border-t border-border pt-4">
            <div className="flex flex-col gap-1 rounded-xl border border-border/60 bg-surface/40 px-3 py-3">
              <span className="text-[10px] font-medium uppercase tracking-wider text-fg-subtle">Long exposure</span>
              <span className="font-mono text-metric-sm font-semibold tabular-nums text-profit">{fmtMoney(split.long)}</span>
            </div>
            <div className="flex flex-col gap-1 rounded-xl border border-border/60 bg-surface/40 px-3 py-3">
              <span className="text-[10px] font-medium uppercase tracking-wider text-fg-subtle">Short exposure</span>
              <span className="font-mono text-metric-sm font-semibold tabular-nums text-risk">{fmtMoney(split.short)}</span>
            </div>
          </div>
        </Panel>
      </Section>

      <CorrelationMatrix title="Cross-asset correlation" icon={<Grid3x3 size={16} />} />
    </div>
  )
}
