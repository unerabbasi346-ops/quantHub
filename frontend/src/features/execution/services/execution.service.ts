// Doc 08 §API Layer: centralized client
import { apiClient } from '@/lib/api/client'
import type { Order } from '../types'

export const executionService = {
  getOrders: (portfolioId: string) =>
    apiClient.get<Order[]>(`/v1/portfolios/${portfolioId}/orders`),
}
