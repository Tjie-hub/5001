/**
 * Watchlist Domain Adapter — ADR-003 §4.1: "composing multiple read models,
 * exposing the hook surface a workspace consumes." This is the ONLY hook
 * `watchlist-page.tsx` (via its ViewModel) calls; nothing above this layer
 * touches useQuery directly (N-3).
 *
 * Composes five read models: current watchlist (or a historical date),
 * history (available snapshot dates), diff (vs the prior snapshot for the
 * date being viewed), and the persistent multi-day watchlist. Degrades to
 * partial data (M-2) rather than failing the whole page when a secondary
 * query (diff/persistent/history) fails but the primary candidate list
 * loaded successfully — WATCHLIST_DESIGN_SPEC_v1.0_FROZEN.md §11 requires
 * PARTIAL_DATA to be a real, reachable state, not just documented.
 *
 * `selectedDate` is Page State (owned by watchlist-page.tsx's local state),
 * not Resource State: the frozen route is flat "/watchlist" with no date
 * segment (Phase 5 Wireframes names "/watchlist/:group" but the master goal
 * for this slice restricts routing to the existing "/watchlist" only), so
 * viewing a historical snapshot cannot be bookmarked/shared today. That is
 * a real, honest limitation, not an oversight — see watchlist-page.tsx.
 */
import type { PersistentWatchlistEntry, WatchlistDiffBody, WatchlistEntry } from '@models/watchlist'
import {
  useCurrentWatchlistQuery,
  useInvalidateWatchlist,
  usePersistentWatchlistQuery,
  useWatchlistByDateQuery,
  useWatchlistDiffQuery,
  useWatchlistHistoryQuery,
} from '../repository/queries'
import { classifyWorkspaceError, isNoDataError, type SingleQueryErrorState } from './error-classification'

export type WatchlistStrategy = 'eod' | 'premarket'

interface PrimaryWatchlist {
  readonly entries: WatchlistEntry[] | null
  readonly date: string | null
  /** Never drives a skeleton by itself (S-12/N-8) — components read isPending, not this. */
  readonly isFetching: boolean
  readonly isPending: boolean
  readonly errorState: SingleQueryErrorState | null
  /** The 404 NO_WATCHLIST_DATA case: a legitimate empty state, distinct from errorState. */
  readonly isEmpty: boolean
  /** Cached data present alongside a failed background refetch (§11.2 STALE_DATA). */
  readonly isStaleWithFailedRefresh: boolean
}

interface SecondaryReadModel<T> {
  readonly data: T | null
  readonly isPending: boolean
  readonly isFetching: boolean
  readonly errorState: SingleQueryErrorState | null
}

export interface WatchlistDomainData {
  readonly primary: PrimaryWatchlist
  readonly diff: SecondaryReadModel<WatchlistDiffBody | null>
  readonly persistent: SecondaryReadModel<PersistentWatchlistEntry[]>
  readonly history: SecondaryReadModel<string[]>
  /** WATCHLIST_DESIGN_SPEC §11 PARTIAL_DATA: primary succeeded, a secondary read model did not. */
  readonly isPartialData: boolean
  readonly refresh: () => void
}

export function useWatchlistData(
  strategy: WatchlistStrategy,
  selectedDate: string | null,
): WatchlistDomainData {
  const currentQuery = useCurrentWatchlistQuery(strategy)
  const historyQuery = useWatchlistHistoryQuery(strategy)

  const isViewingHistorical = selectedDate !== null
  const byDateQuery = useWatchlistByDateQuery(strategy, selectedDate ?? '', isViewingHistorical)

  const primaryQuery = isViewingHistorical ? byDateQuery : currentQuery
  const effectiveDate = isViewingHistorical ? selectedDate : (currentQuery.data?.date ?? null)

  const diffQuery = useWatchlistDiffQuery(strategy, effectiveDate ?? '', effectiveDate !== null)

  const persistentQuery = usePersistentWatchlistQuery('active')

  const primaryNoData = isNoDataError(primaryQuery.error)

  const primary: PrimaryWatchlist = {
    entries: primaryQuery.data?.watchlist ?? null,
    date: primaryQuery.data?.date ?? effectiveDate,
    isFetching: primaryQuery.isFetching,
    isPending: primaryQuery.isPending,
    errorState:
      primaryQuery.isError && !primaryNoData ? classifyWorkspaceError(primaryQuery.error) : null,
    isEmpty: primaryNoData,
    isStaleWithFailedRefresh: primaryQuery.isError && primaryQuery.data !== undefined,
  }

  const diff: SecondaryReadModel<WatchlistDiffBody | null> = {
    data: diffQuery.data?.diff ?? null,
    isPending: diffQuery.isPending && effectiveDate !== null,
    isFetching: diffQuery.isFetching,
    errorState: diffQuery.isError ? classifyWorkspaceError(diffQuery.error) : null,
  }

  const persistent: SecondaryReadModel<PersistentWatchlistEntry[]> = {
    data: persistentQuery.data?.watchlist ?? null,
    isPending: persistentQuery.isPending,
    isFetching: persistentQuery.isFetching,
    errorState: persistentQuery.isError ? classifyWorkspaceError(persistentQuery.error) : null,
  }

  const history: SecondaryReadModel<string[]> = {
    data: historyQuery.data?.dates ?? null,
    isPending: historyQuery.isPending,
    isFetching: historyQuery.isFetching,
    errorState: historyQuery.isError ? classifyWorkspaceError(historyQuery.error) : null,
  }

  const primaryOk = primary.entries !== null || primary.isEmpty
  const isPartialData =
    primaryOk && (diff.errorState !== null || persistent.errorState !== null || history.errorState !== null)

  const refresh = useInvalidateWatchlist()

  return { primary, diff, persistent, history, isPartialData, refresh }
}
