import { expect, test } from '@playwright/test'

/**
 * Shell navigation in a real browser — Phase 9 Workstream B (B2, B7).
 *
 * These assert the things jsdom cannot honestly verify: genuine browser
 * history, reload, and bookmark/deep-link behaviour.
 *
 * Authority:
 *   Phase 4 NP-12       Back, Forward, Refresh, Bookmark, Copy URL, New Tab
 *   Phase 4 P4-06 §13   normalization REPLACES, so Back must skip it
 *   Phase 4 P4-13 §14   refresh restores workspace and resource
 *   Phase 4 P4-13 §12   one canonical representation
 */

test.describe('Phase 4 NP-12 — browser history', () => {
  test('Back and Forward move between workspaces', async ({ page }) => {
    await page.goto('/decision')
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Decision Center')

    const sidebar = page.getByRole('navigation', { name: 'Workspaces' })
    // Frontend freeze 2026-10-06: this journey used to click the Portfolio
    // sidebar link; that workspace is retired, so the round-trip now runs on
    // Market.
    await sidebar.getByRole('link', { name: /Market/ }).click()
    await expect(page).toHaveURL('/market')

    await sidebar.getByRole('link', { name: /Search/ }).click()
    await expect(page).toHaveURL('/search')

    await page.goBack()
    await expect(page).toHaveURL('/market')
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Market')

    await page.goBack()
    await expect(page).toHaveURL('/decision')

    await page.goForward()
    await expect(page).toHaveURL('/market')
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Market')
  })

  test('normalization uses REPLACE, so Back never lands on a non-canonical URL', async ({
    page,
  }) => {
    await page.goto('/decision')
    await page.goto('/ticker/bbca')
    await expect(page).toHaveURL('/ticker/BBCA')

    await page.goBack()

    // If normalization had PUSHed, Back would land on /ticker/bbca and bounce.
    await expect(page).toHaveURL('/decision')
  })
})

test.describe('Phase 4 P4-13 §14 — refresh restores the route', () => {
  for (const path of [
    '/decision',
    '/portfolio',
    '/watchlist',
    '/market',
    '/search',
    '/settings',
    '/ticker/BBCA',
  ]) {
    test(`reload keeps ${path}`, async ({ page }) => {
      await page.goto(path)
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible()

      await page.reload()

      await expect(page).toHaveURL(path)
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    })
  }
})

test.describe('Frontend freeze 2026-10-06 — frozen paths', () => {
  test('a bookmark to a removed workspace lands on the frozen banner page, not a 404', async ({
    page,
  }) => {
    await page.goto('/watchlist')

    await expect(page.getByRole('heading', { level: 1 })).toContainText('Workspace frozen')
    await expect(page.getByTestId('frozen-banner')).toContainText('5001 frontend is frozen')

    const link = page.getByTestId('frozen-banner').getByRole('link', { name: /jurnal26 :5004/ })
    await expect(link).toHaveAttribute('href', 'http://localhost:5004/')
  })
})

test.describe('Phase 4 P4-07 — deep links', () => {
  test('a resource deep link opens directly, in one navigation step', async ({ page }) => {
    await page.goto('/ticker/BBCA')

    const heading = page.getByRole('heading', { level: 1 })
    await expect(heading).toContainText('Ticker')
    await expect(heading).toContainText('BBCA')
  })

  test('a deep link survives being opened in a fresh context (bookmark-safe)', async ({
    browser,
  }) => {
    const context = await browser.newContext()
    const page = await context.newPage()

    await page.goto('/decision')
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Decision Center')

    await context.close()
  })

  test('query parameters survive path normalization', async ({ page }) => {
    await page.goto('/ticker/bbca?tab=ownership')

    await expect(page).toHaveURL('/ticker/BBCA?tab=ownership')
  })
})

test.describe('Phase 4 NP-07 — recovery', () => {
  test('an unknown route recovers without dead-ending', async ({ page }) => {
    await page.goto('/not-a-workspace')

    await expect(page.getByRole('heading', { level: 1 })).toContainText('Page not found')

    await page
      .getByRole('navigation', { name: 'Recovery' })
      .getByRole('link', { name: 'Home' })
      .click()
    await expect(page).toHaveURL('/decision')
  })
})

test.describe('Phase 6 P6-14 — theme switching', () => {
  test('switches theme and persists it across a reload', async ({ page }) => {
    await page.goto('/decision')

    const root = page.locator('html')
    await expect(root).toHaveAttribute('data-theme', 'light')

    await page.getByRole('button', { name: /switch to dark theme/i }).click()
    await expect(root).toHaveAttribute('data-theme', 'dark')

    await page.reload()
    await expect(root).toHaveAttribute('data-theme', 'dark')

    // P6-14: switching preserves layout and navigation.
    await expect(page.getByRole('navigation', { name: 'Workspaces' })).toBeVisible()
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Decision Center')
  })
})

test.describe('Phase 6 P6-43 — keyboard access', () => {
  test('the skip link is the first tab stop and reaches the workspace', async ({ page }) => {
    await page.goto('/decision')

    // Seat focus in the document before tabbing. Without this the first Tab is
    // consumed moving focus from the browser chrome into the page.
    await page.locator('body').evaluate((body: HTMLElement) => body.focus())
    await page.keyboard.press('Tab')

    const skip = page.getByRole('link', { name: /skip to workspace content/i })
    await expect(skip).toBeFocused()

    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/#workspace-content$/)
  })
})
