/** Local display formatters — specific enough to Watchlist's own fields
 * (confidence 0-1 floats, rank deltas, multi-day streaks) that promoting
 * them to src/utils would give that leaf layer domain knowledge it doesn't
 * need elsewhere. Same convention as domains/settings/format.ts. */

export function formatConfidencePct(confidence: number | null): string {
  if (confidence === null) return '—'
  return `${Math.round(confidence * 100)}%`
}

export function formatConviction(conviction: number | null): string {
  if (conviction === null) return '—'
  return conviction.toFixed(2)
}

export function formatRankChange(rankChange: number | null): string | null {
  if (rankChange === null || rankChange === 0) return null
  return rankChange > 0 ? `▲ ${rankChange}` : `▼ ${Math.abs(rankChange)}`
}

export function formatScoreDelta(scoreDelta: number | null): string | null {
  if (scoreDelta === null) return null
  const pct = Math.round(scoreDelta * 100)
  if (pct === 0) return null
  return pct > 0 ? `+${pct}%` : `${pct}%`
}

export function formatStreak(consecutiveDays: number | null): string | null {
  if (consecutiveDays === null) return null
  if (consecutiveDays === 1) return '1 day on watchlist'
  return `${consecutiveDays} consecutive days on watchlist`
}

/** Dates are already "YYYY-MM-DD" strings from the backend — displayed
 * verbatim rather than re-parsed/re-zoned, matching this repo's "shown
 * verbatim" convention for operational data (see domains/settings/format.ts). */
export function formatDate(value: string | null): string {
  return value ?? '—'
}

/** Presentation-only grouping of an already-real date list by calendar
 * month (WATCHLIST_DESIGN_SPEC §12 MAY: Group) — never fabricates dates,
 * only buckets the ones the backend actually returned. */
export function groupDatesByMonth(dates: string[]): { month: string; dates: string[] }[] {
  const groups = new Map<string, string[]>()
  for (const date of dates) {
    const month = date.slice(0, 7) // "YYYY-MM"
    const existing = groups.get(month)
    if (existing) existing.push(date)
    else groups.set(month, [date])
  }
  return Array.from(groups.entries()).map(([month, monthDates]) => ({ month, dates: monthDates }))
}
