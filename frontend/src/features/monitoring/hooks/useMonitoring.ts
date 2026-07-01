// Doc 08 §State Management: TanStack Query for server state
import { useQuery } from '@tanstack/react-query'
import { monitoringService } from '../services/monitoring.service'

export function useServiceHealth() {
  return useQuery({
    queryKey: ['service-health'],
    queryFn: monitoringService.getHealth,
    refetchInterval: 30_000,
  })
}
