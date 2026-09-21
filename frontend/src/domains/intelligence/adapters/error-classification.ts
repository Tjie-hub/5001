/**
 * Workspace error-state classification — ADR-003 §11.2's binding map,
 * applied to any of the intelligence queries' thrown errors. Same
 * convention as domains/market/adapters/error-classification.ts.
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
