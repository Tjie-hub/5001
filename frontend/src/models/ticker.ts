/**
 * Ticker domain DTOs — 1:1 with the backend JSON (routes/v1/ticker_detail.py
 * over engine/ticker_detail.py). Same "no camelCase remapping" convention as
 * models/market.ts: field names mirror the wire format exactly, so the
 * Repository needs no mapping step.
 */
import type { MarketSummary } from './market'

export interface TickerIdentity {
  readonly status: string
  readonly in_idx30: boolean
  readonly in_lq45: boolean
  readonly in_idx80: boolean
  readonly sector: string | null
}

export interface TickerPrice {
  readonly date: string
  readonly open: number
  readonly high: number
  readonly low: number
  readonly close: number
  readonly volume: number
  readonly chg: number
  readonly chg_pct: number
}

export interface TickerRegime {
  readonly regime: string
  readonly adx14: number | null
  readonly band: string
}

/** One engine.admission.evaluate outcome for a regime-map candidate. */
export interface TickerAdmissionVerdict {
  readonly strategy: string
  readonly admitted: boolean
  /** disabled | registry | rule_parity | oos_evidence | evidence_staleness | admitted */
  readonly stage: string
  readonly reason: string
  readonly registry_state: string
  readonly is_counter_trend: boolean
}

export interface ProductionAdmission {
  readonly band: string
  readonly candidates: readonly string[]
  readonly admitted: readonly string[]
  readonly verdicts: readonly TickerAdmissionVerdict[]
}

export interface TickerSignal {
  readonly scan_time: string
  readonly strategies: string
  readonly direction: string
  readonly flow_score: number | null
  readonly flow_verdict: string | null
  readonly smart_money: string | null
  readonly reasons: string | null
}

export interface TickerFlowLatest {
  readonly trade_date: string
  readonly composite_score: number | null
  readonly verdict: string | null
  readonly smart_money: string | null
  readonly net_value: number | null
}

export interface TickerForeignAccumulation {
  readonly score_pct: number | null
  readonly foreign_net_lots: number | null
  readonly avg_daily_vol_lots: number | null
  readonly dates_used: number | null
  readonly latest_date: string | null
}

export interface TickerFlow {
  readonly latest: TickerFlowLatest | null
  readonly foreign_accumulation: TickerForeignAccumulation | null
}

export interface WatchlistMembership {
  readonly date: string
  readonly strategy: string
  readonly rank: number
  readonly confidence: number | null
  readonly conviction: number | null
  readonly confluence: number | null
}

export interface AgentDecision {
  readonly scan_time: string
  readonly strategy: string
  readonly decision: string
  readonly confidence: number | null
  readonly size_hint: number | null
  readonly rationale: string | null
}

export interface OpenPosition {
  readonly strategy: string
  readonly entry_date: string | null
  readonly entry_price: number | null
  readonly lots: number | null
  readonly tp_price: number | null
  readonly sl_price: number | null
}

export interface TickerTimelineEvent {
  readonly at: string
  readonly kind: string
  readonly summary: string
}

export interface TickerDataFreshness {
  readonly ohlcv: string | null
  readonly stockbit_flow: string | null
  readonly broker_flow: string | null
}

/** Trade Flow read model (GET /api/v1/tickers/:symbol/trade-flow,
 * engine.trade_flow). Field names match the backend JSON 1:1. */
export interface TradeFlowSession {
  readonly date: string
  readonly minutes: number
  readonly buy_value: number
  readonly sell_value: number
  readonly net_value: number
  readonly net_value_exact: number
  readonly last_price: number
  readonly first_bar: string
  readonly last_bar: string
}

export interface TradeFlowSessionMark {
  readonly date: string
  readonly index: number
}

export interface TradeFlowSeries {
  readonly points: number
  readonly time: readonly string[]
  readonly cum_buy: readonly number[]
  readonly cum_sell: readonly number[]
  readonly net_flow: readonly number[]
  readonly price: readonly number[]
}

export interface TradeFlowFiltersSupported {
  readonly investor: readonly string[]
  readonly trade_type: readonly string[]
  readonly metric: readonly string[]
}

export interface TradeFlow {
  readonly symbol: string
  readonly metric: string
  readonly requested: { readonly start: string; readonly end: string }
  readonly coverage: {
    readonly first_available_session: string
    readonly last_available_session: string
  }
  readonly sessions: readonly TradeFlowSession[]
  readonly missing_sessions: readonly string[]
  readonly session_marks: readonly TradeFlowSessionMark[]
  readonly series: TradeFlowSeries
  readonly totals: {
    readonly buy_value: number
    readonly sell_value: number
    readonly net_value: number
    readonly net_value_exact: number
    readonly net_side: 'accumulation' | 'distribution' | 'neutral'
    readonly last_price: number
  }
  readonly anomaly_minutes: number
  readonly big_money: { readonly available: boolean; readonly reason: string }
  readonly filters_supported: TradeFlowFiltersSupported
  readonly as_of: string
}

export interface TickerDetail {
  readonly symbol: string
  readonly identity: TickerIdentity | null
  readonly price: TickerPrice | null
  readonly regime: TickerRegime | null
  readonly production_admission: ProductionAdmission | null
  readonly signals: readonly TickerSignal[] | null
  readonly flow: TickerFlow | null
  readonly watchlist_membership: readonly WatchlistMembership[] | null
  readonly agent_decisions: readonly AgentDecision[] | null
  readonly position: OpenPosition | null
  readonly timeline: readonly TickerTimelineEvent[] | null
  /** Same aggregator as the Market workspace (engine.dashboard.get_risk_dashboard). */
  readonly market_context: MarketSummary | null
  readonly data_freshness: TickerDataFreshness | null
  readonly as_of: string
}

/** Status-footer read model (GET /api/v1/runtime). */
export interface RuntimeStatus {
  readonly environment: string
  readonly release_source: string
  readonly version: string | null
  readonly timezone: string
  readonly snapshot: { readonly date: string; readonly strategy: string } | null
  readonly freshness: {
    readonly ohlcv: string | null
    readonly stockbit_flow: string | null
  }
  readonly components: Readonly<Record<string, { readonly status: string }>>
  readonly overall: string | null
}
