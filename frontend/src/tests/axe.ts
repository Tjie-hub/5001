/**
 * Accessibility assertion helper — Phase 9 Workstream A (task A7).
 *
 * Phase 6 P6-42 makes accessibility an architectural requirement and states
 * that "accessibility regressions are considered architectural defects". This
 * helper is how that is enforced at the component level; @axe-core/playwright
 * covers the assembled page in tests/e2e.
 *
 * axe-core is used directly rather than through a matcher wrapper: the wrapper
 * libraries lag Vitest releases, and the surface we need is one function.
 */
import axe, { type AxeResults, type ElementContext, type RunOptions } from 'axe-core'

/**
 * WCAG 2.2 Level AA — the target named in Phase 6 P6-42 and P6-45, and in the
 * Phase 4 accessibility appendix. Earlier levels are included because AA is
 * cumulative.
 */
export const WCAG_22_AA_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] as const

/**
 * Rules that cannot produce a meaningful result under jsdom.
 *
 * color-contrast needs a real layout and canvas to sample rendered pixels;
 * jsdom has neither, so axe logs "getContext() not implemented" and returns
 * nothing useful. Disabling it here is not a waiver — contrast is asserted
 * against a real browser in tests/e2e/accessibility.spec.ts, which is where
 * Phase 6 P6-45's contrast requirements are actually verifiable.
 */
const JSDOM_UNSUPPORTED_RULES = {
  'color-contrast': { enabled: false },
} as const

/**
 * axe-core refuses to run two analyses at once ("Axe is already running").
 * Vitest happily runs tests concurrently within a worker, so calls are chained
 * through a single promise. Serialising here rather than forcing tests to be
 * sequential keeps the constraint where it belongs — with the library that has
 * it — instead of leaking into every suite that wants an a11y assertion.
 */
let axeQueue: Promise<unknown> = Promise.resolve()

export async function runAxe(
  container: ElementContext,
  options: RunOptions = {},
): Promise<AxeResults> {
  const run = axeQueue.then(() =>
    axe.run(container, {
      runOnly: { type: 'tag', values: [...WCAG_22_AA_TAGS] },
      rules: { ...JSDOM_UNSUPPORTED_RULES, ...options.rules },
      ...options,
    }),
  )

  // Keep the chain alive even when a run rejects.
  axeQueue = run.catch(() => undefined)

  return run
}

/** Format violations into something a failing test can be read from. */
export function formatViolations(results: AxeResults): string {
  if (results.violations.length === 0) return 'no violations'

  return results.violations
    .map((v) => {
      const nodes = v.nodes.map((n) => `      ${n.html}`).join('\n')
      return `  [${v.impact ?? 'unknown'}] ${v.id}: ${v.help}\n${nodes}`
    })
    .join('\n')
}

/**
 * Assert a container has no WCAG 2.2 AA violations.
 *
 * Throws with the full violation report on failure — deliberately an assertion
 * helper rather than a boolean, so callers cannot accidentally ignore it.
 */
export async function expectNoAccessibilityViolations(
  container: ElementContext,
  options: RunOptions = {},
): Promise<void> {
  const results = await runAxe(container, options)

  if (results.violations.length > 0) {
    throw new Error(
      `Expected no WCAG 2.2 AA violations, found ${results.violations.length}:\n` +
        formatViolations(results),
    )
  }
}
