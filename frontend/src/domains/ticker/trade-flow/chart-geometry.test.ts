import { describe, expect, it } from 'vitest'
import {
  buildScales,
  formatAxisIdr,
  linePath,
  nearestIndex,
  niceCeil,
  priceTicks,
  stepPath,
  valueTicks,
} from './chart-geometry'

const box = {
  width: 500,
  height: 200,
  marginTop: 10,
  marginRight: 50,
  marginLeft: 50,
  marginBottom: 20,
}

describe('buildScales', () => {
  it('maps index 0..n-1 across the plot width', () => {
    const s = buildScales(box, 5, 100, 0, 10)
    expect(s.plotWidth).toBe(400)
    expect(s.plotHeight).toBe(170)
    expect(s.x(0)).toBe(50)
    expect(s.x(4)).toBe(450)
  })

  it('maps a single point to the plot centre', () => {
    const s = buildScales(box, 1, 100, 0, 10)
    expect(s.x(0)).toBe(250)
  })

  it('maps value axis top-down and clamps below zero', () => {
    const s = buildScales(box, 2, 100, 0, 10)
    expect(s.yValue(100)).toBe(10) // top
    expect(s.yValue(0)).toBe(180) // bottom
    expect(s.yValue(-50)).toBe(180) // clamped
  })

  it('maps price right-side axis', () => {
    const s = buildScales(box, 2, 100, 100, 200)
    expect(s.yPrice(200)).toBe(10)
    expect(s.yPrice(100)).toBe(180)
  })
})

describe('paths', () => {
  it('stepPath holds values between points', () => {
    const s = buildScales(box, 3, 100, 0, 10)
    const d = stepPath([0, 100], s.x, s.yValue)
    expect(d).toBe('M 50.00 180.00 H 250.00 V 10.00')
  })

  it('linePath is a straight polyline', () => {
    const s = buildScales(box, 3, 100, 0, 10)
    const d = linePath([0, 100], s.x, s.yValue)
    expect(d).toBe('M 50.00 180.00 L 250.00 10.00')
  })

  it('empty series produce empty paths', () => {
    expect(stepPath([], (i) => i, (v) => v)).toBe('')
    expect(linePath([], (i) => i, (v) => v)).toBe('')
  })
})

describe('niceCeil / ticks', () => {
  it('rounds up to 1/2/2.5/5 × 10^k', () => {
    expect(niceCeil(8.9e9)).toBe(1e10)
    expect(niceCeil(6.7e9)).toBe(1e10)
    expect(niceCeil(2.2e9)).toBe(2.5e9)
    expect(niceCeil(0)).toBe(1)
  })

  it('valueTicks span 0..nice with count+1 labels', () => {
    expect(valueTicks(8.9e9, 4)).toEqual([0, 2.5e9, 5e9, 7.5e9, 1e10])
  })

  it('priceTicks produce readable steps inside the domain', () => {
    const ticks = priceTicks(443, 458, 4)
    expect(ticks[0]).toBeGreaterThanOrEqual(443)
    expect(ticks[ticks.length - 1]).toBeLessThanOrEqual(458)
    for (let i = 1; i < ticks.length; i++) {
      const prev = ticks[i - 1]
      const curr = ticks[i]
      if (prev !== undefined && curr !== undefined) {
        expect(curr).toBeGreaterThan(prev)
      }
    }
  })

  it('priceTicks on a flat series returns the single level', () => {
    expect(priceTicks(450, 450, 4)).toEqual([450])
  })
})

describe('formatAxisIdr', () => {
  it('formats billions and millions like the reference axis', () => {
    expect(formatAxisIdr(0)).toBe('0')
    expect(formatAxisIdr(1.1e9)).toBe('1.1 B')
    expect(formatAxisIdr(8.9e9)).toBe('8.9 B')
    expect(formatAxisIdr(850e6)).toBe('850 M')
    expect(formatAxisIdr(-2.2e9)).toBe('-2.2 B')
  })
})

describe('nearestIndex', () => {
  it('finds the closest point and clamps', () => {
    const s = buildScales(box, 5, 100, 0, 10)
    expect(nearestIndex(49, 5, s.x)).toBe(0)
    expect(nearestIndex(251, 5, s.x)).toBe(2)
    expect(nearestIndex(9999, 5, s.x)).toBe(4)
    expect(nearestIndex(0, 0, s.x)).toBe(0)
  })
})
