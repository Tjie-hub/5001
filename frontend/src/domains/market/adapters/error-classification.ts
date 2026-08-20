/**
 * Workspace error-state classification — ADR-003 §11.2's binding map,
 * applied to the summary query's thrown error. Same convention as
 * domains/watchlist/adapters/error-classification.ts.
 *
 * PARTIAL_DATA does not apply here (a single read model backs this slice —
 * see MARKET_DESIGN_SPEC_v1.0_FROZEN.md §11 vs. use-market-data.ts
 * docstring for what is and isn't built yet). STALE_DATA is computed
 * structurally from query state in use-market-data.ts, not from a caught
 * error.
 */
import { ApiRequestError } from '@api/client'

export type WorkspaceErrorState = 'NETWORK_ERROR' | 'API_ERROR' | 'STALE_DATA' | 'UNAUTHORIZED'

export function classifyWorkspaceError(error: unknown): WorkspaceErrorState {
  if (error instanceof ApiRequestError) {
    if (error.status === 401 || error.status === 403) return 'UNAUTHORIZED'
    if (error.status === 0) return 'NETWORK_ERROR'
    return 'API_ERROR'
  }
  return 'API_ERROR'
}
