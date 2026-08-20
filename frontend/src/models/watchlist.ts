/**
 * Watchlist domain models — mirrors /api/v1/watchlists/* and /api/v1/
 * snapshots verbatim (routes/v1/watchlists.py, routes/v1/snapshots.py, over
 * engine/trade_plan.py's watchlist_snapshot reads and
 * engine/persistent_watchlist.py), same "no camelCase remapping" convention
 * as models/operations.ts.
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

export interface WatchlistByDate {
  readonly strategy: string
  readonly date: string
  readonly watchlist: WatchlistEntry[]
}

export interface WatchlistHistory {
  readonly strategy: string
  readonly dates: string[]
  readonly count: number
}

/**
 * `status` is `diff_watchlist`'s own classification (engine/trade_plan.py):
 * "upgraded"/"downgraded" cross a +/-0.05 confidence-delta threshold,
 * "unchanged" otherwise. Not the WATCHLIST_DESIGN_SPEC's aspirational
 * Discovered/Observed/Strengthening/... lifecycle taxonomy — that lifecycle
 * has no backend representation today (see the Watchlist repository/
 * adapter docstrings for the full mapping decision).
 */
export interface WatchlistDiffChange {
  readonly ticker: string
  readonly prior_rank: number | null
  readonly rank: number
  readonly rank_change: number | null
  readonly prior_confidence: number | null
  readonly confidence: number | null
  readonly score_delta: number | null
  readonly status: 'upgraded' | 'downgraded' | 'unchanged'
  readonly prior_sources: string[]
  readonly sources: string[]
}

export interface WatchlistDiffBody {
  readonly prior_date: string
  readonly added: string[]
  readonly removed: string[]
  readonly changes: WatchlistDiffChange[]
}

export interface WatchlistDiff {
  readonly strategy: string
  readonly date: string
  /** null means no prior snapshot exists yet (first run, or after a gap) — a legitimate empty state, not an error. */
  readonly diff: WatchlistDiffBody | null
}

/**
 * `status` is the persisted lifecycle engine.persistent_watchlist actually
 * tracks: continuous presence on the firm-APPROVED EOD watchlist across
 * days. ACTIVE/REMOVED only — the row is never deleted, so REMOVED still
 * carries its held history (consecutive_days/total_appearances as of removal).
 */
export interface PersistentWatchlistEntry {
  readonly ticker: string
  readonly first_added_date: string
  readonly last_seen_date: string
  readonly status: 'ACTIVE' | 'REMOVED'
  readonly consecutive_days: number
  readonly total_appearances: number
}

export interface PersistentWatchlist {
  readonly status: string
  readonly watchlist: PersistentWatchlistEntry[]
  readonly count: number
}
