/**
 * Vitest global setup — Phase 9 Workstream A (task A5), extended in Workstream B.
 *
 * Loaded by vite.config.ts `test.setupFiles`.
 */
import '@testing-library/jest-dom/vitest'
import { afterEach, beforeEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// React Testing Library does not auto-clean under Vitest's globals mode in
// every configuration; doing it explicitly keeps tests isolated regardless.
afterEach(() => {
  cleanup()
})

/**
 * jsdom does not implement matchMedia, which the responsive shell depends on
 * (Phase 9 Workstream B, B11). Default every query to "does not match" — i.e.
 * the DESKTOP layout, which Phase 6 P6-38 designates the reference
 * implementation. Tests that need tablet or mobile override this explicitly.
 */
export function setViewportMatches(matcher: (query: string) => boolean) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockImplementation((query: string) => ({
      matches: matcher(query),
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  )
}

beforeEach(() => {
  setViewportMatches(() => false)
  window.localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
})
