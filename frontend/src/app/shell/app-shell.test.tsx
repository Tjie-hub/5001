/**
 * Application Shell contract — Phase 9 Workstream B (B1, B3, B4, B5, B12).
 *
 * Authority:
 *   Phase 4 P4-03 §3   four persistent navigation zones
 *   Phase 4 P4-03 §4   frozen sidebar order
 *   Phase 4 P4-03 §5   sidebar rules — one workspace per item, no nesting
 *   Phase 4 P4-03 §17  no hidden navigation, no dynamic navigation
 *   Phase 4 NP-03      every workspace directly reachable
 *   Phase 5 v1.1 §2    shell layout
 *   Phase 6 P6-44      one H1, semantic landmarks, accessible names
 */
import { describe, expect, it } from 'vitest'
import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderApp } from '../../tests/render-app'
import { WORKSPACES } from '../router/workspaces'

describe('Phase 4 P4-03 §3 — the four navigation zones', () => {
  it('renders Header, Sidebar, Workspace and Footer', () => {
    renderApp('/decision')

    expect(screen.getByRole('banner')).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Workspaces' })).toBeInTheDocument()
    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(screen.getByRole('contentinfo')).toBeInTheDocument()
  })

  it('exposes exactly one banner — the workspace page must not add a second', () => {
    renderApp('/decision')

    expect(screen.getAllByRole('banner')).toHaveLength(1)
  })
})

describe('Phase 6 P6-44 — landmarks and headings', () => {
  it('exposes exactly one main landmark', () => {
    renderApp('/portfolio')

    expect(screen.getAllByRole('main')).toHaveLength(1)
  })

  it('exposes exactly one h1', () => {
    renderApp('/portfolio')

    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
  })

  it('names every navigation landmark', () => {
    renderApp('/market')

    for (const nav of screen.getAllByRole('navigation')) {
      expect(nav).toHaveAccessibleName()
    }
  })

  it('gives the skip link a target that exists', () => {
    renderApp('/market')

    const skipLink = screen.getByRole('link', { name: /skip to workspace content/i })
    const targetId = skipLink.getAttribute('href')?.replace('#', '')

    expect(document.getElementById(targetId ?? '')).toBe(screen.getByRole('main'))
  })
})

describe('Phase 4 P4-03 §4 — the frozen sidebar', () => {
  it('lists all seven workspaces in the frozen order', () => {
    renderApp('/decision')

    const sidebar = screen.getByRole('navigation', { name: 'Workspaces' })
    const links = within(sidebar).getAllByRole('link')

    expect(links.map((link) => link.textContent)).toEqual(
      WORKSPACES.map((w) => `▸${w.label}${w.responsibility}`),
    )
  })

  it('points each item at that workspace canonical route (NP-03)', () => {
    renderApp('/decision')

    const sidebar = screen.getByRole('navigation', { name: 'Workspaces' })

    for (const workspace of WORKSPACES) {
      expect(
        within(sidebar).getByRole('link', { name: new RegExp(workspace.label) }),
      ).toHaveAttribute('href', workspace.navPath)
    }
  })

  it('marks the active workspace with more than colour (P6-45)', () => {
    renderApp('/watchlist')

    const sidebar = screen.getByRole('navigation', { name: 'Workspaces' })
    const active = within(sidebar).getByRole('link', { name: /Watchlist/ })

    expect(active).toHaveAttribute('aria-current', 'page')
  })

  it('nests no submenu — every item is one workspace (P4-03 §5)', () => {
    renderApp('/decision')

    const sidebar = screen.getByRole('navigation', { name: 'Workspaces' })

    expect(within(sidebar).queryAllByRole('navigation')).toHaveLength(0)
    expect(within(sidebar).getAllByRole('link')).toHaveLength(WORKSPACES.length)
  })
})

describe('Phase 4 P4-03 §15 — keyboard navigation', () => {
  it('moves between sidebar items with the arrow keys', async () => {
    const user = userEvent.setup()
    renderApp('/decision')

    const sidebar = screen.getByRole('navigation', { name: 'Workspaces' })
    const links = within(sidebar).getAllByRole('link')

    links[0]?.focus()
    expect(links[0]).toHaveFocus()

    await user.keyboard('{ArrowDown}')
    expect(links[1]).toHaveFocus()

    await user.keyboard('{ArrowUp}')
    expect(links[0]).toHaveFocus()

    await user.keyboard('{End}')
    expect(links[links.length - 1]).toHaveFocus()

    await user.keyboard('{Home}')
    expect(links[0]).toHaveFocus()
  })

  it('reaches every sidebar link by keyboard without a trap', () => {
    renderApp('/decision')

    const sidebar = screen.getByRole('navigation', { name: 'Workspaces' })

    for (const link of within(sidebar).getAllByRole('link')) {
      expect(link).not.toHaveAttribute('tabindex', '-1')
    }
  })
})

describe('Phase 4 P4-03 §3 Zone B — Global Header', () => {
  it('renders the application title as a link home', () => {
    renderApp('/market')

    expect(screen.getByRole('link', { name: 'Production Decision OS' })).toHaveAttribute(
      'href',
      '/',
    )
  })

  it('renders the global search entry point (P4-03 §16)', () => {
    renderApp('/market')

    // Scoped to the banner: the sidebar also owns a "Search" link, and the two
    // are different things — the header entry point is Global Navigation
    // (P4-03 §16), the sidebar item is the workspace itself.
    const banner = screen.getByRole('banner')

    expect(within(banner).getByRole('link', { name: /search/i })).toHaveAttribute('href', '/search')
  })

  it('renders environment and snapshot status placeholders', () => {
    renderApp('/market')

    const banner = screen.getByRole('banner')

    expect(within(banner).getByText('Env')).toBeInTheDocument()
    expect(within(banner).getByText('Snapshot')).toBeInTheDocument()
  })

  it('renders notification and account placeholders as disabled', () => {
    renderApp('/market')

    expect(screen.getByRole('button', { name: 'Notifications' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Account' })).toBeDisabled()
  })

  it('never owns workspace filters or business actions (P4-11 §5)', () => {
    renderApp('/market')

    const banner = screen.getByRole('banner')
    const forbidden = /buy|sell|filter|rank|score|execute/i

    for (const control of within(banner).getAllByRole('button')) {
      expect(control.textContent ?? '').not.toMatch(forbidden)
    }
  })
})

describe('Phase 4 P4-03 §3 Zone D — Status Footer', () => {
  it('renders the frozen footer fields', () => {
    renderApp('/market')

    const footer = screen.getByRole('contentinfo')

    for (const label of ['Environment', 'Snapshot', 'Connection', 'Time zone', 'Version']) {
      expect(within(footer).getByText(label)).toBeInTheDocument()
    }
  })

  it('is purely informational — no links, no buttons', () => {
    renderApp('/market')

    const footer = screen.getByRole('contentinfo')

    expect(within(footer).queryAllByRole('link')).toHaveLength(0)
    expect(within(footer).queryAllByRole('button')).toHaveLength(0)
  })
})
