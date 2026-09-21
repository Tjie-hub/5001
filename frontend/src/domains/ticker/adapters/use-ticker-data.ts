/**
 * Ticker Domain Adapter — ADR-003 §4.1: "composing multiple read models,
 * exposing the hook surface a workspace consumes." This is the ONLY hook
 * the view model calls; nothing above this layer touches useQuery
 * directly (N-3).
 *
 * D4 slice 1 scope: one primary read model, GET /api/v1/tickers/:symbol
 * (engine.ticker_detail.get_ticker_detail()), which assembles every region
 * of the workspace from production tables and the production admission
 * chain. The StatusFooter's runtime-status read model (GET /api/v1/runtime,
 * blocker U-2's backend-owned footer values) is consumed directly from the
 * same repository by app/shell — it is workspace-independent state, not
 * detail data.
 *
 * A 404 TICKER_NOT_FOUND is surfaced as a distinct errorState (NOT_FOUND),
 * not a generic failure: an unknown symbol is a valid user input, not a
 * server malfunction.
 */
import type { TickerDetail } from '@models/ticker'
import { useInvalidateTicker, useTickerDetailQuery } from '../repository/queries'
import {
  classifyWorkspaceError,
  type WorkspaceErrorState,
} from './error-classification'

export interface TickerDomainData {
  readonly detail: TickerDetail | null
  /** Never drives a skeleton by itself (S-12/N-8) — the ViewModel reads isPending, not this. */
  readonly isFetching: boolean
  readonly isPending: boolean
  readonly errorState: WorkspaceErrorState | null
  /** Cached data present alongside a failed background refetch (§11.2 STALE_DATA). */
  readonly isStaleWithFailedRefresh: boolean
  readonly refresh: () => void
}

export function useTickerData(symbol: string): TickerDomainData {
  const query = useTickerDetailQuery(symbol)
  const refresh = useInvalidateTicker(symbol)

  return {
    detail: query.data ?? null,
    isFetching: query.isFetching,
    isPending: query.isPending,
    errorState: query.isError ? classifyWorkspaceError(query.error) : null,
    isStaleWithFailedRefresh: query.isError && query.data !== undefined,
    refresh,
  }
}
