/**
 * Frozen workspace page — owner-directed 2026-10-06.
 *
 * The retirement page the removed workspaces' old paths resolve to. The 5001
 * frontend freeze removed the portfolio, intelligence and watchlist
 * workspaces because they duplicated or mis-stated the jurnal26 ledger; old
 * bookmarks and stale links must still land on a real page — never a blank
 * SPA error or a 404 — that points at jurnal26 (port 5004).
 *
 * The freeze banner itself renders once from AppShell on every route; this
 * page adds the workspace-specific context and, for /portfolio, the note that
 * the underlying 5001 investment store stopped at 2026-04-14 and is no longer
 * maintained. Its API routes (/api/v1/investments*) are kept — only the UI
 * surface was retired.
 *
 * Accessibility (P6-44): exactly one <h1>, focusable so route changes can
 * move focus to it (P4-14 §20).
 */
import { cx } from '@utils/cx'
import { jurnal26Url } from '../shell/jurnal26-url'
import styles from './frozen-workspace-page.module.css'

/** The stopped-at note required on the /portfolio retirement page. */
export const PORTFOLIO_FROZEN_NOTE =
  'This portfolio store stopped at 2026-04-14 and is no longer maintained.'

export interface FrozenWorkspacePageProps {
  /** Human name of the retired workspace, for the page context. */
  readonly retired: string
  /** Optional extra sentence (e.g. the /portfolio stopped-at note). */
  readonly note?: string | undefined
}

export function FrozenWorkspacePage({ retired, note }: FrozenWorkspacePageProps) {
  return (
    <article className={cx(styles['container'])}>
      <h1 tabIndex={-1} className={cx(styles['title'])}>
        Workspace frozen
      </h1>

      <p className={cx(styles['message'])}>
        The {retired} workspace was removed on 2026-10-06 — the 5001 frontend is frozen, and
        jurnal26 is the live ledger for portfolio, watchlist and daily research.
      </p>

      {note ? <p className={cx(styles['note'])}>{note}</p> : null}

      <p className={cx(styles['message'])}>
        Continue in{' '}
        <a className={cx(styles['link'])} href={jurnal26Url()}>
          jurnal26 :5004
        </a>
        .
      </p>
    </article>
  )
}
