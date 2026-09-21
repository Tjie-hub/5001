/**
 * Intelligence Domain Adapter — ADR-003 §4.1: composing multiple read
 * models, exposing the hook surface the workspace consumes. The only hook
 * intelligence-page.tsx (via its ViewModel) calls; nothing above this layer
 * touches useQuery directly (N-3).
 *
 * Failure model: the four read models fail independently. The page keeps
 * rendering whichever regions loaded (each region renders its own inline
 * error state) — a failed market read must not hide the portfolio summary,
 * which is the whole point of composing them here. `fatalErrorState` is set
 * only when EVERYTHING failed, so the page can show one blocking error
 * instead of four identical ones.
 */
import type {
  InvestmentSummary,
} from '@models/investments'
import type { MarketSummary } from '@models/market'
import type { CurrentWatchlist, PersistentWatchlist } from '@models/watchlist'
import type { RegistryStatus } from '@models/registry'
import {
  useIntelligenceSummaryQuery,
  useIntelligenceMarketQuery,
  useIntelligenceWatchlistQuery,
  useIntelligencePersistentQuery,
  useIntelligenceRegistryQuery,
  useInvalidateIntelligence,
} from '../repository/queries'
import { classifyWorkspaceError, type WorkspaceErrorState } from './error-classification'

export interface RegionState<T> {
  readonly data: T | null
  readonly isPending: boolean
  readonly isFetching: boolean
  readonly errorState: WorkspaceErrorState | null
  readonly isStaleWithFailedRefresh: boolean
}

export interface IntelligenceDomainData {
  readonly summary: RegionState<InvestmentSummary>
  readonly market: RegionState<MarketSummary>
  readonly watchlist: RegionState<CurrentWatchlist>
  readonly persistent: RegionState<PersistentWatchlist>
  readonly registry: RegionState<RegistryStatus>
  /** True only when every backing read failed — a blocking page error. */
  readonly allFailed: boolean
  readonly isFetchingAny: boolean
  readonly isPendingAny: boolean
  readonly refresh: () => void
}

function regionState<T>(query: {
  data: T | undefined | null
  isPending: boolean
  isFetching: boolean
  isError: boolean
  error: unknown
}): RegionState<T> {
  const errorState = query.isError ? classifyWorkspaceError(query.error) : null
  return {
    data: (query.data ?? null) as T | null,
    isPending: query.isPending,
    isFetching: query.isFetching,
    errorState,
    isStaleWithFailedRefresh: query.isError && query.data !== undefined && query.data !== null,
  }
}

export function useIntelligenceData(): IntelligenceDomainData {
  const summary = useIntelligenceSummaryQuery()
  const market = useIntelligenceMarketQuery()
  const watchlist = useIntelligenceWatchlistQuery()
  const persistent = useIntelligencePersistentQuery()
  const registry = useIntelligenceRegistryQuery()
  const refresh = useInvalidateIntelligence()

  const regions = {
    summary: regionState<InvestmentSummary>(summary),
    market: regionState<MarketSummary>(market),
    watchlist: regionState<CurrentWatchlist>(watchlist),
    persistent: regionState<PersistentWatchlist>(persistent),
    registry: regionState<RegistryStatus>(registry),
  }

  const failedCount = Object.values(regions).filter((r) => r.errorState !== null).length
  const loadedCount = Object.values(regions).filter((r) => r.data !== null).length

  return {
    ...regions,
    allFailed: failedCount === Object.keys(regions).length && loadedCount === 0,
    isFetchingAny:
      summary.isFetching || market.isFetching || watchlist.isFetching ||
      persistent.isFetching || registry.isFetching,
    isPendingAny:
      summary.isPending || market.isPending || watchlist.isPending ||
      persistent.isPending || registry.isPending,
    refresh,
  }
}
