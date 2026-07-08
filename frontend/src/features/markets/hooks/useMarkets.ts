// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// State Management: TanStack Query for server state — Doc 08 §State Management
// Architecture: hooks separate business logic from presentation — Doc 08 §Architecture
// Per Doc 00 §14.11
import { useQuery } from '@tanstack/react-query'
import { marketsService } from '../services/markets.service'

export function useAssets() {
  return useQuery({ queryKey: ['assets'], queryFn: marketsService.getAssets })
}

export function useBars(assetId: string, interval: string) {
  return useQuery({
    // interval is part of the key so switching intervals refetches/caches
    // independently — Doc 08 §State Management server-state caching.
    queryKey: ['bars', assetId, interval],
    queryFn: () => marketsService.getBars(assetId, interval),
    enabled: Boolean(assetId),
  })
}

export function useCorrelation(interval = '1h') {
  return useQuery({
    queryKey: ['correlation', interval],
    queryFn: () => marketsService.getCorrelation(interval),
  })
}
