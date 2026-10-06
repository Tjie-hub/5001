/**
 * Application Shell — Phase 9 Workstream B (B1, B11, B12).
 *
 * Assembles the four persistent navigation zones frozen by Phase 4 P4-03 §3
 * and laid out by Phase 5 v1.1 §2:
 *
 *   Zone A  Global Sidebar   workspace navigation only
 *   Zone B  Global Header    global application controls
 *   Zone C  Active Workspace the routed outlet
 *   Zone D  Status Footer    informational only
 *
 * Responsive behaviour (P4-03 §14, P4-14 §14, Phase 6 Appendix H):
 *   Desktop  persistent sidebar
 *   Tablet   collapsible sidebar
 *   Mobile   drawer + bottom navigation
 *
 * NP-14 / P4-14 §17: presentation adapts, hierarchy does not. The same seven
 * workspaces, in the same order, with the same routes, on every device.
 *
 * State held here is limited to what P4-03 §10 permits Global Navigation to
 * own: navigation collapse state. Active workspace and active resource are
 * owned by the Router and the URL (ADR-001 §3) — never mirrored here.
 */
import { Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { Outlet, useLocation } from 'react-router'
import { GlobalHeader } from './global-header'
import { GlobalSidebar } from './global-sidebar'
import { StatusFooter } from './status-footer'
import { BottomNavigation } from './bottom-navigation'
import { FrozenBanner } from './frozen-banner'
import { WorkspaceLoadingPlaceholder } from './loading-shell'
import { BREAKPOINTS, useMediaQuery } from './use-media-query'
import { cx } from '@utils/cx'
import styles from './app-shell.module.css'

const SIDEBAR_ID = 'global-sidebar'
const MAIN_ID = 'workspace-content'

export function AppShell() {
  const isMobile = useMediaQuery(BREAKPOINTS.mobile)
  const isCollapsible = useMediaQuery(BREAKPOINTS.collapsibleSidebar)
  const { pathname } = useLocation()

  // Navigation collapse state — the only navigation state the shell may own
  // (P4-03 §10).
  //
  // Only the user-controlled drawer is stored. Whether the sidebar is VISIBLE
  // is derived: on desktop it is persistent (Phase 6 Appendix H) and no state
  // can hide it. Deriving rather than syncing removes a whole class of bug
  // where a resize leaves the stored flag disagreeing with the viewport.
  const [drawerOpen, setDrawerOpen] = useState(false)
  const sidebarExpanded = isCollapsible ? drawerOpen : true

  // The drawer is Overlay State: never persisted, never survives navigation
  // (ADR-001 §3, P4-12 §10). Reset during render rather than in an effect —
  // React's documented pattern for state derived from a changing input, and it
  // avoids the cascading re-render an effect would cause.
  const [lastPathname, setLastPathname] = useState(pathname)
  if (pathname !== lastPathname) {
    setLastPathname(pathname)
    if (drawerOpen) setDrawerOpen(false)
  }

  /**
   * Route-change focus — Phase 4 P4-14 §20: "route changes move focus to the
   * primary heading".
   *
   * Owned here, not by the route element, for two reasons:
   *
   *   1. Route elements unmount on navigation, so any state tracking "did the
   *      route change?" resets on the transition it needs to detect. AppShell
   *      persists across route changes; it can tell.
   *   2. Comparing the previous pathname (rather than an "is first render"
   *      flag) is StrictMode-safe. React double-invokes effects in
   *      development, which silently defeats a boolean guard.
   *
   * Not fired on first load: P4-14 §20 says route *changes*, and stealing
   * focus on load would push the user straight past the skip link — the one
   * aid that exists for exactly that moment (WCAG 2.4.1).
   */
  const mainRef = useRef<HTMLElement>(null)
  const previousPathname = useRef(pathname)

  useEffect(() => {
    if (previousPathname.current === pathname) return
    previousPathname.current = pathname

    const heading = mainRef.current?.querySelector<HTMLElement>('h1')
    ;(heading ?? mainRef.current)?.focus()
  }, [pathname])

  // Esc closes the drawer (P4-03 §15, P6-43).
  useEffect(() => {
    if (!isCollapsible || !drawerOpen) return

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setDrawerOpen(false)
    }

    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [isCollapsible, drawerOpen])

  const toggleSidebar = useCallback(() => setDrawerOpen((open) => !open), [])
  const closeSidebar = useCallback(() => setDrawerOpen(false), [])
  const openSidebar = useCallback(() => setDrawerOpen(true), [])

  return (
    <div className={cx(styles['shell'])} data-sidebar={sidebarExpanded ? 'expanded' : 'collapsed'}>
      {/* WCAG 2.4.1 — keyboard users bypass navigation on every route change. */}
      <a className={cx(styles['skipLink'])} href={`#${MAIN_ID}`}>
        Skip to workspace content
      </a>

      {/*
        Frontend freeze (owner-directed 2026-10-06): one thin line at the top
        of every workspace pointing at jurnal26 (port 5004). Rendered from the
        shell so no route can omit it.
      */}
      <FrozenBanner />

      <div className={cx(styles['header'])}>
        <GlobalHeader
          onToggleSidebar={toggleSidebar}
          sidebarExpanded={sidebarExpanded}
          sidebarControlsId={SIDEBAR_ID}
        />
      </div>

      {/*
        `inert` when the drawer is closed. CSS alone (transform + visibility)
        hides it visually, but a closed off-screen drawer must not be reachable
        by Tab either — that is a keyboard trap in disguise and would violate
        P6-43's "no unreachable / no invisible focus" rules.
      */}
      <div className={cx(styles['sidebar'])} inert={isMobile && !sidebarExpanded}>
        <GlobalSidebar id={SIDEBAR_ID} onNavigate={isMobile ? closeSidebar : undefined} />
      </div>

      {isMobile && sidebarExpanded ? (
        <button
          type="button"
          className={cx(styles['backdrop'])}
          aria-label="Close workspace navigation"
          onClick={closeSidebar}
        />
      ) : null}

      {/* Exactly one <main> landmark per page (Phase 6 P6-44). */}
      <main id={MAIN_ID} ref={mainRef} className={cx(styles['main'])} tabIndex={-1}>
        <Suspense fallback={<WorkspaceLoadingPlaceholder />}>
          <Outlet />
        </Suspense>
      </main>

      <div className={cx(styles['footer'])}>
        <StatusFooter />
      </div>

      {/*
        Rendered only on mobile, not merely CSS-hidden. Phase 6 Appendix H
        gives bottom navigation to mobile alone; leaving it in the DOM at
        desktop would duplicate every workspace link in the accessibility tree
        for no benefit.
      */}
      {isMobile ? (
        <div className={cx(styles['bottomNav'])}>
          <BottomNavigation
            onOpenDrawer={openSidebar}
            drawerExpanded={sidebarExpanded}
            drawerControlsId={SIDEBAR_ID}
          />
        </div>
      ) : null}
    </div>
  )
}
