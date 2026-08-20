/**
 * Search API surface — typed wrapper over the Search Workspace's one v1
 * read model (routes/v1/search.py), same shape as api/market.ts.
 */
import { apiGet } from './client'
import type { InstrumentSearchResponse } from '@models/search'

export function searchInstruments(query: string, limit = 20): Promise<InstrumentSearchResponse> {
  return apiGet<InstrumentSearchResponse>('/api/v1/search/instruments', { q: query, limit })
}
