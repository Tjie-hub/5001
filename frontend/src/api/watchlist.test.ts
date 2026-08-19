import { afterEach, describe, expect, it, vi } from 'vitest'
import { getCurrentWatchlist } from './watchlist'

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
})
