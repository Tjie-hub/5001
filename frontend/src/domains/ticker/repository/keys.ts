/**
 * Ticker query-key factory — ADR-003 §6, colocated with the Repository (S-3).
 * Canonical shape: [domain, readModel, resourceIdentifier?, params?].
 * `symbol` is the resourceIdentifier (position 3) for the detail read model.
 *
 * The runtime-status read model (GET /api/v1/runtime) is served from this
 * repository because the Ticker slice introduced it (blocker U-2's first
 * consumer: the global StatusFooter plus the ticker page's own freshness
 * display), but its cache namespace is `platform`, not `ticker` — the
 * payload is workspace-independent production state.
 */

export const tickerKeys = {
  all: ['ticker'] as const,

  detail: (symbol: string) => ['ticker', 'detail', symbol] as const,

  /** Trade Flow read model; `range` is the params object (position 4). */
  tradeFlow: (symbol: string, range: { start?: string; end?: string; metric?: string }) =>
    ['ticker', 'trade-flow', symbol, range] as const,
}

export const platformKeys = {
  all: ['platform'] as const,

  runtimeStatus: () => ['platform', 'runtime-status'] as const,
}
