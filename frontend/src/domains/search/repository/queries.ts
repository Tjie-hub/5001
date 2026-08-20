/**
 * Search Repository — the only place in this workspace that imports
 * @tanstack/react-query (ADR-003 N-3). DTO shapes already match the Domain
 * Model 1:1 (models/search.ts's "no camelCase remapping" convention), so
 * no separate mapping step is needed here.
 *
 * ADR-003 §7 has no declared row for `search` specifically. idx_tickers
 * (what this query reads) is reference data that changes only on a
 * corporate action (listing/delisting/index reconstitution) — the same
 * cadence §7 states for its `ref` row — so this reuses that row's policy
 * verbatim (staleTime 24h, gcTime 24h, no refetch on focus, refetch on
 * reconnect) rather than inventing a new number.
 */
import { queryOptions, useQuery } from '@tanstack/react-query'
import { searchInstruments } from '@api/search'
import { searchKeys } from './keys'

const SEARCH_STALE_TIME = 24 * 60 * 60 * 1000
const SEARCH_GC_TIME = 24 * 60 * 60 * 1000

const cachePolicy = {
  staleTime: SEARCH_STALE_TIME,
  gcTime: SEARCH_GC_TIME,
  refetchOnWindowFocus: false,
  refetchOnReconnect: true,
} as const

export function instrumentSearchOptions(query: string) {
  return queryOptions({
    queryKey: searchKeys.instruments(query),
    queryFn: () => searchInstruments(query),
    ...cachePolicy,
  })
}

export function useInstrumentSearchQuery(query: string, enabled: boolean) {
  return useQuery({ ...instrumentSearchOptions(query), enabled })
}
