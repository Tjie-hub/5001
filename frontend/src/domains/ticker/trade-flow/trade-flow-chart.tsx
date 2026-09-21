/**
 * Trade Flow chart — dependency-free SVG dual-axis chart (the design
 * system has no chart primitive yet and the frontend carries no chart
 * library; this component is the local primitive, styled only with
 * component-scoped custom properties on top of the shell tokens).
 *
 * Left axis: cumulative Buy/Sell value (IDR, step lines). Right axis:
 * price (polyline). X: minute slots across the selected sessions, with a
 * separator at each session boundary. Hover shows a crosshair and a
 * tooltip with the bar's exact production values.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { TradeFlow } from '@models/ticker'
import {
  buildScales,
  formatAxisIdr,
  linePath,
  nearestIndex,
  priceTicks,
  stepPath,
  valueTicks,
  type ChartBox,
} from './chart-geometry'
import { formatSignedIdr, formatTooltipTime } from './trade-flow-view-model'
import styles from './trade-flow-section.module.css'

const BOX: ChartBox = {
  width: 0,
  height: 300,
  marginTop: 10,
  marginRight: 52,
  marginBottom: 26,
  marginLeft: 58,
}

export function TradeFlowChart({ flow }: { flow: TradeFlow }) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [width, setWidth] = useState(0)
  const [hover, setHover] = useState<number | null>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    // jsdom (and any environment without ResizeObserver) falls back to a
    // one-time measure — the chart still renders at a sane width.
    if (typeof ResizeObserver === 'undefined') {
      setWidth(el.getBoundingClientRect().width)
      return
    }
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) setWidth(entry.contentRect.width)
    })
    observer.observe(el)
    setWidth(el.getBoundingClientRect().width)
    return () => observer.disconnect()
  }, [])

  const { series, session_marks } = flow
  const points = series.points

  const scales = useMemo(() => {
    const valueMax = Math.max(...series.cum_buy, ...series.cum_sell, 1)
    let priceMin = Infinity
    let priceMax = -Infinity
    for (const p of series.price) {
      if (p < priceMin) priceMin = p
      if (p > priceMax) priceMax = p
    }
    if (!Number.isFinite(priceMin)) {
      priceMin = 0
      priceMax = 1
    }
    const pad = (priceMax - priceMin) * 0.08 || Math.max(priceMax * 0.01, 1)
    return buildScales(
      { ...BOX, width: Math.max(width, 120) },
      points,
      valueMax,
      priceMin - pad,
      priceMax + pad,
    )
  }, [series, width, points])

  const vTicks = useMemo(
    () => valueTicks(Math.max(...series.cum_buy, ...series.cum_sell, 1)),
    [series],
  )
  const pTicks = useMemo(() => {
    let priceMin = Infinity
    let priceMax = -Infinity
    for (const p of series.price) {
      if (p < priceMin) priceMin = p
      if (p > priceMax) priceMax = p
    }
    if (!Number.isFinite(priceMin)) return []
    const pad = (priceMax - priceMin) * 0.08 || Math.max(priceMax * 0.01, 1)
    return priceTicks(priceMin - pad, priceMax + pad, 4)
  }, [series])

  const onMove = useCallback(
    (event: React.MouseEvent<SVGSVGElement>) => {
      const rect = event.currentTarget.getBoundingClientRect()
      setHover(nearestIndex(event.clientX - rect.left, points, scales.x))
    },
    [points, scales],
  )

  const plotHeight = BOX.height - BOX.marginTop - BOX.marginBottom
  const plotBottom = BOX.marginTop + plotHeight

  const hoverX = hover !== null && hover < points ? scales.x(hover) : null

  return (
    <div ref={containerRef} className={styles['chartWrap']}>
      {points > 0 ? (
        <>
          <svg
            role="img"
            aria-label={`Trade flow chart, ${points} minutes: cumulative buy ${formatAxisIdr(
              series.cum_buy[points - 1] ?? 0,
            )}, cumulative sell ${formatAxisIdr(series.cum_sell[points - 1] ?? 0)}, net ${formatSignedIdr(
              series.net_flow[points - 1] ?? 0,
            )}`}
            width="100%"
            height={BOX.height}
            viewBox={`0 0 ${Math.max(width, 120)} ${BOX.height}`}
            preserveAspectRatio="none"
            onMouseMove={onMove}
            onMouseLeave={() => setHover(null)}
            className={styles['chartSvg']}
          >
            {/* value gridlines + left labels */}
            {vTicks.map((t) => (
              <g key={`v${t}`}>
                <line
                  x1={BOX.marginLeft}
                  x2={Math.max(width, 120) - BOX.marginRight}
                  y1={scales.yValue(t)}
                  y2={scales.yValue(t)}
                  className={styles['gridline']}
                />
                <text
                  x={BOX.marginLeft - 8}
                  y={scales.yValue(t) + 3}
                  textAnchor="end"
                  className={styles['axisLabel']}
                >
                  {formatAxisIdr(t)}
                </text>
              </g>
            ))}
            {/* price ticks + right labels */}
            {pTicks.map((t) => (
              <text
                key={`p${t}`}
                x={Math.max(width, 120) - BOX.marginRight + 8}
                y={scales.yPrice(t) + 3}
                textAnchor="start"
                className={styles['axisLabel']}
              >
                {t}
              </text>
            ))}
            {/* session separators */}
            {session_marks
              .filter((m) => m.index > 0)
              .map((m) => (
                <line
                  key={m.date}
                  x1={scales.x(m.index)}
                  x2={scales.x(m.index)}
                  y1={BOX.marginTop}
                  y2={plotBottom}
                  className={styles['sessionSeparator']}
                />
              ))}
            {/* series */}
            <path d={stepPath(series.cum_sell, scales.x, scales.yValue)} className={styles['sellLine']} />
            <path d={stepPath(series.cum_buy, scales.x, scales.yValue)} className={styles['buyLine']} />
            <path d={linePath(series.price, scales.x, scales.yPrice)} className={styles['priceLine']} />
            {/* crosshair */}
            {hoverX !== null ? (
              <line
                x1={hoverX}
                x2={hoverX}
                y1={BOX.marginTop}
                y2={plotBottom}
                className={styles['crosshair']}
              />
            ) : null}
          </svg>
          {hover !== null && hover < points ? (
            <div
              className={styles['tooltip']}
              style={{
                left: `${(hoverX! / Math.max(width, 120)) * 100}%`,
              }}
            >
              <span className={styles['tooltipTime']}>
                {formatTooltipTime(series.time[hover] ?? '')}
              </span>
              <span>
                <i className={`${styles['swatch']} ${styles['swatchBuy']}`} /> Buy{' '}
                {formatAxisIdr(series.cum_buy[hover] ?? 0)}
              </span>
              <span>
                <i className={`${styles['swatch']} ${styles['swatchSell']}`} /> Sell{' '}
                {formatAxisIdr(series.cum_sell[hover] ?? 0)}
              </span>
              <span>
                <i className={`${styles['swatch']} ${styles['swatchPrice']}`} /> Price{' '}
                {series.price[hover] ?? '—'}
              </span>
              <span>Net {formatSignedIdr(series.net_flow[hover] ?? 0)}</span>
            </div>
          ) : null}
        </>
      ) : (
        <p className={styles['emptyChart']}>No intraday flow minutes in this range.</p>
      )}
    </div>
  )
}
