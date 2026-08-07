import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright configuration — Phase 9 Workstream A (task A6).
 *
 * Phase 7 v1.1 §17 designates Playwright for end-to-end coverage of the
 * critical journeys: login, navigation, search, workspace transitions. None of
 * those exist yet — routing is Workstream B (B3) and authentication is blocked
 * on U-4 — so this configures the harness and proves it runs against the empty
 * application. The journey specs land with the features they cover.
 *
 * E2E is deliberately NOT one of the four required CI gates (A8); it needs a
 * browser download and a live server, and Workstream A has no journeys to
 * assert. It is wired here so Workstream B can add specs without touching
 * configuration.
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env['CI'],
  retries: process.env['CI'] ? 2 : 0,
  workers: process.env['CI'] ? 1 : undefined,
  reporter: process.env['CI'] ? [['github'], ['html', { open: 'never' }]] : [['list']],

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Phase 6 P6-38 makes Desktop the reference implementation; tablet and mobile
  // projects are added in Workstream F alongside the responsive audit.

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env['CI'],
    timeout: 120_000,
  },
})
