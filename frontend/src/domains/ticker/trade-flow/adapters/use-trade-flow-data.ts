/**
 * Trade Flow Domain Adapter — same seam discipline as
 * ../adapters/use-ticker-data.ts: the only hook the Trade Flow view model
 * calls; nothing above this layer touches useQuery directly (N-3).
 *
 * One read model, GET /api/v1/tickers/:symbol/trade-flow
 * (engine.trade_flow.get_trade_flow). An absent range lets the backend
 * default to the latest available session.
 */
import type { TradeFlow } from '@models/ticker'
import { useInvalidateTicker, useTickerTradeFlowQuery } from '../../repository/queries'
import {
  classifyWorkspaceError,
  type WorkspaceErrorState,
} from '../../adapters/error-classification'

export interface TradeFlowRange {
  readonly start?: string
  readonly end?: string
}

export interface TradeFlowDomainData {
  readonly flow: TradeFlow | null
  readonly isPending: boolean
  readonly isFetching: boolean
  readonly errorState: WorkspaceErrorState | null
  readonly refresh: () => void
}

export function useTradeFlowData(symbol: string, range: TradeFlowRange): TradeFlowDomainData {
  const query = useTickerTradeFlowQuery(symbol, {
    ...(range.start !== undefined ? { start: range.start } : {}),
    ...(range.end !== undefined ? { end: range.end } : {}),
    metric: 'value',
  })
  const refresh = useInvalidateTicker(symbol)

  return {
    flow: query.data ?? null,
    isPending: query.isPending,
    isFetching: query.isFetching,
    errorState: query.isError ? classifyWorkspaceError(query.error) : null,
    refresh,
  }
}
