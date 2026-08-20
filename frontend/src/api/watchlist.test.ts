import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  getCurrentWatchlist,
  getPersistentWatchlist,
  getWatchlistByDate,
  getWatchlistDiff,
  getWatchlistHistory,
} from './watchlist'

function stubFetch(data: unknown) {
  const fetchMock = vi.fn().mockResolvedValue({
    status: 200,
    json: () =>
      Promise.resolve({
        ok: true,
        data,
        meta: { api_version: 'v1', request_id: 'r', timestamp: 't' },
      }),
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('watchlist API wrapper', () => {
  it('getCurrentWatchlist hits /api/v1/watchlists/current with default strategy=eod', async () => {
    const fetchMock = stubFetch({ strategy: 'eod', date: '2026-08-19', watchlist: [] })

    await getCurrentWatchlist()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/watchlists/current?strategy=eod',
      expect.anything(),
    )
  })

  it('getCurrentWatchlist passes an explicit strategy through', async () => {
    const fetchMock = stubFetch({ strategy: 'premarket', date: '2026-08-19', watchlist: [] })

    await getCurrentWatchlist('premarket')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/watchlists/current?strategy=premarket',
      expect.anything(),
    )
  })

  it('getWatchlistHistory hits /api/v1/watchlists/history', async () => {
    const fetchMock = stubFetch({ strategy: 'eod', dates: ['2026-08-19'], count: 1 })

    await getWatchlistHistory()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/watchlists/history?strategy=eod',
      expect.anything(),
    )
  })

  it('getWatchlistByDate hits /api/v1/watchlists/<date> with strategy', async () => {
    const fetchMock = stubFetch({ strategy: 'eod', date: '2026-08-18', watchlist: [] })

    await getWatchlistByDate('2026-08-18')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/watchlists/2026-08-18?strategy=eod',
      expect.anything(),
    )
  })

  it('getWatchlistDiff hits /api/v1/watchlists/diff with strategy and date', async () => {
    const fetchMock = stubFetch({ strategy: 'eod', date: '2026-08-19', diff: null })

    await getWatchlistDiff('2026-08-19')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/watchlists/diff?strategy=eod&date=2026-08-19',
      expect.anything(),
    )
  })

  it('getPersistentWatchlist defaults to status=active', async () => {
    const fetchMock = stubFetch({ status: 'active', watchlist: [], count: 0 })

    await getPersistentWatchlist()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/watchlists/persistent?status=active',
      expect.anything(),
    )
  })

  it('getPersistentWatchlist passes an explicit status through', async () => {
    const fetchMock = stubFetch({ status: 'all', watchlist: [], count: 0 })

    await getPersistentWatchlist('all')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/watchlists/persistent?status=all',
      expect.anything(),
    )
  })
})
