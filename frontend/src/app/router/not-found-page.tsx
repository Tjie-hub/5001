/**
 * Route not found — Phase 9 Workstream B (B2, B7).
 *
 * Phase 4 P4-13 §17 maps an unknown route to 404, and P4-06 §11 requires that
 * "users shall always receive a recovery path". NP-07 forbids navigation dead
 * ends outright, and P4-05 §16 names the three valid escapes: Search, the
 * previous screen, and Home.
 *
 * Phase 6 P6-31 forbids technical detail in error messaging, so the path is
 * echoed back plainly without any router or stack context.
 */
import { Link, useLocation } from 'react-router'
import { ROUTE_PATHS } from './workspaces'
import { cx } from '@utils/cx'
import styles from './not-found-page.module.css'

export function NotFoundPage() {
  const { pathname } = useLocation()

  return (
    <article className={cx(styles['container'])}>
      <h1 className={cx(styles['title'])}>Page not found</h1>

      <p className={cx(styles['message'])}>
        No workspace owns <code className={cx(styles['path'])}>{pathname}</code>.
      </p>

      <nav className={cx(styles['actions'])} aria-label="Recovery">
        <Link className={cx(styles['action'])} to={ROUTE_PATHS.decision}>
          Decision Center
        </Link>
        <Link className={cx(styles['action'])} to={ROUTE_PATHS.search}>
          Search
        </Link>
        <Link className={cx(styles['action'])} to={ROUTE_PATHS.home}>
          Home
        </Link>
      </nav>
    </article>
  )
}
