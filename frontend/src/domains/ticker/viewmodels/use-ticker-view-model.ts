/**
 * Ticker ViewModel — ADR-003 §4.1: "Formatting, labels, derived display
 * values, mapping domain state -> the frozen error/loading states." The
 * only thing ticker-detail-page.tsx (Component layer) calls; it never
 * touches the Domain Adapter, Repository or TanStack Query directly (N-3).
 *
 * `showSkeleton` reads only `isPending`, never `isFetching` — background
 * revalidation must never reset the region to a skeleton (S-12/N-8), same
 * rule as Market, Watchlist and Decision Center.
 *
 * Nothing here invents values: absent production state renders as an
 * honest em-dash or an explicit "none" label (e.g. no admissible strategy
 * is itself the production truth since the 2026-09-02 audit — it is shown,
 * with the blocking stage, not hidden).
 */
import { useMemo } from 'react'
import { useTickerData } from '../adapters/use-ticker-data'
import {
  formatIdrCompact,
  formatPct,
  formatPrice,
  formatScore,
  formatTimelineAt,
  humaniseLabel,
} from './format'
import { presentError, type ErrorPresentation } from './error-presentation'

export interface AdmissionBlocker {
  readonly strategy: string
  readonly stage: string
  readonly reason: string
}

export interface TimelineItem {
  readonly at: string
  readonly summary: string
}

export interface TickerViewModel {
  readonly showSkeleton: boolean
  readonly showBackgroundIndicator: boolean
  readonly errorPresentation: ErrorPresentation | null
  readonly isNotFound: boolean

  // Executive Summary
  readonly priceLabel: string
  readonly chgPctLabel: string
  readonly priceDateLabel: string
  readonly flowVerdictLabel: string
  readonly flowScoreLabel: string
  readonly flowNetValueLabel: string
  readonly foreignAccLabel: string
  readonly admissibleLabel: string
  readonly admissionBandLabel: string
  readonly admissionBlockers: readonly AdmissionBlocker[]
  readonly watchlistLabel: string
  readonly positionLabel: string
  readonly latestSignalLabel: string

  // Primary Region
  readonly regimeBandLabel: string
  readonly regimeLabel: string
  readonly adxLabel: string

  // Context
  readonly sectorLabel: string
  readonly marketRiskLabel: string
  readonly marketTierLabel: string
  readonly ihsgCloseLabel: string
  readonly breadthLabel: string
  readonly foreign5dLabel: string
  readonly freshnessLabel: string

  // Activity Timeline
  readonly timeline: readonly TimelineItem[]

  readonly refresh: () => void
}

export function useTickerViewModel(symbol: string): TickerViewModel {
  const domain = useTickerData(symbol)

  return useMemo(() => {
    const { detail, isPending, isFetching, errorState, isStaleWithFailedRefresh, refresh } = domain

    const showSkeleton = isPending
    const showBackgroundIndicator = isFetching && !isPending

    let errorPresentation: ErrorPresentation | null = null
    if (errorState) {
      errorPresentation = presentError(errorState)
    } else if (isStaleWithFailedRefresh) {
      errorPresentation = presentError('STALE_DATA')
    }

    const isNotFound = errorState === 'NOT_FOUND'

    // ── Executive Summary ────────────────────────────────────────────────
    const price = detail?.price ?? null
    const flow = detail?.flow?.latest ?? null
    const foreign = detail?.flow?.foreign_accumulation ?? null
    const admission = detail?.production_admission ?? null
    const watchlist = detail?.watchlist_membership ?? []
    const position = detail?.position ?? null
    const signals = detail?.signals ?? []

    const latestMembership = watchlist[0] ?? null
    const watchlistLabel = latestMembership
      ? `${humaniseLabel(latestMembership.strategy)} watchlist — rank ${latestMembership.rank}` +
        (latestMembership.confidence !== null
          ? `, confidence ${latestMembership.confidence}`
          : '')
      : 'Not on any production watchlist'

    const positionLabel = position
      ? `Open paper position (${position.strategy}) @ ${formatPrice(position.entry_price)}` +
        (position.lots !== null ? ` · ${position.lots} lots` : '')
      : 'No open paper position'

    const latestSignal = signals[0] ?? null
    const latestSignalLabel = latestSignal
      ? `${latestSignal.scan_time} — ${latestSignal.direction} (${latestSignal.strategies})`
      : 'No scan signal recorded'

    const admissionBlockers: AdmissionBlocker[] = (admission?.verdicts ?? [])
      .filter((v) => !v.admitted)
      .map((v) => ({ strategy: v.strategy, stage: v.stage, reason: v.reason }))

    return {
      showSkeleton,
      showBackgroundIndicator,
      errorPresentation,
      isNotFound,

      priceLabel: formatPrice(price?.close ?? null),
      chgPctLabel: formatPct(price?.chg_pct ?? null, { signed: true }),
      priceDateLabel: price?.date ?? '—',
      flowVerdictLabel: humaniseLabel(flow?.verdict ?? null),
      flowScoreLabel: formatScore(flow?.composite_score ?? null),
      flowNetValueLabel: formatIdrCompact(flow?.net_value ?? null),
      foreignAccLabel: formatPct(foreign?.score_pct ?? null, { signed: true }),
      admissibleLabel:
        admission === null
          ? '—'
          : admission.admitted.length > 0
            ? admission.admitted.join(', ')
            : 'None admitted',
      admissionBandLabel: humaniseLabel(admission?.band ?? null),
      admissionBlockers,

      watchlistLabel,
      positionLabel,
      latestSignalLabel,

      // ── Primary Region ─────────────────────────────────────────────────
      regimeBandLabel: humaniseLabel(detail?.regime?.band ?? null),
      regimeLabel: humaniseLabel(detail?.regime?.regime ?? null),
      adxLabel: detail?.regime ? `ADX(14) ${formatScore(detail.regime.adx14)}` : '—',

      // ── Context ────────────────────────────────────────────────────────
      sectorLabel: detail?.identity?.sector ?? '—',
      marketRiskLabel: detail?.market_context
        ? formatScore(detail.market_context.risk_score)
        : '—',
      marketTierLabel: humaniseLabel(detail?.market_context?.tier ?? null),
      ihsgCloseLabel: formatPrice(detail?.market_context?.ihsg.close ?? null),
      breadthLabel: humaniseLabel(detail?.market_context?.breadth.label ?? null),
      foreign5dLabel: formatIdrCompact(detail?.market_context?.foreign_flow.net_5d ?? null),
      freshnessLabel: (() => {
        const f = detail?.data_freshness
        if (!f) return '—'
        return `price ${f.ohlcv ?? '—'} · flow ${f.stockbit_flow ?? '—'} · broker ${f.broker_flow ?? '—'}`
      })(),

      // ── Activity Timeline ──────────────────────────────────────────────
      timeline: (detail?.timeline ?? []).map((e) => ({
        at: formatTimelineAt(e.at),
        summary: e.summary,
      })),

      refresh,
    }
  }, [domain])
}
