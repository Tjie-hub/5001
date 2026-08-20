/**
 * Search Domain Adapter — ADR-003 §4.1: "composing multiple read models,
 * exposing the hook surface a workspace consumes." This is the ONLY hook
 * search-page.tsx (via its ViewModel) calls; nothing above this layer
 * touches useQuery directly (N-3).
 *
 * Slice 5 scope: instrument search only, GET /api/v1/search/instruments
 * (engine.instrument_search.search_instruments()) — SEARCH_DESIGN_SPEC_
 * v1.0_FROZEN.md §5's "Search Instrument" scenario. The spec's other five
 * scenarios (watchlist candidate, portfolio position, recommendation,
 * market context, unified cross-domain results) have no backend search
 * service to back them — production has no unified search index today,
 * and building UI for a search source that doesn't exist would be
 * fabrication, not implementation. This stays a real, single-domain search,
 * same "smallest complete slice" pattern as Decision Center/Market's
 * single populated region.
 *
 * Owns the 300ms debounce (SEARCH_DESIGN_SPEC §11 QUERY_ENTERED ->
 * SEARCHING transition) — the query is only enabled once the debounced
 * value is non-empty, so an empty input never fires a request (IDLE state,
 * not SEARCHING).
 */
import { useEffect, useState } from 'react'
import type { InstrumentSearchResult } from '@models/search'
import { useInstrumentSearchQuery } from '../repository/queries'
import { classifyWorkspaceError, type WorkspaceErrorState } from './error-classification'

const DEBOUNCE_MS = 300

export interface SearchDomainData {
  readonly results: InstrumentSearchResult[] | null
  readonly debouncedQuery: string
  /** True only while a query is in flight and no debounce delay is pending. */
  readonly isSearching: boolean
  /** True during the debounce window itself, before the request fires. */
  readonly isDebouncing: boolean
  readonly errorState: WorkspaceErrorState | null
  readonly retry: () => void
}

export function useSearchData(rawQuery: string): SearchDomainData {
  const trimmed = rawQuery.trim()
  const [debouncedQuery, setDebouncedQuery] = useState(trimmed)

  useEffect(() => {
    const handle = setTimeout(() => setDebouncedQuery(trimmed), DEBOUNCE_MS)
    return () => clearTimeout(handle)
  }, [trimmed])

  const enabled = debouncedQuery.length > 0
  const query = useInstrumentSearchQuery(debouncedQuery, enabled)

  return {
    results: query.data?.results ?? null,
    debouncedQuery,
    isSearching: enabled && query.isFetching,
    isDebouncing: trimmed.length > 0 && trimmed !== debouncedQuery,
    errorState: query.isError ? classifyWorkspaceError(query.error) : null,
    retry: () => void query.refetch(),
  }
}
