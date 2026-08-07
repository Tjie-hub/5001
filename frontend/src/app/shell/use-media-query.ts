/**
 * Media query hook — Phase 9 Workstream B (B11).
 *
 * Presentation-only. Phase 4 NP-14 and P4-14 §17 are emphatic that responsive
 * layouts may change presentation but never navigation hierarchy, workspace
 * ownership, route identity or workflow — so this hook must only ever drive
 * layout, never routing or business behaviour.
 *
 * Implemented with useSyncExternalStore rather than useState + useEffect.
 * matchMedia IS an external store, and subscribing to it properly avoids the
 * setState-in-effect cascade (and the tearing) that the naive version causes.
 *
 * Breakpoint VALUES are provisional (blocker U-1: no tokens exist). Workstream C
 * replaces them, and the CSS breakpoints in *.module.css must move with them.
 */
import { useCallback, useSyncExternalStore } from 'react'

/** Provisional. Mirrors the CSS breakpoints in app-shell.module.css. */
export const BREAKPOINTS = {
  /** Below this width the sidebar becomes a drawer + bottom navigation. */
  mobile: '(max-width: 47.99rem)',
  /** Below this width the sidebar is collapsible rather than persistent. */
  collapsibleSidebar: '(max-width: 79.99rem)',
} as const

export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onStoreChange: () => void) => {
      const list = window.matchMedia(query)
      list.addEventListener('change', onStoreChange)
      return () => list.removeEventListener('change', onStoreChange)
    },
    [query],
  )

  const getSnapshot = useCallback(() => window.matchMedia(query).matches, [query])

  // Server snapshot: no viewport, so nothing matches. The application is an
  // SPA (Phase 7 v1.1 §3) so this only guards against a non-DOM environment.
  const getServerSnapshot = useCallback(() => false, [])

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}
