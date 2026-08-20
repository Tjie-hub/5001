/**
 * Market API surface — typed wrapper over the Market Workspace's one v1
 * read model (routes/v1/market.py), same shape as api/registry.ts.
 */
import { apiGet } from './client'
import type { MarketSummary } from '@models/market'

export function getMarketSummary(date?: string): Promise<MarketSummary> {
  return apiGet<MarketSummary>('/api/v1/market/summary', { date })
}
