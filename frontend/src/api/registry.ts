/**
 * Edge Registry API surface — typed wrapper over the already-frozen
 * registry endpoint (routes/v1/registry.py). Read-only.
 */
import { apiGet } from './client'
import type { RegistryStatus } from '@models/registry'

export function getRegistryStatus(): Promise<RegistryStatus> {
  return apiGet<RegistryStatus>('/api/v1/registry/status')
}
