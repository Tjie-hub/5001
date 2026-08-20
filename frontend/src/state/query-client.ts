/**
 * QueryClient factory — ADR-003 §7.1, §10.
 *
 * "Global defaults live in a single QueryClient configuration. Per-domain
 * overrides live in the Repository. Per-call-site overrides are prohibited."
 * (§7.1). This file owns only the global retry predicate (§10.1, S-9) and a
 * conservative default staleTime/gcTime; every domain's actual freshness
 * policy (§7 table) is declared in that domain's `repository/queries.ts`.
 *
 * A fresh QueryClient must be constructed per test (S-15) — see
 * createTestQueryClient in src/tests/query-client-test-utils.ts.
 */
import { QueryClient } from '@tanstack/react-query'
import { ApiRequestError } from '@api/client'

const MAX_QUERY_RETRIES = 3

/**
 * §10.1 retry table, expressed as a predicate over the typed error (S-9).
 * Network failures carry status 0 (see api/client.ts's ApiRequestError
 * construction) and are retried the same as 5xx/408. 429 caps at 2 attempts
 * per the table; everything else in the table (400/401/403/404/maintenance)
 * does not retry.
 */
export function queryRetryPredicate(failureCount: number, error: unknown): boolean {
  if (!(error instanceof ApiRequestError)) return false

  const { status } = error

  if (status === 429) return failureCount < 2
  if (status === 0 || status === 408 || (status >= 500 && status < 600)) {
    return failureCount < MAX_QUERY_RETRIES
  }
  // 400 / 401 / 403 / 404 and anything else: deterministic, do not retry.
  return false
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: queryRetryPredicate,
        staleTime: 0,
        gcTime: 5 * 60 * 1000,
      },
      mutations: {
        // S-8 / N-9: mutations never retry automatically. P4-14 §12 requires
        // an explicit user-driven Retry action instead.
        retry: false,
      },
    },
  })
}
