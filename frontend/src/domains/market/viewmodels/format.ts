/** Local display formatters for Market's numeric fields — same "specific
 * enough to stay local rather than promote to src/utils" convention as
 * domains/watchlist/viewmodels/format.ts. Never invents a value: every
 * formatter maps null straight through to the em-dash placeholder. */

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

export function formatCount(value: number | null): string {
  if (value === null) return '—'
  return value.toLocaleString('id-ID')
}

export function formatTierLabel(tier: string): string {
  return tier.charAt(0) + tier.slice(1).toLowerCase()
}

export function formatBreadthLabel(label: string): string {
  return label
    .split('_')
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(' ')
}
