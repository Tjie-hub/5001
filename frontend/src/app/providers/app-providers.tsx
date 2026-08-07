/**
 * Application providers — Phase 9 Workstream B.
 *
 * Provider nesting is fixed by ADR-003 §16.1:
 *
 *   ErrorBoundary
 *     └── ApplicationProviders        theme · environment · flags · auth
 *           └── QueryClientProvider   ← Server State (Workstream E)
 *                 └── RouterProvider  ← Resource State
 *                       └── WorkspaceShell
 *
 * Workstream B installs the Error Boundary, the Application providers and the
 * Router. QueryClientProvider is deliberately absent: this workstream forbids
 * TanStack Query usage, and it must sit between the application providers and
 * the router when Workstream E adds it. The slot is marked below so it is
 * added in the right place rather than wherever is convenient.
 *
 * Environment, feature flags and auth are also Application State but have no
 * source yet — environment/flags are backend-owned (U-2) and auth is blocked
 * on U-4. Only theme is real today.
 */
import type { ReactNode } from 'react'
import { BrowserRouter } from 'react-router'
import { AppErrorBoundary } from '../shell/error-boundary'
import { ThemeProvider } from './theme-provider'

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <AppErrorBoundary>
      <ThemeProvider>
        {/* ADR-003 §16.1: QueryClientProvider goes HERE, wrapping the router.
            Workstream E, task E4. Do not mount it inside the router. */}
        <BrowserRouter>{children}</BrowserRouter>
      </ThemeProvider>
    </AppErrorBoundary>
  )
}
