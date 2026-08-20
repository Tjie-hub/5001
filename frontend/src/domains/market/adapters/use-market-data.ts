/**
 * Market Domain Adapter — ADR-003 §4.1: "composing multiple read models,
 * exposing the hook surface a workspace consumes." This is the ONLY hook
 * market-page.tsx (via its ViewModel) calls; nothing above this layer
 * touches useQuery directly (N-3).
 *
 * Slice 4 scope: one read model, GET /api/v1/market/summary
 * (engine.dashboard.get_risk_dashboard()) — the Executive Market Summary
 * region of MARKET_DESIGN_SPEC_v1.0_FROZEN.md §8. The spec's other five
 * regions (Market Regime Analysis, Market Breadth & Participation as a
 * standalone region, Sector Rotation, Historical Market Evolution,
 * Portfolio Impact) have no backing v1 read model yet — sector rotation and
 * portfolio-conditioned context do not exist in the engine today, and
 * building them would mean fabricating data, not implementing the spec.
 * They stay honest "Reserved" placeholders, same pattern Decision Center
 * established for its own three unbuilt regions.
 *
 * The backend never 404s for this read model (engine/dashboard.py degrades
 * every sensor to an INSUFFICIENT_DATA/NEUTRAL summary rather than
 * erroring), so there is no NO_DATA empty-query case to model here the way
 * Watchlist's adapter has to — "empty" is a real, always-200 payload the
 * ViewModel presents honestly (see use-market-view-model.ts).
 */
import type { MarketSummary } from '@models/market'
import { useMarketSummaryQuery, useInvalidateMarket } from '../repository/queries'
import { classifyWorkspaceError, type WorkspaceErrorState } from './error-classification'

export interface MarketDomainData {
  readonly summary: MarketSummary | null
  /** Never drives a skeleton by itself (S-12/N-8) — the ViewModel reads isPending, not this. */
  readonly isFetching: boolean
  readonly isPending: boolean
  readonly errorState: WorkspaceErrorState | null
  /** Cached data present alongside a failed background refetch (§11.2 STALE_DATA). */
  readonly isStaleWithFailedRefresh: boolean
  readonly refresh: () => void
}

export function useMarketData(date: string | null): MarketDomainData {
  const query = useMarketSummaryQuery(date)
  const refresh = useInvalidateMarket()

  return {
    summary: query.data ?? null,
    isFetching: query.isFetching,
    isPending: query.isPending,
    errorState: query.isError ? classifyWorkspaceError(query.error) : null,
    isStaleWithFailedRefresh: query.isError && query.data !== undefined,
    refresh,
  }
}
