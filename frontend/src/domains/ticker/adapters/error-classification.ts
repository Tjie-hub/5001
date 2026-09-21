/**
 * Ticker workspace error-state classification — ADR-003 §11.2's binding
 * map, applied to the detail query's thrown error. Same convention as
 * domains/market/adapters/error-classification.ts, plus a NOT_FOUND state:
 * a symbol with neither ohlcv history nor an idx_tickers row is a real,
 * expected 404 (routes/v1/ticker_detail.py's TICKER_NOT_FOUND), not a
 * server malfunction.
 */
import { ApiRequestError } from '@api/client'

export type WorkspaceErrorState =
  | 'NETWORK_ERROR'
  | 'NOT_FOUND'
  | 'TICKER_UNAVAILABLE'
  | 'UNAUTHORIZED'
  | 'STALE_DATA'

export function classifyWorkspaceError(error: unknown): WorkspaceErrorState {
  if (error instanceof ApiRequestError) {
    if (error.status === 401 || error.status === 403) return 'UNAUTHORIZED'
    if (error.status === 404) return 'NOT_FOUND'
    if (error.status === 0) return 'NETWORK_ERROR'
    return 'TICKER_UNAVAILABLE'
  }
  return 'TICKER_UNAVAILABLE'
}
