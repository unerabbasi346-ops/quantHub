// Doc 08 §API Layer: typed models — operational monitoring data
import type { ISOTimestamp } from '@/types'

export interface ServiceHealth {
  service: string
  status: 'healthy' | 'degraded' | 'down'
  checkedAt: ISOTimestamp
}
