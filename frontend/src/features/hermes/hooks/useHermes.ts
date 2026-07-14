// Doc 08 §State Management: TanStack Query for server state.
import { useQuery } from '@tanstack/react-query'
import { hermesService } from '../services/hermes.service'

// 30s polling everywhere Hermes is consumed (Intelligence Workspace,
// Monitoring page System Health Strip) — task-specified interval, matching
// the platform's existing Markets live-bar polling cadence.
const POLL_MS = 30_000

export function useHermesStatus() {
  return useQuery({
    queryKey: ['hermes', 'status'],
    queryFn: hermesService.getStatus,
    refetchInterval: POLL_MS,
  })
}

export function useHermesHealth() {
  return useQuery({
    queryKey: ['hermes', 'health'],
    queryFn: hermesService.getHealth,
    refetchInterval: POLL_MS,
  })
}

export function useHermesPipeline() {
  return useQuery({
    queryKey: ['hermes', 'pipeline'],
    queryFn: hermesService.getPipeline,
    refetchInterval: POLL_MS,
  })
}

export function useHermesStrategies() {
  return useQuery({
    queryKey: ['hermes', 'strategies'],
    queryFn: hermesService.getStrategies,
    refetchInterval: POLL_MS,
  })
}

export function useHermesMl() {
  return useQuery({
    queryKey: ['hermes', 'ml'],
    queryFn: hermesService.getMl,
    refetchInterval: POLL_MS,
  })
}
