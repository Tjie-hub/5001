/**
 * Search ViewModel — ADR-003 §4.1: "Formatting, labels, derived display
 * values, mapping domain state -> the frozen error/loading states." The
 * only thing search-page.tsx (Component layer) calls; it never touches
 * the Domain Adapter, Repository or TanStack Query directly (N-3).
 *
 * State model mapping onto SEARCH_DESIGN_SPEC_v1.0_FROZEN.md §11:
 * IDLE (no query typed) -> QUERY_ENTERED/SEARCHING (debouncing or
 * in-flight) -> RESULTS_READY (results, possibly empty -> NO_RESULTS).
 */
import { useMemo } from 'react'
import { useSearchData } from '../adapters/use-search-data'
import { presentError, type ErrorPresentation } from './error-presentation'

export type SearchViewState = 'idle' | 'searching' | 'no_results' | 'results' | 'error'

export interface InstrumentResultViewModel {
  readonly ticker: string
  readonly badges: string[]
}

export interface SearchViewModel {
  readonly viewState: SearchViewState
  readonly errorPresentation: ErrorPresentation | null
  readonly results: InstrumentResultViewModel[]
  readonly query: string
  readonly retry: () => void
}

function buildBadges(result: { in_idx30: boolean; in_lq45: boolean; in_idx80: boolean }): string[] {
  const badges: string[] = []
  if (result.in_idx30) badges.push('IDX30')
  if (result.in_lq45) badges.push('LQ45')
  if (result.in_idx80) badges.push('IDX80')
  return badges
}

export function useSearchViewModel(rawQuery: string): SearchViewModel {
  const domain = useSearchData(rawQuery)

  return useMemo(() => {
    const { results, debouncedQuery, isSearching, isDebouncing, errorState, retry } = domain

    if (debouncedQuery.length === 0) {
      return { viewState: 'idle', errorPresentation: null, results: [], query: debouncedQuery, retry }
    }

    if (errorState) {
      return {
        viewState: 'error',
        errorPresentation: presentError(errorState),
        results: [],
        query: debouncedQuery,
        retry,
      }
    }

    if (isSearching || isDebouncing) {
      return {
        viewState: 'searching',
        errorPresentation: null,
        results: [],
        query: debouncedQuery,
        retry,
      }
    }

    const viewModels = (results ?? []).map((r) => ({ ticker: r.ticker, badges: buildBadges(r) }))

    return {
      viewState: viewModels.length === 0 ? 'no_results' : 'results',
      errorPresentation: null,
      results: viewModels,
      query: debouncedQuery,
      retry,
    }
  }, [domain])
}
