/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const resolveSrc = (segment: string) => fileURLToPath(new URL(`./src/${segment}`, import.meta.url))

export default defineConfig({
  plugins: [react()],

  // Aliases mirror tsconfig.app.json `paths` and the Phase 7 v1.1 §4 structure.
  // Keep the two in sync — the architecture-boundary lint rules match on the
  // alias forms, so a missing alias silently disables a guard.
  resolve: {
    alias: {
      '@app': resolveSrc('app'),
      '@domains': resolveSrc('domains'),
      '@design-system': resolveSrc('design-system'),
      '@api': resolveSrc('api'),
      '@models': resolveSrc('models'),
      '@state': resolveSrc('state'),
      '@hooks': resolveSrc('hooks'),
      '@utils': resolveSrc('utils'),
      '@tests': resolveSrc('tests'),
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/tests/setup.ts'],
    // tests/e2e is Playwright's; Vitest must not try to run it.
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules', 'dist', 'tests/e2e'],
    coverage: {
      provider: 'v8',
      reportsDirectory: './coverage',
      exclude: [
        'node_modules',
        'dist',
        'tests/e2e',
        'src/tests/**',
        '**/*.config.*',
        '**/.gitkeep',
      ],
    },
  },
})
