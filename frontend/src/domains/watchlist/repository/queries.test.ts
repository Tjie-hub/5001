import { describe, expect, it, vi } from 'vitest'
import {
  currentWatchlistOptions,
  persistentWatchlistOptions,
  watchlistByDateOptions,
  watchlistDiffOptions,
  watchlistHistoryOptions,
} from './queries'
import { watchlistKeys } from './keys'

vi.mock('@api/watchlist', () => ({
  getCurrentWatchlist: vi.fn(() => Promise.resolve({ strategy: 'eod', date: 'd', watchlist: [] })),
  getWatchlistHistory: vi.fn(() => Promise.resolve({ strategy: 'eod', dates: [], count: 0 })),
  getWatchlistByDate: vi.fn(() => Promise.resolve({ strategy: 'eod', date: 'd', watchlist: [] })),
  getWatchlistDiff: vi.fn(() => Promise.resolve({ strategy: 'eod', date: 'd', diff: null })),
  getPersistentWatchlist: vi.fn(() => Promise.resolve({ status: 'active', watchlist: [], count: 0 })),
}))

const WATCHLIST_STALE_TIME = 60 * 1000
const WATCHLIST_GC_TIME = 10 * 60 * 1000

describe('Watchlist Repository — ADR-003 §7 cache policy', () => {
  it('currentWatchlistOptions uses the watchlist domain cache policy and key', () => {
    const opts = currentWatchlistOptions('eod')

    expect(opts.queryKey).toEqual(watchlistKeys.current('eod'))
    expect(opts.staleTime).toBe(WATCHLIST_STALE_TIME)
    expect(opts.gcTime).toBe(WATCHLIST_GC_TIME)
    expect(opts.refetchOnWindowFocus).toBe(true)
    expect(opts.refetchOnReconnect).toBe(true)
  })

  it('watchlistHistoryOptions calls the history API through queryFn', async () => {
    const { getWatchlistHistory } = await import('@api/watchlist')
    const opts = watchlistHistoryOptions('eod')

    expect(opts.queryKey).toEqual(watchlistKeys.history('eod'))
    await opts.queryFn?.({} as never)
    expect(getWatchlistHistory).toHaveBeenCalledWith('eod')
  })

  it('watchlistByDateOptions keys and calls by the given date', async () => {
    const { getWatchlistByDate } = await import('@api/watchlist')
    const opts = watchlistByDateOptions('eod', '2026-08-18')

    expect(opts.queryKey).toEqual(watchlistKeys.byDate('eod', '2026-08-18'))
    await opts.queryFn?.({} as never)
    expect(getWatchlistByDate).toHaveBeenCalledWith('2026-08-18', 'eod')
  })

  it('watchlistDiffOptions keys and calls by the given date', async () => {
    const { getWatchlistDiff } = await import('@api/watchlist')
    const opts = watchlistDiffOptions('eod', '2026-08-19')

    expect(opts.queryKey).toEqual(watchlistKeys.diff('eod', '2026-08-19'))
    await opts.queryFn?.({} as never)
    expect(getWatchlistDiff).toHaveBeenCalledWith('2026-08-19', 'eod')
  })

  it('persistentWatchlistOptions defaults to status=active', () => {
    const opts = persistentWatchlistOptions()

    expect(opts.queryKey).toEqual(watchlistKeys.persistent('active'))
  })
})
