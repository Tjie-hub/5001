/**
 * Search query-key factory — ADR-003 §6. Colocated with the Repository
 * (S-3): every key used by domains/search/repository/queries.ts is
 * produced here, never written inline (N-15).
 *
 * Canonical shape: [domain, readModel, resourceIdentifier?, params?]. The
 * query string is the resourceIdentifier — each distinct query is its own
 * cache entry (retyping an earlier query re-hits the cache instead of the
 * network, a natural fit for TanStack Query, not special-cased here).
 */

export const searchKeys = {
  all: ['search'] as const,

  instruments: (query: string) => ['search', 'instruments', query] as const,
}
