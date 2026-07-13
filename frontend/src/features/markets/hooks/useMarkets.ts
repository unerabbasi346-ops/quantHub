// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// State Management: TanStack Query for server state — Doc 08 §State Management
// Architecture: hooks separate business logic from presentation — Doc 08 §Architecture
// Per Doc 00 §14.11
import { useQueries, useQuery } from '@tanstack/react-query'
import { marketsService } from '../services/markets.service'
import type { Asset } from '../types'

export function useAssets() {
  return useQuery({ queryKey: ['assets'], queryFn: marketsService.getAssets })
}

export function useBars(assetId: string, interval: string, limit?: number) {
  return useQuery({
    // interval (+ limit, when explicit) is part of the key so a wider window
    // request caches independently from the default — Doc 08 §State Management.
    queryKey: limit ? ['bars', assetId, interval, limit] : ['bars', assetId, interval],
    queryFn: () => marketsService.getBars(assetId, interval, limit),
    enabled: Boolean(assetId),
  })
}

// Every asset's 1h bars in one batch — the shared source for the asset stats
// strip, volume ranking, and 24h performance ranking widgets, all of which
// need "latest bar" / "last 24 bars" across ALL instruments, not just the
// selected one. Mirrors the useQueries pattern already established in
// features/strategies/hooks/useStrategyPerformance.ts.
export function useAllBars(assets: Asset[], interval = '1h') {
  return useQueries({
    queries: assets.map((a) => ({
      queryKey: ['bars', a.id, interval],
      queryFn: () => marketsService.getBars(a.id, interval),
      enabled: Boolean(a.id),
    })),
  })
}

export function useCorrelation(interval = '1h') {
  return useQuery({
    queryKey: ['correlation', interval],
    queryFn: () => marketsService.getCorrelation(interval),
  })
}

// Perpetual funding-rate history — `enabled` gates on the caller already
// knowing the asset is PERPETUAL (instrument_type), so a SPOT selection never
// fires this query at all rather than firing it and rendering an empty result.
export function useFundingRates(assetId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['funding-rates', assetId],
    queryFn: () => marketsService.getFundingRates(assetId),
    enabled: Boolean(assetId) && enabled,
  })
}
