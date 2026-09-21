/**
 * Ticker Repository — the only place in this workspace that imports
 * @tanstack/react-query (ADR-003 N-3, enforced by
 * tools/eslint/architecture-boundaries.js's per-workspace repository
 * relaxation). DTO shapes already match the backend JSON 1:1 (models/
 * ticker.ts's stated "no camelCase remapping" convention).
 *
 * Cache policy, ADR-003 §7 semantics: the detail read model mixes an
 * intraday price/flow surface with hourly-cadence scan signals — fresher
 * than Market's EOD cadence, so staleTime 1min with refetch on focus and
 * reconnect; the runtime status powers the global footer's Connection
 * value, so it stays valid for 30s and refetches on focus/reconnect.
 * Declared once here, never overridden at a call site.
 */
import { useCallback } from 'react'
import { queryOptions, useQuery, useQueryClient } from '@tanstack/react-query'
import { getRuntimeStatus, getTickerDetail, getTickerTradeFlow } from '@api/ticker'
import { platformKeys, tickerKeys } from './keys'

const DETAIL_STALE_TIME = 60 * 1000
const DETAIL_GC_TIME = 10 * 60 * 1000
const RUNTIME_STALE_TIME = 30 * 1000
const RUNTIME_GC_TIME = 5 * 60 * 1000

const detailCachePolicy = {
  staleTime: DETAIL_STALE_TIME,
  gcTime: DETAIL_GC_TIME,
  refetchOnWindowFocus: true,
  refetchOnReconnect: true,
} as const

const runtimeCachePolicy = {
  staleTime: RUNTIME_STALE_TIME,
  gcTime: RUNTIME_GC_TIME,
  refetchOnWindowFocus: true,
  refetchOnReconnect: true,
} as const

export function tickerDetailOptions(symbol: string) {
  return queryOptions({
    queryKey: tickerKeys.detail(symbol),
    queryFn: () => getTickerDetail(symbol),
    ...detailCachePolicy,
  })
}

export function useTickerDetailQuery(symbol: string) {
  return useQuery(tickerDetailOptions(symbol))
}

export function runtimeStatusOptions() {
  return queryOptions({
    queryKey: platformKeys.runtimeStatus(),
    queryFn: getRuntimeStatus,
    ...runtimeCachePolicy,
  })
}

export function useRuntimeStatusQuery() {
  return useQuery(runtimeStatusOptions())
}

/** Trade Flow — same intraday-freshness cadence as the detail read model. */
export function tickerTradeFlowOptions(
  symbol: string,
  range: { start?: string; end?: string; metric?: string },
) {
  return queryOptions({
    queryKey: tickerKeys.tradeFlow(symbol, range),
    queryFn: () => getTickerTradeFlow(symbol, range),
    ...detailCachePolicy,
  })
}

export function useTickerTradeFlowQuery(
  symbol: string,
  range: { start?: string; end?: string; metric?: string },
) {
  return useQuery(tickerTradeFlowOptions(symbol, range))
}

/** Domain-scoped prefix invalidation (§8.1 rule 2). */
export function useInvalidateTicker(symbol: string): () => void {
  const queryClient = useQueryClient()
  return useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: tickerKeys.detail(symbol) })
  }, [queryClient, symbol])
}
