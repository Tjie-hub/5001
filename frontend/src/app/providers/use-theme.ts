/**
 * Theme hook — Phase 9 Workstream B (B8).
 *
 * Separate module so theme-provider.tsx exports only a component (React Fast
 * Refresh requirement).
 */
import { use } from 'react'
import { ThemeContext, type ThemeContextValue } from './theme-context'

export function useTheme(): ThemeContextValue {
  const context = use(ThemeContext)

  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }

  return context
}
