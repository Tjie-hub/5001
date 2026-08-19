import { useProductionSummary } from './hooks'
import { cx } from '@utils/cx'
import styles from './decision-page.module.css'

const RESERVED_REGIONS = ['Primary Region', 'Context', 'Activity Timeline']

/**
 * Decision Center — Workstream D, first real workspace slice. Replaces the
 * generic WorkspaceShellPage for this one route only (app/router/
 * app-router.tsx), same override pattern OperationsPage already uses.
 *
 * Populates only the Executive Summary region with real Production OS
 * state (scheduler, Edge Registry admission, current watchlist) read
 * through the already-frozen /api/v1 surface. The other three reserved
 * regions (Primary Region, Context, Activity Timeline) stay placeholders —
 * honestly "not yet built" rather than fabricated, same as before.
 */
export function DecisionPage() {
  const { data, loading, error } = useProductionSummary()

  return (
    <article className={cx(styles['page'])} aria-labelledby="workspace-title">
      <div className={cx(styles['pageHeader'])}>
        <h1 id="workspace-title" tabIndex={-1} className={cx(styles['title'])}>
          Decision Center
        </h1>
        <p className={cx(styles['purpose'])}>
          Evaluate, prioritise and act on investment recommendations.
        </p>
      </div>

      <section className={cx(styles['contentRegion'])} aria-label="Workspace content">
        <h2 className={cx(styles['regionTitle'])}>Executive Summary</h2>

        {loading ? <p className={cx(styles['status'])}>Loading production state…</p> : null}

        {error ? (
          <p className={cx(styles['error'])} role="alert">
            Failed to load production state: {error}
          </p>
        ) : null}

        {data ? (
          <dl className={cx(styles['summary'])}>
            <div className={cx(styles['stat'])}>
              <dt>Scheduler</dt>
              <dd>
                {data.scheduler.available ? data.scheduler.state : 'unavailable'}
                {data.scheduler.available
                  ? ` · ${data.scheduler.job_count} jobs registered`
                  : ''}
              </dd>
            </div>

            <div className={cx(styles['stat'])}>
              <dt>Admission</dt>
              <dd>
                {data.registry.approved} approved · {data.registry.shadow} shadow
              </dd>
            </div>

            <div className={cx(styles['stat'])}>
              <dt>Live Capital</dt>
              <dd>
                {data.registry.approved === 0
                  ? 'No approved strategies'
                  : data.registry.entries
                      .filter((e) => e.status === 'APPROVED')
                      .map((e) => e.id)
                      .join(', ')}
              </dd>
            </div>

            <div className={cx(styles['stat'])}>
              <dt>Shadow</dt>
              <dd>
                {data.registry.shadow === 0
                  ? 'None'
                  : data.registry.entries
                      .filter((e) => e.status === 'SHADOW')
                      .map((e) => e.id)
                      .join(', ')}
              </dd>
            </div>

            <div className={cx(styles['stat'])}>
              <dt>Production Signals</dt>
              <dd>
                {data.watchlist === null
                  ? 'No production signals yet'
                  : data.watchlist.watchlist.length === 0
                    ? 'None'
                    : `${data.watchlist.watchlist.length} tickers (${data.watchlist.strategy}, ${data.watchlist.date})`}
              </dd>
            </div>
          </dl>
        ) : null}
      </section>

      <section className={cx(styles['regions'])} aria-label="Reserved regions">
        {RESERVED_REGIONS.map((region) => (
          <div key={region} className={cx(styles['region'])}>
            <h2 className={cx(styles['regionTitle'])}>{region}</h2>
            <p className={cx(styles['placeholder'])}>Reserved</p>
          </div>
        ))}
      </section>
    </article>
  )
}
