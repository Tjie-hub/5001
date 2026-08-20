/**
 * Market domain models — mirrors the /api/v1/market/summary response shape
 * verbatim (routes/v1/market.py over engine/dashboard.py::get_risk_dashboard()),
 * same "no camelCase remapping for a read-only v1 slice" convention as
 * models/operations.ts and models/registry.ts.
 *
 * The backend never 404s here — missing/insufficient data degrades to a
 * labelled empty summary (INSUFFICIENT_DATA / NEUTRAL), not an error. That
 * degraded shape is exactly this same interface with null/zero fields, so
 * there is no separate "empty" type.
 *
 * Pure types only (Phase 7 v1.1 §9): no api/design-system/workspace imports.
 */

export type MarketRiskTier = 'GREEN' | 'YELLOW' | 'ORANGE' | 'RED' | 'CRITICAL'

export type BreadthLabel =
  | 'BULL_MARKET'
  | 'NEUTRAL'
  | 'WEAK'
  | 'BEAR_MARKET'
  | 'INSUFFICIENT_DATA'

export interface MarketRiskComponents {
  readonly vpin: number
  readonly accdist: number
  readonly breadth: number
  readonly technicals: number
  readonly foreign_flow: number
}

export interface MarketIhsgTechnicals {
  readonly close: number | null
  readonly ma5: number | null
  readonly ma20: number | null
  readonly death_cross: boolean
  readonly lower_high: boolean
  readonly support_breaks: number[]
  readonly ytd_pct: number | null
}

export interface MarketBreadth {
  readonly date: string
  readonly advancers: number
  readonly decliners: number
  readonly unchanged: number
  readonly adv_dec_ratio: number
  readonly pct_advancing: number
  readonly pct_above_ma20: number
  readonly label: BreadthLabel
}

export interface MarketForeignFlow {
  readonly today: number | null
  readonly net_5d: number | null
  readonly net_20d: number | null
  readonly trend: 'INFLOW' | 'OUTFLOW' | 'NEUTRAL'
}

export interface MarketVpinSummary {
  readonly date?: string
  readonly tickers_with_vpin?: number
  readonly avg_vpin: number | null
  readonly pct_above_08: number
  readonly pct_above_095: number
  readonly count_above_08?: number
  readonly count_above_095?: number
  readonly label: string
}

export interface MarketAccDistSummary {
  readonly date: string
  readonly total: number
  readonly dist_count: number
  readonly acc_count: number
  readonly neutral_count: number
  readonly dist_pct: number
  readonly acc_pct: number
  readonly avg_numeric_score: number
  readonly label: string
}

export interface MarketSummary {
  readonly date: string
  readonly risk_score: number
  readonly tier: MarketRiskTier
  readonly components: MarketRiskComponents
  readonly ihsg: MarketIhsgTechnicals
  readonly breadth: MarketBreadth
  readonly foreign_flow: MarketForeignFlow
  readonly vpin: MarketVpinSummary
  readonly accdist: MarketAccDistSummary
}
