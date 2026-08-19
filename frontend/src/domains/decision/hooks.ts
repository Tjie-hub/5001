/**
 * Decision Center data hook — Executive Summary region (Workstream D,
 * first real workspace slice). Same "plain fetch-on-mount, no TanStack
 * Query" shape as domains/settings/hooks.ts (formerly domains/operations/
 * hooks.ts; relocated under ADR-008): ADR-003 is still PROPOSED
 * and the library isn't installed, so this is the smallest working data
 * layer; a future Repository migration would replace the internals without
 * changing the hook's loading/error/data/refresh call signature.
 *
 * A missing watchlist snapshot (ApiRequestError NO_WATCHLIST_DATA, 404) is
 * a legitimate empty state, not a page-level error — caught separately so
 * one workspace with no watchlist yet doesn't hide real scheduler/registry
 * data behind an error screen.
 */
import { useCallback, useEffect, useState } from 'react'
import { getSchedulerStatus } from '@api/operations'
import { getRegistryStatus } from '@api/registry'
import { getCurrentWatchlist } from '@api/watchlist'
import { ApiRequestError } from '@api/client'
import type { SchedulerStatus } from '@models/operations'
import type { RegistryStatus } from '@models/registry'
import type { CurrentWatchlist } from '@models/watchlist'

interface AsyncState<T> {
  readonly data: T | null
  readonly loading: boolean
  readonly error: string | null
}

function errorMessage(cause: unknown): string {
  if (cause instanceof ApiRequestError) return cause.message
  if (cause instanceof Error) return cause.message
  return 'unknown error'
}

export interface ProductionSummary {
  readonly scheduler: SchedulerStatus
  readonly registry: RegistryStatus
  /** null means no watchlist snapshot exists yet — a legitimate empty state. */
  readonly watchlist: CurrentWatchlist | null
}

async function fetchWatchlistOrNull(): Promise<CurrentWatchlist | null> {
  try {
    return await getCurrentWatchlist()
  } catch (cause) {
    if (cause instanceof ApiRequestError && cause.code === 'NO_WATCHLIST_DATA') return null
    throw cause
  }
}

/** Production state for the Decision Center Executive Summary region. */
export function useProductionSummary(): AsyncState<ProductionSummary> & { refresh: () => void } {
  const [state, setState] = useState<AsyncState<ProductionSummary>>({
    data: null,
    loading: true,
    error: null,
  })
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let cancelled = false

    Promise.resolve().then(() => {
      if (!cancelled) setState((prev) => ({ ...prev, loading: true, error: null }))
    })

    Promise.all([getSchedulerStatus(), getRegistryStatus(), fetchWatchlistOrNull()])
      .then(([scheduler, registry, watchlist]) => {
        if (cancelled) return
        setState({ data: { scheduler, registry, watchlist }, loading: false, error: null })
      })
      .catch((cause: unknown) => {
        if (cancelled) return
        setState({ data: null, loading: false, error: errorMessage(cause) })
      })

    return () => {
      cancelled = true
    }
  }, [nonce])

  const refresh = useCallback(() => setNonce((n) => n + 1), [])

  return { ...state, refresh }
}
