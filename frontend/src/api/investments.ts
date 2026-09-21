/**
 * Investment portfolio API surface — typed wrapper over the canonical
 * investment ledger endpoints (routes/v1/investments.py), same shape as
 * api/market.ts. Read-only: the Intelligence workspace consumes portfolio
 * state; mutations live in the Portfolio workspace's own pages.
 */
import { apiGet } from './client'
import type { InvestmentSummary } from '@models/investments'

export function getInvestmentSummary(): Promise<InvestmentSummary> {
  return apiGet<InvestmentSummary>('/api/v1/investments/summary')
}
