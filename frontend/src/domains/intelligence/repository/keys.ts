/**
 * Intelligence query-key factory — ADR-003 §6, colocated with the
 * Repository (S-3). The Intelligence workspace composes read models owned
 * by other endpoints, so all of its keys are intelligence-prefixed: this
 * workspace has its own cache scope and never invalidates another
 * workspace's entries.
 */

export const intelligenceKeys = {
  all: ['intelligence'] as const,

  investmentsSummary: () => ['intelligence', 'investments', 'summary'] as const,
  marketSummary: () => ['intelligence', 'market', 'summary'] as const,
  watchlistCurrent: () => ['intelligence', 'watchlists', 'current'] as const,
  watchlistPersistent: () => ['intelligence', 'watchlists', 'persistent'] as const,
  registryStatus: () => ['intelligence', 'registry', 'status'] as const,
}
