import type { SchedulerJob } from '@models/operations'
import { cx } from '@utils/cx'
import { useJobHistory } from './hooks'
import { formatDuration, formatTimestamp } from './format'
import { StatusBadge } from './status-badge'
import styles from './job-detail-panel.module.css'

interface JobDetailPanelProps {
  readonly job: SchedulerJob
}

/** Row click → job detail (design doc §3): trigger/next-run/paused state
 * from the selected SchedulerJob, plus its recent execution history —
 * status, duration, failure reason, timestamps — for the drill-into-failure
 * view the DoD calls for. History comes from GET /api/v1/status/jobs/history
 * filtered to this job's id, not from `last_run` alone (which is only the
 * single most recent row).
 *
 * Filtered by `job.job_id`, NOT `job.name`: job_execution_log.job_name is
 * the APScheduler job id (scheduler/__init__.py's _add_job docstring: "job_
 * name == APScheduler job id, exact, not a heuristic"), while `job.name` is
 * a separate human-readable display string (e.g. "Premarket Firm Scan
 * 08:35" vs. id "premarket_firm_scan") that never appears in
 * job_execution_log at all. Caught by live-data verification against
 * production, not by the unit tests — their fixtures happened to use the
 * same string for both fields. */
export function JobDetailPanel({ job }: JobDetailPanelProps) {
  const { data: history, loading, error, refresh } = useJobHistory(job.job_id)

  return (
    <section className={cx(styles['panel'])} aria-labelledby="job-detail-title">
      <div className={cx(styles['header'])}>
        <h2 id="job-detail-title" className={cx(styles['title'])}>
          {job.name}
        </h2>
        <button type="button" className={cx(styles['refreshButton'])} onClick={refresh}>
          Refresh
        </button>
      </div>

      <dl className={cx(styles['meta'])}>
        <div className={cx(styles['metaRow'])}>
          <dt>Trigger</dt>
          <dd>{job.trigger}</dd>
        </div>
        <div className={cx(styles['metaRow'])}>
          <dt>Next run</dt>
          <dd>{formatTimestamp(job.next_run_time)}</dd>
        </div>
        <div className={cx(styles['metaRow'])}>
          <dt>Paused</dt>
          <dd>{job.paused ? 'yes' : 'no'}</dd>
        </div>
      </dl>

      <h3 className={cx(styles['subtitle'])}>Recent executions</h3>

      {loading ? <p className={cx(styles['status'])}>Loading history…</p> : null}
      {error ? (
        <p className={cx(styles['error'])} role="alert">
          Failed to load history: {error}
        </p>
      ) : null}

      {history && history.length === 0 ? (
        <p className={cx(styles['status'])}>No recorded executions for this job yet.</p>
      ) : null}

      {history && history.length > 0 ? (
        <ul className={cx(styles['history'])}>
          {history.map((run) => (
            <li key={run.run_id} className={cx(styles['historyItem'])}>
              <div className={cx(styles['historyRow'])}>
                <StatusBadge status={run.status} />
                <span className={cx(styles['historyTimestamp'])}>
                  {formatTimestamp(run.started_at)}
                </span>
                <span className={cx(styles['historyDuration'])}>
                  {formatDuration(run.duration_ms)}
                </span>
              </div>
              {run.error_message ? (
                <p className={cx(styles['errorMessage'])}>{run.error_message}</p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
