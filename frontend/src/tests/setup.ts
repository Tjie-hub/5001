/**
 * Vitest global setup — Phase 9 Workstream A (task A5).
 *
 * Loaded by vite.config.ts `test.setupFiles`.
 */
import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// React Testing Library does not auto-clean under Vitest's globals mode in
// every configuration; doing it explicitly keeps tests isolated regardless.
afterEach(() => {
  cleanup()
})
