import { useState } from 'react'
import { cx } from '@utils/cx'
import { useSchedulerOverview } from './hooks'
import { SchedulerBanner } from './scheduler-banner'
import { JobTable } from './job-table'
import { JobDetailPanel } from './job-detail-panel'
import styles from './settings-page.module.css'

/**
 * Settings — Workstream D, second real workspace slice, and the ADR-008
 * home for scheduler/job-history/system-status information.
 *
 * ADR-008 (docs/OneDrive_2026-08-07/Frontend arch/
 * ADR-008_OPERATIONS_DASHBOARD_SETTINGS_PLACEMENT.md): Operations Dashboard
 * is not an eighth primary workspace. Its information is owned by Settings,
 * under Settings' own already-frozen "System Information" and "Support &
 * Diagnostics" regions (SETTINGS_DESIGN_SPEC_v1.0_FROZEN.md §7/§8) — read
 * per §7 of that ADR: scheduler state → System Information, job execution
 * history + drill-down → Support & Diagnostics. The former standalone
 * `/internal/operations` route (unreachable from any navigation, per that
 * ADR's §1 Context) is retired by this change; the same components move
 * here unchanged in behavior (only relocated + heading levels adjusted for
 * correct nesting, see job-detail-panel.tsx).
 *
 * Every other Settings region (Account & Identity, Security & Privacy,
 * Notifications, Appearance & Localization, Workspace Preferences, Support)
 * remains an unbuilt reserved placeholder — same honest "not yet built"
 * pattern Decision Center uses for its own non-Executive-Summary regions.
 * Read-only here too: no pause/resume/trigger controls, unchanged from the
 * original Operations scope.
 */
export function SettingsPage() {
  const { data, loading, error, refresh } = useSchedulerOverview()
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)

  const selectedJob = data?.jobs.find((job) => job.job_id === selectedJobId) ?? null

  return (
    <article className={cx(styles['page'])} aria-labelledby="workspace-title">
      <div className={cx(styles['pageHeader'])}>
        <h1 id="workspace-title" tabIndex={-1} className={cx(styles['title'])}>
          Settings
        </h1>
        <p className={cx(styles['purpose'])}>
          Manage account, security, notifications and preferences.
        </p>
      </div>

      <section className={cx(styles['region'])} aria-labelledby="system-information-title">
        <div className={cx(styles['regionHeader'])}>
          <h2 id="system-information-title" className={cx(styles['regionTitle'])}>
            System Information
          </h2>
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

        {data ? <SchedulerBanner status={data.status} /> : null}
      </section>

      {data ? (
        <section className={cx(styles['region'])} aria-labelledby="support-diagnostics-title">
          <h2 id="support-diagnostics-title" className={cx(styles['regionTitle'])}>
            Support &amp; Diagnostics
          </h2>
          <p className={cx(styles['regionPurpose'])}>
            Scheduler liveness and job execution history — read-only observability, no
            pause/resume/trigger controls.
          </p>

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
        </section>
      ) : null}

      <section className={cx(styles['regions'])} aria-label="Reserved regions">
        {['Account & Identity', 'Security & Privacy', 'Notifications', 'Appearance & Localization',
          'Workspace Preferences', 'Support'].map((region) => (
          <div key={region} className={cx(styles['reservedRegion'])}>
            <h2 className={cx(styles['reservedRegionTitle'])}>{region}</h2>
            <p className={cx(styles['placeholder'])}>Reserved</p>
          </div>
        ))}
      </section>
    </article>
  )
}
