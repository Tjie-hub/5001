/**
 * Status Footer — Phase 9 Workstream B (B5).
 *
 * Zone D (Phase 4 P4-03 §3). Displays application status and is "purely
 * informational" — it owns no navigation, no actions and no business state.
 *
 * Frozen contents: Environment · Snapshot Version · Connection Status ·
 * Time Zone · Version.
 *
 * D4 slice 1 (2026-09-02) — blocker U-2's footer values are now
 * backend-owned in fact, not just in intent: GET /api/v1/runtime
 * (engine.platform_info.get_runtime_status) supplies Environment (derived
 * from utils.release's source distinction), the latest production
 * Snapshot (watchlist_snapshot), Connection (engine.health's overall
 * component state — the fetch itself is the connectivity signal), and
 * Version. Values render as '—' while loading; the footer never fabricates
 * a fallback. Time zone is the one value genuinely known here: the whole
 * system is WIB by definition.
 */
import { cx } from '@utils/cx'
import { useRuntimeStatusQuery } from '@domains/ticker/repository/queries'
import styles from './status-footer.module.css'

interface FooterItem {
  readonly label: string
  readonly value: string
}

export function StatusFooter() {
  const query = useRuntimeStatusQuery()
  const status = query.data ?? null

  const snapshotLabel = status?.snapshot
    ? `${status.snapshot.date} · ${status.snapshot.strategy}`
    : '—'
  const connectionLabel = status?.overall ?? '—'

  const ITEMS: readonly FooterItem[] = [
    { label: 'Environment', value: status?.environment ?? '—' },
    { label: 'Snapshot', value: snapshotLabel },
    { label: 'Connection', value: connectionLabel },
    { label: 'Time zone', value: 'WIB (UTC+7)' },
    { label: 'Version', value: status?.version ?? '—' },
  ]

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
