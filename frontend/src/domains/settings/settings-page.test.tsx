import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SettingsPage } from './settings-page'
import type { JobExecution, SchedulerJob, SchedulerStatus } from '@models/operations'

/**
 * Relocated from the former domains/operations/operations-page.test.tsx
 * (ADR-008: scheduler/job-history/system-status information is owned by
 * Settings' System Information / Support & Diagnostics regions, not a
 * standalone Operations workspace). Behavior asserted is unchanged from the
 * original test — only the render target and heading/region structure
 * reflect the new placement.
 */

const mockStatus: SchedulerStatus = {
  available: true,
  state: 'running',
  timezone: 'Asia/Jakarta',
  job_count: 2,
}

// job_id and name deliberately differ, matching real production shape
// (e.g. job_id "premarket_firm_scan", display name "Premarket Firm Scan
// 08:35") -- job_execution_log.job_name is keyed by job_id, never by the
// display name, and fixtures that used the same string for both would mask
// exactly the bug live-data verification against production caught here
// (job-detail-panel.tsx originally queried history by `job.name`).
const mockJobs: SchedulerJob[] = [
  {
    job_id: 'flow_fetch_0930',
    name: 'Flow Fetch 09:30',
    trigger: 'cron[hour=9]',
    next_run_time: '2026-08-19T09:00:00+07:00',
    paused: false,
    last_run: {
      run_id: 'r1',
      job_name: 'flow_fetch_0930',
      run_type: 'scheduled',
      started_at: '2026-08-18 09:00:00',
      completed_at: '2026-08-18 09:00:05',
      duration_ms: 5000,
      status: 'success',
      records_processed: 10,
      telegram_sent: 0,
      error_message: null,
      retry_count: 0,
      engine_version: 'abc123',
    },
  },
  {
    job_id: 'eod_trade_plan',
    name: 'EOD Trade Plan 16:40',
    trigger: 'cron[hour=16,minute=40]',
    next_run_time: '2026-08-18T16:40:00+07:00',
    paused: false,
    last_run: {
      run_id: 'r2',
      job_name: 'eod_trade_plan',
      run_type: 'scheduled',
      started_at: '2026-08-17 16:40:00',
      completed_at: null,
      duration_ms: null,
      status: 'failed',
      records_processed: null,
      telegram_sent: 0,
      error_message: 'Telegram API timeout',
      retry_count: 0,
      engine_version: 'abc123',
    },
  },
]

const mockHistory: JobExecution[] = [
  mockJobs[1]!.last_run!,
  {
    ...mockJobs[1]!.last_run!,
    run_id: 'r0',
    started_at: '2026-08-16 16:40:00',
    status: 'success',
    error_message: null,
    duration_ms: 4200,
  },
]

vi.mock('@api/operations', () => ({
  getSchedulerStatus: vi.fn(() => Promise.resolve(mockStatus)),
  getSchedulerJobs: vi.fn(() => Promise.resolve({ jobs: mockJobs, count: mockJobs.length })),
  getJobHistory: vi.fn(() => Promise.resolve({ history: mockHistory })),
}))

describe('SettingsPage', () => {
  it('renders the Settings heading', async () => {
    render(<SettingsPage />)

    expect(await screen.findByRole('heading', { level: 1, name: /Settings/ })).toBeVisible()
  })

  it('renders scheduler status under System Information and the job table under Support & Diagnostics', async () => {
    render(<SettingsPage />)

    expect(
      await screen.findByRole('heading', { level: 2, name: 'System Information' }),
    ).toBeVisible()
    expect(
      screen.getByRole('heading', { level: 2, name: 'Support & Diagnostics' }),
    ).toBeVisible()

    await waitFor(() => {
      expect(screen.getByText(/2 jobs registered/)).toBeVisible()
    })

    const table = screen.getByRole('table')
    expect(within(table).getByText('Flow Fetch 09:30')).toBeVisible()
    expect(within(table).getByText('EOD Trade Plan 16:40')).toBeVisible()
  })

  it('drills into a job to show its failure history and error message', async () => {
    const user = userEvent.setup()
    render(<SettingsPage />)

    const jobLink = await screen.findByRole('button', { name: 'EOD Trade Plan 16:40' })
    await user.click(jobLink)

    expect(
      await screen.findByRole('heading', { level: 3, name: 'EOD Trade Plan 16:40' }),
    ).toBeVisible()

    await waitFor(() => {
      expect(screen.getByText('Telegram API timeout')).toBeVisible()
    })

    // Regression guard: history must be queried by job_id (job_execution_
    // log's actual key), never by the human-readable display name -- this
    // is the exact bug live-data verification against production caught.
    const operationsApi = await import('@api/operations')
    expect(operationsApi.getJobHistory).toHaveBeenCalledWith(
      expect.objectContaining({ jobName: 'eod_trade_plan' }),
    )
  })

  it('shows an unavailable state without crashing when the scheduler is not running', async () => {
    const operationsApi = await import('@api/operations')
    vi.mocked(operationsApi.getSchedulerStatus).mockResolvedValueOnce({
      available: false,
      state: 'unavailable',
      timezone: null,
      job_count: 0,
    })
    vi.mocked(operationsApi.getSchedulerJobs).mockResolvedValueOnce({ jobs: [], count: 0 })

    render(<SettingsPage />)

    expect(await screen.findByText(/Scheduler unavailable in this process/)).toBeVisible()
  })
})
