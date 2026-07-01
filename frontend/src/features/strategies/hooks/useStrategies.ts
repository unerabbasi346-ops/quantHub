// Doc 08 §State Management: TanStack Query for server state
import { useQuery } from '@tanstack/react-query'
import { strategiesService } from '../services/strategies.service'

export function useStrategies() {
  return useQuery({ queryKey: ['strategies'], queryFn: strategiesService.getStrategies })
}
