import { afterEach, describe, expect, it, vi } from 'vitest'
import { searchInstruments } from './search'

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

describe('search API wrapper', () => {
  it('searchInstruments hits /api/v1/search/instruments with q and default limit', async () => {
    const fetchMock = stubFetch({
      query: 'BB',
      results: [{ ticker: 'BBCA', in_idx30: true, in_lq45: true, in_idx80: true }],
      count: 1,
    })

    const result = await searchInstruments('BB')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/search/instruments?q=BB&limit=20',
      expect.anything(),
    )
    expect(result.count).toBe(1)
    expect(result.results[0]?.ticker).toBe('BBCA')
  })

  it('forwards an explicit limit', async () => {
    const fetchMock = stubFetch({ query: 'B', results: [], count: 0 })

    await searchInstruments('B', 5)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/search/instruments?q=B&limit=5',
      expect.anything(),
    )
  })
})
