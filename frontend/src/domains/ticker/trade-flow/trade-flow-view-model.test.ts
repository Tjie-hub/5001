import { describe, expect, it } from 'vitest'
import {
  formatSessionDate,
  formatSignedIdr,
  formatTooltipTime,
  markerPct,
  netShare,
  netStateLabel,
  shiftIsoDate,
  shiftRange,
} from './trade-flow-view-model'

describe('shiftIsoDate', () => {
  it('shifts across month boundaries without timezone drift', () => {
    expect(shiftIsoDate('2026-09-01', -1)).toBe('2026-08-31')
    expect(shiftIsoDate('2026-08-31', 1)).toBe('2026-09-01')
    expect(shiftIsoDate('2026-09-03', -1)).toBe('2026-09-02')
  })
})

describe('shiftRange', () => {
  const bounds = { first: '2026-08-31', last: '2026-09-02' }
  it('steps forward and back inside coverage; edges are no-ops', () => {
    const range = { start: '2026-09-01', end: '2026-09-02' }
    expect(shiftRange(range, -1, bounds)).toEqual({ start: '2026-08-31', end: '2026-09-01' })
    const leftEdge = { start: '2026-08-31', end: '2026-08-31' }
    expect(shiftRange(leftEdge, -1, bounds)).toEqual(leftEdge)
  })
  it('refuses to step past either edge', () => {
    const leftEdge = { start: '2026-08-31', end: '2026-09-01' }
    expect(shiftRange(leftEdge, -1, bounds)).toEqual(leftEdge)
    const rightEdge = { start: '2026-09-01', end: '2026-09-02' }
    expect(shiftRange(rightEdge, 1, bounds)).toEqual(rightEdge)
  })
})

describe('date labels', () => {
  it('formats the range chip like the reference', () => {
    expect(formatSessionDate('2026-09-03')).toBe('03 Sep 26')
    expect(formatSessionDate('garbage')).toBe('garbage')
  })
  it('formats tooltip timestamps', () => {
    expect(formatTooltipTime('2026-09-01 09:00')).toBe('01 Sep 26 09:00')
  })
})

describe('net share / marker', () => {
  it('maps net flow share to the Dist↔Acc scale', () => {
    expect(netShare(0, 0)).toBe(0)
    expect(netShare(3e9, 1e9)).toBeCloseTo(0.5)
    expect(netShare(1e9, 3e9)).toBeCloseTo(-0.5)
    expect(markerPct(0.5)).toBe(75)
    expect(markerPct(-0.5)).toBe(25)
  })
  it('clamps to the bar edges', () => {
    expect(netShare(1e12, 1)).toBeCloseTo(1, 9)
    expect(markerPct(1)).toBe(100)
    expect(markerPct(-1)).toBe(0)
  })
  it('labels the side', () => {
    expect(netStateLabel('accumulation')).toBe('Net Accumulation')
    expect(netStateLabel('distribution')).toBe('Net Distribution')
    expect(netStateLabel('neutral')).toBe('Neutral')
  })
})

describe('formatSignedIdr', () => {
  it('signs non-zero flows and never double-signs', () => {
    expect(formatSignedIdr(1.2e9)).toBe('+Rp1.2B')
    expect(formatSignedIdr(-7.2e9)).toBe('-Rp7.2B')
    expect(formatSignedIdr(0)).toBe('Rp0')
  })
})
