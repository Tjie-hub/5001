import type { SchedulerStatus } from '@models/operations'
import { cx } from '@utils/cx'
import { StatusBadge } from './status-badge'
import styles from './scheduler-banner.module.css'

interface SchedulerBannerProps {
  readonly status: SchedulerStatus
}

/** Scheduler state banner (design doc §3): running/paused/stopped, from
 * GET /api/v1/scheduler. */
export function SchedulerBanner({ status }: SchedulerBannerProps) {
  if (!status.available) {
    return (
      <div className={cx(styles['banner'], styles['unavailable'])} role="status">
        <span>Scheduler unavailable in this process.</span>
      </div>
    )
  }

  return (
    <div className={cx(styles['banner'])} role="status">
      <StatusBadge status={status.state} />
      <span className={cx(styles['detail'])}>
        {status.job_count} job{status.job_count === 1 ? '' : 's'} registered
        {status.timezone ? ` · ${status.timezone}` : ''}
      </span>
    </div>
  )
}
