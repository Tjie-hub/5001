import { describe, expect, it } from 'vitest'
import { marketKeys } from './keys'

describe('marketKeys — ADR-003 §6', () => {
  it('scopes every key under the market domain prefix', () => {
    expect(marketKeys.all[0]).toBe('market')
    expect(marketKeys.summary('2026-08-20')[0]).toBe('market')
  })

  it('produces distinct keys per date (no cross-date cache collision)', () => {
    expect(marketKeys.summary('2026-08-20')).not.toEqual(marketKeys.summary('2026-08-19'))
  })

  it('produces distinct keys for null (latest) vs an explicit date', () => {
    expect(marketKeys.summary(null)).not.toEqual(marketKeys.summary('2026-08-20'))
  })

  it('is stable for repeated calls with the same arguments', () => {
    expect(marketKeys.summary('2026-08-20')).toEqual(marketKeys.summary('2026-08-20'))
  })
})
