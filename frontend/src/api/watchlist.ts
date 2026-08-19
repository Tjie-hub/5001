/**
 * Watchlist API surface — typed wrapper over the already-frozen watchlist
 * endpoint (routes/v1/watchlists.py). Read-only.
 */
import { apiGet } from './client'
import type { CurrentWatchlist } from '@models/watchlist'

export function getCurrentWatchlist(strategy = 'eod'): Promise<CurrentWatchlist> {
  return apiGet<CurrentWatchlist>('/api/v1/watchlists/current', { strategy })
}
