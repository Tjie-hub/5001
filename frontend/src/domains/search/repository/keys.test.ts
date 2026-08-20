import { describe, expect, it } from 'vitest'
import { searchKeys } from './keys'

describe('searchKeys — ADR-003 §6', () => {
  it('scopes every key under the search domain prefix', () => {
    expect(searchKeys.all[0]).toBe('search')
    expect(searchKeys.instruments('BB')[0]).toBe('search')
  })

  it('produces distinct keys per query (no cross-query cache collision)', () => {
    expect(searchKeys.instruments('BB')).not.toEqual(searchKeys.instruments('BC'))
  })

  it('is stable for repeated calls with the same arguments', () => {
    expect(searchKeys.instruments('BB')).toEqual(searchKeys.instruments('BB'))
  })
})
