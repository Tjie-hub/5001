/**
 * Trade Flow ViewModel — formatting, range navigation and derived display
 * values for the Trade Flow section. Pure functions are exported separately
 * from the hook so they stay unit-testable without React
 * (same discipline as ../viewmodels/use-ticker-view-model.ts).
 *
 * Nothing here invents values: a session the backend reported as missing
 * renders as an explicit gap note, and Big Money renders disabled with the
 * backend's own reason string.
 */
import { useMemo, useState } from 'react'
import { useTradeFlowData } from './adapters/use-trade-flow-data'
import { formatIdrCompact } from '../viewmodels/format'

export type Range = { readonly start: string; readonly end: string } | null

/** Calendar-day ISO shift, no timezone maths (dates are plain YYYY-MM-DD). */
export function shiftIsoDate(iso: string, days: number): string {
  const parts = iso.split('-')
  if (parts.length !== 3) return iso
  const y = Number(parts[0])
  const m = Number(parts[1])
  const d = Number(parts[2])
  if (Number.isNaN(y) || Number.isNaN(m) || Number.isNaN(d)) return iso
  const date = new Date(Date.UTC(y, m - 1, d))
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

export interface RangeBounds {
  readonly first: string
  readonly last: string
}

/** Shifts the window one calendar day, clamped to the ticker's coverage. */
export function shiftRange(range: Range, direction: -1 | 1, bounds: RangeBounds | null): Range {
  if (range === null || bounds === null) return range
  const start = shiftIsoDate(range.start, direction)
  const end = shiftIsoDate(range.end, direction)
  if (start < bounds.first) return range
  if (end > bounds.last) return range
  return { start, end }
}

/** "01 Sep 26" — the reference app's range-chip style. */
export function formatSessionDate(iso: string): string {
  const [y, m, d] = iso.split('-')
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const mi = Number(m) - 1
  if (!y || Number.isNaN(mi) || !months[mi]) return iso
  return `${d} ${months[mi]} ${y.slice(2)}`
}

/** Net flow as a share of two-sided value, clamped to [-1, 1]. Drives the
 * Net Dist ↔ Net Acc marker: 0 = centre, +1 = full accumulation. */
export function netShare(buyValue: number, sellValue: number): number {
  const total = buyValue + sellValue
  if (total <= 0) return 0
  return Math.max(-1, Math.min(1, (buyValue - sellValue) / total))
}

export function markerPct(share: number): number {
  return 50 + share * 50
}

export function netStateLabel(side: 'accumulation' | 'distribution' | 'neutral'): string {
  if (side === 'accumulation') return 'Net Accumulation'
  if (side === 'distribution') return 'Net Distribution'
  return 'Neutral'
}

export function formatSignedIdr(value: number): string {
  if (value > 0) return `+${formatIdrCompact(value)}`
  if (value < 0) return `-${formatIdrCompact(-value)}`
  return formatIdrCompact(0)
}

/** Tooltip line for one bar: "2026-09-01 09:00" → "01 Sep 26 09:00". */
export function formatTooltipTime(time: string): string {
  const [date, hhmm] = time.split(' ')
  if (!date) return time
  return `${formatSessionDate(date)}${hhmm ? ` ${hhmm}` : ''}`
}

export interface TradeFlowViewModel {
  readonly range: Range
  readonly setRange: (range: Range) => void
  readonly bounds: RangeBounds | null
  readonly canGoPrev: boolean
  readonly canGoNext: boolean
  readonly goPrev: () => void
  readonly goNext: () => void
  readonly flow: ReturnType<typeof useTradeFlowData>['flow']
  readonly isPending: boolean
  readonly errorState: ReturnType<typeof useTradeFlowData>['errorState']
  readonly refresh: () => void
}

export function useTradeFlowViewModel(symbol: string): TradeFlowViewModel {
  const [range, setRange] = useState<Range>(null)
  const data = useTradeFlowData(symbol, range ?? {})

  const bounds = useMemo<RangeBounds | null>(() => {
    if (!data.flow) return null
    return {
      first: data.flow.coverage.first_available_session,
      last: data.flow.coverage.last_available_session,
    }
  }, [data.flow])

  const goPrev = () => setRange((r) => shiftRange(r ?? currentRangeOf(data.flow), -1, bounds))
  const goNext = () => setRange((r) => shiftRange(r ?? currentRangeOf(data.flow), 1, bounds))

  return {
    range,
    setRange,
    bounds,
    canGoPrev: range === null || bounds === null || range.start > bounds.first,
    canGoNext: range === null || bounds === null || range.end < bounds.last,
    goPrev,
    goNext,
    flow: data.flow,
    isPending: data.isPending,
    errorState: data.errorState,
    refresh: data.refresh,
  }
}

/** The range the backend actually served for the current (possibly default)
 * request — used as the base when the user first presses < or >. */
function currentRangeOf(flow: ReturnType<typeof useTradeFlowData>['flow']): Range {
  if (!flow) return null
  return { start: flow.requested.start, end: flow.requested.end }
}
