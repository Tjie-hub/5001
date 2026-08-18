import { cx } from '@utils/cx'
import styles from './status-badge.module.css'

interface StatusBadgeProps {
  readonly status: string
}

/** Small colored label for a job/scheduler status string. Falls back to a
 * neutral style for any status value it doesn't recognize, rather than
 * throwing — this reads live operational data, which can carry a status the
 * frontend was never told about. */
export function StatusBadge({ status }: StatusBadgeProps) {
  const known = ['success', 'failed', 'running', 'skipped', 'paused', 'stopped'].includes(status)

  return (
    <span className={cx(styles['badge'], styles[known ? status : 'unknown'])} data-status={status}>
      {status}
    </span>
  )
}
