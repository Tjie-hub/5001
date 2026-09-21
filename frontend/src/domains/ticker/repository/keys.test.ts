/**
 * Keys test — mirrors domains/market/repository/keys.test.ts: the key
 * factory is frozen architecture surface, so its shapes are pinned.
 */
import { describe, expect, it } from 'vitest'
import { platformKeys, tickerKeys } from './keys'

describe('tickerKeys', () => {
  it('namespaces detail under [ticker, detail, symbol]', () => {
    expect(tickerKeys.detail('BBCA')).toEqual(['ticker', 'detail', 'BBCA'])
  })

  it('keeps the domain prefix invalidatable via all', () => {
    expect(tickerKeys.all).toEqual(['ticker'])
  })
})

describe('platformKeys', () => {
  it('namespaces runtime status under [platform, runtime-status]', () => {
    expect(platformKeys.runtimeStatus()).toEqual(['platform', 'runtime-status'])
  })
})
