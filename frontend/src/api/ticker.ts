/**
 * Ticker API surface — typed wrappers over the Ticker workspace's v1 read
 * models (routes/v1/ticker_detail.py, routes/v1/trade_flow.py,
 * routes/v1/platform.py /runtime), same shape as api/market.ts.
 */
import { apiGet } from './client'
import type { RuntimeStatus, TickerDetail, TradeFlow } from '@models/ticker'

export function getTickerDetail(symbol: string): Promise<TickerDetail> {
  return apiGet<TickerDetail>(`/api/v1/tickers/${encodeURIComponent(symbol)}`)
}

export function getRuntimeStatus(): Promise<RuntimeStatus> {
  return apiGet<RuntimeStatus>('/api/v1/runtime')
}

export interface TradeFlowRange {
  readonly start?: string
  readonly end?: string
  readonly metric?: string
}

export function getTickerTradeFlow(
  symbol: string,
  range: TradeFlowRange = {},
): Promise<TradeFlow> {
  return apiGet<TradeFlow>(
    `/api/v1/tickers/${encodeURIComponent(symbol)}/trade-flow`,
    { ...range },
  )
}
