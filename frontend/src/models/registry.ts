/**
 * Edge Registry domain models — mirrors the /api/v1/registry/status
 * response shape verbatim (routes/v1/registry.py over
 * engine/registry_loader.py), same "no camelCase remapping for a read-only
 * v1 slice" convention as models/operations.ts.
 *
 * Pure types only (Phase 7 v1.1 §9): no api/design-system/workspace imports.
 */

export type RegistryEntryStatus = 'APPROVED' | 'SHADOW'

export interface RegistryEntry {
  readonly id: string
  readonly version: number
  readonly status: RegistryEntryStatus
  readonly strategy_fn: string
  readonly regimes: string[]
}

export interface RegistryStatus {
  readonly hash: string
  readonly approved: number
  readonly shadow: number
  readonly entries: RegistryEntry[]
  readonly skipped_count: number
  readonly debt_count: number
  readonly violation_count: number
}
