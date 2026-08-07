/**
 * Theme provider — Phase 9 Workstream B (B8).
 *
 * Theme is Application State (ADR-001 §3): session-lived, owned by the
 * application, shared across browser tabs (Phase 4 P4-12 §16), and persisted.
 * It is deliberately NOT workspace, page or server state.
 *
 * Phase 6 P6-14 freezes two themes, Light and Dark, and requires that switching
 * preserves layout, navigation, interaction and accessibility — "only token
 * values shall change". This provider therefore does exactly one thing: it sets
 * `data-theme` on the document root. No component branches on the theme; the
 * CSS custom properties do the work. That is what makes P6-14's guarantee
 * structural rather than a matter of discipline.
 *
 * Token VALUES are Workstream C's (blocker U-1). The provisional stand-ins live
 * in ../shell/shell-theme.placeholder.css.
 */
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  persistTheme,
  resolveInitialTheme,
  ThemeContext,
  type Theme,
  type ThemeContextValue,
} from './theme-context'

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(resolveInitialTheme)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next)
    persistTheme(next)
  }, [])

  const toggleTheme = useCallback(() => {
    setThemeState((current) => {
      const next: Theme = current === 'dark' ? 'light' : 'dark'
      persistTheme(next)
      return next
    })
  }, [])

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, setTheme, toggleTheme }),
    [theme, setTheme, toggleTheme],
  )

  return <ThemeContext value={value}>{children}</ThemeContext>
}
