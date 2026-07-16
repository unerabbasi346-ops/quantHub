// Doc 08 §State Management: TanStack Query for server state.
import { useQuery } from '@tanstack/react-query'
import { hermesService } from '../services/hermes.service'

// 60s polling everywhere Hermes is consumed (Intelligence Workspace,
// Monitoring page System Health Strip) — raised from 30s (perf pass):
// 5 concurrent Hermes queries at 30s was a real chunk of the dashboard's
// steady-state request volume; Hermes health data doesn't need sub-minute
// freshness.
const POLL_MS = 60_000

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
