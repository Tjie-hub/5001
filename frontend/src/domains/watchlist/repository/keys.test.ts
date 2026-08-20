import { describe, expect, it } from 'vitest'
import { watchlistKeys } from './keys'

describe('watchlistKeys — ADR-003 §6', () => {
  it('scopes every key under the watchlist domain prefix', () => {
    expect(watchlistKeys.current('eod')[0]).toBe('watchlist')
    expect(watchlistKeys.history('eod')[0]).toBe('watchlist')
    expect(watchlistKeys.byDate('eod', '2026-08-19')[0]).toBe('watchlist')
    expect(watchlistKeys.diff('eod', '2026-08-19')[0]).toBe('watchlist')
    expect(watchlistKeys.persistent('active')[0]).toBe('watchlist')
  })

  it('produces distinct keys per strategy (no cross-strategy cache collision)', () => {
    expect(watchlistKeys.current('eod')).not.toEqual(watchlistKeys.current('premarket'))
  })

  it('places the date as the resource identifier for byDate and diff', () => {
    expect(watchlistKeys.byDate('eod', '2026-08-19')).toEqual([
      'watchlist',
      'byDate',
      '2026-08-19',
      { strategy: 'eod' },
    ])
    expect(watchlistKeys.diff('eod', '2026-08-19')).toEqual([
      'watchlist',
      'diff',
      '2026-08-19',
      { strategy: 'eod' },
    ])
  })

  it('is stable for repeated calls with the same arguments (referential key equality by value)', () => {
    expect(watchlistKeys.current('eod')).toEqual(watchlistKeys.current('eod'))
  })
})
