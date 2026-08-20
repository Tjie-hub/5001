/**
 * Workspace error-state classification — ADR-003 §11.2's binding map,
 * applied to a single query's thrown error. PARTIAL_DATA and STALE_DATA are
 * deliberately not produced here: both are structural (derived from
 * composing multiple queries, or from stale-cache-plus-failing-refetch),
 * not classifiable from one caught error in isolation — use-watchlist-data.ts
 * computes those directly from query state.
 *
 * This is also where ADR-003 §11.1's "Repository maps ApiError -> DomainError"
 * step collapses into "Domain Adapter maps DomainError -> workspace error
 * state": no Watchlist read model adds domain-specific error semantics
 * beyond what the API Client's ApiRequestError already carries (status,
 * code), so there is no separate DomainError type to introduce here.
 */
import { ApiRequestError } from '@api/client'

/** WATCHLIST_DESIGN_SPEC_v1.0_FROZEN.md §11 Error States (all five, ADR-003 §11.2). */
export type WorkspaceErrorState =
  | 'NETWORK_ERROR'
  | 'API_ERROR'
  | 'PARTIAL_DATA'
  | 'STALE_DATA'
  | 'UNAUTHORIZED'

export type SingleQueryErrorState = 'NETWORK_ERROR' | 'API_ERROR' | 'UNAUTHORIZED'

/** WATCHLIST_DESIGN_SPEC_v1.0_FROZEN.md §11 Error States, minus the two structural ones. */
export function classifyWorkspaceError(error: unknown): SingleQueryErrorState {
  if (error instanceof ApiRequestError) {
    if (error.status === 401 || error.status === 403) return 'UNAUTHORIZED'
    if (error.status === 0) return 'NETWORK_ERROR'
    return 'API_ERROR'
  }
  return 'API_ERROR'
}

/** The 404 NO_WATCHLIST_DATA / NO_SNAPSHOT_DATA case is a legitimate empty
 * state, not an error — same distinction Decision Center's hooks.ts already
 * makes for the current-watchlist read. */
export function isNoDataError(error: unknown): boolean {
  return (
    error instanceof ApiRequestError &&
    (error.code === 'NO_WATCHLIST_DATA' || error.code === 'NO_SNAPSHOT_DATA')
  )
}
