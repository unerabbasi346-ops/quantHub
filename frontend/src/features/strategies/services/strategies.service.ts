// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// API Layer: all backend communication through centralized client — Doc 08 §API Layer
// Per Doc 00 §14.11
import { apiClient } from '@/lib/api/client'
import type { Backtest, ComputedMetrics, MonthlyReturn, Signal, Strategy, TradePnlDistribution } from '../types'

export const strategiesService = {
  // The registry — every registered strategy (api/v1/strategies.py, Step 4.5).
  getStrategies: () => apiClient.get<Strategy[]>('/v1/strategies'),
  // Recent signal feed for a strategy (bounded, most-recent-first).
  getSignals: (strategyId: string, limit = 100) =>
    apiClient.get<Signal[]>(`/v1/strategies/${strategyId}/signals?limit=${limit}`),
  // Backtest results for a strategy (fills, final P&L, determinism hash).
  getBacktests: (strategyId: string) =>
    apiClient.get<Backtest[]>(`/v1/strategies/${strategyId}/backtests`),
  // Computed performance metrics (win rate, Sharpe, max drawdown, ...) for a
  // strategy's most recent COMPLETED backtest. 404s when none exists yet —
  // callers treat that as "no metrics", not an error.
  getMetrics: (strategyId: string) =>
    apiClient.get<ComputedMetrics>(`/v1/strategies/${strategyId}/metrics`),
  // Monthly realized P&L calendar, aggregated server-side from executions —
  // one row per month, so 5 years is 60 rows (never hits the signal cap).
  getMonthlyReturns: (strategyId: string) =>
    apiClient.get<MonthlyReturn[]>(`/v1/strategies/${strategyId}/monthly-returns`),
  // Write: governed Activate/Deactivate lifecycle transition (Doc 14 §10.2.6;
  // api/v1/strategies.py PATCH /strategies/{id}/status). The first real write.
  setStatus: (strategyId: string, status: 'ACTIVE' | 'INACTIVE') =>
    apiClient.patch<Strategy>(`/v1/strategies/${strategyId}/status`, { status }),
  // Server-computed histogram of realized trade P&L (core.executions).
  getTradePnlDistribution: (strategyId: string) =>
    apiClient.get<TradePnlDistribution>(`/v1/strategies/${strategyId}/trade-pnl-distribution`),
}
