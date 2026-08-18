import { useState } from 'react'
import { cx } from '@utils/cx'
import { useSchedulerOverview } from './hooks'
import { SchedulerBanner } from './scheduler-banner'
import { JobTable } from './job-table'
import { JobDetailPanel } from './job-detail-panel'
import styles from './operations-page.module.css'

/**
 * Operations Dashboard — Job History (docs/superpowers/specs/
 * 2026-08-15-operations-dashboard-job-history-design.md §3, §6 exit
 * criterion 1). Read-only: "is the scheduler alive and did today's jobs
 * run" over the already-frozen scheduler + status v1 APIs.
 *
 * Deliberately NOT registered in app/router/workspaces.ts. That registry is
 * frozen (Phase 4 P4-02 §3, "the seven workspaces") and its own docstring
 * requires an ADR to add an eighth — and semantically this page is an
 * engineering/ops surface ("is the scheduler alive"), not a trading
 * decision workspace (Decide/Evaluate/Observe/Investigate/Understand/
 * Discover/Configure), so it isn't a good fit for that registry even if an
 * ADR were in scope here. It is mounted as a standalone route
 * (/internal/operations, app-router.tsx) inside AppShell — the same pattern
 * NotFoundPage already uses for a page that isn't one of the seven
 * workspaces — reachable by direct URL/bookmark rather than global nav,
 * since both Zone A (sidebar) and Zone B (header) have their own frozen,
 * enumerated content lists that don't include an Operations entry. See this
 * session's report for the full flagged deviation from the design doc's
 * (incorrect) assumption that domains/decision/ could double as this page.
 */
export function OperationsPage() {
  const { data, loading, error, refresh } = useSchedulerOverview()
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)

  const selectedJob = data?.jobs.find((job) => job.job_id === selectedJobId) ?? null

  return (
    <article className={cx(styles['page'])} aria-labelledby="operations-title">
      <div className={cx(styles['pageHeader'])}>
        <h1 id="operations-title" tabIndex={-1} className={cx(styles['title'])}>
          Operations · Job History
        </h1>
        <p className={cx(styles['purpose'])}>
          Scheduler liveness and job execution history — read-only observability, no
          pause/resume/trigger controls (out of scope for v1, see design doc §5).
        </p>
        <button type="button" className={cx(styles['refreshButton'])} onClick={refresh}>
          Refresh
        </button>
      </div>

      {loading ? <p className={cx(styles['status'])}>Loading scheduler state…</p> : null}

      {error ? (
        <p className={cx(styles['error'])} role="alert">
          Failed to load scheduler state: {error}
        </p>
      ) : null}

      {data ? (
        <div className={cx(styles['content'])}>
          <SchedulerBanner status={data.status} />

          <div className={cx(styles['layout'])}>
            <div className={cx(styles['tableRegion'])}>
              <JobTable
                jobs={data.jobs}
                selectedJobId={selectedJobId}
                onSelect={setSelectedJobId}
              />
            </div>

            <div className={cx(styles['detailRegion'])}>
              {selectedJob ? (
                <JobDetailPanel job={selectedJob} />
              ) : (
                <p className={cx(styles['status'])}>Select a job to see its execution history.</p>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </article>
  )
}
