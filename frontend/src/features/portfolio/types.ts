// Doc 08 §API Layer: typed models — anchored to core.portfolios / core.positions schema
import type { UUID, ISOTimestamp } from '@/types'

export interface Portfolio {
  id: UUID
  name: string
  baseCurrency: string
  portfolioType: 'LIVE' | 'PAPER' | 'BACKTEST'
  isActive: boolean
  createdAt: ISOTimestamp
}

export interface Position {
  id: UUID
  portfolioId: UUID
  assetId: UUID
  quantity: number
  averageEntryPrice: string   // NUMERIC(18,8) → string to preserve precision
  marketValue: string         // NUMERIC(20,4)
  unrealizedPnl: string
  realizedPnlToday: string
  isClosed: boolean
}
