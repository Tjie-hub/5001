import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { createTestQueryClient, queryClientWrapper } from '@tests/query-client-test-utils'
import { useWatchlistViewModel } from './use-watchlist-view-model'
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
    changes: [
      {
        ticker: 'APEX',
        prior_rank: 3,
        rank: 2,
        rank_change: 1,
        prior_confidence: 0.3,
        confidence: 0.4,
        score_delta: 0.1,
        status: 'upgraded',
        prior_sources: ['S'],
        sources: ['S'],
      },
    ],
  },
}

const mockPersistent: PersistentWatchlist = {
  status: 'active',
  watchlist: [
    {
      ticker: 'APEX',
      first_added_date: '2026-08-15',
      last_seen_date: '2026-08-19',
      status: 'ACTIVE',
      consecutive_days: 4,
      total_appearances: 4,
    },
  ],
  count: 1,
}

const mockHistory: WatchlistHistory = {
  strategy: 'eod',
  dates: ['2026-08-19', '2026-08-18', '2026-07-30'],
  count: 3,
}

vi.mock('@api/watchlist', () => ({
  getCurrentWatchlist: vi.fn(() => Promise.resolve(mockCurrent)),
  getWatchlistHistory: vi.fn(() => Promise.resolve(mockHistory)),
  getWatchlistByDate: vi.fn(() => Promise.resolve(mockCurrent)),
  getWatchlistDiff: vi.fn(() => Promise.resolve(mockDiff)),
  getPersistentWatchlist: vi.fn(() => Promise.resolve(mockPersistent)),
}))

function renderVm(selectedDate: string | null = null) {
  const client = createTestQueryClient()
  return renderHook(() => useWatchlistViewModel('eod', selectedDate), {
    wrapper: queryClientWrapper(client),
  })
}

describe('useWatchlistViewModel', () => {
  it('shows a skeleton only while isPending, never merely isFetching', async () => {
    const { result } = renderVm()

    expect(result.current.showSkeleton).toBe(true)

    await waitFor(() => expect(result.current.showSkeleton).toBe(false))
  })

  it('formats candidates with confidence %, diff status and streak label', async () => {
    const { result } = renderVm()

    await waitFor(() => expect(result.current.candidates).toHaveLength(2))

    const dmas = result.current.candidateDetail('DMAS')
    expect(dmas?.confidencePct).toBe('62%')
    expect(dmas?.diffStatus).toBe('new')

    const apex = result.current.candidateDetail('APEX')
    expect(apex?.diffStatus).toBe('upgraded')
    expect(apex?.rankChangeLabel).toBe('▲ 1')
    expect(apex?.scoreDeltaLabel).toBe('+10%')
    expect(apex?.streakLabel).toBe('4 consecutive days on watchlist')
  })

  it('computes summary metrics from the diff', async () => {
    const { result } = renderVm()

    await waitFor(() => expect(result.current.summary).not.toBeNull())

    expect(result.current.summary).toMatchObject({
      totalCandidates: 2,
      addedCount: 1,
      upgradedCount: 1,
      downgradedCount: 0,
      removedCount: 1,
      priorDateLabel: '2026-08-18',
      hasPriorSnapshot: true,
    })
  })

  it('builds an activity timeline from added/removed/upgraded/downgraded', async () => {
    const { result } = renderVm()

    await waitFor(() => expect(result.current.activity.length).toBeGreaterThan(0))

    const kinds = result.current.activity.map((a) => `${a.kind}:${a.ticker}`)
    expect(kinds).toContain('added:DMAS')
    expect(kinds).toContain('removed:XYZ')
    expect(kinds).toContain('upgraded:APEX')
  })

  it('groups history dates by month without fabricating dates', async () => {
    const { result } = renderVm()

    await waitFor(() => expect(result.current.historyGroups.length).toBeGreaterThan(0))

    const allDates = result.current.historyGroups.flatMap((g) => g.dates)
    expect(allDates.sort()).toEqual([...mockHistory.dates].sort())
  })

  it('surfaces an empty state, not an error, for NO_WATCHLIST_DATA', async () => {
    const watchlistApi = await import('@api/watchlist')
    vi.mocked(watchlistApi.getCurrentWatchlist).mockRejectedValueOnce(
      new ApiRequestError('NO_WATCHLIST_DATA', 404, 'no snapshot', {}),
    )

    const { result } = renderVm()

    await waitFor(() => expect(result.current.showSkeleton).toBe(false))

    expect(result.current.isEmpty).toBe(true)
    expect(result.current.errorPresentation).toBeNull()
  })

  it('surfaces a classified error presentation on primary failure', async () => {
    const watchlistApi = await import('@api/watchlist')
    vi.mocked(watchlistApi.getCurrentWatchlist).mockRejectedValueOnce(
      new ApiRequestError('NETWORK_ERROR', 0, 'network request failed', {}),
    )

    const { result } = renderVm()

    await waitFor(() => expect(result.current.errorPresentation).not.toBeNull())

    expect(result.current.errorPresentation?.state).toBe('NETWORK_ERROR')
    expect(result.current.errorPresentation?.recoveryActions).toContain('retry')
  })

  it('surfaces PARTIAL_DATA when a secondary query fails but candidates still render', async () => {
    const watchlistApi = await import('@api/watchlist')
    vi.mocked(watchlistApi.getPersistentWatchlist).mockRejectedValueOnce(
      new ApiRequestError('API_ERROR', 500, 'boom', {}),
    )

    const { result } = renderVm()

    await waitFor(() => expect(result.current.errorPresentation?.state).toBe('PARTIAL_DATA'))

    expect(result.current.candidates.length).toBeGreaterThan(0)
  })
})
