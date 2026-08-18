import { useMemo, useState } from 'react'
import type { SchedulerJob } from '@models/operations'
import { cx } from '@utils/cx'
import { formatTimestamp } from './format'
import { StatusBadge } from './status-badge'
import styles from './job-table.module.css'

type SortKey = 'name' | 'next_run_time' | 'last_run_status'
type SortDirection = 'asc' | 'desc'

interface JobTableProps {
  readonly jobs: readonly SchedulerJob[]
  readonly selectedJobId: string | null
  readonly onSelect: (jobId: string) => void
}

function sortValue(job: SchedulerJob, key: SortKey): string {
  switch (key) {
    case 'name':
      return job.name
    case 'next_run_time':
      return job.next_run_time ?? ''
    case 'last_run_status':
      return job.last_run?.status ?? ''
  }
}

/** Sortable scheduler job table (design doc §3 "sortable job table"). Client-
 * side sort over an already-small list (~20 scheduler jobs) — no pagination
 * or server-side sort needed at this scale. */
export function JobTable({ jobs, selectedJobId, onSelect }: JobTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('name')
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')

  const sortedJobs = useMemo(() => {
    const copy = [...jobs]
    copy.sort((a, b) => {
      const cmp = sortValue(a, sortKey).localeCompare(sortValue(b, sortKey))
      return sortDirection === 'asc' ? cmp : -cmp
    })
    return copy
  }, [jobs, sortKey, sortDirection])

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDirection((dir) => (dir === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDirection('asc')
    }
  }

  const sortIndicator = (key: SortKey) => {
    if (key !== sortKey) return ''
    return sortDirection === 'asc' ? ' ▲' : ' ▼'
  }

  if (jobs.length === 0) {
    return <p className={cx(styles['empty'])}>No scheduler jobs registered.</p>
  }

  return (
    <table className={cx(styles['table'])}>
      <caption className="sr-only">Scheduler jobs, sortable by column header</caption>
      <thead>
        <tr>
          <th scope="col">
            <button
              type="button"
              className={cx(styles['sortButton'])}
              onClick={() => toggleSort('name')}
            >
              Job{sortIndicator('name')}
            </button>
          </th>
          <th scope="col">Trigger</th>
          <th scope="col">
            <button
              type="button"
              className={cx(styles['sortButton'])}
              onClick={() => toggleSort('next_run_time')}
            >
              Next run{sortIndicator('next_run_time')}
            </button>
          </th>
          <th scope="col">
            <button
              type="button"
              className={cx(styles['sortButton'])}
              onClick={() => toggleSort('last_run_status')}
            >
              Last run{sortIndicator('last_run_status')}
            </button>
          </th>
          <th scope="col">Paused</th>
        </tr>
      </thead>
      <tbody>
        {sortedJobs.map((job) => (
          <tr
            key={job.job_id}
            className={cx(styles['row'], job.job_id === selectedJobId && styles['rowSelected'])}
          >
            <td>
              <button
                type="button"
                className={cx(styles['jobLink'])}
                onClick={() => onSelect(job.job_id)}
                aria-current={job.job_id === selectedJobId ? 'true' : undefined}
              >
                {job.name}
              </button>
            </td>
            <td className={cx(styles['muted'])}>{job.trigger}</td>
            <td>{formatTimestamp(job.next_run_time)}</td>
            <td>
              {job.last_run ? (
                <StatusBadge status={job.last_run.status} />
              ) : (
                <span className={cx(styles['muted'])}>never run</span>
              )}
            </td>
            <td>{job.paused ? 'yes' : 'no'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
