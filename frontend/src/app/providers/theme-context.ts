/**
 * Theme context and types — Phase 9 Workstream B (B8).
 *
 * Split from the provider component so that the provider file exports only a
 * component. Mixing components and non-component exports in one module breaks
 * React Fast Refresh, which is what `react-refresh/only-export-components`
 * warns about.
 */
import { createContext } from 'react'

/** Phase 6 P6-14 freezes exactly two themes. */
export type Theme = 'light' | 'dark'

export interface ThemeContextValue {
  readonly theme: Theme
  readonly setTheme: (theme: Theme) => void
  readonly toggleTheme: () => void
}

export const THEME_STORAGE_KEY = 'decision-os.theme'

export const ThemeContext = createContext<ThemeContextValue | null>(null)

function prefersDark(): boolean {
  return (
    typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches
  )
}

function readStoredTheme(): Theme | null {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
    return stored === 'light' || stored === 'dark' ? stored : null
  } catch {
    // Storage can throw in private modes. Falling back to the system
    // preference is correct: theme is a convenience, never a blocker.
    return null
  }
}

/** Stored choice wins; otherwise follow the operating system. */
export function resolveInitialTheme(): Theme {
  return readStoredTheme() ?? (prefersDark() ? 'dark' : 'light')
}

export function persistTheme(theme: Theme): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    // Non-fatal — the theme still applies for this session.
  }
}
