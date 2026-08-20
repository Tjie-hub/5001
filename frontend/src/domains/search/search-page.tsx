/**
 * Search — Production OS Slice 5, third workspace built directly on the
 * approved ADR-003 architecture after Watchlist and Market. Replaces the
 * generic WorkspaceShellPage for this one route only (app/router/
 * app-router.tsx), same override pattern the other real workspaces use.
 *
 * Populates Search Input & Query Context and Unified Search Results with
 * real instrument search over idx_tickers (GET /api/v1/search/instruments)
 * — the "Search Instrument" scenario in SEARCH_DESIGN_SPEC_v1.0_FROZEN.md
 * §5. Entity Preview is folded into each result card (index-membership
 * badges — the only real per-instrument data this endpoint returns; a
 * separate preview region would either duplicate that or fabricate content
 * that doesn't exist). Search Filters and Search History stay honest
 * "Reserved" placeholders — see adapters/use-search-data.ts's docstring
 * for why the spec's other four scenarios (watchlist candidate, portfolio
 * position, recommendation, market context) aren't attempted here: no
 * unified backend search service exists for them yet.
 *
 * `inputValue` is Page State (local, not persisted) — the frozen route is
 * flat "/search" with no query segment, same reasoning as Watchlist's
 * selectedDate.
 */
import { useState } from 'react'
import { Link } from 'react-router'
import { cx } from '@utils/cx'
import { useSearchViewModel } from './viewmodels/use-search-view-model'
import styles from './search-page.module.css'

const RESERVED_REGIONS = ['Search Filters', 'Search History']

export function SearchPage() {
  const [inputValue, setInputValue] = useState('')
  const vm = useSearchViewModel(inputValue)

  return (
    <article className={cx(styles['page'])} aria-labelledby="workspace-title">
      <div className={cx(styles['pageHeader'])}>
        <h1 id="workspace-title" tabIndex={-1} className={cx(styles['title'])}>
          Search
        </h1>
        <p className={cx(styles['purpose'])}>
          Find an instrument and navigate to it without leaving your context.
        </p>
      </div>

      <input
        type="search"
        className={cx(styles['searchInput'])}
        placeholder="Search by ticker code (e.g. BBCA)"
        aria-label="Search instruments"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
      />

      <section className={cx(styles['region'])} aria-label="Search Results">
        {vm.viewState === 'idle' ? (
          <p className={cx(styles['guidance'])}>
            Start typing a ticker code to search across active IDX instruments.
          </p>
        ) : null}

        {vm.viewState === 'searching' ? (
          <div role="status" aria-label="Searching">
            <div className={cx(styles['skeleton'])} />
          </div>
        ) : null}

        {vm.viewState === 'error' && vm.errorPresentation ? (
          <ErrorBox presentation={vm.errorPresentation} onRetry={vm.retry} />
        ) : null}

        {vm.viewState === 'no_results' ? (
          <p className={cx(styles['guidance'])}>No instruments match “{vm.query}”.</p>
        ) : null}

        {vm.viewState === 'results' ? (
          <ul className={cx(styles['resultList'])}>
            {vm.results.map((result) => (
              <li key={result.ticker}>
                <Link className={cx(styles['resultCard'])} to={`/ticker/${result.ticker}`}>
                  <span className={cx(styles['resultTicker'])}>{result.ticker}</span>
                  <span className={cx(styles['badgeRow'])}>
                    {result.badges.map((badge) => (
                      <span key={badge} className={cx(styles['badge'])}>
                        {badge}
                      </span>
                    ))}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        ) : null}
      </section>

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
  presentation: NonNullable<ReturnType<typeof useSearchViewModel>['errorPresentation']>
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
