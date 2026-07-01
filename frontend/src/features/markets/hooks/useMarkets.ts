// Doc 08 §State Management: TanStack Query for server state
import { useQuery } from '@tanstack/react-query'
import { marketsService } from '../services/markets.service'

export function useAssets() {
  return useQuery({ queryKey: ['assets'], queryFn: marketsService.getAssets })
}

export function useBars(assetId: string, interval: string) {
  return useQuery({
    queryKey: ['bars', assetId, interval],
    queryFn: () => marketsService.getBars(assetId, interval),
    enabled: Boolean(assetId),
  })
}
