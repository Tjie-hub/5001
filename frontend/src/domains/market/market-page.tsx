/**
 * Market — Production OS Slice 4, first workspace built directly on the
 * approved ADR-003 architecture after Watchlist. Replaces the generic
 * WorkspaceShellPage for this one route only (app/router/app-router.tsx),
 * same override pattern Decision Center, Settings and Watchlist use.
 *
 * Populates only the Executive Summary region with real backend market
 * state (risk score/tier, IHSG technicals, breadth, foreign flow, VPIN,
 * accumulation/distribution — all from GET /api/v1/market/summary, which
 * wraps the pre-existing engine.dashboard.get_risk_dashboard() aggregator).
 * The other three reserved regions (Primary Region, Context, Activity
 * Timeline) stay placeholders — honestly "not yet built" rather than
 * fabricated, same pattern Decision Center established. See
 * adapters/use-market-data.ts's docstring for why MARKET_DESIGN_SPEC's own
 * named regions (Regime Analysis, Sector Rotation, Historical Evolution,
 * Portfolio Impact) aren't attempted in this slice: no backing data exists
 * for them yet, and building UI for data that isn't there would be
 * fabrication, not implementation.
 */
import { useMarketViewModel } from './viewmodels/use-market-view-model'
import { cx } from '@utils/cx'
import { Link } from 'react-router'
import styles from './market-page.module.css'

const RESERVED_REGIONS = ['Primary Region', 'Context', 'Activity Timeline']

export function MarketPage() {
  const vm = useMarketViewModel(null)

  // Blocking: the summary failed to load at all, nothing safe to render
  // below it. Non-blocking: data DID load — STALE_DATA is a banner
  // alongside the content, never in place of it.
  const blockingError = vm.errorPresentation !== null && vm.errorPresentation.state !== 'STALE_DATA'
  const nonBlockingNotice = vm.errorPresentation !== null && vm.errorPresentation.state === 'STALE_DATA'
  const showContent = !vm.showSkeleton && !blockingError

  return (
    <article className={cx(styles['page'])} aria-labelledby="workspace-title">
      <div className={cx(styles['pageHeader'])}>
        <h1 id="workspace-title" tabIndex={-1} className={cx(styles['title'])}>
          Market
        </h1>
        <p className={cx(styles['purpose'])}>
          Understand the shared market environment used across workspaces.
        </p>
      </div>

      <div className={cx(styles['controls'])}>
        <button type="button" className={cx(styles['refreshButton'])} onClick={vm.refresh}>
          Refresh
        </button>
        {vm.showBackgroundIndicator ? (
          <span className={cx(styles['backgroundIndicator'])} aria-live="polite">
            Updating…
          </span>
        ) : null}
      </div>

      {vm.showSkeleton ? (
        <div className={cx(styles['region'])} role="status" aria-label="Loading market summary">
          <div className={cx(styles['skeleton'])} />
        </div>
      ) : null}

      {blockingError && vm.errorPresentation ? (
        <div className={cx(styles['region'])}>
          <ErrorBox presentation={vm.errorPresentation} onRetry={vm.refresh} />
        </div>
      ) : null}

      {showContent ? (
        <section className={cx(styles['region'])} aria-label="Executive Market Summary">
          <h2 className={cx(styles['regionTitle'])}>Executive Market Summary</h2>

          {nonBlockingNotice && vm.errorPresentation ? (
            <div role="alert" style={{ marginBlockEnd: '0.75rem' }}>
              <ErrorBox presentation={vm.errorPresentation} onRetry={vm.refresh} />
            </div>
          ) : null}

          {vm.isInsufficientData ? (
            <p className={cx(styles['notice'])}>
              Insufficient market data for {vm.date ?? 'this date'} — showing degraded sensor
              readings rather than fabricated values.
            </p>
          ) : null}

          <div className={cx(styles['summaryHeadline'])}>
            <span className={cx(styles['riskScore'])}>{vm.riskScoreLabel ?? '—'}</span>
            <span className={cx(styles['riskTier'])}>{vm.riskTierLabel ?? '—'}</span>
            {vm.date ? <span className={cx(styles['dateLabel'])}>as of {vm.date}</span> : null}
          </div>

          <dl className={cx(styles['summaryGrid'])}>
            <div className={cx(styles['stat'])}>
              <dt>IHSG Close</dt>
              <dd>{vm.ihsgCloseLabel}</dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>MA5 / MA20</dt>
              <dd>
                {vm.ihsgMa5Label} / {vm.ihsgMa20Label}
              </dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>YTD</dt>
              <dd>{vm.ihsgYtdLabel}</dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>Death Cross</dt>
              <dd>{vm.deathCross ? 'Active' : 'No'}</dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>Breadth</dt>
              <dd>{vm.breadthLabel}</dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>Advancers / Decliners</dt>
              <dd>
                {vm.advancers} / {vm.decliners}
              </dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>% Above MA20</dt>
              <dd>{vm.pctAboveMa20Label}</dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>Foreign Flow (5d)</dt>
              <dd>
                {vm.foreignFlow5dLabel} · {vm.foreignFlowTrend}
              </dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>VPIN</dt>
              <dd>{vm.vpinLabel}</dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>Accumulation / Distribution</dt>
              <dd>{vm.accdistLabel}</dd>
            </div>
          </dl>
        </section>
      ) : null}

      <section className={cx(styles['regions'])} aria-label="Reserved regions">
        {RESERVED_REGIONS.map((region) => (
          <div key={region} className={cx(styles['reservedRegion'])}>
            <h2 className={cx(styles['regionTitle'])}>{region}</h2>
            <p className={cx(styles['placeholder'])}>Reserved</p>
          </div>
        ))}
      </section>
    </article>
  )
}

function ErrorBox({
  presentation,
  onRetry,
}: {
  presentation: NonNullable<ReturnType<typeof useMarketViewModel>['errorPresentation']>
  onRetry: () => void
}) {
  return (
    <div className={cx(styles['errorBox'])}>
      <p className={cx(styles['errorTitle'])}>{presentation.title}</p>
      <p className={cx(styles['errorMessage'])}>{presentation.message}</p>
      <div className={cx(styles['recoveryActions'])}>
        {presentation.recoveryActions.includes('retry') ? (
          <button type="button" className={cx(styles['recoveryButton'])} onClick={onRetry}>
            Retry
          </button>
        ) : null}
        {presentation.recoveryActions.includes('goToDecisionCenter') ? (
          <Link className={cx(styles['recoveryButton'])} to="/decision">
            Decision Center
          </Link>
        ) : null}
      </div>
    </div>
  )
}
