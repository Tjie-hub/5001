/** Local display formatters — small enough, and specific enough to this
 * page's fields (job duration_ms, WIB timestamp strings), that promoting
 * them to src/utils would give that leaf layer domain knowledge it doesn't
 * need elsewhere. */

export function formatDuration(durationMs: number | null): string {
  if (durationMs === null) return '—'
  if (durationMs < 1000) return `${durationMs}ms`
  const seconds = durationMs / 1000
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.round(seconds % 60)
  return `${minutes}m ${remainingSeconds}s`
}

/** Timestamps are already WIB "YYYY-MM-DD HH:MM:SS" strings from the backend
 * — displayed verbatim rather than re-parsed/re-zoned, matching this repo's
 * "shown verbatim, never translated" convention for operational data. */
export function formatTimestamp(value: string | null): string {
  return value ?? '—'
}
