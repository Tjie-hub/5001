import { expect, test } from '@playwright/test'

/**
 * Harness smoke test — Phase 9 Workstream A (task A6).
 *
 * Proves the Playwright harness boots the application and can assert against
 * it. It deliberately asserts almost nothing about the page, because the page
 * is deliberately empty until Workstream B.
 *
 * The critical journeys named in Phase 7 v1.1 §17 — login, navigation, search,
 * workspace transitions — are added with the features they exercise.
 */
test('application mounts and renders its root', async ({ page }) => {
  await page.goto('/')

  await expect(page.locator('#root')).toBeAttached()
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
})

test('document exposes a main landmark and exactly one h1', async ({ page }) => {
  await page.goto('/')

  // Phase 6 P6-44: one H1 per page, semantic landmarks. Enforced from the
  // first commit so the shell inherits the constraint rather than retrofitting it.
  await expect(page.locator('main')).toHaveCount(1)
  await expect(page.locator('h1')).toHaveCount(1)
})
