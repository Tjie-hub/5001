import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'

/**
 * Composition root.
 *
 * Provider nesting is fixed by ADR-003 §16.1 and is assembled here in
 * Workstream B:
 *
 *   ErrorBoundary
 *     └── ApplicationProviders   (theme · environment · flags · auth)
 *           └── QueryClientProvider  ← Server State
 *                 └── RouterProvider (Resource State)
 *                       └── WorkspaceShell
 *
 * Workstream A mounts the bare application only.
 */
const container = document.getElementById('root')

if (!container) {
  throw new Error('Root container #root not found in index.html')
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
