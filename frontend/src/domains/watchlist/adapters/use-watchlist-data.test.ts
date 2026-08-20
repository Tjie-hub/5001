import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { createTestQueryClient, queryClientWrapper } from '@tests/query-client-test-utils'
import { useWatchlistData } from './use-watchlist-data'
import { ApiRequestError } from '@api/client'
import type {
  CurrentWatchlist,
  PersistentWatchlist,
  WatchlistDiff,
  WatchlistHistory,
} from '@models/watchlist'

const mockCurrent: CurrentWatchlist = {
  strategy: 'eod',
  date: '2026-08-19',
  watchlist: [
    { ticker: 'DMAS', rank: 1, confidence: 0.6, conviction: 0.5, confluence: 3, sources: ['S'] },
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

const mockPersistent: PersistentWatchlist = {
  status: 'active',
  watchlist: [
    {
      ticker: 'DMAS',
      first_added_date: '2026-08-15',
      last_seen_date: '2026-08-19',
      status: 'ACTIVE',
      consecutive_days: 3,
      total_appearances: 3,
    },
  ],
  count: 1,
}

const mockHistory: WatchlistHistory = { strategy: 'eod', dates: ['2026-08-19', '2026-08-18'], count: 2 }

vi.mock('@api/watchlist', () => ({
  getCurrentWatchlist: vi.fn(() => Promise.resolve(mockCurrent)),
  getWatchlistHistory: vi.fn(() => Promise.resolve(mockHistory)),
  getWatchlistByDate: vi.fn(() => Promise.resolve(mockCurrent)),
  getWatchlistDiff: vi.fn(() => Promise.resolve(mockDiff)),
  getPersistentWatchlist: vi.fn(() => Promise.resolve(mockPersistent)),
}))

function renderData(selectedDate: string | null = null) {
  const client = createTestQueryClient()
  return renderHook(() => useWatchlistData('eod', selectedDate), {
    wrapper: queryClientWrapper(client),
  })
}

describe('useWatchlistData', () => {
  it('composes current, diff and persistent into one domain surface', async () => {
    const { result } = renderData()

    await waitFor(() => expect(result.current.primary.isPending).toBe(false))
    await waitFor(() => expect(result.current.diff.data).not.toBeNull())
    await waitFor(() => expect(result.current.persistent.data).not.toBeNull())

    expect(result.current.primary.entries).toEqual(mockCurrent.watchlist)
    expect(result.current.primary.date).toBe('2026-08-19')
    expect(result.current.diff.data?.added).toEqual(['DMAS'])
    expect(result.current.persistent.data?.[0]?.consecutive_days).toBe(3)
    expect(result.current.isPartialData).toBe(false)
  })

  it('degrades to isPartialData when a secondary query fails but the primary succeeds', async () => {
    const watchlistApi = await import('@api/watchlist')
    vi.mocked(watchlistApi.getPersistentWatchlist).mockRejectedValueOnce(
      new ApiRequestError('API_ERROR', 500, 'boom', {}),
    )

    const { result } = renderData()

    await waitFor(() => expect(result.current.primary.isPending).toBe(false))
    await waitFor(() => expect(result.current.persistent.errorState).not.toBeNull())

    expect(result.current.primary.entries).not.toBeNull()
    expect(result.current.isPartialData).toBe(true)
  })

  it('treats NO_WATCHLIST_DATA as an empty state, not an error', async () => {
    const watchlistApi = await import('@api/watchlist')
    vi.mocked(watchlistApi.getCurrentWatchlist).mockRejectedValueOnce(
      new ApiRequestError('NO_WATCHLIST_DATA', 404, 'no snapshot', {}),
    )

    const { result } = renderData()

    await waitFor(() => expect(result.current.primary.isPending).toBe(false))

    expect(result.current.primary.isEmpty).toBe(true)
    expect(result.current.primary.errorState).toBeNull()
  })

  it('classifies a real primary failure as an error state', async () => {
    const watchlistApi = await import('@api/watchlist')
    vi.mocked(watchlistApi.getCurrentWatchlist).mockRejectedValueOnce(
      new ApiRequestError('NETWORK_ERROR', 0, 'network request failed', {}),
    )

    const { result } = renderData()

    await waitFor(() => expect(result.current.primary.isPending).toBe(false))

    expect(result.current.primary.errorState).toBe('NETWORK_ERROR')
    expect(result.current.primary.isEmpty).toBe(false)
  })

  it('fetches a historical date via byDate when selectedDate is set', async () => {
    const watchlistApi = await import('@api/watchlist')

    const { result } = renderData('2026-08-18')

    await waitFor(() => expect(result.current.primary.isPending).toBe(false))

    expect(watchlistApi.getWatchlistByDate).toHaveBeenCalledWith('2026-08-18', 'eod')
    expect(result.current.primary.date).toBe('2026-08-19') // mock returns mockCurrent's date
  })
})
