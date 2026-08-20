/**
 * Watchlist Repository — the only place in this workspace that imports
 * @tanstack/react-query (ADR-003 N-3, enforced by
 * tools/eslint/architecture-boundaries.js's per-workspace repository
 * relaxation — its own message is explicit that this confinement covers
 * "Components AND ADAPTERS", not components alone). Query definitions,
 * cache policy, and the hook wrappers the Domain Adapter calls instead of
 * `useQuery`/`useQueryClient` directly. DTO shapes already match the Domain
 * Model 1:1 (models/watchlist.ts's stated "no camelCase remapping"
 * convention), so no separate mapping step is needed here (S-5 is satisfied
 * by that existing convention, not by new code).
 *
 * Cache policy is the 'watchlist' row of ADR-003 §7's table: staleTime 60s,
 * gcTime 10min, refetch on focus and reconnect — "intraday candidate
 * movement". Declared once here, never overridden at a call site (§7.1).
 */
import { useCallback } from 'react'
import { queryOptions, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getCurrentWatchlist,
  getPersistentWatchlist,
  getWatchlistByDate,
  getWatchlistDiff,
  getWatchlistHistory,
} from '@api/watchlist'
import { watchlistKeys } from './keys'

const WATCHLIST_STALE_TIME = 60 * 1000
const WATCHLIST_GC_TIME = 10 * 60 * 1000

const cachePolicy = {
  staleTime: WATCHLIST_STALE_TIME,
  gcTime: WATCHLIST_GC_TIME,
  refetchOnWindowFocus: true,
  refetchOnReconnect: true,
} as const

export function currentWatchlistOptions(strategy: string) {
  return queryOptions({
    queryKey: watchlistKeys.current(strategy),
    queryFn: () => getCurrentWatchlist(strategy),
    ...cachePolicy,
  })
}

export function watchlistHistoryOptions(strategy: string) {
  return queryOptions({
    queryKey: watchlistKeys.history(strategy),
    queryFn: () => getWatchlistHistory(strategy),
    ...cachePolicy,
  })
}

export function watchlistByDateOptions(strategy: string, date: string) {
  return queryOptions({
    queryKey: watchlistKeys.byDate(strategy, date),
    queryFn: () => getWatchlistByDate(date, strategy),
    ...cachePolicy,
  })
}

export function watchlistDiffOptions(strategy: string, date: string) {
  return queryOptions({
    queryKey: watchlistKeys.diff(strategy, date),
    queryFn: () => getWatchlistDiff(date, strategy),
    ...cachePolicy,
  })
}

export function persistentWatchlistOptions(status: 'active' | 'removed' | 'all' = 'active') {
  return queryOptions({
    queryKey: watchlistKeys.persistent(status),
    queryFn: () => getPersistentWatchlist(status),
    ...cachePolicy,
  })
}

/**
 * Hook wrappers — what the Domain Adapter (adapters/use-watchlist-data.ts)
 * actually calls. Each is a plain function that happens to call useQuery
 * internally; the adapter never imports the library itself (N-3).
 */

export function useCurrentWatchlistQuery(strategy: string) {
  return useQuery(currentWatchlistOptions(strategy))
}

export function useWatchlistHistoryQuery(strategy: string) {
  return useQuery(watchlistHistoryOptions(strategy))
}

export function useWatchlistByDateQuery(strategy: string, date: string, enabled: boolean) {
  return useQuery({ ...watchlistByDateOptions(strategy, date), enabled })
}

export function useWatchlistDiffQuery(strategy: string, date: string, enabled: boolean) {
  return useQuery({ ...watchlistDiffOptions(strategy, date), enabled })
}

export function usePersistentWatchlistQuery(status: 'active' | 'removed' | 'all' = 'active') {
  return useQuery(persistentWatchlistOptions(status))
}

/** Domain-scoped prefix invalidation (§8.1 rule 2) — refetches every
 * watchlist query in the background rather than an exhaustive per-key list. */
export function useInvalidateWatchlist(): () => void {
  const queryClient = useQueryClient()
  return useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: watchlistKeys.all })
  }, [queryClient])
}
