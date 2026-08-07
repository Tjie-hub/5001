/**
 * Application loading shell — Phase 9 Workstream B (B10).
 *
 * Phase 4 P4-14 §6 is explicit about initial loading:
 *
 *   displays  — Application Shell, Header, Sidebar, Workspace Skeleton
 *   forbidden — blank pages, empty layouts, SPINNER-ONLY screens
 *
 * So the loading state is the shell itself with a placeholder content region,
 * not an overlay and not a spinner. Navigation stays visible and usable while
 * a route resolves (P4-14 §7: "navigation remains available").
 *
 * ADR-003 §12.1 draws the line this must respect once data arrives:
 * `isPending` may drive a skeleton; `isFetching` must never. That rule binds
 * Workstream E — the placeholder here is route-level, not data-level.
 *
 * Real skeleton components are Phase 6 P6-32 and belong to Workstream C.
 */
import { cx } from '@utils/cx'
import styles from './loading-shell.module.css'

export function WorkspaceLoadingPlaceholder() {
  return (
    <div className={cx(styles['region'])} role="status" aria-live="polite">
      <span className="sr-only">Loading workspace</span>
      <div className={cx(styles['bar'])} aria-hidden="true" />
      <div className={cx(styles['barShort'])} aria-hidden="true" />
      <div className={cx(styles['block'])} aria-hidden="true" />
    </div>
  )
}
