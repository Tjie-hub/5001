/**
 * Market query-key factory — ADR-003 §6. Colocated with the Repository
 * (S-3): every key used by domains/market/repository/queries.ts is
 * produced here, never written inline (N-15).
 *
 * Canonical shape: [domain, readModel, resourceIdentifier?, params?].
 * `date` is the resourceIdentifier (position 3): unlike Watchlist's flat
 * "/watchlist" route, the Market summary is parameterised purely by query
 * param today, but the date being viewed is a real cache-relevant
 * dimension, so it is keyed explicitly rather than folded into `all`.
 */

export const marketKeys = {
  all: ['market'] as const,

  summary: (date: string | null) => ['market', 'summary', date] as const,
}
