/**
 * Workspace registry contract — Phase 9 Workstream B.
 *
 * The registry is the single source of truth for which workspaces exist, what
 * they are called, and in what order they appear in Global Navigation. Both
 * the router (B2) and the sidebar (B3) read from it, so drift between routes
 * and navigation is structurally impossible.
 *
 * Authority:
 *   Phase 4 P4-02 §3   seven workspaces, flat, no nesting
 *   Phase 4 P4-03 §4   frozen sidebar order and separators
 *   Phase 4 Appendix B route registry
 *   Phase 4 NP-01      one responsibility per workspace
 */
import { describe, expect, it } from 'vitest'
import { ROUTE_PATHS, WORKSPACES, WORKSPACE_GROUPS } from './workspaces'

describe('Phase 4 P4-02 §3 — the seven frozen workspaces', () => {
  it('registers exactly seven workspaces', () => {
    expect(WORKSPACES).toHaveLength(7)
  })

  it('registers exactly the frozen set', () => {
    expect(WORKSPACES.map((w) => w.id).sort()).toEqual([
      'decision',
      'market',
      'portfolio',
      'search',
      'settings',
      'ticker',
      'watchlist',
    ])
  })

  it('gives every workspace exactly one responsibility (NP-01)', () => {
    const responsibilities = WORKSPACES.map((w) => w.responsibility)

    expect(responsibilities).toEqual([
      'Decide',
      'Evaluate',
      'Observe',
      'Investigate',
      'Understand',
      'Discover',
      'Configure',
    ])
    expect(new Set(responsibilities).size).toBe(7)
  })
})

describe('Phase 4 P4-03 §4 — frozen sidebar order', () => {
  it('orders navigation exactly as frozen', () => {
    expect(WORKSPACES.map((w) => w.label)).toEqual([
      'Decision Center',
      'Portfolio',
      'Watchlist',
      'Ticker',
      'Market',
      'Search',
      'Settings',
    ])
  })

  it('groups the sidebar with the two frozen separators', () => {
    expect(WORKSPACE_GROUPS.map((g) => g.map((w) => w.id))).toEqual([
      ['decision', 'portfolio'],
      ['watchlist', 'ticker', 'market', 'search'],
      ['settings'],
    ])
  })

  it('reaches every workspace directly from global navigation (NP-03)', () => {
    for (const workspace of WORKSPACES) {
      expect(workspace.navPath, `${workspace.id} must be directly reachable`).toMatch(/^\/[a-z]+$/)
    }
  })
})

describe('Phase 4 Appendix B — canonical routes', () => {
  it('assigns each workspace one canonical route', () => {
    expect(ROUTE_PATHS).toMatchObject({
      home: '/',
      decision: '/decision',
      portfolio: '/portfolio',
      watchlist: '/watchlist',
      ticker: '/ticker',
      tickerSymbol: '/ticker/:symbol',
      market: '/market',
      search: '/search',
      settings: '/settings',
    })
  })

  it('never assigns two workspaces the same route', () => {
    const navPaths = WORKSPACES.map((w) => w.navPath)

    expect(new Set(navPaths).size).toBe(navPaths.length)
  })
})
