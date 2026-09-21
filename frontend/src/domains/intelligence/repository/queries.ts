/**
 * Intelligence Repository — the only place in this workspace that imports
 * @tanstack/react-query (ADR-003 N-3).
 *
 * Composes four existing read models — the canonical investment summary
 * (data/investments.py, ex-5003), the market risk dashboard, the current
 * watchlist and the Edge Registry — through their shared api/ modules.
 * Deliberately no imports from other domains (the cross-workspace boundary,
 * tools/eslint/architecture-boundaries.js): shared reads go through the
 * shared api layer, so each workspace's cache policy stays independent.
 *
 * Cache policy: ADR-003 §7's `market` row (staleTime 5min, gcTime 30min,
 * refetch on focus/reconnect) fits the EOD-cadence reads this workspace
 * makes; declared once here, never overridden at call sites. An empty
 * watchlist snapshot (NO_WATCHLIST_DATA) is a legitimate empty state, not
 * an error — surfaced as `null` data, same convention as the Decision
 * Center hooks.
 */
import { useCallback } from 'react'
import { queryOptions, useQuery, useQueryClient } from '@tanstack/react-query'
import { getInvestmentSummary } from '@api/investments'
import { getMarketSummary } from '@api/market'
import { getCurrentWatchlist, getPersistentWatchlist } from '@api/watchlist'
import { getRegistryStatus } from '@api/registry'
import { ApiRequestError } from '@api/client'
import { intelligenceKeys } from './keys'

const STALE_TIME = 5 * 60 * 1000
const GC_TIME = 30 * 60 * 1000

const cachePolicy = {
  staleTime: STALE_TIME,
  gcTime: GC_TIME,
  refetchOnWindowFocus: true,
  refetchOnReconnect: true,
} as const

export function investmentsSummaryOptions() {
  return queryOptions({
    queryKey: intelligenceKeys.investmentsSummary(),
    queryFn: getInvestmentSummary,
    ...cachePolicy,
  })
}

export function intelligenceMarketSummaryOptions() {
  return queryOptions({
    queryKey: intelligenceKeys.marketSummary(),
    queryFn: () => getMarketSummary(undefined),
    ...cachePolicy,
  })
}

export function intelligenceWatchlistCurrentOptions() {
  return queryOptions({
    queryKey: intelligenceKeys.watchlistCurrent(),
    queryFn: async () => {
      try {
        return await getCurrentWatchlist()
      } catch (cause) {
        if (cause instanceof ApiRequestError && cause.code === 'NO_WATCHLIST_DATA') return null
        throw cause
      }
    },
    ...cachePolicy,
  })
}

export function intelligenceWatchlistPersistentOptions() {
  return queryOptions({
    queryKey: intelligenceKeys.watchlistPersistent(),
    queryFn: () => getPersistentWatchlist('active'),
    ...cachePolicy,
  })
}

export function intelligenceRegistryStatusOptions() {
  return queryOptions({
    queryKey: intelligenceKeys.registryStatus(),
    queryFn: getRegistryStatus,
    ...cachePolicy,
  })
}

export function useIntelligenceSummaryQuery() {
  return useQuery(investmentsSummaryOptions())
}
export function useIntelligenceMarketQuery() {
  return useQuery(intelligenceMarketSummaryOptions())
}
export function useIntelligenceWatchlistQuery() {
  return useQuery(intelligenceWatchlistCurrentOptions())
}
export function useIntelligencePersistentQuery() {
  return useQuery(intelligenceWatchlistPersistentOptions())
}
export function useIntelligenceRegistryQuery() {
  return useQuery(intelligenceRegistryStatusOptions())
}

/** Workspace-scoped refresh: invalidates every intelligence key. */
export function useInvalidateIntelligence(): () => void {
  const queryClient = useQueryClient()
  return useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: intelligenceKeys.all })
  }, [queryClient])
}
