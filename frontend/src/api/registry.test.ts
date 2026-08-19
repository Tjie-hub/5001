import { afterEach, describe, expect, it, vi } from 'vitest'
import { getRegistryStatus } from './registry'

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

describe('registry API wrapper', () => {
  it('getRegistryStatus hits /api/v1/registry/status', async () => {
    const fetchMock = stubFetch({
      hash: 'abc1234',
      approved: 0,
      shadow: 1,
      entries: [
        { id: 'NR7_BULL', version: 2, status: 'SHADOW', strategy_fn: 'NR7 Breakout',
          regimes: ['BULL_MODERATE', 'BULL_STRONG'] },
      ],
      skipped_count: 0,
      debt_count: 1,
      violation_count: 0,
    })

    const result = await getRegistryStatus()

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/registry/status', expect.anything())
    expect(result.approved).toBe(0)
    expect(result.shadow).toBe(1)
    expect(result.entries[0]?.id).toBe('NR7_BULL')
  })
})
