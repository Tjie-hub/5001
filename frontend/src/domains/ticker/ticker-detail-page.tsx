/**
 * Ticker Detail — Production OS Ticker workspace, D4 slice 1. Replaces the
 * generic WorkspaceShellPage for the /ticker/:symbol route only (same
 * override pattern Decision Center, Watchlist, Market and Search use); the
 * /ticker index stays on the placeholder shell.
 *
 * All four workspace regions render production-derived data from
 * GET /api/v1/tickers/:symbol (engine.ticker_detail):
 *   Executive Summary — live price, flow verdict, foreign accumulation,
 *                       the production admission chain's verdicts (incl.
 *                       blocking stages — audit S-1 observability), latest
 *                       watchlist membership, paper position, latest scan
 *                       signal.
 *   Primary Region    — the ticker's detected regime band (the same
 *                       detect_regime + ADX banding the scanner routes on).
 *   Context           — market context from the same aggregator as the
 *                       Market workspace, plus sector and per-source data
 *                       freshness.
 *   Activity Timeline — merged production events: scan signals, watchlist
 *                       snapshot memberships, agent-firm decisions, paper
 *                       trade open/close.
 *
 * No value is invented client-side: every field maps 1:1 to backend state,
 * and absent state renders as an em-dash or an explicit "none" sentence.
 */
import { useParams } from 'react-router'
import { Link } from 'react-router'
import { useTickerViewModel } from './viewmodels/use-ticker-view-model'
import { TradeFlowSection } from './trade-flow/trade-flow-section'
import { cx } from '@utils/cx'
import styles from './ticker-detail-page.module.css'

export function TickerDetailPage() {
  const { symbol = '' } = useParams<{ symbol: string }>()
  const vm = useTickerViewModel(symbol.toUpperCase())

  // Blocking: the detail failed to load at all, nothing safe to render
  // below it. Non-blocking: data DID load — STALE_DATA is a banner
  // alongside the content, never in place of it.
  const blockingError = vm.errorPresentation !== null && vm.errorPresentation.state !== 'STALE_DATA'
  const nonBlockingNotice = vm.errorPresentation !== null && vm.errorPresentation.state === 'STALE_DATA'
  const showContent = !vm.showSkeleton && !blockingError

  return (
    <article className={cx(styles['page'])} aria-labelledby="workspace-title">
      <div className={cx(styles['pageHeader'])}>
        <h1 id="workspace-title" tabIndex={-1} className={cx(styles['title'])}>
          Ticker · {symbol.toUpperCase()}
        </h1>
        <p className={cx(styles['purpose'])}>
          Production detail for one instrument — the same data the scanner
          and trade plan act on.
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
        <div className={cx(styles['region'])} role="status" aria-label="Loading ticker detail">
          <div className={cx(styles['skeleton'])} />
        </div>
      ) : null}

      {blockingError && vm.errorPresentation ? (
        <div className={cx(styles['region'])}>
          <ErrorBox presentation={vm.errorPresentation} onRetry={vm.refresh} />
        </div>
      ) : null}

      {showContent ? (
        <>
          {nonBlockingNotice && vm.errorPresentation ? (
            <div role="alert" style={{ marginBlockEnd: '0.75rem' }}>
              <ErrorBox presentation={vm.errorPresentation} onRetry={vm.refresh} />
            </div>
          ) : null}

          <section className={cx(styles['region'])} aria-label="Executive Summary">
            <h2 className={cx(styles['regionTitle'])}>Executive Summary</h2>

            <div className={cx(styles['summaryHeadline'])}>
              <span className={cx(styles['price'])}>{vm.priceLabel}</span>
              <span className={cx(styles['chg'])}>{vm.chgPctLabel}</span>
              {vm.priceDateLabel !== '—' ? (
                <span className={cx(styles['dateLabel'])}>as of {vm.priceDateLabel}</span>
              ) : null}
            </div>

            <dl className={cx(styles['summaryGrid'])}>
              <div className={cx(styles['stat'])}>
                <dt>Flow verdict</dt>
                <dd>
                  {vm.flowVerdictLabel} · score {vm.flowScoreLabel} ·{' '}
                  {vm.flowNetValueLabel}
                </dd>
              </div>
              <div className={cx(styles['stat'])}>
                <dt>Foreign accumulation (5d)</dt>
                <dd>{vm.foreignAccLabel}</dd>
              </div>
              <div className={cx(styles['stat'])}>
                <dt>Admissible strategies ({vm.admissionBandLabel})</dt>
                <dd>{vm.admissibleLabel}</dd>
              </div>
              <div className={cx(styles['stat'])}>
                <dt>Production watchlist</dt>
                <dd>{vm.watchlistLabel}</dd>
              </div>
              <div className={cx(styles['stat'])}>
                <dt>Paper position</dt>
                <dd>{vm.positionLabel}</dd>
              </div>
              <div className={cx(styles['stat'])}>
                <dt>Latest scan signal</dt>
                <dd>{vm.latestSignalLabel}</dd>
              </div>
            </dl>

            {vm.admissionBlockers.length > 0 ? (
              <div className={cx(styles['blockers'])}>
                <h3 className={cx(styles['blockersTitle'])}>
                  Why nothing is admissible right now
                </h3>
                <ul className={cx(styles['blockerList'])}>
                  {vm.admissionBlockers.map((b) => (
                    <li key={b.strategy}>
                      <strong>{b.strategy}</strong> — {humaniseStage(b.stage)}:{' '}
                      {b.reason}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>

          <TradeFlowSection symbol={symbol.toUpperCase()} />

          <section className={cx(styles['region'])} aria-label="Primary Region">
            <h2 className={cx(styles['regionTitle'])}>Primary Region</h2>
            <dl className={cx(styles['summaryGrid'])}>
              <div className={cx(styles['stat'])}>
                <dt>Regime</dt>
                <dd>{vm.regimeLabel}</dd>
              </div>
              <div className={cx(styles['stat'])}>
                <dt>Scan band</dt>
                <dd>{vm.regimeBandLabel}</dd>
              </div>
              <div className={cx(styles['stat'])}>
                <dt>Strength</dt>
                <dd>{vm.adxLabel}</dd>
              </div>
            </dl>
          </section>

          <section className={cx(styles['region'])} aria-label="Context">
            <h2 className={cx(styles['regionTitle'])}>Context</h2>
            <dl className={cx(styles['summaryGrid'])}>
              <div className={cx(styles['stat'])}>
                <dt>Sector</dt>
                <dd>{vm.sectorLabel}</dd>
              </div>
              <div className={cx(styles['stat'])}>
                <dt>Market risk score</dt>
                <dd>
                  {vm.marketRiskLabel} · {vm.marketTierLabel}
                </dd>
              </div>
              <div className={cx(styles['stat'])}>
                <dt>IHSG close</dt>
                <dd>{vm.ihsgCloseLabel}</dd>
              </div>
              <div className={cx(styles['stat'])}>
                <dt>Market breadth</dt>
                <dd>{vm.breadthLabel}</dd>
              </div>
              <div className={cx(styles['stat'])}>
                <dt>Market foreign flow (5d)</dt>
                <dd>{vm.foreign5dLabel}</dd>
              </div>
              <div className={cx(styles['stat'])}>
                <dt>Data freshness</dt>
                <dd>{vm.freshnessLabel}</dd>
              </div>
            </dl>
          </section>

          <section className={cx(styles['region'])} aria-label="Activity Timeline">
            <h2 className={cx(styles['regionTitle'])}>Activity Timeline</h2>
            {vm.timeline.length > 0 ? (
              <ol className={cx(styles['timeline'])}>
                {vm.timeline.map((event, index) => (
                  <li key={`${event.at}-${index}`} className={cx(styles['timelineItem'])}>
                    <span className={cx(styles['timelineAt'])}>{event.at}</span>
                    <span className={cx(styles['timelineSummary'])}>{event.summary}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className={cx(styles['notice'])}>No production events recorded yet.</p>
            )}
          </section>
        </>
      ) : null}
    </article>
  )
}

function humaniseStage(stage: string): string {
  return stage
    .split('_')
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(' ')
}

function ErrorBox({
  presentation,
  onRetry,
}: {
  presentation: { title: string; message: string; recoveryActions: readonly string[] }
  onRetry: () => void
}) {
  return (
    <div role="alert" className={cx(styles['errorBox'])}>
      <p className={cx(styles['errorTitle'])}>{presentation.title}</p>
      <p className={cx(styles['errorMessage'])}>{presentation.message}</p>
      <div className={cx(styles['errorActions'])}>
        {presentation.recoveryActions.includes('retry') ? (
          <button type="button" className={cx(styles['refreshButton'])} onClick={onRetry}>
            Retry
          </button>
        ) : null}
        {presentation.recoveryActions.includes('goToSearch') ? (
          <Link to="/search" className={cx(styles['errorLink'])}>
            Search instruments
          </Link>
        ) : null}
        {presentation.recoveryActions.includes('goToDecisionCenter') ? (
          <Link to="/decision" className={cx(styles['errorLink'])}>
            Go to Decision Center
          </Link>
        ) : null}
      </div>
    </div>
  )
}
