/**
 * Global Header — Phase 9 Workstream B (B4).
 *
 * Zone B (Phase 4 P4-03 §3). Contains global application controls and is
 * identical across every workspace.
 *
 * Frozen contents: Search · Notifications · User Menu · Environment Indicator ·
 * Snapshot Status · Help.
 *
 * MUST NEVER own (P4-11 §5): workspace filters, business actions, security
 * analysis, portfolio controls.
 *
 * Everything except navigation and the theme toggle is a PLACEHOLDER. There is
 * no backend integration in Workstream B, and the endpoints these would read
 * do not exist yet (blockers U-2, U-4). Placeholders are rendered as disabled
 * controls rather than working-looking ones, so the shell never implies a
 * capability it does not have.
 */
import { Link } from 'react-router'
import { useTheme } from '../providers/use-theme'
import { ROUTE_PATHS } from '../router/workspaces'
import { cx } from '@utils/cx'
import styles from './global-header.module.css'

interface GlobalHeaderProps {
  readonly onToggleSidebar: () => void
  readonly sidebarExpanded: boolean
  readonly sidebarControlsId: string
}

export function GlobalHeader({
  onToggleSidebar,
  sidebarExpanded,
  sidebarControlsId,
}: GlobalHeaderProps) {
  const { theme, toggleTheme } = useTheme()

  return (
    <header className={cx(styles['header'])}>
      <button
        type="button"
        className={cx(styles['action'], styles['toggle'])}
        onClick={onToggleSidebar}
        aria-expanded={sidebarExpanded}
        aria-controls={sidebarControlsId}
      >
        <span aria-hidden="true">☰</span>
        <span className="sr-only"> {sidebarExpanded ? 'Hide' : 'Show'} workspace navigation</span>
      </button>

      <p className={cx(styles['title'])}>
        <Link to={ROUTE_PATHS.home} className={cx(styles['titleLink'])}>
          Production Decision OS
        </Link>
      </p>

      {/* Global Search is part of Global Navigation (P4-03 §16) and navigates
          to the Search workspace. It never renders analytical content itself
          (SNS-02). The input surface is Workstream D's. */}
      <Link to={ROUTE_PATHS.search} className={cx(styles['search'])}>
        Search…
      </Link>

      <span className={cx(styles['spacer'])} />

      <span className={cx(styles['status'])}>
        <span className={cx(styles['statusLabel'])}>Env</span>
        <span className={cx(styles['statusValue'])}>—</span>
      </span>

      <span className={cx(styles['status'])}>
        <span className={cx(styles['statusLabel'])}>Snapshot</span>
        <span className={cx(styles['statusValue'])}>—</span>
      </span>

      <button type="button" className={cx(styles['action'])} onClick={toggleTheme}>
        <span aria-hidden="true">{theme === 'dark' ? '☾' : '☀'}</span>
        <span className="sr-only"> Switch to {theme === 'dark' ? 'light' : 'dark'} theme</span>
      </button>

      <button
        type="button"
        className={cx(styles['action'])}
        disabled
        title="Available in a later phase"
      >
        Notifications
      </button>

      <button
        type="button"
        className={cx(styles['action'])}
        disabled
        title="Available in a later phase"
      >
        Account
      </button>
    </header>
  )
}
