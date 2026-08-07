// Named import, not default: the package is CJS, and under
// verbatimModuleSyntax + nodenext a default import resolves to the module
// namespace rather than the class.
import { AxeBuilder } from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

/**
 * End-to-end accessibility scan — Phase 9 Workstream A (task A7).
 *
 * Component-level a11y is covered by src/tests/accessibility.test.tsx; this
 * scans the assembled document, which is where landmark, heading-order and
 * contrast problems actually surface.
 *
 * Phase 6 P6-42 / P6-45 target WCAG 2.2 Level AA. Tags are pinned rather than
 * left at axe's default so the standard is explicit and cannot silently drift.
 */
const WCAG_22_AA_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']

test('application has no WCAG 2.2 AA violations', async ({ page }) => {
  await page.goto('/')

  const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA_TAGS).analyze()

  expect(results.violations).toEqual([])
})
