/**
 * Workspace registry — Phase 9 Workstream B (B2, B3).
 *
 * Single source of truth for the seven frozen workspaces. The router and the
 * sidebar both read from here, so navigation and routing cannot drift apart.
 *
 * Authority:
 *   Phase 4 P4-02 §3   seven workspaces, flat, no nesting, no subordination
 *   Phase 4 P4-02 §4   mutually exclusive responsibilities
 *   Phase 4 P4-03 §4   frozen sidebar order and separator placement
 *   Phase 4 Appendix B canonical route registry
 *   Phase 4 NP-01      one responsibility per workspace
 *   Phase 4 NP-03      every workspace directly reachable from global nav
 *
 * This file is frozen architecture expressed as data. Adding a workspace
 * requires an ADR (Phase 4 P4-16 §14) — not an edit here.
 */

/** Canonical route paths (Phase 4 Appendix B). */
export const ROUTE_PATHS = {
  home: '/',
  decision: '/decision',
  portfolio: '/portfolio',
  watchlist: '/watchlist',
  ticker: '/ticker',
  tickerSymbol: '/ticker/:symbol',
  market: '/market',
  search: '/search',
  settings: '/settings',
} as const

export type WorkspaceId =
  'decision' | 'portfolio' | 'watchlist' | 'ticker' | 'market' | 'search' | 'settings'

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
    id: 'portfolio',
    label: 'Portfolio',
    responsibility: 'Evaluate',
    navPath: ROUTE_PATHS.portfolio,
    purpose: 'Assess portfolio quality, risk exposure, allocation and capacity.',
  },
  {
    id: 'watchlist',
    label: 'Watchlist',
    responsibility: 'Observe',
    navPath: ROUTE_PATHS.watchlist,
    purpose: 'Track candidate evolution ahead of investigation or decision.',
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
 *   Portfolio
 *   ────────────────
 *   Watchlist
 *   Ticker
 *   Market
 *   Search
 *   ────────────────
 *   Settings
 *
 * The separators are visual grouping only. They introduce no hierarchy —
 * P4-02 §3 keeps all seven workspaces at the same level.
 */
export const WORKSPACE_GROUPS: readonly (readonly Workspace[])[] = [
  [getWorkspace('decision'), getWorkspace('portfolio')],
  [
    getWorkspace('watchlist'),
    getWorkspace('ticker'),
    getWorkspace('market'),
    getWorkspace('search'),
  ],
  [getWorkspace('settings')],
] as const
