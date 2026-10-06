/**
 * Workspace registry — Phase 9 Workstream B (B2, B3).
 *
 * Single source of truth for which workspaces exist, what they are called, and
 * in what order they appear in Global Navigation. Both the router (B2) and the
 * sidebar (B3) read from here, so navigation and routing cannot drift apart.
 *
 * Authority:
 *   Phase 4 P4-02 §3   flat workspaces, no nesting, no subordination
 *   Phase 4 P4-02 §4   mutually exclusive responsibilities
 *   Phase 4 P4-03 §4   frozen sidebar order and separator placement
 *   Phase 4 Appendix B canonical route registry
 *   Phase 4 NP-01      one responsibility per workspace
 *   Phase 4 NP-03      every workspace directly reachable from global nav
 *
 * This file is frozen architecture expressed as data. Adding a workspace
 * requires an ADR (Phase 4 P4-16 §14) — not an edit here. Two dated exceptions
 * to date, both user-directed at the application level:
 *
 *   - 'intelligence' (consolidation 2026-09-03): absorbed the external
 *     Investment Dashboard (ex-port 5003); see its entry comment and
 *     docs/INTEGRATION_CONSOLIDATION_MAP_2026-09-03.md.
 *   - Frontend freeze (owner-directed 2026-10-06): the 5001 frontend is
 *     frozen; the portfolio, intelligence and watchlist workspaces were
 *     removed because they duplicate or mis-state the jurnal26 ledger.
 *     The jurnal26 app (port 5004) is the live investment journal, watchlist
 *     and daily-research surface. The retirement paths ('/portfolio',
 *     '/intelligence', '/watchlist') stay registered — they resolve to the
 *     frozen-workspace banner page so old bookmarks still work. See
 *     docs/INTEGRATION_CONSOLIDATION_MAP_2026-10-06.md.
 */

/** Canonical route paths (Phase 4 Appendix B). */
export const ROUTE_PATHS = {
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
} as const

export type WorkspaceId = 'decision' | 'ticker' | 'market' | 'search' | 'settings'

export interface Workspace {
  readonly id: WorkspaceId
  readonly label: string
  /** The single responsibility this workspace owns (Phase 4 NP-01). */
  readonly responsibility: string
  /** Target for the sidebar link. Must be directly reachable (NP-03). */
  readonly navPath: string
  /** Short description rendered by the workspace shell page. */
  readonly purpose: string
}

/**
 * Ordered exactly as Phase 4 P4-03 §4 freezes the sidebar.
 *
 * The order reflects operational priority, not dependency — Decision Center
 * first because it is the primary operational workspace (UI-001), Settings
 * last because it is configuration rather than analysis.
 *
 * Frontend freeze 2026-10-06: 'portfolio', 'intelligence' and 'watchlist'
 * were removed from this registry (owner-directed; see the header note).
 * Their routes remain registered as frozen-workspace banner pages.
 */
export const WORKSPACES: readonly Workspace[] = [
  {
    id: 'decision',
    label: 'Decision Center',
    responsibility: 'Decide',
    navPath: ROUTE_PATHS.decision,
    purpose: 'Evaluate, prioritise and act on investment recommendations.',
  },
  {
    id: 'ticker',
    label: 'Ticker',
    responsibility: 'Investigate',
    navPath: ROUTE_PATHS.ticker,
    purpose: 'Investigate a single instrument in depth.',
  },
  {
    id: 'market',
    label: 'Market',
    responsibility: 'Understand',
    navPath: ROUTE_PATHS.market,
    purpose: 'Understand the shared market environment used across workspaces.',
  },
  {
    id: 'search',
    label: 'Search',
    responsibility: 'Discover',
    navPath: ROUTE_PATHS.search,
    purpose: 'Locate entities and navigate to the workspace that owns them.',
  },
  {
    id: 'settings',
    label: 'Settings',
    responsibility: 'Configure',
    navPath: ROUTE_PATHS.settings,
    purpose: 'Manage account, security, notifications and preferences.',
  },
] as const

const byId = new Map(WORKSPACES.map((w) => [w.id, w]))

export function getWorkspace(id: WorkspaceId): Workspace {
  const workspace = byId.get(id)
  if (!workspace) {
    throw new Error(`Unknown workspace: ${id}`)
  }
  return workspace
}

/**
 * Sidebar groups, separated exactly as Phase 4 P4-03 §4 draws them:
 *
 *   Decision Center
 *   ────────────────
 *   Ticker
 *   Market
 *   Search
 *   ────────────────
 *   Settings
 *
 * The separators are visual grouping only. They introduce no hierarchy —
 * P4-02 §3 keeps all workspaces at the same level.
 *
 * Frontend freeze 2026-10-06: the first group's Portfolio / Investment
 * Intelligence entries and the second group's Watchlist entry were removed
 * with their workspaces; the group boundaries are otherwise unchanged.
 */
export const WORKSPACE_GROUPS: readonly (readonly Workspace[])[] = [
  [getWorkspace('decision')],
  [getWorkspace('ticker'), getWorkspace('market'), getWorkspace('search')],
  [getWorkspace('settings')],
] as const
