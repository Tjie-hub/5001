/**
 * Responsive shell contract — Phase 9 Workstream B (B11).
 *
 * Authority:
 *   Phase 4 P4-03 §14   Desktop persistent · Tablet collapsible · Mobile drawer
 *                       + bottom navigation
 *   Phase 4 NP-14       responsive layouts NEVER change navigation hierarchy,
 *                       workspace ownership, route identity or workflow
 *   Phase 4 P4-14 §17   only layout changes
 *   Phase 6 Appendix H  adaptation matrix
 *   Phase 6 P6-40       no mobile-only rules, no feature removal, no different
 *                       terminology, no different hierarchy
 */
import { describe, expect, it } from 'vitest'
import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderApp } from '../../tests/render-app'
import { setViewportMatches } from '../../tests/setup'
import { BREAKPOINTS } from './use-media-query'
import { WORKSPACES } from '../router/workspaces'

const desktop = () => setViewportMatches(() => false)
const tablet = () => setViewportMatches((query) => query === BREAKPOINTS.collapsibleSidebar)
const mobile = () =>
  setViewportMatches(
    (query) => query === BREAKPOINTS.mobile || query === BREAKPOINTS.collapsibleSidebar,
  )

function workspaceLinkHrefs(container: HTMLElement): string[] {
  return within(container)
    .getAllByRole('link')
    .map((link) => link.getAttribute('href') ?? '')
}

describe('Phase 4 P4-03 §14 — Desktop', () => {
  it('keeps the sidebar persistent and expanded', () => {
    desktop()
    renderApp('/decision')

    expect(screen.getByRole('navigation', { name: 'Workspaces' })).toBeVisible()
  })

  it('shows no bottom navigation', () => {
    desktop()
    renderApp('/decision')

    expect(screen.queryByRole('navigation', { name: 'Quick access' })).not.toBeInTheDocument()
  })
})

describe('Phase 4 P4-03 §14 — Tablet', () => {
  it('collapses the sidebar but keeps it reachable', async () => {
    const user = userEvent.setup()
    tablet()
    renderApp('/decision')

    const toggle = screen.getByRole('button', { name: /show workspace navigation/i })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')

    await user.click(toggle)

    expect(screen.getByRole('navigation', { name: 'Workspaces' })).toBeVisible()
    expect(screen.getByRole('button', { name: /hide workspace navigation/i })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
  })
})

describe('Phase 4 P4-03 §14 — Mobile', () => {
  it('provides both a drawer and bottom navigation', () => {
    mobile()
    renderApp('/decision')

    expect(screen.getByRole('navigation', { name: 'Quick access' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /show workspace navigation/i })).toBeInTheDocument()
  })

  it('opens the drawer from bottom navigation, exposing all seven workspaces', async () => {
    const user = userEvent.setup()
    mobile()
    renderApp('/decision')

    await user.click(screen.getByRole('button', { name: /all workspaces/i }))

    const sidebar = screen.getByRole('navigation', { name: 'Workspaces' })
    expect(within(sidebar).getAllByRole('link')).toHaveLength(WORKSPACES.length)
  })

  it('closes the drawer with Escape (P4-03 §15)', async () => {
    const user = userEvent.setup()
    mobile()
    renderApp('/decision')

    await user.click(screen.getByRole('button', { name: /show workspace navigation/i }))
    expect(screen.getByRole('button', { name: /hide workspace navigation/i })).toBeInTheDocument()

    await user.keyboard('{Escape}')

    expect(screen.getByRole('button', { name: /show workspace navigation/i })).toBeInTheDocument()
  })

  it('closes the drawer after navigating — overlay state never survives a route change', async () => {
    const user = userEvent.setup()
    mobile()
    renderApp('/decision')

    await user.click(screen.getByRole('button', { name: /show workspace navigation/i }))

    const sidebar = screen.getByRole('navigation', { name: 'Workspaces' })
    await user.click(within(sidebar).getByRole('link', { name: /Market/ }))

    expect(await screen.findByRole('heading', { level: 1, name: /Market/ })).toBeVisible()
    expect(screen.getByRole('button', { name: /show workspace navigation/i })).toBeInTheDocument()
  })
})

describe('Phase 4 NP-14 — hierarchy is identical on every device', () => {
  it('exposes the same seven workspaces, in the same order, with the same routes', async () => {
    const user = userEvent.setup()

    desktop()
    const desktopView = renderApp('/decision')
    const desktopHrefs = workspaceLinkHrefs(
      within(desktopView.container).getByRole('navigation', { name: 'Workspaces' }),
    )
    desktopView.unmount()

    mobile()
    const mobileView = renderApp('/decision')
    await user.click(screen.getByRole('button', { name: /show workspace navigation/i }))
    const mobileHrefs = workspaceLinkHrefs(
      within(mobileView.container).getByRole('navigation', { name: 'Workspaces' }),
    )

    expect(mobileHrefs).toEqual(desktopHrefs)
    expect(mobileHrefs).toEqual(WORKSPACES.map((w) => w.navPath))
  })

  it('uses identical terminology on every device (P6-40)', async () => {
    const user = userEvent.setup()

    mobile()
    renderApp('/decision')
    await user.click(screen.getByRole('button', { name: /show workspace navigation/i }))

    const sidebar = screen.getByRole('navigation', { name: 'Workspaces' })

    for (const workspace of WORKSPACES) {
      expect(within(sidebar).getByRole('link', { name: new RegExp(workspace.label) })).toBeVisible()
    }
  })

  it('keeps route identity unchanged on mobile', async () => {
    mobile()
    renderApp('/ticker/bbca')

    const heading = await screen.findByRole('heading', { level: 1 })
    expect(heading).toHaveTextContent('Ticker')
  })
})
