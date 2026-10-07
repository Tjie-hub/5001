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
 * Consolidation 2026-09-03: 'intelligence' joined the registry — the
 * user-directed Investment Intelligence workspace that absorbed the external
 * Investment Dashboard (ex-port 5003); the frozen-seven assertions became
 * eight.
 *
 * Frontend freeze 2026-10-06 (owner-directed): the 5001 frontend is frozen;
 * 'portfolio', 'intelligence' and 'watchlist' were REMOVED from the registry
 * because they duplicate or mis-state the jurnal26 ledger (port 5004). The
 * assertions below went from eight workspaces to five as part of that change.
 * Their routes stay registered as frozen-workspace banner pages (see
 * app-router.tsx); only the workspace set shrinks. See
 * docs/INTEGRATION_CONSOLIDATION_MAP_2026-10-06.md.
 */
import { describe, expect, it } from 'vitest'
import { ROUTE_PATHS, WORKSPACES, WORKSPACE_GROUPS } from './workspaces'

describe('Phase 4 P4-02 §3 — flat workspaces (five, after the 2026-10-06 freeze)', () => {
  it('registers exactly five workspaces', () => {
    expect(WORKSPACES).toHaveLength(5)
  })

  it('registers exactly the post-freeze set', () => {
    expect(WORKSPACES.map((w) => w.id).sort()).toEqual([
      'decision',
      'market',
      'search',
      'settings',
      'ticker',
    ])
  })

  it('no longer registers the three frozen workspaces', () => {
    const ids = WORKSPACES.map((w) => w.id)
    for (const retired of ['portfolio', 'intelligence', 'watchlist']) {
      expect(ids).not.toContain(retired)
    }
  })

  it('gives every workspace exactly one responsibility (NP-01)', () => {
    const responsibilities = WORKSPACES.map((w) => w.responsibility)

    expect(responsibilities).toEqual([
      'Decide',
      'Investigate',
      'Understand',
      'Discover',
      'Configure',
    ])
    expect(new Set(responsibilities).size).toBe(5)
  })
})

describe('Phase 4 P4-03 §4 — frozen sidebar order', () => {
  it('orders navigation exactly as frozen', () => {
    expect(WORKSPACES.map((w) => w.label)).toEqual([
      'Decision Center',
      'Ticker',
      'Market',
      'Search',
      'Settings',
    ])
  })

  it('groups the sidebar with the two frozen separators', () => {
    expect(WORKSPACE_GROUPS.map((g) => g.map((w) => w.id))).toEqual([
      ['decision'],
      ['ticker', 'market', 'search'],
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
    for (const workspace of WORKSPACES) {
      expect(Object.values(ROUTE_PATHS)).toContain(workspace.navPath)
    }
  })

  it('keeps the frozen workspaces’ retirement paths registered', () => {
    // The workspace entries are gone, but the old paths must still resolve —
    // to the frozen-workspace banner page (app-router.tsx), never a 404.
    expect(ROUTE_PATHS.portfolio).toBe('/portfolio')
    expect(ROUTE_PATHS.intelligence).toBe('/intelligence')
    expect(ROUTE_PATHS.watchlist).toBe('/watchlist')
  })

  it('never assigns two workspaces the same route', () => {
    const navPaths = WORKSPACES.map((w) => w.navPath)

    expect(new Set(navPaths).size).toBe(navPaths.length)
  })
})
