import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  getFailedJobs,
  getJobHistory,
  getJobSummary,
  getSchedulerJobDetail,
  getSchedulerJobs,
  getSchedulerStatus,
} from './operations'

function stubFetch(data: unknown) {
  const fetchMock = vi.fn().mockResolvedValue({
    status: 200,
    json: () =>
      Promise.resolve({
        ok: true,
        data,
        meta: { api_version: 'v1', request_id: 'r', timestamp: 't' },
      }),
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('operations API wrappers', () => {
  it('getSchedulerStatus hits /api/v1/scheduler', async () => {
    const fetchMock = stubFetch({
      available: true,
      state: 'running',
      timezone: 'Asia/Jakarta',
      job_count: 3,
    })
    const result = await getSchedulerStatus()
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/scheduler', expect.anything())
    expect(result.state).toBe('running')
  })

  it('getSchedulerJobs hits /api/v1/scheduler/jobs', async () => {
    const fetchMock = stubFetch({ jobs: [], count: 0 })
    await getSchedulerJobs()
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/scheduler/jobs', expect.anything())
  })

  it('getSchedulerJobDetail encodes the job id into the path', async () => {
    const fetchMock = stubFetch({
      job_id: 'a b',
      name: 'x',
      trigger: 't',
      next_run_time: null,
      paused: false,
      last_run: null,
    })
    await getSchedulerJobDetail('a b')
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/scheduler/jobs/a%20b', expect.anything())
  })

  it('getJobHistory passes job_name and limit as query params', async () => {
    const fetchMock = stubFetch({ history: [] })
    await getJobHistory({ jobName: 'run_flow_fetch', limit: 10 })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/status/jobs/history?job_name=run_flow_fetch&limit=10',
      expect.anything(),
    )
  })

  it('getJobHistory omits query params when not given', async () => {
    const fetchMock = stubFetch({ history: [] })
    await getJobHistory()
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/status/jobs/history', expect.anything())
  })

  it('getFailedJobs passes since as a query param', async () => {
    const fetchMock = stubFetch({ failed: [] })
    await getFailedJobs({ since: '2026-08-01 00:00:00' })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/status/jobs/failed?since=2026-08-01+00%3A00%3A00',
      expect.anything(),
    )
  })

  it('getJobSummary hits /api/v1/status/summary', async () => {
    const fetchMock = stubFetch({ total: 0, success: 0, failed: 0, skipped: 0, running: 0 })
    await getJobSummary()
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/status/summary', expect.anything())
  })
})
