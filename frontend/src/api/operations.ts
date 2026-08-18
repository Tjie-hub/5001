/**
 * Operations / Job History API surface — typed wrappers over the already-
 * frozen scheduler and status v1 endpoints (routes/v1/scheduler.py,
 * routes/v1/status.py). No new backend routes were needed for this slice
 * (design doc §3 "Job History... has zero backend gaps — pure frontend work
 * over already-frozen API"); `getJobHistory`'s `jobName` filter uses the one
 * small, additive `job_name` query param added alongside this page.
 */
import { apiGet } from './client'
import type { JobExecution, JobSummary, SchedulerJob, SchedulerStatus } from '@models/operations'

export function getSchedulerStatus(): Promise<SchedulerStatus> {
  return apiGet<SchedulerStatus>('/api/v1/scheduler')
}

export function getSchedulerJobs(): Promise<{ jobs: SchedulerJob[]; count: number }> {
  return apiGet<{ jobs: SchedulerJob[]; count: number }>('/api/v1/scheduler/jobs')
}

export function getSchedulerJobDetail(jobId: string): Promise<SchedulerJob> {
  return apiGet<SchedulerJob>(`/api/v1/scheduler/jobs/${encodeURIComponent(jobId)}`)
}

export function getJobHistory(options?: {
  jobName?: string
  limit?: number
}): Promise<{ history: JobExecution[] }> {
  return apiGet<{ history: JobExecution[] }>('/api/v1/status/jobs/history', {
    job_name: options?.jobName,
    limit: options?.limit,
  })
}

export function getFailedJobs(options?: { since?: string }): Promise<{ failed: JobExecution[] }> {
  return apiGet<{ failed: JobExecution[] }>('/api/v1/status/jobs/failed', {
    since: options?.since,
  })
}

export function getJobSummary(): Promise<JobSummary> {
  return apiGet<JobSummary>('/api/v1/status/summary')
}
