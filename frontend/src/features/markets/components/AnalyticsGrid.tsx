// Governing specification: handbook/ui/visual_engineering/13_VISUAL_DNA —
//   dense 3-column analytics grid below the primary chart. Doc 00 §14.5/
//   §14.7 DATA HONESTY: every widget is a real computed transform of ingested
//   bars (volume/performance) or the real correlation endpoint — nothing
//   fabricated.
'use client'

import { BarChart3, Grid3x3, TrendingUp } from 'lucide-react'
import { Panel, Section } from '@/components/ui'
import { CorrelationMatrix } from './CorrelationMatrix'
import { PerformanceRankingChart, VolumeRankingChart } from './charts'
import type { RankedAsset } from '../analytics'

export function AnalyticsGrid({
  volumeRanking,
  performanceRanking,
  selectedAssetId,
}: {
  volumeRanking: RankedAsset[]
  performanceRanking: RankedAsset[]
  selectedAssetId: string | null
}) {
  return (
    <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-3">
      <CorrelationMatrix title="Cross-asset correlation" icon={<Grid3x3 size={16} />} />

      <Section icon={<BarChart3 size={16} />} title="Volume ranking" description="Latest bar volume across every ingested instrument.">
        <Panel className="p-4">
          <VolumeRankingChart ranked={volumeRanking} selectedAssetId={selectedAssetId} />
        </Panel>
      </Section>

      <Section icon={<TrendingUp size={16} />} title="24h performance" description="Return since 24 bars ago, biggest movers first.">
        <Panel className="p-4">
          <PerformanceRankingChart ranked={performanceRanking} selectedAssetId={selectedAssetId} />
        </Panel>
      </Section>
    </div>
  )
}
