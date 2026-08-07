/**
 * Workspace shell page — Phase 9 Workstream B (B6).
 *
 * A generic container standing in for all seven workspaces. It renders the
 * workspace title, an empty content region and placeholder regions — nothing
 * more. There is no business UI, no data and no API access anywhere in it.
 *
 * WHY this lives in app/shell rather than in src/domains/<workspace>/:
 *
 *   1. src/domains is Workstream D's territory. Filling it with placeholder
 *      pages that Workstream D immediately deletes creates churn and invites
 *      someone to grow the placeholder instead of replacing it.
 *   2. A shared container in a domain would have to be imported across
 *      workspace boundaries, which ADR-001 §4 forbids, or duplicated seven
 *      times.
 *
 * Workstream D replaces each route element here with the real workspace,
 * built inside its own domain directory.
 *
 * Accessibility (B12): exactly one <h1> per page (Phase 6 P6-44), and the
 * heading is focusable so route changes can move focus to it (P4-14 §20).
 */
import type { Workspace } from '../router/workspaces'
import { cx } from '@utils/cx'
import styles from './workspace-shell-page.module.css'

interface WorkspaceShellPageProps {
  readonly workspace: Workspace
  /** Resource identifier from the URL, when the route carries one. */
  readonly resourceId?: string | undefined
}

export function WorkspaceShellPage({ workspace, resourceId }: WorkspaceShellPageProps) {
  /*
   * Route-change focus (Phase 4 P4-14 §20) is NOT handled here. This component
   * is a route element, so it unmounts and remounts on every navigation — any
   * "did the route change?" state it kept would reset on the very transition it
   * needs to detect. AppShell owns it instead, because AppShell persists.
   *
   * The heading keeps tabIndex={-1} so the shell can target it.
   */

  return (
    <article className={cx(styles['page'])} aria-labelledby="workspace-title">
      {/* A <div>, not a <header>: the shell already owns the single banner
          landmark (Phase 4 P4-03 Zone B), and a second <header> muddies the
          landmark map for screen-reader users even where ARIA scoping would
          technically demote it. */}
      <div className={cx(styles['pageHeader'])}>
        <h1 id="workspace-title" tabIndex={-1} className={cx(styles['title'])}>
          {workspace.label}
          {resourceId ? <span className={cx(styles['resource'])}> · {resourceId}</span> : null}
        </h1>
        <p className={cx(styles['purpose'])}>{workspace.purpose}</p>
      </div>

      {/* Empty content region. Phase 4 P4-14 §6 forbids blank pages and
          spinner-only screens; an explicitly-labelled empty region is the
          honest representation of "built, but not yet populated". */}
      <section className={cx(styles['contentRegion'])} aria-label="Workspace content">
        <p className={cx(styles['placeholder'])}>
          Workspace shell. Content is delivered in Phase 9 Workstream D.
        </p>
      </section>

      {/* Placeholder regions. Region NAMES come from the frozen layout
          specification (Phase 4 Workspace Layout Spec §Reusable Regions); only
          their contents are pending. */}
      <section className={cx(styles['regions'])} aria-label="Reserved regions">
        {['Executive Summary', 'Primary Region', 'Context', 'Activity Timeline'].map((region) => (
          <div key={region} className={cx(styles['region'])}>
            <h2 className={cx(styles['regionTitle'])}>{region}</h2>
            <p className={cx(styles['placeholder'])}>Reserved</p>
          </div>
        ))}
      </section>
    </article>
  )
}
