/**
 * Accessibility harness tests — Phase 9 Workstream A (task A7).
 *
 * Two obligations, mirroring the architecture-guard suite:
 *
 *   1. the empty application is clean, and
 *   2. the harness demonstrably FAILS on a deliberate violation.
 *
 * (2) is the one that matters. An a11y check that cannot fail is worse than no
 * check, because it manufactures confidence. Phase 6 P6-42 treats accessibility
 * regressions as architectural defects; this proves the detector works before
 * any component depends on it.
 */
import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import App from '../App'
import { expectNoAccessibilityViolations, runAxe } from './axe'

describe('accessibility harness', () => {
  // Scans the whole application shell (Workstream B): header, sidebar,
  // workspace region, footer. Slower than the empty app it replaced, hence the
  // explicit timeout — axe walks a real tree under jsdom.
  it('reports no WCAG 2.2 AA violations for the application shell', async () => {
    const { container } = render(<App />)

    await expectNoAccessibilityViolations(container)
  }, 30_000)

  it('detects a deliberate violation (image without alt text)', async () => {
    const { container } = render(
      <main>
        <h1>Deliberate violation fixture</h1>
        {/* Intentional violation: no alt attribute. Proves the detector fires. */}
        <img src="/favicon.svg" />
      </main>,
    )

    const results = await runAxe(container)
    const ids = results.violations.map((v) => v.id)

    expect(ids).toContain('image-alt')
  })

  it('throws with a readable report when violations are present', async () => {
    const { container } = render(
      <main>
        <h1>Deliberate violation fixture</h1>
        {/* Intentional violation: no alt attribute. */}
        <img src="/favicon.svg" />
      </main>,
    )

    await expect(expectNoAccessibilityViolations(container)).rejects.toThrow(/image-alt/)
  })
})
