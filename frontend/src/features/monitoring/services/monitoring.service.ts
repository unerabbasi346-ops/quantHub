// Doc 08 §API Layer: centralized client
import { apiClient } from '@/lib/api/client'
import type { ServiceHealth } from '../types'

export const monitoringService = {
  getHealth: () => apiClient.get<ServiceHealth[]>('/v1/health'),
}
