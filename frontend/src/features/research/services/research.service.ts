// Doc 08 §API Layer: centralized client. Real endpoints only —
// /v1/backtests (api/v1/backtests.py) and /api/ml (api/ml.py; mounted
// outside /v1 by design, see that module's header).
import { apiClient } from '@/lib/api/client'
import type {
  BacktestSummary,
  EquityPoint,
  RegimeState,
  RunBacktestRequest,
  RunBacktestResponse,
  TrainJob,
  TrainStatus,
} from '../types'

export const researchService = {
  // Every backtest run across all strategies, newest first, with metrics.
  getBacktests: (limit = 100) =>
    apiClient.get<BacktestSummary[]>(`/v1/backtests?limit=${limit}`),
  // Persisted per-step equity curve, downsampled server-side.
  getEquityCurve: (backtestId: string) =>
    apiClient.get<EquityPoint[]>(`/v1/backtests/${backtestId}/equity-curve`),
  // Start a background replay (plugin strategies only; 400 otherwise).
  runBacktest: (body: RunBacktestRequest) =>
    apiClient.post<RunBacktestResponse>('/v1/backtests', body),
  // Background metalabeler training on the server-built REAL signal dataset;
  // deploys only if held-out accuracy beats the majority-class baseline.
  trainMetalabeler: (body: { instrument_type: 'SPOT' | 'PERPETUAL'; horizon_bars?: number }) =>
    apiClient.post<TrainJob>('/api/ml/train/metalabeler', body),
  // LSTM on the same server-built signal dataset (sequences); baseline-gated.
  trainLstm: (body: { instrument_type: 'SPOT' | 'PERPETUAL'; seq_length?: number }) =>
    apiClient.post<TrainJob>('/api/ml/train/lstm', body),
  // HMM regime detector on real bar returns — no accuracy gate.
  trainHmm: (body: { symbol?: string; exchange?: string; interval?: string }) =>
    apiClient.post<TrainJob>('/api/ml/train/hmm', body),
  // Latest trained HMM regime state (null when none trained yet).
  getRegime: () => apiClient.get<RegimeState | null>('/api/ml/regime'),
  getTrainStatus: (jobId: string) =>
    apiClient.get<TrainStatus>(`/api/ml/train/${jobId}/status`),
}
