import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiGet, ApiRequestError } from './client'

function mockFetchOnce(body: unknown, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      status,
      json: () => Promise.resolve(body),
    }),
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('apiGet', () => {
  it('unwraps a successful envelope', async () => {
    mockFetchOnce({
      ok: true,
      data: { hello: 'world' },
      meta: { api_version: 'v1', request_id: 'abc', timestamp: '2026-08-18T00:00:00Z' },
    })

    const result = await apiGet<{ hello: string }>('/api/v1/example')
    expect(result).toEqual({ hello: 'world' })
  })

  it('appends defined query params and omits undefined ones', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      status: 200,
      json: () =>
        Promise.resolve({
          ok: true,
          data: {},
          meta: { api_version: 'v1', request_id: 'abc', timestamp: 't' },
        }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await apiGet('/api/v1/example', { limit: 5, job_name: undefined })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/example?limit=5',
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('throws ApiRequestError with the envelope error on ok:false', async () => {
    mockFetchOnce(
      {
        ok: false,
        error: { code: 'JOB_NOT_FOUND', message: 'no such job', details: {} },
        meta: { api_version: 'v1', request_id: 'abc', timestamp: 't' },
      },
      404,
    )

    await expect(apiGet('/api/v1/example')).rejects.toMatchObject({
      code: 'JOB_NOT_FOUND',
      status: 404,
      message: 'no such job',
    })
    await expect(apiGet('/api/v1/example')).rejects.toBeInstanceOf(ApiRequestError)
  })

  it('throws ApiRequestError on a network failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network down')))

    await expect(apiGet('/api/v1/example')).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
  })

  it('throws ApiRequestError on a non-JSON response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        status: 500,
        json: () => Promise.reject(new Error('not json')),
      }),
    )

    await expect(apiGet('/api/v1/example')).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
  })
})
