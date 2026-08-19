import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { DecisionPage } from './decision-page'
import { ApiRequestError } from '@api/client'
import type { SchedulerStatus } from '@models/operations'
import type { RegistryStatus } from '@models/registry'
import type { CurrentWatchlist } from '@models/watchlist'

const mockScheduler: SchedulerStatus = {
  available: true,
  state: 'running',
  timezone: 'Asia/Jakarta',
  job_count: 46,
}

const mockRegistryShadow: RegistryStatus = {
  hash: 'abc1234',
  approved: 0,
  shadow: 1,
  entries: [
    { id: 'NR7_BULL', version: 2, status: 'SHADOW', strategy_fn: 'NR7 Breakout',
      regimes: ['BULL_MODERATE', 'BULL_STRONG'] },
  ],
  skipped_count: 0,
  debt_count: 1,
  violation_count: 0,
}

const mockWatchlist: CurrentWatchlist = {
  strategy: 'eod',
  date: '2026-08-19',
  watchlist: [
    { ticker: 'DMAS', rank: 1, confidence: 0.4, conviction: 0, confluence: 2, sources: ['S', 'V'] },
    { ticker: 'APEX', rank: 2, confidence: 0.4, conviction: 0, confluence: 2, sources: ['S', 'V'] },
  ],
}

vi.mock('@api/operations', () => ({
  getSchedulerStatus: vi.fn(() => Promise.resolve(mockScheduler)),
}))
vi.mock('@api/registry', () => ({
  getRegistryStatus: vi.fn(() => Promise.resolve(mockRegistryShadow)),
}))
vi.mock('@api/watchlist', () => ({
  getCurrentWatchlist: vi.fn(() => Promise.resolve(mockWatchlist)),
}))

describe('DecisionPage', () => {
  it('renders the Decision Center heading', async () => {
    render(<DecisionPage />)

    expect(
      await screen.findByRole('heading', { level: 1, name: /Decision Center/ }),
    ).toBeVisible()
  })

  it('renders real scheduler, admission and watchlist state in the Executive Summary', async () => {
    render(<DecisionPage />)

    await waitFor(() => {
      expect(screen.getByText(/running/i)).toBeVisible()
    })
    expect(screen.getByText(/46 jobs/)).toBeVisible()
    expect(screen.getByText(/0 approved/)).toBeVisible()
    expect(screen.getByText(/1 shadow/)).toBeVisible()
    expect(screen.getByText('NR7_BULL')).toBeVisible()
    expect(screen.getByText(/2 tickers/)).toBeVisible()
  })

  it('shows a loading state before data arrives', () => {
    render(<DecisionPage />)

    expect(screen.getByText(/Loading production state/i)).toBeVisible()
  })

  it('shows an explicit no-approved-strategies state when approved is zero', async () => {
    render(<DecisionPage />)

    expect(await screen.findByText(/No approved strategies/i)).toBeVisible()
  })

  it('shows an error state without crashing when a call fails', async () => {
    const registryApi = await import('@api/registry')
    vi.mocked(registryApi.getRegistryStatus).mockRejectedValueOnce(new Error('boom'))

    render(<DecisionPage />)

    expect(await screen.findByRole('alert')).toHaveTextContent(/boom/)
  })

  it('shows an explicit empty state, not an error, when no watchlist snapshot exists yet', async () => {
    const watchlistApi = await import('@api/watchlist')
    vi.mocked(watchlistApi.getCurrentWatchlist).mockRejectedValueOnce(
      new ApiRequestError('NO_WATCHLIST_DATA', 404, 'no watchlist snapshot', {}),
    )

    render(<DecisionPage />)

    expect(await screen.findByText(/No production signals yet/i)).toBeVisible()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
