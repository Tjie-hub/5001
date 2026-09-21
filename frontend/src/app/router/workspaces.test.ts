/**
 * Workspace registry contract — Phase 9 Workstream B.
 *
 * The registry is the single source of truth for which workspaces exist, what
 * they are called, and in what order they appear in Global Navigation. Both
 * the router (B2) and the sidebar (B3) read from it, so drift between routes
 * and navigation is structurally impossible.
 *
 * Authority:
 *   Phase 4 P4-02 §3   flat workspaces, no nesting
 *   Phase 4 P4-03 §4   frozen sidebar order and separators
 *   Phase 4 Appendix B route registry
 *   Phase 4 NP-01      one responsibility per workspace
 *
 * Consolidation 2026-09-03: 'intelligence' joins the registry — the
 * user-directed Investment Intelligence workspace that absorbed the external
 * Investment Dashboard (ex-port 5003). See
 * docs/INTEGRATION_CONSOLIDATION_MAP_2026-09-03.md; the frozen-seven
 * assertions below were updated to eight as part of that change.
 */
import { describe, expect, it } from 'vitest'
import { ROUTE_PATHS, WORKSPACES, WORKSPACE_GROUPS } from './workspaces'

describe('Phase 4 P4-02 §3 — flat workspaces (seven frozen + consolidation)', () => {
  it('registers exactly eight workspaces', () => {
    expect(WORKSPACES).toHaveLength(8)
  })

  it('registers exactly the frozen set plus intelligence', () => {
    expect(WORKSPACES.map((w) => w.id).sort()).toEqual([
      'decision',
      'intelligence',
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
      'Synthesize',
      'Observe',
      'Investigate',
      'Understand',
      'Discover',
      'Configure',
    ])
    expect(new Set(responsibilities).size).toBe(8)
  })
})

describe('Phase 4 P4-03 §4 — frozen sidebar order', () => {
  it('orders navigation exactly as frozen', () => {
    expect(WORKSPACES.map((w) => w.label)).toEqual([
      'Decision Center',
      'Portfolio',
      'Investment Intelligence',
      'Watchlist',
      'Ticker',
      'Market',
      'Search',
      'Settings',
    ])
  })

  it('groups the sidebar with the two frozen separators', () => {
    expect(WORKSPACE_GROUPS.map((g) => g.map((w) => w.id))).toEqual([
      ['decision', 'portfolio', 'intelligence'],
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
      intelligence: '/intelligence',
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
