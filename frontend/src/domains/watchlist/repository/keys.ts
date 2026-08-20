/**
 * Watchlist query-key factory — ADR-003 §6. Colocated with the Repository
 * (S-3): every key used by domains/watchlist/repository/queries.ts is
 * produced here, never written inline (N-15).
 *
 * Canonical shape: [domain, readModel, resourceIdentifier?, params?].
 * Domain is always 'watchlist' (§6.1 position 1), matching the Domain
 * Model name and making domain-scoped cache invalidation a prefix match.
 *
 * `date` positions are the resourceIdentifier (position 3) only when they
 * come from a real navigable resource; here the "resource" a user is
 * viewing is the selected watchlist date, held as Page State in
 * watchlist-page.tsx (not Resource State/URL — see the adapter docstring
 * for why: the frozen route is flat "/watchlist", no date segment).
 */

export const watchlistKeys = {
  all: ['watchlist'] as const,

  current: (strategy: string) => ['watchlist', 'current', null, { strategy }] as const,

  history: (strategy: string) => ['watchlist', 'history', null, { strategy }] as const,

  byDate: (strategy: string, date: string) =>
    ['watchlist', 'byDate', date, { strategy }] as const,

  diff: (strategy: string, date: string) => ['watchlist', 'diff', date, { strategy }] as const,

  persistent: (status: 'active' | 'removed' | 'all') =>
    ['watchlist', 'persistent', null, { status }] as const,
}
