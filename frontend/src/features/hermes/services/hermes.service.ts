// Doc 08 §API Layer: centralized client. Hermes is mounted at /api/hermes —
// deliberately not under /v1, mirroring the backend router's own module
// docstring (a separate observability surface, not a governed REST resource).
import { apiClient } from '@/lib/api/client'
import type { HealthSummary, MLStatus, PipelineStatus, StrategiesStatus, SystemStatus } from '../types'

export const hermesService = {
  getStatus: () => apiClient.get<SystemStatus>('/api/hermes/status'),
  getHealth: () => apiClient.get<HealthSummary>('/api/hermes/health'),
  getPipeline: () => apiClient.get<PipelineStatus>('/api/hermes/pipeline'),
  getStrategies: () => apiClient.get<StrategiesStatus>('/api/hermes/strategies'),
  getMl: () => apiClient.get<MLStatus>('/api/hermes/ml'),
}
