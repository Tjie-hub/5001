/**
 * Application root — Phase 9 Workstream B.
 *
 * Composes the provider stack (ADR-003 §16.1) with the route table. Everything
 * of substance lives in app/providers and app/router; this file stays a
 * two-line composition so there is never a temptation to put logic in it.
 */
import { AppProviders } from './app/providers/app-providers'
import { AppRoutes } from './app/router/app-router'
import './app/shell/shell-theme.placeholder.css'

export default function App() {
  return (
    <AppProviders>
      <AppRoutes />
    </AppProviders>
  )
}
