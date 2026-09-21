/**
 * Trade Flow chart geometry — pure functions, no React, no DOM.
 * Unit-tested in chart-geometry.test.ts; trade-flow-chart.tsx only maps
 * these onto SVG elements.
 */

export interface ChartBox {
  readonly width: number
  readonly height: number
  readonly marginTop: number
  readonly marginRight: number
  readonly marginBottom: number
  readonly marginLeft: number
}

export interface Scales {
  readonly plotWidth: number
  readonly plotHeight: number
  /** index (0..points-1) → x pixel; points ≤ 1 maps to the plot centre. */
  readonly x: (index: number) => number
  /** value → y pixel on the left (cumulative IDR) scale, top-clamped. */
  readonly yValue: (value: number) => number
  /** price → y pixel on the right (price) scale. */
  readonly yPrice: (price: number) => number
}

export function buildScales(
  box: ChartBox,
  points: number,
  valueMax: number,
  priceMin: number,
  priceMax: number,
): Scales {
  const plotWidth = Math.max(box.width - box.marginLeft - box.marginRight, 1)
  const plotHeight = Math.max(box.height - box.marginTop - box.marginBottom, 1)
  const x =
    points <= 1
      ? () => box.marginLeft + plotWidth / 2
      : (index: number) => box.marginLeft + (index / (points - 1)) * plotWidth
  const valueSpan = Math.max(valueMax, 1)
  const priceSpan = Math.max(priceMax - priceMin, 1e-9)
  return {
    plotWidth,
    plotHeight,
    x,
    yValue: (value: number) =>
      box.marginTop + plotHeight - (Math.min(Math.max(value, 0), valueMax) / valueSpan) * plotHeight,
    yPrice: (price: number) =>
      box.marginTop + plotHeight - ((price - priceMin) / priceSpan) * plotHeight,
  }
}

/** Step-after path (cumulative series hold their value between points). */
export function stepPath(
  values: readonly number[],
  x: (i: number) => number,
  y: (v: number) => number,
): string {
  const first = values[0]
  if (first === undefined) return ''
  let d = `M ${x(0).toFixed(2)} ${y(first).toFixed(2)}`
  for (let i = 1; i < values.length; i++) {
    const v = values[i]
    if (v === undefined) break
    d += ` H ${x(i).toFixed(2)} V ${y(v).toFixed(2)}`
  }
  return d
}

/** Straight polyline path (the price series is not cumulative). */
export function linePath(
  values: readonly number[],
  x: (i: number) => number,
  y: (v: number) => number,
): string {
  const first = values[0]
  if (first === undefined) return ''
  let d = `M ${x(0).toFixed(2)} ${y(first).toFixed(2)}`
  for (let i = 1; i < values.length; i++) {
    const v = values[i]
    if (v === undefined) break
    d += ` L ${x(i).toFixed(2)} ${y(v).toFixed(2)}`
  }
  return d
}

/** Rounds up to a "nice" axis maximum (1/2/2.5/5 × 10^k ≥ value). */
export function niceCeil(value: number): number {
  if (value <= 0) return 1
  const exponent = Math.floor(Math.log10(value))
  const base = 10 ** exponent
  const fraction = value / base
  const niceFraction =
    fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 2.5 ? 2.5 : fraction <= 5 ? 5 : 10
  return niceFraction * base
}

/** Compact IDR axis label without the Rp prefix ("0", "1.1 B", "850 M"). */
export function formatAxisIdr(value: number): string {
  const abs = Math.abs(value)
  const sign = value < 0 ? '-' : ''
  if (abs >= 1e12) return `${sign}${trimZeros(abs / 1e12)} T`
  if (abs >= 1e9) return `${sign}${trimZeros(abs / 1e9)} B`
  if (abs >= 1e6) return `${sign}${trimZeros(abs / 1e6)} M`
  if (abs >= 1e3) return `${sign}${trimZeros(abs / 1e3)} k`
  return `${sign}${abs}`
}

function trimZeros(n: number): string {
  return String(Math.round(n * 10) / 10)
}

/** Even value-axis ticks: count+1 labels from 0 to a nice maximum. */
export function valueTicks(valueMax: number, count = 4): number[] {
  const nice = niceCeil(valueMax)
  return Array.from({ length: count + 1 }, (_, i) => (nice / count) * i)
}

/** ~count price ticks across [min, max], rounded to readable steps. */
export function priceTicks(min: number, max: number, count = 4): number[] {
  if (!(max > min)) return [min]
  const rawStep = (max - min) / count
  const exponent = Math.floor(Math.log10(rawStep))
  const base = 10 ** exponent
  const step = Math.ceil(rawStep / base) * base
  const first = Math.ceil(min / step) * step
  const ticks: number[] = []
  for (let v = first; v <= max + 1e-9; v += step) ticks.push(Math.round(v * 100) / 100)
  return ticks
}

/** Index of the point whose x pixel is nearest `px` (clamped). */
export function nearestIndex(px: number, points: number, x: (i: number) => number): number {
  if (points === 0) return 0
  const clamped = Math.min(Math.max(px, x(0)), x(points - 1))
  const step = points > 1 ? (x(points - 1) - x(0)) / (points - 1) : 0
  if (step === 0) return 0
  return Math.min(points - 1, Math.max(0, Math.round((clamped - x(0)) / step)))
}
