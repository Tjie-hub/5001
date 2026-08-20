import { describe, expect, it, vi } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithQueryClient } from '@tests/query-client-test-utils'
import { WatchlistPage } from './watchlist-page'
import { ApiRequestError } from '@api/client'
import type { CurrentWatchlist, PersistentWatchlist, WatchlistDiff, WatchlistHistory } from '@models/watchlist'

const mockCurrent: CurrentWatchlist = {
  strategy: 'eod',
  date: '2026-08-19',
  watchlist: [
    { ticker: 'DMAS', rank: 1, confidence: 0.62, conviction: 0.5, confluence: 3, sources: ['S', 'V'] },
    { ticker: 'APEX', rank: 2, confidence: 0.4, conviction: 0.3, confluence: 2, sources: ['S'] },
  ],
}

const mockDiff: WatchlistDiff = {
  strategy: 'eod',
  date: '2026-08-19',
  diff: {
    prior_date: '2026-08-18',
    added: ['DMAS'],
    removed: ['XYZ'],
    changes: [],
  },
}

const mockPersistent: PersistentWatchlist = { status: 'active', watchlist: [], count: 0 }
const mockHistory: WatchlistHistory = { strategy: 'eod', dates: ['2026-08-19', '2026-08-18'], count: 2 }

vi.mock('@api/watchlist', () => ({
  getCurrentWatchlist: vi.fn(() => Promise.resolve(mockCurrent)),
  getWatchlistHistory: vi.fn(() => Promise.resolve(mockHistory)),
  getWatchlistByDate: vi.fn(() => Promise.resolve(mockCurrent)),
  getWatchlistDiff: vi.fn(() => Promise.resolve(mockDiff)),
  getPersistentWatchlist: vi.fn(() => Promise.resolve(mockPersistent)),
}))

describe('WatchlistPage', () => {
  it('renders the Watchlist heading immediately', () => {
    renderWithQueryClient(<WatchlistPage />)

    expect(screen.getByRole('heading', { level: 1, name: 'Watchlist' })).toBeVisible()
  })

  it('shows a loading skeleton before data arrives', () => {
    renderWithQueryClient(<WatchlistPage />)

    expect(screen.getByRole('status', { name: /loading watchlist/i })).toBeVisible()
  })

  it('renders real candidate data from the API, not hardcoded values', async () => {
    renderWithQueryClient(<WatchlistPage />)

    expect(await screen.findByText('DMAS')).toBeVisible()
    expect(screen.getByText('APEX')).toBeVisible()
    expect(screen.getByText('62%')).toBeVisible()
    expect(screen.queryByRole('status', { name: /loading watchlist/i })).not.toBeInTheDocument()
  })

  it('renders summary metrics computed from the diff', async () => {
    renderWithQueryClient(<WatchlistPage />)

    await screen.findByText('DMAS')

    const summary = screen.getByRole('region', { name: 'Summary Metrics' })
    expect(within(summary).getByText('2')).toBeVisible() // totalCandidates
  })

  it('renders the activity timeline from added/removed tickers', async () => {
    renderWithQueryClient(<WatchlistPage />)

    const timeline = await screen.findByRole('region', { name: 'Activity Timeline' })
    expect(await within(timeline).findByText('XYZ')).toBeVisible()
  })

  it('shows an explicit empty state, not an error, when no watchlist snapshot exists', async () => {
    const watchlistApi = await import('@api/watchlist')
    vi.mocked(watchlistApi.getCurrentWatchlist).mockRejectedValueOnce(
      new ApiRequestError('NO_WATCHLIST_DATA', 404, 'no snapshot', {}),
    )

    renderWithQueryClient(<WatchlistPage />)

    expect(await screen.findByText(/No watchlist snapshot yet/i)).toBeVisible()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows a real error state with a retry action when the primary query fails', async () => {
    const watchlistApi = await import('@api/watchlist')
    vi.mocked(watchlistApi.getCurrentWatchlist).mockRejectedValueOnce(
      new ApiRequestError('NETWORK_ERROR', 0, 'network request failed', {}),
    )

    renderWithQueryClient(<WatchlistPage />)

    expect(await screen.findByText(/Connection problem/i)).toBeVisible()
    expect(screen.getByRole('button', { name: /retry/i })).toBeVisible()
  })

  it('expands candidate detail and navigates to the Ticker workspace', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<WatchlistPage />)

    await screen.findByText('DMAS')
    await user.click(screen.getByRole('button', { name: /DMAS/ }))

    const tickerLink = screen.getByRole('link', { name: /view ticker/i })
    expect(tickerLink).toHaveAttribute('href', '/ticker/DMAS')
  })

  it('links to Decision Center from candidate detail', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<WatchlistPage />)

    await screen.findByText('DMAS')
    await user.click(screen.getByRole('button', { name: /DMAS/ }))

    expect(screen.getByRole('link', { name: /open decision center/i })).toHaveAttribute(
      'href',
      '/decision',
    )
  })

  it('switches strategy and refetches under the new key', async () => {
    const user = userEvent.setup()
    const watchlistApi = await import('@api/watchlist')

    renderWithQueryClient(<WatchlistPage />)
    await screen.findByText('DMAS')

    await user.click(screen.getByRole('button', { name: 'Premarket' }))

    await waitFor(() =>
      expect(watchlistApi.getCurrentWatchlist).toHaveBeenCalledWith('premarket'),
    )
  })
})
