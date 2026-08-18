/**
 * Operations / Job History domain models — Job History half of the
 * Operations Dashboard milestone (docs/superpowers/specs/
 * 2026-08-15-operations-dashboard-job-history-design.md §3).
 *
 * Field names and shapes mirror the backend response shapes verbatim
 * (routes/v1/scheduler.py, routes/v1/status.py over engine/job_status.py's
 * job_execution_log) rather than introducing a camelCase remapping layer —
 * for a read-only v1 slice like this, a DTO→Model rename buys no safety and
 * adds a second place field names can drift out of sync with the backend.
 * Timestamps stay as the WIB "YYYY-MM-DD HH:MM:SS" strings the backend
 * already produces (job_status.py's own WIB-formatted `started_at`/
 * `completed_at`) — displayed verbatim, per this repo's established
 * "exit reasons shown verbatim, never translated" convention
 * (CLAUDE.md, Forward-Testing Summary).
 *
 * Pure types only (Phase 7 v1.1 §9): no api/design-system/workspace imports.
 */

export type JobExecutionStatus = 'running' | 'success' | 'failed' | 'skipped'

export interface SchedulerStatus {
  readonly available: boolean
  readonly state: string
  readonly timezone: string | null
  readonly job_count: number
}

export interface JobExecution {
  readonly run_id: string
  readonly job_name: string
  readonly run_type: string
  readonly started_at: string
  readonly completed_at: string | null
  readonly duration_ms: number | null
  readonly status: JobExecutionStatus
  readonly records_processed: number | null
  readonly telegram_sent: number
  readonly error_message: string | null
  readonly retry_count: number
  readonly engine_version: string | null
}

export interface SchedulerJob {
  readonly job_id: string
  readonly name: string
  readonly trigger: string
  readonly next_run_time: string | null
  readonly paused: boolean
  readonly last_run: JobExecution | null
}

export interface JobSummary {
  readonly total: number
  readonly success: number
  readonly failed: number
  readonly skipped: number
  readonly running: number
}
