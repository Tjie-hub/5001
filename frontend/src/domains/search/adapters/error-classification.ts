/**
 * Workspace error-state classification — ADR-003 §11.2's binding map,
 * applied to the search query's thrown error. Same convention as
 * domains/market/adapters/error-classification.ts.
 */
import { ApiRequestError } from '@api/client'

export type WorkspaceErrorState = 'NETWORK_ERROR' | 'SEARCH_UNAVAILABLE' | 'UNAUTHORIZED'

export function classifyWorkspaceError(error: unknown): WorkspaceErrorState {
  if (error instanceof ApiRequestError) {
    if (error.status === 401 || error.status === 403) return 'UNAUTHORIZED'
    if (error.status === 0) return 'NETWORK_ERROR'
    return 'SEARCH_UNAVAILABLE'
  }
  return 'SEARCH_UNAVAILABLE'
}
