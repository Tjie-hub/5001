/**
 * Investment portfolio models — mirrors the /api/v1/investments/summary
 * response shape verbatim (routes/v1/investments.py over
 * data/investments.py::summary()), same "no camelCase remapping" convention
 * as models/market.ts and models/registry.ts.
 *
 * This is the canonical portfolio ledger that absorbed the Investment
 * Dashboard (ex-port 5003). The Intelligence workspace only READS it — the
 * Portfolio workspace owns the data (see docs/INTEGRATION_CONSOLIDATION_MAP_2026-09-03.md).
 *
 * Pure types only (Phase 7 v1.1 §9): no api/design-system/workspace imports.
 */

export interface AllocationSlice {
  readonly ticker: string
  readonly value: number
  readonly pct: number
}

export interface InvestmentFees {
  readonly buy_fee_pct: number
  readonly sell_fee_pct: number
  readonly default_div_tax_pct: number
}

export interface InvestmentSummary {
  readonly portfolio_value: number
  readonly equity_cost_basis: number
  readonly unrealized_pl: number
  readonly unrealized_pct: number
  readonly realized_equity_pl: number
  readonly realized_fund_pl: number
  readonly realized_pl: number
  readonly closed_equity_count: number
  readonly closed_fund_count: number
  readonly dividends_gross: number
  readonly dividends_tax: number
  readonly dividends_net: number
  readonly dividend_count: number
  readonly fund_open_value: number
  readonly fund_open_cost: number
  readonly fund_open_count: number
  readonly total_return: number
  readonly total_return_pct: number
  readonly allocation: readonly AllocationSlice[]
  readonly open_positions: number
  readonly fees: InvestmentFees
}
