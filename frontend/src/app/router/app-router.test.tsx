/**
 * Routing and navigation contract — Phase 9 Workstream B (B2, B7).
 *
 * Authority:
 *   Phase 4 Appendix B  canonical route registry
 *   Phase 4 P4-06 §4    one canonical root per workspace
 *   Phase 4 P4-06 §11   invalid routes recover, never dead-end
 *   Phase 4 P4-06 §13   normalization uses REPLACE, not PUSH
 *   Phase 4 P4-13 §12   exactly one canonical representation per resource
 *   Phase 4 NP-05       navigation is deterministic
 *   Phase 4 NP-07       every screen has a recovery path
 *   ADR-001 §3          Resource State is owned by the URL / Router
 */
import { describe, expect, it } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderApp } from '../../tests/render-app'
import { WORKSPACES } from './workspaces'

describe('Phase 4 Appendix B — deep links resolve to their workspace', () => {
  // ADR-006 §5 interim fix (2026-08-20): 'portfolio' is excluded here because
  // its SPA <Route> was deliberately removed -- see the dedicated describe
  // block below. It remains a full member of WORKSPACES (workspaces.ts is
  // unchanged); only its SPA route registration is affected.
  it.each(
    WORKSPACES.filter((w) => w.id !== 'portfolio').map((w) => [w.navPath, w.label] as const),
  )('renders %s as the %s workspace', async (path, label) => {
    renderApp(path)

    expect(
      await screen.findByRole('heading', { level: 1, name: new RegExp(label) }),
    ).toBeVisible()
  })

  it('resolves / to the primary operational workspace (UI-001)', async () => {
    renderApp('/')

    expect(await screen.findByRole('heading', { level: 1, name: /Decision Center/ })).toBeVisible()
    expect(window.location.pathname).toBe('/decision')
  })
})

describe('ADR-006 §5 — /portfolio SPA route removed (interim fix, 2026-08-20)', () => {
  it('does not render the empty Portfolio workspace shell at /portfolio', async () => {
    renderApp('/portfolio')

    expect(await screen.findByRole('heading', { level: 1, name: /page not found/i })).toBeVisible()
    expect(screen.queryByRole('heading', { level: 1, name: /^Portfolio$/ })).not.toBeInTheDocument()
  })

  it('still lists Portfolio in the sidebar (workspaces.ts is unchanged) but its link leads to the not-found recovery page, not a crash', async () => {
    const user = userEvent.setup()
    renderApp('/decision')

    const sidebar = screen.getByRole('navigation', { name: 'Workspaces' })
    const portfolioLink = within(sidebar).getByRole('link', { name: /Portfolio/ })
    expect(portfolioLink).toBeInTheDocument()

    await user.click(portfolioLink)

    expect(await screen.findByRole('heading', { level: 1, name: /page not found/i })).toBeVisible()
    expect(window.location.pathname).toBe('/portfolio')
    expect(screen.getByRole('navigation', { name: 'Workspaces' })).toBeInTheDocument()
  })
})

describe('ADR-001 §3 — Resource State is owned by the URL', () => {
  it('reads the ticker symbol from the route, not from component state', async () => {
    renderApp('/ticker/BBCA')

    const heading = await screen.findByRole('heading', { level: 1 })

    expect(heading).toHaveTextContent('Ticker')
    expect(heading).toHaveTextContent('BBCA')
  })

  it('renders the ticker workspace with no instrument selected', async () => {
    renderApp('/ticker')

    const heading = await screen.findByRole('heading', { level: 1 })

    expect(heading).toHaveTextContent('Ticker')
    expect(heading).not.toHaveTextContent('·')
  })
})

describe('Phase 4 P4-13 §12 — URL normalization', () => {
  it('uppercases a lowercase symbol', async () => {
    renderApp('/ticker/bbca')

    await waitFor(() => expect(window.location.pathname).toBe('/ticker/BBCA'))
  })

  it('strips a trailing slash', async () => {
    renderApp('/portfolio/')

    await waitFor(() => expect(window.location.pathname).toBe('/portfolio'))
  })

  it('preserves query parameters while normalizing the path', async () => {
    renderApp('/ticker/bbca?tab=ownership')

    await waitFor(() => expect(window.location.pathname).toBe('/ticker/BBCA'))
    expect(window.location.search).toBe('?tab=ownership')
  })

  it('does not normalize an already-canonical URL', async () => {
    renderApp('/ticker/BBCA')

    await screen.findByRole('heading', { level: 1 })
    expect(window.location.pathname).toBe('/ticker/BBCA')
  })
})

describe('Phase 4 NP-05 — navigation is deterministic', () => {
  it('navigates between workspaces from the sidebar', async () => {
    const user = userEvent.setup()
    renderApp('/decision')

    const sidebar = screen.getByRole('navigation', { name: 'Workspaces' })
    await user.click(within(sidebar).getByRole('link', { name: /Search/ }))

    expect(await screen.findByRole('heading', { level: 1, name: /Search/ })).toBeVisible()
    expect(window.location.pathname).toBe('/search')
  })

  it('produces the same destination for the same action', async () => {
    const user = userEvent.setup()
    renderApp('/decision')

    const sidebar = screen.getByRole('navigation', { name: 'Workspaces' })

    await user.click(within(sidebar).getByRole('link', { name: /Market/ }))
    expect(window.location.pathname).toBe('/market')

    await user.click(within(sidebar).getByRole('link', { name: /Watchlist/ }))
    await user.click(within(sidebar).getByRole('link', { name: /Market/ }))
    expect(window.location.pathname).toBe('/market')
  })

  it('moves focus to the primary heading on route change (P4-14 §20)', async () => {
    const user = userEvent.setup()
    renderApp('/decision')

    const sidebar = screen.getByRole('navigation', { name: 'Workspaces' })
    await user.click(within(sidebar).getByRole('link', { name: /Settings/ }))

    await waitFor(() =>
      expect(screen.getByRole('heading', { level: 1, name: /Settings/ })).toHaveFocus(),
    )
  })
})

describe('Phase 4 P4-06 §11 / NP-07 — unknown routes recover', () => {
  it('renders a not-found page for an unowned route', async () => {
    renderApp('/nope')

    expect(await screen.findByRole('heading', { level: 1, name: /page not found/i })).toBeVisible()
  })

  it('offers recovery paths and is never a dead end', async () => {
    renderApp('/nope')

    const recovery = await screen.findByRole('navigation', { name: 'Recovery' })

    expect(within(recovery).getByRole('link', { name: /Decision Center/ })).toBeInTheDocument()
    expect(within(recovery).getByRole('link', { name: /Search/ })).toBeInTheDocument()
    expect(within(recovery).getByRole('link', { name: /Home/ })).toBeInTheDocument()
  })

  it('keeps global navigation available on the not-found page', async () => {
    renderApp('/nope')

    await screen.findByRole('heading', { level: 1, name: /page not found/i })
    expect(screen.getByRole('navigation', { name: 'Workspaces' })).toBeInTheDocument()
  })

  it('does not register the retired standalone /internal/operations route (ADR-008)', async () => {
    renderApp('/internal/operations')

    expect(await screen.findByRole('heading', { level: 1, name: /page not found/i })).toBeVisible()
  })
})
