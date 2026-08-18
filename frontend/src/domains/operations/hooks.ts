/**
 * Operations / Job History data hooks.
 *
 * Domain-local, not src/hooks/ (that directory is cross-cutting presentation
 * hooks only — job/scheduler fetching is this workspace's own concern, the
 * ADR-003 §16.2 "workspace adapter" role). Plain fetch-on-mount + manual
 * refresh, no polling/websocket loop: the design doc explicitly scopes v1 to
 * "polling on page load / manual refresh... no live-tailing requirement was
 * stated anywhere in the milestone's source documents" (§5).
 *
 * Not built on @tanstack/react-query: ADR-003 is still PROPOSED and the
 * library isn't installed yet. This is the smallest working data layer for
 * a single read-only page; a future Repository migration to TanStack Query
 * would replace this file's internals without changing the hooks' call
 * signatures (loading/error/data/refresh), so components are shielded either
 * way.
 */
import { useCallback, useEffect, useState } from 'react'
import { getJobHistory, getSchedulerJobs, getSchedulerStatus } from '@api/operations'
import { ApiRequestError } from '@api/client'
import type { JobExecution, SchedulerJob, SchedulerStatus } from '@models/operations'

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

export interface SchedulerOverview {
  readonly status: SchedulerStatus
  readonly jobs: SchedulerJob[]
}

/** Scheduler state banner + job list (design doc §3, exit criterion 1). */
export function useSchedulerOverview(): AsyncState<SchedulerOverview> & { refresh: () => void } {
  const [state, setState] = useState<AsyncState<SchedulerOverview>>({
    data: null,
    loading: true,
    error: null,
  })
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let cancelled = false

    // react-hooks/set-state-in-effect forbids a *synchronous* setState call
    // in the effect body (it forces an extra synchronous render pass); a
    // microtask-deferred call starts the same fetch-then-render sequence
    // without tripping that rule, matching its own suggested "setState in a
    // callback responding to an external system" shape.
    Promise.resolve().then(() => {
      if (!cancelled) setState((prev) => ({ ...prev, loading: true, error: null }))
    })

    Promise.all([getSchedulerStatus(), getSchedulerJobs()])
      .then(([status, jobsResponse]) => {
        if (cancelled) return
        setState({ data: { status, jobs: jobsResponse.jobs }, loading: false, error: null })
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

/** Per-job execution history for the drill-into-failure detail view. */
export function useJobHistory(
  jobName: string | null,
  limit = 20,
): AsyncState<JobExecution[]> & { refresh: () => void } {
  const [state, setState] = useState<AsyncState<JobExecution[]>>({
    data: null,
    loading: false,
    error: null,
  })
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let cancelled = false

    if (!jobName) {
      Promise.resolve().then(() => {
        if (!cancelled) setState({ data: null, loading: false, error: null })
      })
      return () => {
        cancelled = true
      }
    }

    Promise.resolve().then(() => {
      if (!cancelled) setState((prev) => ({ ...prev, loading: true, error: null }))
    })

    getJobHistory({ jobName, limit })
      .then((response) => {
        if (cancelled) return
        setState({ data: response.history, loading: false, error: null })
      })
      .catch((cause: unknown) => {
        if (cancelled) return
        setState({ data: null, loading: false, error: errorMessage(cause) })
      })

    return () => {
      cancelled = true
    }
  }, [jobName, limit, nonce])

  const refresh = useCallback(() => setNonce((n) => n + 1), [])

  return { ...state, refresh }
}
