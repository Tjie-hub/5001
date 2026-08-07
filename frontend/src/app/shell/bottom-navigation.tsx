/**
 * Bottom navigation — Phase 9 Workstream B (B3, B11).
 *
 * Mobile only. Phase 4 P4-03 §14 lists BOTH a navigation drawer and bottom
 * navigation for mobile, and Phase 6 Appendix H confirms
 * "Navigation | Sidebar | Sidebar | Bottom Navigation".
 *
 * Division of responsibility, so that NP-03 ("every workspace directly
 * reachable") and the "no hidden navigation" anti-pattern both hold:
 *
 *   drawer      the complete, ordered set of all seven workspaces — identical
 *               to the desktop sidebar. This is the navigation.
 *   bottom nav  a visible shortcut layer over the first four, plus an explicit
 *               control that opens the drawer.
 *
 * Nothing is hidden behind a gesture or an unlabelled affordance: every
 * workspace is reachable in at most two visible, labelled interactions.
 */
import { NavLink } from 'react-router'
import { WORKSPACES } from '../router/workspaces'
import { cx } from '@utils/cx'
import styles from './bottom-navigation.module.css'

/** Shortcut set. The drawer remains the complete navigation. */
const SHORTCUT_COUNT = 4

interface BottomNavigationProps {
  readonly onOpenDrawer: () => void
  readonly drawerExpanded: boolean
  readonly drawerControlsId: string
}

export function BottomNavigation({
  onOpenDrawer,
  drawerExpanded,
  drawerControlsId,
}: BottomNavigationProps) {
  return (
    <nav className={cx(styles['nav'])} aria-label="Quick access">
      <ul className={cx(styles['list'])}>
        {WORKSPACES.slice(0, SHORTCUT_COUNT).map((workspace) => (
          <li key={workspace.id} className={cx(styles['item'])}>
            <NavLink to={workspace.navPath} className={cx(styles['link'])}>
              {workspace.label}
            </NavLink>
          </li>
        ))}
        <li className={cx(styles['item'])}>
          <button
            type="button"
            className={cx(styles['link'])}
            onClick={onOpenDrawer}
            aria-expanded={drawerExpanded}
            aria-controls={drawerControlsId}
          >
            All workspaces
          </button>
        </li>
      </ul>
    </nav>
  )
}
