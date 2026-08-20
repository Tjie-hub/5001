import { describe, expect, it } from 'vitest'
import { createQueryClient, queryRetryPredicate } from './query-client'
import { ApiRequestError } from '@api/client'

describe('queryRetryPredicate — ADR-003 §10.1', () => {
  it('retries a network failure (status 0) up to 3 attempts', () => {
    const err = new ApiRequestError('NETWORK_ERROR', 0, 'network request failed', {})
    expect(queryRetryPredicate(0, err)).toBe(true)
    expect(queryRetryPredicate(2, err)).toBe(true)
    expect(queryRetryPredicate(3, err)).toBe(false)
  })

  it('retries 5xx responses', () => {
    const err = new ApiRequestError('API_ERROR', 503, 'service unavailable', {})
    expect(queryRetryPredicate(0, err)).toBe(true)
    expect(queryRetryPredicate(3, err)).toBe(false)
  })

  it('retries 429 up to only 2 attempts', () => {
    const err = new ApiRequestError('RATE_LIMITED', 429, 'rate limited', {})
    expect(queryRetryPredicate(0, err)).toBe(true)
    expect(queryRetryPredicate(1, err)).toBe(true)
    expect(queryRetryPredicate(2, err)).toBe(false)
  })

  it('never retries deterministic client errors (400/401/403/404)', () => {
    for (const status of [400, 401, 403, 404]) {
      const err = new ApiRequestError('CLIENT_ERROR', status, 'client error', {})
      expect(queryRetryPredicate(0, err)).toBe(false)
    }
  })

  it('does not retry a non-ApiRequestError', () => {
    expect(queryRetryPredicate(0, new Error('unexpected'))).toBe(false)
  })
})

describe('createQueryClient', () => {
  it('configures mutations to never retry (S-8/N-9)', () => {
    const client = createQueryClient()
    expect(client.getDefaultOptions().mutations?.retry).toBe(false)
  })

  it('uses the retry predicate for queries', () => {
    const client = createQueryClient()
    expect(client.getDefaultOptions().queries?.retry).toBe(queryRetryPredicate)
  })
})
