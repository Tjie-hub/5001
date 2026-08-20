/**
 * Watchlist API surface — typed wrapper over the already-frozen watchlist
 * endpoints (routes/v1/watchlists.py, routes/v1/snapshots.py). Read-only.
 * No new backend route was added for the Watchlist workspace (Production OS
 * Slice 2) — these five existing endpoints already cover current/history/
 * by-date/diff/persistent reads.
 */
import { apiGet } from './client'
import type {
  CurrentWatchlist,
  PersistentWatchlist,
  WatchlistByDate,
  WatchlistDiff,
  WatchlistHistory,
} from '@models/watchlist'

export function getCurrentWatchlist(strategy = 'eod'): Promise<CurrentWatchlist> {
  return apiGet<CurrentWatchlist>('/api/v1/watchlists/current', { strategy })
}

export function getWatchlistHistory(strategy = 'eod'): Promise<WatchlistHistory> {
  return apiGet<WatchlistHistory>('/api/v1/watchlists/history', { strategy })
}

export function getWatchlistByDate(
  dateStr: string,
  strategy = 'eod',
): Promise<WatchlistByDate> {
  return apiGet<WatchlistByDate>(`/api/v1/watchlists/${dateStr}`, { strategy })
}

export function getWatchlistDiff(dateStr: string, strategy = 'eod'): Promise<WatchlistDiff> {
  return apiGet<WatchlistDiff>('/api/v1/watchlists/diff', { strategy, date: dateStr })
}

export function getPersistentWatchlist(
  status: 'active' | 'removed' | 'all' = 'active',
): Promise<PersistentWatchlist> {
  return apiGet<PersistentWatchlist>('/api/v1/watchlists/persistent', { status })
}
