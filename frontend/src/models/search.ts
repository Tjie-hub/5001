/**
 * Search domain models — mirrors the /api/v1/search/instruments response
 * shape verbatim (routes/v1/search.py over engine/instrument_search.py),
 * same "no camelCase remapping for a read-only v1 slice" convention as
 * models/market.ts and models/registry.ts.
 *
 * Instrument search only (SEARCH_DESIGN_SPEC_v1.0_FROZEN.md §5 lists five
 * other scenarios — watchlist candidate, portfolio position, recommendation,
 * market context — with no unified backend search service to back them
 * yet; see domains/search/adapters/use-search-data.ts).
 *
 * Pure types only (Phase 7 v1.1 §9): no api/design-system/workspace imports.
 */

export interface InstrumentSearchResult {
  readonly ticker: string
  readonly in_idx30: boolean
  readonly in_lq45: boolean
  readonly in_idx80: boolean
}

export interface InstrumentSearchResponse {
  readonly query: string
  readonly results: InstrumentSearchResult[]
  readonly count: number
}
