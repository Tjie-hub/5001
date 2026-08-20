/**
 * Watchlist — Workstream D, first workspace built directly on the approved
 * ADR-003 architecture (Component -> ViewModel -> Domain Adapter ->
 * Repository -> Server State -> API Client -> Backend). Replaces the
 * generic WorkspaceShellPage for this one route only (app/router/
 * app-router.tsx), same override pattern Decision Center and Settings use.
 *
 * Structure follows PHASE_5_WIREFRAMES_v1.1 §5 exactly: Header, Summary
 * Metrics, Candidate List + Candidate Detail, Activity Timeline. Portfolio
 * Relevance and Market Context (named only in WATCHLIST_DESIGN_SPEC §8, not
 * in the implementation-ready wireframe) are omitted — no Portfolio or
 * Market /api/v1 read model exists yet to back them honestly; adding them
 * would mean fabricating data (forbidden by this slice's data-integrity
 * requirement), not implementing the spec.
 *
 * The frozen "Discovered -> Observed -> Strengthening -> Ready for
 * Investigation -> Decision Candidate -> Archived" lifecycle
 * (WATCHLIST_DESIGN_SPEC §10) has no backend representation — the real
 * backend lifecycle concepts are: per-day rank/confidence/conviction
 * (watchlist_snapshot), day-over-day diff status (added/removed/upgraded/
 * downgraded/unchanged), and multi-day persistence
 * (ACTIVE/REMOVED + consecutive_days). The UI presents those real states,
 * not the aspirational taxonomy — see the ViewModel/adapter docstrings.
 *
 * strategy/selectedDate/selectedTicker are Page State (local, not persisted,
 * not in the query cache — ADR-003 §5 row 4, N-7) since the frozen route is
 * flat "/watchlist" with no date or group segment.
 */
import { useState } from 'react'
import { Link } from 'react-router'
import { cx } from '@utils/cx'
import { useWatchlistViewModel } from './viewmodels/use-watchlist-view-model'
import type { WatchlistStrategy } from './adapters/use-watchlist-data'
import { CandidateCard } from './candidate-card'
import styles from './watchlist-page.module.css'

const STRATEGIES: { id: WatchlistStrategy; label: string }[] = [
  { id: 'eod', label: 'EOD' },
  { id: 'premarket', label: 'Premarket' },
]

export function WatchlistPage() {
  const [strategy, setStrategy] = useState<WatchlistStrategy>('eod')
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)

  const vm = useWatchlistViewModel(strategy, selectedDate)

  // Blocking: primary data failed to load at all, nothing safe to render
  // below it. Non-blocking: primary data DID load — PARTIAL_DATA/STALE_DATA
  // are shown as a banner alongside the content, never in place of it.
  const blockingError =
    vm.errorPresentation !== null &&
    vm.errorPresentation.state !== 'PARTIAL_DATA' &&
    vm.errorPresentation.state !== 'STALE_DATA'
  const nonBlockingNotice =
    vm.errorPresentation !== null &&
    (vm.errorPresentation.state === 'PARTIAL_DATA' || vm.errorPresentation.state === 'STALE_DATA')
  const showEmpty = !vm.showSkeleton && !blockingError && vm.isEmpty
  const showContent = !vm.showSkeleton && !blockingError && !vm.isEmpty

  function handleStrategyChange(next: WatchlistStrategy) {
    setStrategy(next)
    setSelectedDate(null)
    setSelectedTicker(null)
  }

  function handleDateChange(value: string) {
    setSelectedDate(value === '' ? null : value)
    setSelectedTicker(null)
  }

  return (
    <article className={cx(styles['page'])} aria-labelledby="workspace-title">
      <div className={cx(styles['pageHeader'])}>
        <h1 id="workspace-title" tabIndex={-1} className={cx(styles['title'])}>
          Watchlist
        </h1>
        <p className={cx(styles['purpose'])}>
          Track candidate evolution ahead of investigation or decision.
        </p>
      </div>

      <div className={cx(styles['controls'])}>
        <div className={cx(styles['strategyToggle'])} role="group" aria-label="Strategy">
          {STRATEGIES.map((s) => (
            <button
              key={s.id}
              type="button"
              className={cx(styles['strategyButton'])}
              aria-pressed={strategy === s.id}
              onClick={() => handleStrategyChange(s.id)}
            >
              {s.label}
            </button>
          ))}
        </div>

        {vm.historyGroups.length > 0 ? (
          <select
            className={cx(styles['datePicker'])}
            aria-label="Viewing date"
            value={selectedDate ?? ''}
            onChange={(e) => handleDateChange(e.target.value)}
          >
            <option value="">Latest</option>
            {vm.historyGroups.map((group) => (
              <optgroup key={group.month} label={group.month}>
                {group.dates.map((date) => (
                  <option key={date} value={date}>
                    {date}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        ) : null}

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
        <div
          className={cx(styles['region'])}
          role="status"
          aria-label="Loading watchlist"
        >
          <div className={cx(styles['skeleton'])} />
        </div>
      ) : null}

      {blockingError && vm.errorPresentation ? (
        <div className={cx(styles['region'])}>
          <ErrorBox presentation={vm.errorPresentation} onRetry={vm.refresh} />
        </div>
      ) : null}

      {nonBlockingNotice && vm.errorPresentation ? (
        <div className={cx(styles['region'])} role="alert">
          <ErrorBox presentation={vm.errorPresentation} onRetry={vm.refresh} />
        </div>
      ) : null}

      {showEmpty ? (
        <div className={cx(styles['region'])}>
          <p className={cx(styles['emptyState'])}>
            No watchlist snapshot yet for {strategy === 'eod' ? 'EOD Trade Plan' : 'Premarket Shortlist'}
            {vm.viewedDate ? ` on ${vm.viewedDate}` : ''}.
          </p>
        </div>
      ) : null}

      {showContent ? (
        <>
          {vm.summary ? (
            <section className={cx(styles['region'])} aria-label="Summary Metrics">
              <h2 className={cx(styles['regionTitle'])}>Summary Metrics</h2>
              <dl className={cx(styles['summaryGrid'])}>
                <div className={cx(styles['summaryStat'])}>
                  <dt>Candidates</dt>
                  <dd>{vm.summary.totalCandidates}</dd>
                </div>
                <div className={cx(styles['summaryStat'])}>
                  <dt>New</dt>
                  <dd>{vm.summary.addedCount}</dd>
                </div>
                <div className={cx(styles['summaryStat'])}>
                  <dt>Upgraded</dt>
                  <dd>{vm.summary.upgradedCount}</dd>
                </div>
                <div className={cx(styles['summaryStat'])}>
                  <dt>Downgraded</dt>
                  <dd>{vm.summary.downgradedCount}</dd>
                </div>
                <div className={cx(styles['summaryStat'])}>
                  <dt>Removed</dt>
                  <dd>{vm.summary.removedCount}</dd>
                </div>
              </dl>
              {!vm.summary.hasPriorSnapshot ? (
                <p className={cx(styles['emptyState'])}>No prior snapshot to compare yet.</p>
              ) : null}
            </section>
          ) : null}

          <section className={cx(styles['region'])} aria-label="Candidate Queue">
            <h2 className={cx(styles['regionTitle'])}>
              Candidate Queue{vm.viewedDate ? ` — ${vm.viewedDate}` : ''}
            </h2>
            <ul className={cx(styles['candidateList'])}>
              {vm.candidates.map((candidate) => (
                <CandidateCard
                  key={candidate.ticker}
                  candidate={candidate}
                  expanded={selectedTicker === candidate.ticker}
                  onToggle={() =>
                    setSelectedTicker((current) =>
                      current === candidate.ticker ? null : candidate.ticker,
                    )
                  }
                />
              ))}
            </ul>
          </section>

          <section className={cx(styles['region'])} aria-label="Activity Timeline">
            <h2 className={cx(styles['regionTitle'])}>Activity Timeline</h2>
            {vm.activity.length === 0 ? (
              <p className={cx(styles['emptyState'])}>No changes since the prior snapshot.</p>
            ) : (
              <ul className={cx(styles['activityList'])}>
                {vm.activity.map((entry, i) => (
                  <li key={`${entry.kind}-${entry.ticker}-${i}`} className={cx(styles['activityItem'])}>
                    <span className={cx(styles['activityTicker'])}>{entry.ticker}</span>
                    <span>{ACTIVITY_LABEL[entry.kind]}</span>
                    {entry.detailLabel ? (
                      <span className={cx(styles['activityDetail'])}>{entry.detailLabel}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}
    </article>
  )
}

const ACTIVITY_LABEL: Record<'added' | 'removed' | 'upgraded' | 'downgraded', string> = {
  added: 'added to the watchlist',
  removed: 'removed from the watchlist',
  upgraded: 'upgraded',
  downgraded: 'downgraded',
}

function ErrorBox({
  presentation,
  onRetry,
}: {
  presentation: NonNullable<ReturnType<typeof useWatchlistViewModel>['errorPresentation']>
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
