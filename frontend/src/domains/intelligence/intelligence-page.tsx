/**
 * Investment Intelligence — consolidation slice (2026-09-03).
 *
 * The intelligence layer the Investment Dashboard (ex-port 5003) fed from
 * the outside: one workspace that composes the canonical portfolio summary
 * (data/investments.py, absorbed from 5003) with the read models that were
 * already in the OS — watchlist signals, persistent opportunities, market
 * risk and the Edge Registry. It owns no data: the portfolio is owned by
 * the Portfolio workspace/page and stored once, in walkforward.db.
 *
 * Built on the approved ADR-003 chain (Component -> ViewModel -> Domain
 * Adapter -> Repository -> API Client); composed reads go through the
 * shared api/ layer, never through other domains (cross-workspace rule).
 */
import { useState } from 'react'
import { Link } from 'react-router'
import { useIntelligenceViewModel, type IntelligenceTab } from './viewmodels/use-intelligence-view-model'
import { cx } from '@utils/cx'
import styles from './intelligence-page.module.css'

export function IntelligencePage() {
  const vm = useIntelligenceViewModel()
  const [tab, setTab] = useState<IntelligenceTab>('Dashboard')

  return (
    <article className={cx(styles['page'])} aria-labelledby="workspace-title">
      <div className={cx(styles['pageHeader'])}>
        <h1 id="workspace-title" tabIndex={-1} className={cx(styles['title'])}>
          Investment Intelligence
        </h1>
        <p className={cx(styles['purpose'])}>
          Synthesize the canonical portfolio with signals, opportunities, risk and decisions.
        </p>
      </div>

      <div className={cx(styles['controls'])}>
        <div className={cx(styles['tabBar'])} role="tablist" aria-label="Intelligence sections">
          {vm.tabs.map((t) => (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={tab === t}
              className={cx(styles['tab'], tab === t && styles['tabActive'])}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
        </div>
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
        <div className={cx(styles['region'])} role="status" aria-label="Loading investment intelligence">
          <div className={cx(styles['skeleton'])} />
        </div>
      ) : null}

      {vm.fatalPresentation ? (
        <div className={cx(styles['region'])}>
          <ErrorBox presentation={vm.fatalPresentation} onRetry={vm.refresh} />
        </div>
      ) : null}

      {!vm.showSkeleton && !vm.fatalPresentation ? (
        <>
          {tab === 'Dashboard' ? <DashboardTab vm={vm} /> : null}
          {tab === 'Signals' ? <SignalsTab vm={vm} /> : null}
          {tab === 'Opportunities' ? <OpportunitiesTab vm={vm} /> : null}
          {tab === 'Risk' ? <RiskTab vm={vm} /> : null}
          {tab === 'Decisions' ? <DecisionsTab vm={vm} /> : null}
          {tab === 'Research' ? <ResearchTab vm={vm} /> : null}
        </>
      ) : null}
    </article>
  )
}

function DashboardTab({ vm }: { vm: ReturnType<typeof useIntelligenceViewModel> }) {
  return (
    <section className={cx(styles['region'])} aria-label="Investment dashboard">
      <h2 className={cx(styles['regionTitle'])}>Investment Dashboard</h2>

      {vm.summaryPresentation ? (
        <InlineError presentation={vm.summaryPresentation} onRetry={vm.refresh} />
      ) : vm.summaryPending ? (
        <p className={cx(styles['notice'])}>Loading portfolio summary…</p>
      ) : (
        <>
          <div className={cx(styles['statGrid'])}>
            <div className={cx(styles['stat'])}>
              <dt>Portfolio Value</dt>
              <dd>{vm.portfolioValueLabel}</dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>Equity Cost Basis</dt>
              <dd>{vm.equityCostBasisLabel}</dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>Unrealized P&amp;L</dt>
              <dd className={cx(styles[vm.unrealizedSign])}>
                {vm.unrealizedLabel}{' '}
                <span className={cx(styles['statSub'])}>{vm.unrealizedPctLabel}</span>
              </dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>Realized P&amp;L</dt>
              <dd>{vm.realizedLabel}</dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>Dividends (net)</dt>
              <dd>{vm.dividendsLabel}</dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>Total Return</dt>
              <dd className={cx(styles[vm.totalReturnSign])}>
                {vm.totalReturnLabel}{' '}
                <span className={cx(styles['statSub'])}>{vm.totalReturnPctLabel}</span>
              </dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>Open Positions</dt>
              <dd>{vm.openPositionsLabel}</dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>Mutual Funds</dt>
              <dd>{vm.fundOpenLabel}</dd>
            </div>
          </div>

          <h3 className={cx(styles['subTitle'])}>Allocation by open position</h3>
          {vm.allocation.length ? (
            <ul className={cx(styles['allocList'])}>
              {vm.allocation.map((a) => (
                <li key={a.ticker} className={cx(styles['allocRow'])}>
                  <Link to={`/ticker/${a.ticker}`} className={cx(styles['allocTicker'])}>
                    {a.ticker}
                  </Link>
                  <span className={cx(styles['allocValue'])}>{a.valueLabel}</span>
                  <span className={cx(styles['allocPct'])}>{a.pctLabel}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className={cx(styles['notice'])}>
              No open equity positions — record transactions in the Portfolio workspace.
            </p>
          )}
          <p className={cx(styles['notice'])}>
            Data source: the canonical portfolio ledger (one store, shared with the{' '}
            <Link to="/portfolio">Portfolio</Link> page). No duplicated portfolio database exists.
          </p>
        </>
      )}
    </section>
  )
}

function SignalsTab({ vm }: { vm: ReturnType<typeof useIntelligenceViewModel> }) {
  return (
    <section className={cx(styles['region'])} aria-label="Signals">
      <h2 className={cx(styles['regionTitle'])}>Signals — current watchlist</h2>
      {vm.watchlistPresentation ? (
        <InlineError presentation={vm.watchlistPresentation} onRetry={vm.refresh} />
      ) : vm.watchlistPending ? (
        <p className={cx(styles['notice'])}>Loading watchlist…</p>
      ) : vm.watchlistEmpty || vm.watchlistEntries.length === 0 ? (
        <p className={cx(styles['notice'])}>
          No watchlist snapshot for {vm.watchlistDateLabel ?? 'today'} yet.
        </p>
      ) : (
        <>
          <p className={cx(styles['notice'])}>
            Snapshot {vm.watchlistDateLabel} · {vm.watchlistEntries.length} candidates. Full
            history and diffs live in the <Link to="/watchlist">Watchlist</Link> workspace.
          </p>
          <table className={cx(styles['table'])}>
            <thead>
              <tr>
                <th scope="col">Rank</th>
                <th scope="col">Ticker</th>
                <th scope="col" className={cx(styles['num'])}>Confidence</th>
                <th scope="col" className={cx(styles['num'])}>Conviction</th>
                <th scope="col">Sources</th>
              </tr>
            </thead>
            <tbody>
              {vm.watchlistEntries.map((e) => (
                <tr key={e.ticker}>
                  <td>{e.rank}</td>
                  <td>
                    <Link to={`/ticker/${e.ticker}`}>{e.ticker}</Link>
                  </td>
                  <td className={cx(styles['num'])}>{e.confidence.toFixed(3)}</td>
                  <td className={cx(styles['num'])}>{e.conviction.toFixed(3)}</td>
                  <td>{e.sources.join(', ') || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  )
}

function OpportunitiesTab({ vm }: { vm: ReturnType<typeof useIntelligenceViewModel> }) {
  return (
    <section className={cx(styles['region'])} aria-label="Opportunities">
      <h2 className={cx(styles['regionTitle'])}>Opportunities — persistent watchlist</h2>
      {vm.persistentPresentation ? (
        <InlineError presentation={vm.persistentPresentation} onRetry={vm.refresh} />
      ) : vm.persistentPending ? (
        <p className={cx(styles['notice'])}>Loading persistent watchlist…</p>
      ) : vm.persistentEmpty || vm.persistentEntries.length === 0 ? (
        <p className={cx(styles['notice'])}>No active persistent candidates.</p>
      ) : (
        <table className={cx(styles['table'])}>
          <thead>
            <tr>
              <th scope="col">Ticker</th>
              <th scope="col" className={cx(styles['num'])}>Consecutive days</th>
              <th scope="col" className={cx(styles['num'])}>Total appearances</th>
              <th scope="col">First added</th>
            </tr>
          </thead>
          <tbody>
            {vm.persistentEntries.map((e) => (
              <tr key={e.ticker}>
                <td>
                  <Link to={`/ticker/${e.ticker}`}>{e.ticker}</Link>
                </td>
                <td className={cx(styles['num'])}>{e.consecutiveDays}</td>
                <td className={cx(styles['num'])}>{e.totalAppearances}</td>
                <td>{e.firstAdded}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

function RiskTab({ vm }: { vm: ReturnType<typeof useIntelligenceViewModel> }) {
  return (
    <section className={cx(styles['region'])} aria-label="Risk">
      <h2 className={cx(styles['regionTitle'])}>Risk — market environment</h2>
      {vm.marketPresentation ? (
        <InlineError presentation={vm.marketPresentation} onRetry={vm.refresh} />
      ) : vm.marketPending ? (
        <p className={cx(styles['notice'])}>Loading market risk…</p>
      ) : (
        <>
          <div className={cx(styles['riskHeadline'])}>
            <span className={cx(styles['riskScore'])}>{vm.riskScoreLabel ?? '—'}</span>
            <span className={cx(styles['riskTier'])}>{vm.riskTierLabel ?? '—'}</span>
          </div>
          <dl className={cx(styles['statGrid'])}>
            <div className={cx(styles['stat'])}>
              <dt>IHSG Close</dt>
              <dd>{vm.ihsgCloseLabel}</dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>Breadth</dt>
              <dd>{vm.breadthLabel}</dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>Foreign Flow (5d)</dt>
              <dd>{vm.foreignFlowLabel}</dd>
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
          <p className={cx(styles['notice'])}>
            The full market picture lives in the <Link to="/market">Market</Link> workspace.
          </p>
        </>
      )}
    </section>
  )
}

function DecisionsTab({ vm }: { vm: ReturnType<typeof useIntelligenceViewModel> }) {
  return (
    <section className={cx(styles['region'])} aria-label="Decisions">
      <h2 className={cx(styles['regionTitle'])}>Decisions — Edge Registry</h2>
      {vm.registryPresentation ? (
        <InlineError presentation={vm.registryPresentation} onRetry={vm.refresh} />
      ) : vm.registryPending ? (
        <p className={cx(styles['notice'])}>Loading registry…</p>
      ) : (
        <>
          <div className={cx(styles['statGrid'])}>
            <div className={cx(styles['stat'])}>
              <dt>Approved strategies</dt>
              <dd>{vm.approvedCountLabel}</dd>
            </div>
            <div className={cx(styles['stat'])}>
              <dt>Shadow strategies</dt>
              <dd>{vm.shadowCountLabel}</dd>
            </div>
          </div>
          {vm.registryEntries.length ? (
            <table className={cx(styles['table'])}>
              <thead>
                <tr>
                  <th scope="col">Strategy</th>
                  <th scope="col">Status</th>
                  <th scope="col">Regimes</th>
                </tr>
              </thead>
              <tbody>
                {vm.registryEntries.map((e) => (
                  <tr key={e.id}>
                    <td>{e.id}</td>
                    <td>{e.status}</td>
                    <td>{e.regimes.join(', ') || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          <p className={cx(styles['notice'])}>
            Decision priorities and production state live in the{' '}
            <Link to="/decision">Decision Center</Link>.
          </p>
        </>
      )}
    </section>
  )
}

function ResearchTab({ vm }: { vm: ReturnType<typeof useIntelligenceViewModel> }) {
  return (
    <section className={cx(styles['region'])} aria-label="Research">
      <h2 className={cx(styles['regionTitle'])}>Research — portfolio-aware entry points</h2>
      {vm.researchHoldings.length ? (
        <>
          <p className={cx(styles['notice'])}>Start from your largest open positions:</p>
          <ul className={cx(styles['allocList'])}>
            {vm.researchHoldings.map((h) => (
              <li key={h.ticker} className={cx(styles['allocRow'])}>
                <Link to={`/ticker/${h.ticker}`} className={cx(styles['allocTicker'])}>
                  {h.ticker}
                </Link>
                <span className={cx(styles['allocValue'])}>{h.valueLabel}</span>
                <span className={cx(styles['allocPct'])}>{h.pctLabel}</span>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className={cx(styles['notice'])}>
          No open positions yet — research any instrument via <Link to="/search">Search</Link>.
        </p>
      )}
    </section>
  )
}

function InlineError({
  presentation,
  onRetry,
}: {
  presentation: NonNullable<ReturnType<typeof useIntelligenceViewModel>['fatalPresentation']>
  onRetry: () => void
}) {
  return (
    <div className={cx(styles['errorBox'])} role="alert">
      <p className={cx(styles['errorTitle'])}>{presentation.title}</p>
      <p className={cx(styles['errorMessage'])}>{presentation.message}</p>
      <div className={cx(styles['recoveryActions'])}>
        {presentation.recoveryActions.includes('retry') ? (
          <button type="button" className={cx(styles['recoveryButton'])} onClick={onRetry}>
            Retry
          </button>
        ) : null}
      </div>
    </div>
  )
}

function ErrorBox({
  presentation,
  onRetry,
}: {
  presentation: NonNullable<ReturnType<typeof useIntelligenceViewModel>['fatalPresentation']>
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
