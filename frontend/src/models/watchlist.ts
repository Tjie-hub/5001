/**
 * Watchlist domain models — mirrors /api/v1/watchlists/current verbatim
 * (routes/v1/watchlists.py over engine/trade_plan.py's watchlist_snapshot
 * reads), same "no camelCase remapping" convention as models/operations.ts.
 *
 * Pure types only (Phase 7 v1.1 §9): no api/design-system/workspace imports.
 */

export interface WatchlistEntry {
  readonly ticker: string
  readonly rank: number
  readonly confidence: number
  readonly conviction: number
  readonly confluence: number
  readonly sources: string[]
}

export interface CurrentWatchlist {
  readonly strategy: string
  readonly date: string
  readonly watchlist: WatchlistEntry[]
}
