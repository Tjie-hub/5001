// Named import: the package is CJS; a default import resolves to the namespace
// under verbatimModuleSyntax + nodenext.
import { AxeBuilder } from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

/**
 * Responsive shell in a real browser — Phase 9 Workstream B (B11, B12).
 *
 * Also produces the desktop / tablet / mobile screenshots required by the
 * Workstream B report. Generating them from the same run that asserts the
 * behaviour keeps the evidence and the assertion in step.
 *
 * Authority:
 *   Phase 4 P4-03 §14   Desktop persistent · Tablet collapsible · Mobile drawer
 *                       + bottom navigation
 *   Phase 4 NP-14       hierarchy identical across devices
 *   Phase 6 Appendix H  adaptation matrix
 *   Phase 6 P6-42       WCAG 2.2 AA on every device
 */

const WCAG_22_AA_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  tablet: { width: 900, height: 1180 },
  mobile: { width: 390, height: 844 },
} as const

async function workspaceHrefs(page: Page): Promise<string[]> {
  return page
    .getByRole('navigation', { name: 'Workspaces' })
    .getByRole('link')
    .evaluateAll((links) => links.map((link) => link.getAttribute('href') ?? ''))
}

test.describe('Phase 4 P4-03 §14 — Desktop', () => {
  test.use({ viewport: VIEWPORTS.desktop })

  test('sidebar is persistent; no bottom navigation', async ({ page }) => {
    await page.goto('/decision')

    await expect(page.getByRole('navigation', { name: 'Workspaces' })).toBeVisible()
    await expect(page.getByRole('navigation', { name: 'Quick access' })).toHaveCount(0)
  })

  test('screenshot', async ({ page }) => {
    await page.goto('/decision')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await page.screenshot({ path: 'screenshots/desktop-light.png', fullPage: false })

    await page.getByRole('button', { name: /switch to dark theme/i }).click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
    await page.screenshot({ path: 'screenshots/desktop-dark.png', fullPage: false })
  })
})

test.describe('Phase 4 P4-03 §14 — Tablet', () => {
  test.use({ viewport: VIEWPORTS.tablet })

  test('sidebar is collapsible and reachable', async ({ page }) => {
    await page.goto('/decision')

    const toggle = page.getByRole('button', { name: /show workspace navigation/i })
    await expect(toggle).toBeVisible()

    await toggle.click()
    await expect(page.getByRole('navigation', { name: 'Workspaces' })).toBeVisible()
  })

  test('screenshot', async ({ page }) => {
    await page.goto('/portfolio')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await page.screenshot({ path: 'screenshots/tablet-collapsed.png' })

    await page.getByRole('button', { name: /show workspace navigation/i }).click()
    await expect(page.getByRole('navigation', { name: 'Workspaces' })).toBeVisible()
    await page.screenshot({ path: 'screenshots/tablet-expanded.png' })
  })
})

test.describe('Phase 4 P4-03 §14 — Mobile', () => {
  test.use({ viewport: VIEWPORTS.mobile })

  test('provides drawer and bottom navigation', async ({ page }) => {
    await page.goto('/decision')

    await expect(page.getByRole('navigation', { name: 'Quick access' })).toBeVisible()
    await expect(page.getByRole('button', { name: /show workspace navigation/i })).toBeVisible()
  })

  test('drawer exposes all five workspaces and Escape closes it', async ({ page }) => {
    await page.goto('/decision')

    await page.getByRole('button', { name: /all workspaces/i }).click()
    const sidebar = page.getByRole('navigation', { name: 'Workspaces' })
    await expect(sidebar.getByRole('link')).toHaveCount(5)

    await page.keyboard.press('Escape')
    await expect(page.getByRole('button', { name: /show workspace navigation/i })).toBeVisible()
  })

  test('screenshot', async ({ page }) => {
    await page.goto('/market')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await page.screenshot({ path: 'screenshots/mobile-workspace.png' })

    await page.getByRole('button', { name: /all workspaces/i }).click()
    await expect(page.getByRole('navigation', { name: 'Workspaces' })).toBeVisible()
    await page.screenshot({ path: 'screenshots/mobile-drawer.png' })
  })
})

test.describe('Phase 4 NP-14 — hierarchy is identical across devices', () => {
  test('the same five workspaces, same order, same routes', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop)
    await page.goto('/decision')
    const desktop = await workspaceHrefs(page)

    await page.setViewportSize(VIEWPORTS.mobile)
    await page.reload()
    await page.getByRole('button', { name: /all workspaces/i }).click()
    const mobile = await workspaceHrefs(page)

    expect(mobile).toEqual(desktop)
    // Frontend freeze 2026-10-06: portfolio, intelligence and watchlist were
    // removed from the workspace registry — the five remaining workspaces only.
    expect(desktop).toEqual([
      '/decision',
      '/ticker',
      '/market',
      '/search',
      '/settings',
    ])
  })
})

test.describe('Phase 6 P6-42 — WCAG 2.2 AA on every device', () => {
  for (const [name, viewport] of Object.entries(VIEWPORTS)) {
    test(`no violations at ${name}`, async ({ page }) => {
      await page.setViewportSize(viewport)
      await page.goto('/decision')
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible()

      const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA_TAGS).analyze()

      expect(results.violations).toEqual([])
    })
  }
})
