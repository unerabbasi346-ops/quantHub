// Doc 08 §API Layer: centralized client
import { apiClient } from '@/lib/api/client'
import type { Strategy } from '../types'

export const strategiesService = {
  getStrategies: () => apiClient.get<Strategy[]>('/v1/strategies'),
}
