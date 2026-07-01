// Doc 08 §API Layer: typed models — anchored to core.strategies schema
import type { UUID, ISOTimestamp } from '@/types'

export interface Strategy {
  id: UUID
  name: string
  version: string
  status: 'INACTIVE' | 'PAPER' | 'LIVE' | 'ARCHIVED'
  portfolioId: UUID | null
  createdAt: ISOTimestamp
}
