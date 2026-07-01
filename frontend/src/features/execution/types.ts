// Doc 08 §API Layer: typed models — anchored to core.orders schema + Doc 11 Order contract
import type { UUID, ISOTimestamp } from '@/types'

export interface Order {
  id: UUID
  idempotencyKey: UUID
  clientOrderId: string | null
  portfolioId: UUID
  orderType: 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT' | 'OCO' | 'TRAILING_STOP'
  side: 'BUY' | 'SELL' | 'SELL_SHORT' | 'BUY_TO_COVER'
  quantity: number
  limitPrice: string | null
  status: 'CREATED' | 'VALIDATED' | 'ROUTED' | 'ACKNOWLEDGED' | 'PARTIALLY_FILLED' |
          'FILLED' | 'REJECTED' | 'CANCELLED' | 'CANCEL_PENDING' | 'EXPIRED'
  filledQuantity: number
  createdAt: ISOTimestamp
}
