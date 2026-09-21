/**
 * Intelligence ViewModel — ADR-003 §4.1: formatting, labels, derived
 * display values, mapping domain state -> the frozen error/loading states.
 * The only thing intelligence-page.tsx calls; it never touches the Domain
 * Adapter, Repository or TanStack Query directly (N-3).
 *
 * `showSkeleton` reads only `isPending`, never `isFetching` — background
 * revalidation must never reset a region to a skeleton (S-12/N-8).
 */
import { useMemo } from 'react'
import { useIntelligenceData } from '../adapters/use-intelligence-data'
import {
  formatCount,
  formatIdr,
  formatIdrCompact,
  formatLabel,
  formatPct,
  formatTierLabel,
} from './format'
import { presentError, type ErrorPresentation } from './error-presentation'

export const INTELLIGENCE_TABS = [
  'Dashboard',
  'Signals',
  'Opportunities',
  'Risk',
  'Decisions',
  'Research',
] as const

export type IntelligenceTab = (typeof INTELLIGENCE_TABS)[number]

function presentationFor(region: {
  errorState: ReturnType<typeof useIntelligenceData>['summary']['errorState']
  isStaleWithFailedRefresh: boolean
}): ErrorPresentation | null {
  if (region.errorState) return presentError(region.errorState)
  if (region.isStaleWithFailedRefresh) return presentError('STALE_DATA')
  return null
}

export interface IntelligenceViewModel {
  readonly tabs: readonly IntelligenceTab[]
  readonly showSkeleton: boolean
  readonly showBackgroundIndicator: boolean
  readonly fatalPresentation: ErrorPresentation | null
  readonly refresh: () => void

  // Dashboard
  readonly summaryPresentation: ErrorPresentation | null
  readonly summaryPending: boolean
  readonly portfolioValueLabel: string
  readonly equityCostBasisLabel: string
  readonly unrealizedLabel: string
  readonly unrealizedPctLabel: string | null
  readonly unrealizedSign: 'pos' | 'neg' | 'neu'
  readonly realizedLabel: string
  readonly dividendsLabel: string
  readonly totalReturnLabel: string
  readonly totalReturnPctLabel: string | null
  readonly totalReturnSign: 'pos' | 'neg' | 'neu'
  readonly fundOpenLabel: string
  readonly allocation: readonly { ticker: string; valueLabel: string; pctLabel: string }[]
  readonly openPositionsLabel: string

  // Signals (current watchlist)
  readonly watchlistPresentation: ErrorPresentation | null
  readonly watchlistPending: boolean
  readonly watchlistEntries: readonly {
    ticker: string
    rank: number
    confidence: number
    conviction: number
    sources: readonly string[]
  }[]
  readonly watchlistDateLabel: string | null
  readonly watchlistEmpty: boolean

  // Opportunities (persistent watchlist)
  readonly persistentPresentation: ErrorPresentation | null
  readonly persistentPending: boolean
  readonly persistentEntries: readonly {
    ticker: string
    consecutiveDays: number
    totalAppearances: number
    firstAdded: string
  }[]
  readonly persistentEmpty: boolean

  // Risk (market summary)
  readonly marketPresentation: ErrorPresentation | null
  readonly marketPending: boolean
  readonly riskScoreLabel: string | null
  readonly riskTierLabel: string | null
  readonly breadthLabel: string
  readonly foreignFlowLabel: string
  readonly vpinLabel: string
  readonly accdistLabel: string
  readonly ihsgCloseLabel: string

  // Decisions (registry)
  readonly registryPresentation: ErrorPresentation | null
  readonly registryPending: boolean
  readonly approvedCountLabel: string
  readonly shadowCountLabel: string
  readonly registryEntries: readonly { id: string; status: string; regimes: readonly string[] }[]

  // Research (portfolio-aware quick links)
  readonly researchHoldings: readonly { ticker: string; valueLabel: string; pctLabel: string }[]
}

export function useIntelligenceViewModel(): IntelligenceViewModel {
  const domain = useIntelligenceData()

  return useMemo(() => {
    const { summary, market, watchlist, persistent, registry } = domain
    const s = summary.data
    const m = market.data
    const w = watchlist.data
    const p = persistent.data
    const r = registry.data

    const signOf = (v: number): 'pos' | 'neg' | 'neu' => (v > 0 ? 'pos' : v < 0 ? 'neg' : 'neu')

    const allocation = (s?.allocation ?? []).map((a) => ({
      ticker: a.ticker,
      valueLabel: formatIdr(a.value),
      pctLabel: formatPct(a.pct),
    }))

    return {
      tabs: INTELLIGENCE_TABS,
      showSkeleton: domain.isPendingAny,
      showBackgroundIndicator: domain.isFetchingAny,
      fatalPresentation:
        domain.allFailed && domain.summary.errorState
          ? presentError(domain.summary.errorState)
          : null,
      refresh: domain.refresh,

      summaryPresentation: presentationFor(summary),
      summaryPending: summary.isPending,
      portfolioValueLabel: formatIdr(s?.portfolio_value ?? null),
      equityCostBasisLabel: formatIdr(s?.equity_cost_basis ?? null),
      unrealizedLabel: formatIdr(s?.unrealized_pl ?? null),
      unrealizedPctLabel: s ? formatPct(s.unrealized_pct, { signed: true }) : null,
      unrealizedSign: signOf(s?.unrealized_pl ?? 0),
      realizedLabel: formatIdr(s?.realized_pl ?? null),
      dividendsLabel: formatIdr(s?.dividends_net ?? null),
      totalReturnLabel: formatIdr(s?.total_return ?? null),
      totalReturnPctLabel: s ? formatPct(s.total_return_pct, { signed: true }) : null,
      totalReturnSign: signOf(s?.total_return ?? 0),
      fundOpenLabel: s?.fund_open_count
        ? `${formatCount(s.fund_open_count)} open · ${formatIdr(s.fund_open_value)}`
        : 'No open fund positions',
      allocation,
      openPositionsLabel: s ? formatCount(s.open_positions) : '—',

      watchlistPresentation: presentationFor(watchlist),
      watchlistPending: watchlist.isPending,
      watchlistEntries: (w?.watchlist ?? []).map((e) => ({
        ticker: e.ticker,
        rank: e.rank,
        confidence: e.confidence,
        conviction: e.conviction,
        sources: e.sources,
      })),
      watchlistDateLabel: w?.date ?? null,
      watchlistEmpty: w !== null && w.watchlist.length === 0,

      persistentPresentation: presentationFor(persistent),
      persistentPending: persistent.isPending,
      persistentEntries: (p?.watchlist ?? []).map((e) => ({
        ticker: e.ticker,
        consecutiveDays: e.consecutive_days,
        totalAppearances: e.total_appearances,
        firstAdded: e.first_added_date,
      })),
      persistentEmpty: p !== null && p.watchlist.length === 0,

      marketPresentation: presentationFor(market),
      marketPending: market.isPending,
      riskScoreLabel: m ? m.risk_score.toFixed(1) : null,
      riskTierLabel: m ? formatTierLabel(m.tier) : null,
      breadthLabel: m ? formatLabel(m.breadth.label) : '—',
      foreignFlowLabel: m
        ? `${formatIdrCompact(m.foreign_flow.net_5d)} · ${formatLabel(m.foreign_flow.trend)}`
        : '—',
      vpinLabel: m?.vpin.label ?? '—',
      accdistLabel: m ? formatLabel(m.accdist.label) : '—',
      ihsgCloseLabel: m
        ? (m.ihsg.close ?? null) === null
          ? '—'
          : m.ihsg.close!.toLocaleString('id-ID', { maximumFractionDigits: 2 })
        : '—',

      registryPresentation: presentationFor(registry),
      registryPending: registry.isPending,
      approvedCountLabel: r ? formatCount(r.approved) : '—',
      shadowCountLabel: r ? formatCount(r.shadow) : '—',
      registryEntries: (r?.entries ?? []).map((e) => ({
        id: e.id,
        status: e.status,
        regimes: e.regimes,
      })),

      researchHoldings: allocation,
    }
  }, [domain])
}
