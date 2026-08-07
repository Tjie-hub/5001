/**
 * Status Footer — Phase 9 Workstream B (B5).
 *
 * Zone D (Phase 4 P4-03 §3). Displays application status and is "purely
 * informational" — it owns no navigation, no actions and no business state.
 *
 * Frozen contents: Environment · Snapshot Version · Connection Status ·
 * Time Zone · Version.
 *
 * All values are static placeholders. Environment, snapshot version and
 * connection status are backend-owned (blocker U-2) and the connectivity model
 * belongs to ADR-003 §13, which is Workstream E's. Time zone is the one value
 * that is genuinely known here: the whole system is WIB by definition.
 */
import { cx } from '@utils/cx'
import styles from './status-footer.module.css'

interface FooterItem {
  readonly label: string
  readonly value: string
}

const ITEMS: readonly FooterItem[] = [
  { label: 'Environment', value: '—' },
  { label: 'Snapshot', value: '—' },
  { label: 'Connection', value: '—' },
  { label: 'Time zone', value: 'WIB (UTC+7)' },
  { label: 'Version', value: '0.0.0' },
]

export function StatusFooter() {
  return (
    /*
     * tabIndex={0} because the footer scrolls horizontally on narrow viewports.
     * A scroll container that cannot receive focus is unreachable by keyboard
     * (axe: scrollable-region-focusable, WCAG 2.1.1) — the content would be
     * visible to a mouse user and unreachable to everyone else. It adds a tab
     * stop, not an interactive control: the footer stays purely informational
     * per P4-03 Zone D.
     */
    <footer className={cx(styles['footer'])} tabIndex={0} aria-label="Application status">
      <dl className={cx(styles['list'])}>
        {ITEMS.map((item) => (
          <div key={item.label} className={cx(styles['item'])}>
            <dt className={cx(styles['label'])}>{item.label}</dt>
            <dd className={cx(styles['value'])}>{item.value}</dd>
          </div>
        ))}
      </dl>
    </footer>
  )
}
