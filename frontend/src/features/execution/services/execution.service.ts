// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// API Layer: all backend communication through centralized client — Doc 08 §API Layer
// Per Doc 00 §14.11
import { apiClient } from '@/lib/api/client'
import type { Execution, Order } from '../types'

export const executionService = {
  // The blotter feed — orders for a portfolio (api/v1/execution.py, Step 4.4).
  getOrders: (portfolioId: string) =>
    apiClient.get<Order[]>(`/v1/portfolios/${portfolioId}/orders`),
  // Per-order execution fills — the drill-down over core.executions.
  getExecutions: (orderId: string) =>
    apiClient.get<Execution[]>(`/v1/orders/${orderId}/executions`),
  // Strategy-scoped blotter feed — filters on core.orders.strategy_id
  // directly (real FK lineage), the Execution page's strategy selector.
  getOrdersByStrategy: (strategyId: string) =>
    apiClient.get<Order[]>(`/v1/strategies/${strategyId}/orders`),
  // Strategy-scoped fill batch feed — for analytics (trade ratio, P&L over
  // time, fill size distribution) without an N+1 per-order fetch.
  getExecutionsByStrategy: (strategyId: string) =>
    apiClient.get<Execution[]>(`/v1/strategies/${strategyId}/executions`),
}
