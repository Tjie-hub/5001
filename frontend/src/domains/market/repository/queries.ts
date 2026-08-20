/**
 * Market Repository — the only place in this workspace that imports
 * @tanstack/react-query (ADR-003 N-3, enforced by
 * tools/eslint/architecture-boundaries.js's per-workspace repository
 * relaxation). DTO shapes already match the Domain Model 1:1 (models/
 * market.ts's stated "no camelCase remapping" convention), so no separate
 * mapping step is needed here.
 *
 * Cache policy is ADR-003 §7's `market` row verbatim: staleTime 5min,
 * gcTime 30min, refetch on focus and reconnect — "EOD cadence; intraday
 * drift is slow". Declared once here, never overridden at a call site.
 */
import { useCallback } from 'react'
import { queryOptions, useQuery, useQueryClient } from '@tanstack/react-query'
import { getMarketSummary } from '@api/market'
import { marketKeys } from './keys'

const MARKET_STALE_TIME = 5 * 60 * 1000
const MARKET_GC_TIME = 30 * 60 * 1000

const cachePolicy = {
  staleTime: MARKET_STALE_TIME,
  gcTime: MARKET_GC_TIME,
  refetchOnWindowFocus: true,
  refetchOnReconnect: true,
} as const

export function marketSummaryOptions(date: string | null) {
  return queryOptions({
    queryKey: marketKeys.summary(date),
    queryFn: () => getMarketSummary(date ?? undefined),
    ...cachePolicy,
  })
}

export function useMarketSummaryQuery(date: string | null) {
  return useQuery(marketSummaryOptions(date))
}

/** Domain-scoped prefix invalidation (§8.1 rule 2). */
export function useInvalidateMarket(): () => void {
  const queryClient = useQueryClient()
  return useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: marketKeys.all })
  }, [queryClient])
}
