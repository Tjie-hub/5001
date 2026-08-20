/**
 * Application providers — Phase 9 Workstream B, Server State wired per
 * ADR-003 §16.1 (approved 2026-08-20, Production OS Slice 2).
 *
 * Provider nesting, as fixed by ADR-003 §16.1:
 *
 *   ErrorBoundary
 *     └── ApplicationProviders        theme · environment · flags · auth
 *           └── QueryClientProvider   ← Server State
 *                 └── RouterProvider  ← Resource State
 *                       └── WorkspaceShell
 *
 * One QueryClient is created once per application instance (module scope,
 * not per render) via createQueryClient (src/state/query-client.ts), so
 * route changes never remount the cache and the cache is per-browser-tab by
 * construction (ADR-003 C-11).
 *
 * Environment, feature flags and auth are also Application State but have no
 * source yet — environment/flags are backend-owned (U-2) and auth is blocked
 * on U-4. Only theme and Server State are real today.
 */
import { useState, type ReactNode } from 'react'
import { BrowserRouter } from 'react-router'
import { QueryClientProvider } from '@tanstack/react-query'
import { createQueryClient } from '@state/query-client'
import { AppErrorBoundary } from '../shell/error-boundary'
import { ThemeProvider } from './theme-provider'

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient)

  return (
    <AppErrorBoundary>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>{children}</BrowserRouter>
        </QueryClientProvider>
      </ThemeProvider>
    </AppErrorBoundary>
  )
}
