// Doc 08 §API Layer: typed models — anchored to analytics.risk_snapshots schema
import type { UUID, ISOTimestamp } from '@/types'

export interface RiskSnapshot {
  id: UUID
  portfolioId: UUID
  snapshotAt: ISOTimestamp
  var1d95: string | null
  var1d99: string | null
  grossExposure: string | null
  netExposure: string | null
  leverage: string | null
  drawdownCurrent: string | null
}
