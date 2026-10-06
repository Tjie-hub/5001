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
 *
 * Frontend freeze 2026-10-06: the ADR-006 §5 interim-fix block (which asserted
 * /portfolio fell through to the not-found page) was superseded — the three
 * frozen paths now resolve to the FrozenWorkspacePage banner page. The
 * expectations below were changed to that contract, not deleted.
 */
import { describe, expect, it } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderApp } from '../../tests/render-app'
import { WORKSPACES } from './workspaces'

describe('Phase 4 Appendix B — deep links resolve to their workspace', () => {
  // Frontend freeze 2026-10-06: the original filter (w.id !== 'portfolio') is
  // gone with the retired workspaces — every remaining registry entry owns a
  // live route.
  it.each(WORKSPACES.map((w) => [w.navPath, w.label] as const))(
    'renders %s as the %s workspace',
    async (path, label) => {
      renderApp(path)

      expect(
        await screen.findByRole('heading', { level: 1, name: new RegExp(label) }),
      ).toBeVisible()
    },
  )

  it('resolves / to the primary operational workspace (UI-001)', async () => {
    renderApp('/')

    expect(await screen.findByRole('heading', { level: 1, name: /Decision Center/ })).toBeVisible()
    expect(window.location.pathname).toBe('/decision')
  })
})

describe('Frontend freeze 2026-10-06 — frozen paths resolve to the banner page', () => {
  it.each([
    ['/portfolio', 'Portfolio'],
    ['/intelligence', 'Investment Intelligence'],
    ['/watchlist', 'Watchlist'],
  ] as const)('renders the frozen-workspace page at %s, not a 404', async (path, retired) => {
    renderApp(path)

    expect(await screen.findByRole('heading', { level: 1, name: /workspace frozen/i })).toBeVisible()
    // Scoped to the page copy — the freeze banner also names the workspaces.
    expect(screen.getByText(new RegExp(`The ${retired} workspace was removed`))).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 1, name: /page not found/i })).not.toBeInTheDocument()
  })

  it('carries the freeze banner pointing at jurnal26 :5004', async () => {
    renderApp('/watchlist')

    const banner = await screen.findByTestId('frozen-banner')
    expect(banner).toHaveTextContent('5001 frontend is frozen')
    const link = within(banner).getByRole('link', { name: /jurnal26 :5004/ })
    expect(link).toHaveAttribute('href', 'http://localhost:5004/')
  })

  it('shows the stopped-at note on /portfolio', async () => {
    renderApp('/portfolio')

    expect(
      await screen.findByText(/stopped at 2026-04-14 and is no longer maintained/),
    ).toBeInTheDocument()
  })

  it('does not resurrect the removed workspaces behind their old paths', async () => {
    renderApp('/watchlist')

    await screen.findByRole('heading', { level: 1, name: /workspace frozen/i })
    // The retired candidate-list UI must not render behind its old URL.
    expect(screen.queryByRole('heading', { level: 1, name: /^Watchlist$/ })).not.toBeInTheDocument()
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

  it('strips a trailing slash, including on a frozen path', async () => {
    renderApp('/portfolio/')

    await waitFor(() => expect(window.location.pathname).toBe('/portfolio'))
    expect(
      await screen.findByRole('heading', { level: 1, name: /workspace frozen/i }),
    ).toBeVisible()
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

    await user.click(within(sidebar).getByRole('link', { name: /Search/ }))
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
