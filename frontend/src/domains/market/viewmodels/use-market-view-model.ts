/**
 * Market ViewModel — ADR-003 §4.1: "Formatting, labels, derived display
 * values, mapping domain state -> the frozen error/loading states." The
 * only thing market-page.tsx (Component layer) calls; it never touches the
 * Domain Adapter, Repository or TanStack Query directly (N-3).
 *
 * `showSkeleton` reads only `isPending`, never `isFetching` — background
 * revalidation must never reset the region to a skeleton (S-12/N-8), same
 * rule as Watchlist and Decision Center.
 */
import { useMemo } from 'react'
import { useMarketData } from '../adapters/use-market-data'
import {
  formatBreadthLabel,
  formatCount,
  formatIdrCompact,
  formatPct,
  formatPrice,
  formatTierLabel,
} from './format'
import { presentError, type ErrorPresentation } from './error-presentation'

export interface MarketViewModel {
  readonly showSkeleton: boolean
  readonly showBackgroundIndicator: boolean
  readonly errorPresentation: ErrorPresentation | null
  /** True when the backend degraded every sensor to INSUFFICIENT_DATA —
   * a legitimate, honestly-labelled empty state, not an error (spec §11). */
  readonly isInsufficientData: boolean
  readonly date: string | null
  readonly riskScoreLabel: string | null
  readonly riskTierLabel: string | null
  readonly ihsgCloseLabel: string
  readonly ihsgMa5Label: string
  readonly ihsgMa20Label: string
  readonly ihsgYtdLabel: string
  readonly deathCross: boolean
  readonly breadthLabel: string
  readonly advancers: string
  readonly decliners: string
  readonly pctAboveMa20Label: string
  readonly foreignFlowTrend: string
  readonly foreignFlow5dLabel: string
  readonly vpinLabel: string
  readonly accdistLabel: string
  readonly refresh: () => void
}

export function useMarketViewModel(date: string | null): MarketViewModel {
  const domain = useMarketData(date)

  return useMemo(() => {
    const { summary, isPending, isFetching, errorState, isStaleWithFailedRefresh, refresh } = domain

    const showSkeleton = isPending
    const showBackgroundIndicator = isFetching && !isPending

    let errorPresentation: ErrorPresentation | null = null
    if (errorState) {
      errorPresentation = presentError(errorState)
    } else if (isStaleWithFailedRefresh) {
      errorPresentation = presentError('STALE_DATA')
    }

    const isInsufficientData =
      summary !== null &&
      summary.breadth.label === 'INSUFFICIENT_DATA' &&
      summary.ihsg.close === null

    return {
      showSkeleton,
      showBackgroundIndicator,
      errorPresentation,
      isInsufficientData,
      date: summary?.date ?? null,
      riskScoreLabel: summary ? summary.risk_score.toFixed(1) : null,
      riskTierLabel: summary ? formatTierLabel(summary.tier) : null,
      ihsgCloseLabel: formatPrice(summary?.ihsg.close ?? null),
      ihsgMa5Label: formatPrice(summary?.ihsg.ma5 ?? null),
      ihsgMa20Label: formatPrice(summary?.ihsg.ma20 ?? null),
      ihsgYtdLabel: formatPct(summary?.ihsg.ytd_pct ?? null, { signed: true }),
      deathCross: summary?.ihsg.death_cross ?? false,
      breadthLabel: summary ? formatBreadthLabel(summary.breadth.label) : '—',
      advancers: formatCount(summary?.breadth.advancers ?? null),
      decliners: formatCount(summary?.breadth.decliners ?? null),
      pctAboveMa20Label: formatPct(summary?.breadth.pct_above_ma20 ?? null),
      foreignFlowTrend: summary?.foreign_flow.trend ?? 'NEUTRAL',
      foreignFlow5dLabel: formatIdrCompact(summary?.foreign_flow.net_5d ?? null),
      vpinLabel: summary?.vpin.label ?? '—',
      accdistLabel: summary ? formatBreadthLabel(summary.accdist.label) : '—',
      refresh,
    }
  }, [domain])
}
