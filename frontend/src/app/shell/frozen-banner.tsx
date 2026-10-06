/**
 * Frontend freeze banner — owner-directed 2026-10-06.
 *
 * One thin line at the top of every remaining SPA workspace (rendered once
 * from AppShell, above the global header) announcing the freeze and pointing
 * at the jurnal26 app that now owns portfolio, watchlist and daily research.
 *
 * Plain text and a link only: no dismiss state, no new dependencies. The div
 * carries no landmark role — the app's single `banner` landmark stays the
 * global header (P6-44).
 */
import { cx } from '@utils/cx'
import { jurnal26Url } from './jurnal26-url'
import styles from './frozen-banner.module.css'

export function FrozenBanner() {
  return (
    <div className={cx(styles['banner'])} data-testid="frozen-banner">
      5001 frontend is frozen. Portfolio, watchlist and daily research:{' '}
      <a className={cx(styles['link'])} href={jurnal26Url()}>
        <strong>jurnal26 :5004</strong>
      </a>
    </div>
  )
}
