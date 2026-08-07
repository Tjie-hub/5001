/**
 * Application render helper — Phase 9 Workstream B.
 *
 * Renders the REAL composition — AppProviders (error boundary → theme →
 * BrowserRouter) plus the real route table — rather than a test-only
 * substitute. The route is set through the actual History API, so browser
 * history, deep linking and URL normalization are exercised as shipped rather
 * than simulated.
 *
 * Deliberately no test seam in production code: an injectable router would let
 * the tested composition drift from the shipped one, which is precisely the
 * defect class Workstream B's acceptance criteria are meant to catch.
 */
import { render, type RenderResult } from '@testing-library/react'
import App from '../App'

export function renderApp(initialPath = '/'): RenderResult {
  window.history.pushState({}, '', initialPath)
  return render(<App />)
}
