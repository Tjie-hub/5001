/** Local display formatters for Ticker's fields — same "specific enough to
 * stay local rather than promote to src/utils" convention as Market's.
 * Never invents a value: every formatter maps null straight through to the
 * em-dash placeholder. */

export function formatPrice(value: number | null): string {
  if (value === null) return '—'
  return value.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function formatPct(value: number | null, options?: { signed?: boolean }): string {
  if (value === null) return '—'
  const rounded = Math.round(value * 10) / 10
  const sign = options?.signed && rounded > 0 ? '+' : ''
  return `${sign}${rounded}%`
}

export function formatIdrCompact(value: number | null): string {
  if (value === null) return '—'
  const abs = Math.abs(value)
  const sign = value < 0 ? '-' : ''
  if (abs >= 1e12) return `${sign}Rp${(abs / 1e12).toFixed(1)}T`
  if (abs >= 1e9) return `${sign}Rp${(abs / 1e9).toFixed(1)}B`
  if (abs >= 1e6) return `${sign}Rp${(abs / 1e6).toFixed(1)}M`
  return `${sign}Rp${abs.toLocaleString('id-ID')}`
}

export function formatScore(value: number | null): string {
  if (value === null) return '—'
  const rounded = Math.round(value * 10) / 10
  return `${rounded > 0 ? '+' : ''}${rounded}`
}

/** Humanises SCREAMING_SNAKE and lowercase tag labels ("BULL_MODERATE" ->
 * "Bull Moderate", "eod" -> "Eod"); passes through anything else. */
export function humaniseLabel(value: string | null): string {
  if (value === null) return '—'
  return value
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

/** Renders a production timestamp for the activity timeline: keeps the
 * date and WIB time of ISO values, shows an em-dash for rows the backend
 * flagged as having no parseable timestamp (e.g. instrumentation markers
 * that sort last). */
export function formatTimelineAt(at: string): string {
  if (!/^\d{4}-\d{2}-\d{2}/.test(at)) return '—'
  return at.slice(0, 16).replace('T', ' ')
}
