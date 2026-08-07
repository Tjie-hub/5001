/**
 * URL normalization contract — Phase 9 Workstream B (B7).
 *
 * Authority:
 *   Phase 4 P4-13 §12  "Only one canonical representation is permitted"
 *   Phase 4 RM-01/RU-01 exactly one canonical URL per resource
 *   Phase 4 P4-06 §13  normalization uses history REPLACE, never PUSH
 *   Phase 4 §6         symbol format is uppercase
 */
import { describe, expect, it } from 'vitest'
import { normalizePathname } from './url-normalization'

describe('Phase 4 P4-13 §12 — symbol casing', () => {
  it('uppercases a lowercase ticker symbol', () => {
    expect(normalizePathname('/ticker/bbca')).toBe('/ticker/BBCA')
  })

  it('uppercases a mixed-case ticker symbol', () => {
    expect(normalizePathname('/ticker/BbCa')).toBe('/ticker/BBCA')
  })

  it('leaves an already-canonical symbol unchanged', () => {
    expect(normalizePathname('/ticker/BBCA')).toBeNull()
  })
})

describe('Phase 4 P4-13 §12 — trailing slash', () => {
  it('strips a trailing slash from a resource route', () => {
    expect(normalizePathname('/ticker/BBCA/')).toBe('/ticker/BBCA')
  })

  it('strips a trailing slash from a workspace route', () => {
    expect(normalizePathname('/portfolio/')).toBe('/portfolio')
  })

  it('preserves the root route', () => {
    expect(normalizePathname('/')).toBeNull()
  })
})

describe('combined normalization', () => {
  it('applies casing and slash stripping together', () => {
    expect(normalizePathname('/ticker/bbca/')).toBe('/ticker/BBCA')
  })
})

describe('non-resource routes are left alone', () => {
  it.each(['/', '/decision', '/portfolio', '/watchlist', '/market', '/search', '/settings'])(
    'leaves %s unchanged',
    (path) => {
      expect(normalizePathname(path)).toBeNull()
    },
  )

  it('does not uppercase segments outside the symbol position', () => {
    expect(normalizePathname('/market')).toBeNull()
  })

  it('leaves an unknown route unchanged so the router can 404 it', () => {
    expect(normalizePathname('/foo/bar')).toBeNull()
  })
})
