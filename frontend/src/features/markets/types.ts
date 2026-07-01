// Doc 08 §API Layer: typed models — anchored to market_data schema + Doc 11 contracts
import type { UUID, ISOTimestamp } from '@/types'

export interface Asset {
  id: UUID
  symbol: string
  exchange: string
  assetClass: string
  name: string | null
  currency: string
  isActive: boolean
}

export interface OHLCVBar {
  id: UUID
  assetId: UUID
  interval: string
  ts: ISOTimestamp
  open: string
  high: string
  low: string
  close: string
  volume: number
}
