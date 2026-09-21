import { afterEach, describe, expect, it, vi } from 'vitest'
import { getRuntimeStatus, getTickerDetail } from './ticker'

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

describe('ticker API wrapper', () => {
  it('getTickerDetail hits /api/v1/tickers/:symbol with the symbol encoded', async () => {
    const fetchMock = stubFetch({
      symbol: 'BBCA',
      identity: null,
      price: null,
      regime: null,
      production_admission: null,
      signals: null,
      flow: null,
      watchlist_membership: null,
      agent_decisions: null,
      position: null,
      timeline: null,
      market_context: null,
      data_freshness: null,
      as_of: '2026-09-02T10:00:00+07:00',
    })

    const result = await getTickerDetail('BBCA')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/tickers/BBCA',
      expect.anything(),
    )
    expect(result.symbol).toBe('BBCA')
  })

  it('encodes symbols that need URI escaping', async () => {
    const fetchMock = stubFetch({
      symbol: 'B.B-1',
      identity: null, price: null, regime: null, production_admission: null,
      signals: null, flow: null, watchlist_membership: null,
      agent_decisions: null, position: null, timeline: null,
      market_context: null, data_freshness: null, as_of: 't',
    })

    await getTickerDetail('B.B-1')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/tickers/B.B-1',
      expect.anything(),
    )
  })

  it('getRuntimeStatus hits /api/v1/runtime', async () => {
    const fetchMock = stubFetch({
      environment: 'dev',
      release_source: 'working-tree',
      version: 'dev-9b6e380',
      timezone: 'WIB (UTC+7)',
      snapshot: { date: '2026-09-01', strategy: 'eod' },
      freshness: { ohlcv: '2026-09-02', stockbit_flow: '2026-09-01' },
      components: { database: { status: 'healthy' } },
      overall: 'healthy',
    })

    const result = await getRuntimeStatus()

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/runtime', expect.anything())
    expect(result.environment).toBe('dev')
    expect(result.snapshot?.strategy).toBe('eod')
  })
})
