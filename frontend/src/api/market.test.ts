import { afterEach, describe, expect, it, vi } from 'vitest'
import { getMarketSummary } from './market'

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

describe('market API wrapper', () => {
  it('getMarketSummary hits /api/v1/market/summary with no params by default', async () => {
    const fetchMock = stubFetch({
      date: '2026-08-20',
      risk_score: 14.0,
      tier: 'GREEN',
      components: { vpin: 0, accdist: 40, breadth: 0, technicals: 0, foreign_flow: 40 },
      ihsg: {
        close: 7250.5, ma5: 7230.1, ma20: 7190.4, death_cross: false,
        lower_high: false, support_breaks: [], ytd_pct: 3.2,
      },
      breadth: {
        date: '2026-08-20', advancers: 210, decliners: 150, unchanged: 30,
        adv_dec_ratio: 1.4, pct_advancing: 52.5, pct_above_ma20: 61.0,
        label: 'BULL_MARKET',
      },
      foreign_flow: { today: 1.2e9, net_5d: 5.3e9, net_20d: -2.1e9, trend: 'INFLOW' },
      vpin: { avg_vpin: 0.31, pct_above_08: 0, pct_above_095: 0, label: 'GREEN' },
      accdist: {
        date: '2026-08-20', total: 390, dist_count: 80, acc_count: 160,
        neutral_count: 150, dist_pct: 20.5, acc_pct: 41.0, avg_numeric_score: 0.4,
        label: 'NEUTRAL',
      },
    })

    const result = await getMarketSummary()

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/market/summary', expect.anything())
    expect(result.tier).toBe('GREEN')
    expect(result.breadth.label).toBe('BULL_MARKET')
  })

  it('getMarketSummary forwards an explicit date as a query param', async () => {
    const fetchMock = stubFetch({
      date: '2026-07-01',
      risk_score: 0,
      tier: 'GREEN',
      components: { vpin: 0, accdist: 0, breadth: 0, technicals: 0, foreign_flow: 0 },
      ihsg: {
        close: null, ma5: null, ma20: null, death_cross: false,
        lower_high: false, support_breaks: [], ytd_pct: null,
      },
      breadth: {
        date: '2026-07-01', advancers: 0, decliners: 0, unchanged: 0,
        adv_dec_ratio: 0, pct_advancing: 0, pct_above_ma20: 0,
        label: 'INSUFFICIENT_DATA',
      },
      foreign_flow: { today: null, net_5d: null, net_20d: null, trend: 'NEUTRAL' },
      vpin: { avg_vpin: 0, pct_above_08: 0, pct_above_095: 0, label: 'INSUFFICIENT_DATA' },
      accdist: {
        date: '2026-07-01', total: 0, dist_count: 0, acc_count: 0,
        neutral_count: 0, dist_pct: 0, acc_pct: 0, avg_numeric_score: 0,
        label: 'NEUTRAL',
      },
    })

    await getMarketSummary('2026-07-01')

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/market/summary?date=2026-07-01', expect.anything())
  })
})
