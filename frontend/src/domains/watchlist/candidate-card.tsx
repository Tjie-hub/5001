/**
 * Candidate Card — Component layer (ADR-003 §4.1): rendering + presentation-
 * only interaction (expand/collapse), no domain rule, no fetch. Receives an
 * already-formatted CandidateViewModel; never sees raw API data.
 *
 * Ticker/Decision Center navigation uses literal route paths rather than
 * importing @app/router/workspaces — the composition root direction rule
 * (Phase 7 v1.1 §8, tools/eslint/architecture-boundaries.js
 * COMPOSITION_ROOT_DENIAL) forbids a workspace importing from src/app. The
 * seven canonical paths are the frozen, external contract this domain
 * targets, not something Watchlist owns.
 */
import { Link } from 'react-router'
import { cx } from '@utils/cx'
import type { CandidateViewModel } from './viewmodels/use-watchlist-view-model'
import styles from './candidate-card.module.css'

export function CandidateCard({
  candidate,
  expanded,
  onToggle,
}: {
  candidate: CandidateViewModel
  expanded: boolean
  onToggle: () => void
}) {
  const detailId = `candidate-detail-${candidate.ticker}`

  return (
    <li className={cx(styles['card'])}>
      <button
        type="button"
        className={cx(styles['summaryButton'])}
        aria-expanded={expanded}
        aria-controls={detailId}
        onClick={onToggle}
      >
        <span className={cx(styles['rank'])}>{candidate.rank}</span>
        <span className={cx(styles['ticker'])}>
          <span className={cx(styles['tickerSymbol'])}>{candidate.ticker}</span>
          {candidate.streakLabel ? (
            <span className={cx(styles['streak'])}>{candidate.streakLabel}</span>
          ) : null}
        </span>
        <span className={cx(styles['indicators'])}>
          {candidate.rankChangeLabel ? (
            <span
              className={cx(styles['rankChange'])}
              data-direction={candidate.rankChangeLabel.startsWith('▲') ? 'up' : 'down'}
            >
              {candidate.rankChangeLabel}
            </span>
          ) : null}
          {candidate.diffStatus && candidate.diffStatus !== 'unchanged' ? (
            <span className={cx(styles['badge'])} data-status={candidate.diffStatus}>
              {candidate.diffStatus}
            </span>
          ) : null}
          <span className={cx(styles['confidence'])}>{candidate.confidencePct}</span>
        </span>
      </button>

      {expanded ? (
        <div id={detailId} className={cx(styles['detail'])}>
          <dl className={cx(styles['detailGrid'])}>
            <div>
              <dt>Conviction</dt>
              <dd>{candidate.convictionLabel}</dd>
            </div>
            <div>
              <dt>Confluence</dt>
              <dd>{candidate.confluence}</dd>
            </div>
            {candidate.scoreDeltaLabel ? (
              <div>
                <dt>Score change</dt>
                <dd>{candidate.scoreDeltaLabel}</dd>
              </div>
            ) : null}
          </dl>

          {candidate.sources.length > 0 ? (
            <ul className={cx(styles['sources'])} aria-label="Supporting signals">
              {candidate.sources.map((source) => (
                <li key={source} className={cx(styles['sourceChip'])}>
                  {source}
                </li>
              ))}
            </ul>
          ) : null}

          <div className={cx(styles['detailActions'])}>
            <Link className={cx(styles['detailAction'])} to={`/ticker/${candidate.ticker}`}>
              View Ticker
            </Link>
            <Link className={cx(styles['detailAction'])} to="/decision">
              Open Decision Center
            </Link>
          </div>
        </div>
      ) : null}
    </li>
  )
}
