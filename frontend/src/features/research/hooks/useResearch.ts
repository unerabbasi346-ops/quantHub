// Doc 08 §State Management: TanStack Query for server state.
// Real research surface: /v1/backtests + /api/ml/train (see service).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { researchService } from '../services/research.service'

export function useAllBacktests(refetchWhileRunning = false) {
  return useQuery({
    queryKey: ['all-backtests'],
    queryFn: () => researchService.getBacktests(200),
    // While a run is in flight the explorer/backtester poll for the new row.
    refetchInterval: refetchWhileRunning ? 5000 : false,
  })
}

export function useEquityCurve(backtestId: string | null) {
  return useQuery({
    queryKey: ['equity-curve', backtestId],
    queryFn: () => researchService.getEquityCurve(backtestId as string),
    enabled: Boolean(backtestId),
  })
}

export function useRunBacktest() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: researchService.runBacktest,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['all-backtests'] }),
  })
}

export function useTrainMetalabeler() {
  return useMutation({ mutationFn: researchService.trainMetalabeler })
}

export function useTrainLstm() {
  return useMutation({ mutationFn: researchService.trainLstm })
}

export function useTrainHmm() {
  return useMutation({ mutationFn: researchService.trainHmm })
}

export function useRegime() {
  return useQuery({ queryKey: ['ml-regime'], queryFn: researchService.getRegime })
}

// Poll a training job until it reaches a terminal state.
export function useTrainStatus(jobId: string | null) {
  return useQuery({
    queryKey: ['train-status', jobId],
    queryFn: () => researchService.getTrainStatus(jobId as string),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const s = query.state.data?.status
      return s === 'COMPLETED' || s === 'FAILED' ? false : 3000
    },
  })
}
