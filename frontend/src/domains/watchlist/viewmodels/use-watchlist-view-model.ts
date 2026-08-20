/**
 * Watchlist ViewModel — ADR-003 §4.1: "Formatting, labels, derived display
 * values, mapping domain state -> the frozen error/loading states." The
 * only thing watchlist-page.tsx (Component layer) calls; it never touches
 * the Domain Adapter, Repository or TanStack Query directly (N-3).
 *
 * §12.1's load-bearing rule is implemented here, once: `showSkeleton` reads
 * only `primary.isPending`, never `primary.isFetching` — background
 * revalidation must never reset the region to a skeleton (S-12/N-8).
 */
import { useMemo } from 'react'
import type { WatchlistEntry } from '@models/watchlist'
import { useWatchlistData, type WatchlistStrategy } from '../adapters/use-watchlist-data'
import {
  formatConfidencePct,
  formatConviction,
  formatDate,
  formatRankChange,
  formatScoreDelta,
  formatStreak,
  groupDatesByMonth,
} from './format'
import { presentError, type ErrorPresentation } from './error-presentation'

export interface CandidateViewModel {
  readonly ticker: string
  readonly rank: number
  readonly confidencePct: string
  readonly convictionLabel: string
  readonly confluence: number
  readonly sources: string[]
  readonly diffStatus: 'new' | 'upgraded' | 'downgraded' | 'unchanged' | null
  readonly rankChangeLabel: string | null
  readonly scoreDeltaLabel: string | null
  readonly streakLabel: string | null
}

export interface ActivityEntryViewModel {
  readonly ticker: string
  readonly kind: 'added' | 'removed' | 'upgraded' | 'downgraded'
  readonly detailLabel: string | null
}

export interface SummaryMetricsViewModel {
  readonly totalCandidates: number
  readonly addedCount: number
  readonly upgradedCount: number
  readonly downgradedCount: number
  readonly removedCount: number
  readonly priorDateLabel: string | null
  readonly hasPriorSnapshot: boolean
}

export interface DateGroupViewModel {
  readonly month: string
  readonly dates: string[]
}

export interface WatchlistViewModel {
  readonly showSkeleton: boolean
  readonly showBackgroundIndicator: boolean
  readonly errorPresentation: ErrorPresentation | null
  readonly isEmpty: boolean
  readonly viewedDate: string | null
  readonly strategy: WatchlistStrategy
  readonly candidates: CandidateViewModel[]
  readonly summary: SummaryMetricsViewModel | null
  readonly activity: ActivityEntryViewModel[]
  readonly historyGroups: DateGroupViewModel[]
  readonly candidateDetail: (ticker: string) => CandidateViewModel | null
  readonly refresh: () => void
}

function buildCandidate(
  entry: WatchlistEntry,
  diffStatus: CandidateViewModel['diffStatus'],
  rankChange: number | null,
  scoreDelta: number | null,
  streakDays: number | null,
): CandidateViewModel {
  return {
    ticker: entry.ticker,
    rank: entry.rank,
    confidencePct: formatConfidencePct(entry.confidence),
    convictionLabel: formatConviction(entry.conviction),
    confluence: entry.confluence,
    sources: entry.sources,
    diffStatus,
    rankChangeLabel: formatRankChange(rankChange),
    scoreDeltaLabel: formatScoreDelta(scoreDelta),
    streakLabel: formatStreak(streakDays),
  }
}

export function useWatchlistViewModel(
  strategy: WatchlistStrategy,
  selectedDate: string | null,
): WatchlistViewModel {
  const domain = useWatchlistData(strategy, selectedDate)

  return useMemo(() => {
    const { primary, diff, persistent, history, isPartialData, refresh } = domain

    const showSkeleton = primary.isPending
    const showBackgroundIndicator = primary.isFetching && !primary.isPending

    let errorPresentation: ErrorPresentation | null = null
    if (primary.errorState) {
      errorPresentation = presentError(primary.errorState)
    } else if (primary.isStaleWithFailedRefresh) {
      errorPresentation = presentError('STALE_DATA')
    } else if (isPartialData) {
      errorPresentation = presentError('PARTIAL_DATA')
    }

    const changesByTicker = new Map((diff.data?.changes ?? []).map((c) => [c.ticker, c]))
    const addedSet = new Set(diff.data?.added ?? [])
    const streakByTicker = new Map((persistent.data ?? []).map((p) => [p.ticker, p.consecutive_days]))

    const candidates: CandidateViewModel[] = (primary.entries ?? []).map((entry) => {
      const change = changesByTicker.get(entry.ticker)
      const diffStatus: CandidateViewModel['diffStatus'] = addedSet.has(entry.ticker)
        ? 'new'
        : (change?.status ?? null)
      return buildCandidate(
        entry,
        diffStatus,
        change?.rank_change ?? null,
        change?.score_delta ?? null,
        streakByTicker.get(entry.ticker) ?? null,
      )
    })

    const summary: SummaryMetricsViewModel | null =
      primary.entries !== null
        ? {
            totalCandidates: primary.entries.length,
            addedCount: diff.data?.added.length ?? 0,
            upgradedCount:
              diff.data?.changes.filter((c) => c.status === 'upgraded').length ?? 0,
            downgradedCount:
              diff.data?.changes.filter((c) => c.status === 'downgraded').length ?? 0,
            removedCount: diff.data?.removed.length ?? 0,
            priorDateLabel: diff.data ? formatDate(diff.data.prior_date) : null,
            hasPriorSnapshot: diff.data !== null,
          }
        : null

    const activity: ActivityEntryViewModel[] = []
    for (const ticker of diff.data?.added ?? []) {
      activity.push({ ticker, kind: 'added', detailLabel: null })
    }
    for (const ticker of diff.data?.removed ?? []) {
      activity.push({ ticker, kind: 'removed', detailLabel: null })
    }
    for (const change of diff.data?.changes ?? []) {
      if (change.status === 'upgraded' || change.status === 'downgraded') {
        activity.push({
          ticker: change.ticker,
          kind: change.status,
          detailLabel: formatScoreDelta(change.score_delta),
        })
      }
    }

    const historyGroups = groupDatesByMonth(history.data ?? [])

    const candidateDetail = (ticker: string): CandidateViewModel | null =>
      candidates.find((c) => c.ticker === ticker) ?? null

    return {
      showSkeleton,
      showBackgroundIndicator,
      errorPresentation,
      isEmpty: primary.isEmpty,
      viewedDate: primary.date,
      strategy,
      candidates,
      summary,
      activity,
      historyGroups,
      candidateDetail,
      refresh,
    }
  }, [domain, strategy])
}
