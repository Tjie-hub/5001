/**
 * Trade Flow section — Ticker workspace region rendering the cumulative
 * buy/sell trade flow over a selectable date range, with the price line
 * overlaid and a Net Distribution ↔ Net Accumulation indicator.
 *
 * UX is functionally modelled on the Stockbit trade-flow reference
 * (Chart/Price/Time view chips, ‹ date range ›, All Trades / Big Money,
 * Value metric), backed only by what production data actually supports:
 *   * Big Money is disabled — the backend reports no trade-size
 *     classification exists (big_money.available=false + reason).
 *   * Investor / trade-type dropdowns render the backend's
 *     filters_supported lists only (today: All Investor, Regular).
 *   * Metric renders filters_supported.metric (today: Value only).
 *   * Sessions without ingested bars are shown as an explicit gap note —
 *     never fabricated, never forward-filled.
 */
import { useId } from 'react'
import type { TradeFlow } from '@models/ticker'
import { TradeFlowChart } from './trade-flow-chart'
import {
  formatSessionDate,
  formatSignedIdr,
  markerPct,
  netShare,
  netStateLabel,
  useTradeFlowViewModel,
  type Range,
} from './trade-flow-view-model'
import styles from './trade-flow-section.module.css'

const GENERIC_BIG_MONEY_REASON = 'Unavailable: no production definition yet'

export function TradeFlowSection({ symbol }: { symbol: string }) {
  const vm = useTradeFlowViewModel(symbol)
  const headingId = useId()

  return (
    <section className={styles['section']} aria-labelledby={headingId}>
      <div className={styles['header']}>
        <h3 id={headingId} className={styles['title']}>
          Trade Flow
        </h3>
        {vm.flow ? <NetChip flow={vm.flow} /> : null}
      </div>

      {vm.isPending ? (
        <div className={styles['skeleton']} role="status" aria-label="Loading trade flow" />
      ) : vm.errorState !== null ? (
        <div role="alert" className={styles['errorBox']}>
          Trade Flow failed to load ({vm.errorState}).{' '}
          <button type="button" className={styles['navButton']} onClick={vm.refresh}>
            Retry
          </button>
        </div>
      ) : vm.flow ? (
        <FlowControls flow={vm.flow} vm={vm} />
      ) : null}
    </section>
  )
}

function NetChip({ flow }: { flow: TradeFlow }) {
  const side = flow.totals.net_side
  return (
    <span
      className={`${styles['netChip']} ${
        side === 'accumulation'
          ? styles['netChipAcc']
          : side === 'distribution'
            ? styles['netChipDist']
            : ''
      }`}
    >
      {netStateLabel(side)} · {formatSignedIdr(flow.totals.net_value)}
    </span>
  )
}

function FlowControls({
  flow,
  vm,
}: {
  flow: TradeFlow
  vm: ReturnType<typeof useTradeFlowViewModel>
}) {
  const bigMoneyReason = flow.big_money.available ? '' : flow.big_money.reason
  const share = netShare(flow.totals.buy_value, flow.totals.sell_value)

  return (
    <>
      <div className={styles['controls']}>
        <button
          type="button"
          className={styles['navButton']}
          onClick={vm.goPrev}
          disabled={!vm.canGoPrev}
          aria-label="Previous day"
        >
          ‹
        </button>
        <input
          type="date"
          className={styles['dateInput']}
          value={vm.range?.start ?? flow.requested.start}
          min={vm.bounds?.first}
          max={vm.bounds?.last}
          onChange={(e) =>
            e.target.value &&
            vm.setRange({ start: e.target.value, end: vm.range?.end ?? flow.requested.end } as Range)
          }
          aria-label="Range start"
        />
        <span aria-hidden="true">→</span>
        <input
          type="date"
          className={styles['dateInput']}
          value={vm.range?.end ?? flow.requested.end}
          min={vm.bounds?.first}
          max={vm.bounds?.last}
          onChange={(e) =>
            e.target.value &&
            vm.setRange({ start: vm.range?.start ?? flow.requested.start, end: e.target.value } as Range)
          }
          aria-label="Range end"
        />
        <button
          type="button"
          className={styles['navButton']}
          onClick={vm.goNext}
          disabled={!vm.canGoNext}
          aria-label="Next day"
        >
          ›
        </button>
        <span className={styles['rangeChip']}>
          {formatSessionDate(flow.requested.start)} → {formatSessionDate(flow.requested.end)}
        </span>

        <span className={styles['segmentGroup']}>
          <button type="button" className={`${styles['segmentButton']} ${styles['segmentButtonActive']}`}>
            All Trades
          </button>
          <button
            type="button"
            className={styles['segmentButton']}
            disabled
            title={bigMoneyReason || GENERIC_BIG_MONEY_REASON}
          >
            Big Money
          </button>
        </span>

        <select
          className={styles['select']}
          defaultValue={flow.metric}
          aria-label="Metric"
          title="The only metric the underlying data supports today"
        >
          {flow.filters_supported.metric.map((m) => (
            <option key={m} value={m}>
              {m.charAt(0).toUpperCase() + m.slice(1)}
            </option>
          ))}
        </select>

        <select
          className={styles['select']}
          defaultValue="all"
          aria-label="Investor"
          title="Investor split is not available in intraday flow data"
        >
          {flow.filters_supported.investor.map((i) => (
            <option key={i} value={i}>
              {i === 'all' ? 'All Investor' : i}
            </option>
          ))}
        </select>

        <select
          className={styles['select']}
          defaultValue="regular"
          aria-label="Trade type"
          title="Only the regular board is ingested"
        >
          {flow.filters_supported.trade_type.map((t) => (
            <option key={t} value={t}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </option>
          ))}
        </select>
      </div>

      <TradeFlowChart flow={flow} />

      <div className={styles['legend']} aria-hidden="true">
        <span>
          <i className={`${styles['swatch']} ${styles['swatchBuy']}`} /> Buy (cum)
        </span>
        <span>
          <i className={`${styles['swatch']} ${styles['swatchSell']}`} /> Sell (cum)
        </span>
        <span>
          <i className={`${styles['swatch']} ${styles['swatchPrice']}`} /> Price
        </span>
      </div>

      <div className={styles['netBarWrap']}>
        <span>Net Dist</span>
        <div
          className={styles['netBar']}
          role="img"
          aria-label={`Net flow ${formatSignedIdr(flow.totals.net_value)} — ${netStateLabel(
            flow.totals.net_side,
          )}`}
        >
          <span className={styles['netMarker']} style={{ left: `${markerPct(share)}%` }} />
        </div>
        <span>Net Acc</span>
      </div>

      <dl className={styles['totalsRow']}>
        <div>
          <dt>Buy (cum)</dt>
          <dd className={styles['buyValue']}>{formatSignedIdr(flow.totals.buy_value)}</dd>
        </div>
        <div>
          <dt>Sell (cum)</dt>
          <dd className={styles['sellValue']}>{formatSignedIdr(flow.totals.sell_value)}</dd>
        </div>
        <div>
          <dt>Net flow</dt>
          <dd>
            {formatSignedIdr(flow.totals.net_value)} · {netStateLabel(flow.totals.net_side)}
          </dd>
        </div>
        <div>
          <dt>Sessions</dt>
          <dd>
            {flow.sessions.map((s) => s.date).join(', ') || 'none in range'}
          </dd>
        </div>
      </dl>

      {flow.missing_sessions.length > 0 ? (
        <p className={`${styles['notice']} ${styles['warning']}`}>
          No intraday flow data (shown, not fabricated):{' '}
          {flow.missing_sessions.map(formatSessionDate).join(', ')}
        </p>
      ) : null}
      {flow.anomaly_minutes > 0 ? (
        <p className={styles['notice']}>
          {flow.anomaly_minutes} minute(s) carried vendor revisions (price gaps / downward
          corrections); affected deltas were clamped, not dropped.
        </p>
      ) : null}
      {!flow.big_money.available ? (
        <p className={styles['notice']}>Big Money: {flow.big_money.reason}</p>
      ) : null}
    </>
  )
}
