/**
 * Theme provider contract — Phase 9 Workstream B (B8).
 *
 * Authority:
 *   Phase 6 P6-14  two themes; switching preserves layout, navigation,
 *                  interaction and accessibility — "only token values change"
 *   ADR-001 §3     theme is Application State
 */
import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderApp } from '../../tests/render-app'
import { THEME_STORAGE_KEY } from './theme-context'
import { setViewportMatches } from '../../tests/setup'

describe('Phase 6 P6-14 — supported themes', () => {
  it('defaults to light when the system expresses no dark preference', () => {
    renderApp('/decision')

    expect(document.documentElement).toHaveAttribute('data-theme', 'light')
  })

  it('follows the system dark preference when nothing is stored', () => {
    setViewportMatches((query) => query.includes('prefers-color-scheme: dark'))

    renderApp('/decision')

    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
  })

  it('prefers a stored choice over the system preference', () => {
    setViewportMatches((query) => query.includes('prefers-color-scheme: dark'))
    window.localStorage.setItem(THEME_STORAGE_KEY, 'light')

    renderApp('/decision')

    expect(document.documentElement).toHaveAttribute('data-theme', 'light')
  })
})

describe('theme switching', () => {
  it('toggles between light and dark', async () => {
    const user = userEvent.setup()
    renderApp('/decision')

    expect(document.documentElement).toHaveAttribute('data-theme', 'light')

    await user.click(screen.getByRole('button', { name: /switch to dark theme/i }))
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')

    await user.click(screen.getByRole('button', { name: /switch to light theme/i }))
    expect(document.documentElement).toHaveAttribute('data-theme', 'light')
  })

  it('persists the choice as Application State (ADR-001 §3)', async () => {
    const user = userEvent.setup()
    renderApp('/decision')

    await user.click(screen.getByRole('button', { name: /switch to dark theme/i }))

    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
  })

  /**
   * P6-14: "Changing themes shall preserve layouts, navigation, interactions
   * and accessibility. Only token values shall change."
   *
   * Verified structurally — the same landmarks and the same seven workspace
   * links survive the switch. This is the guarantee that makes theming safe to
   * hand to Workstream C.
   */
  it('preserves layout, navigation and landmarks across a switch', async () => {
    const user = userEvent.setup()
    renderApp('/watchlist')

    const before = screen.getAllByRole('link').map((link) => link.getAttribute('href'))

    await user.click(screen.getByRole('button', { name: /switch to dark theme/i }))

    expect(screen.getByRole('banner')).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Workspaces' })).toBeInTheDocument()
    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(screen.getByRole('contentinfo')).toBeInTheDocument()
    expect(screen.getAllByRole('link').map((link) => link.getAttribute('href'))).toEqual(before)
    expect(screen.getByRole('heading', { level: 1, name: /Watchlist/ })).toBeVisible()
  })
})
