import { afterEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithQueryClient } from '@tests/query-client-test-utils'
import { SearchPage } from './search-page'
import { ApiRequestError } from '@api/client'
import type { InstrumentSearchResponse } from '@models/search'

const mockResults: InstrumentSearchResponse = {
  query: 'BB',
  results: [
    { ticker: 'BB', in_idx30: false, in_lq45: false, in_idx80: false },
    { ticker: 'BBCA', in_idx30: true, in_lq45: true, in_idx80: true },
  ],
  count: 2,
}

const emptyResults: InstrumentSearchResponse = { query: 'ZZZNOPE', results: [], count: 0 }

vi.mock('@api/search', () => ({
  searchInstruments: vi.fn(() => Promise.resolve(mockResults)),
}))

afterEach(() => {
  vi.clearAllMocks()
})

describe('SearchPage', () => {
  it('renders the Search heading immediately', () => {
    renderWithQueryClient(<SearchPage />, { initialEntries: ['/search'] })

    expect(screen.getByRole('heading', { level: 1, name: 'Search' })).toBeVisible()
  })

  it('shows idle guidance before anything is typed, and never fires a request', async () => {
    renderWithQueryClient(<SearchPage />, { initialEntries: ['/search'] })

    expect(screen.getByText(/start typing a ticker code/i)).toBeVisible()
    const searchApi = await import('@api/search')
    expect(searchApi.searchInstruments).not.toHaveBeenCalled()
  })

  it('renders real search results from the API, not hardcoded values', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<SearchPage />, { initialEntries: ['/search'] })

    await user.type(screen.getByRole('searchbox', { name: /search instruments/i }), 'BB')

    expect(await screen.findByText('BBCA', {}, { timeout: 2000 })).toBeVisible()
    expect(screen.getByText('BB')).toBeVisible()
    expect(screen.getAllByText('IDX30')).toHaveLength(1)
  })

  it('links each result to its Ticker workspace route', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<SearchPage />, { initialEntries: ['/search'] })

    await user.type(screen.getByRole('searchbox', { name: /search instruments/i }), 'BB')
    await screen.findByText('BBCA', {}, { timeout: 2000 })

    expect(screen.getByRole('link', { name: /BBCA/ })).toHaveAttribute('href', '/ticker/BBCA')
  })

  it('shows an explicit no-results state, not a blank panel, for a query with no matches', async () => {
    const searchApi = await import('@api/search')
    vi.mocked(searchApi.searchInstruments).mockResolvedValueOnce(emptyResults)

    const user = userEvent.setup()
    renderWithQueryClient(<SearchPage />, { initialEntries: ['/search'] })

    await user.type(screen.getByRole('searchbox', { name: /search instruments/i }), 'ZZZNOPE')

    expect(
      await screen.findByText(/No instruments match/i, {}, { timeout: 2000 }),
    ).toBeVisible()
  })

  it('shows an error state without crashing when the call fails', async () => {
    const searchApi = await import('@api/search')
    vi.mocked(searchApi.searchInstruments).mockRejectedValueOnce(
      new ApiRequestError('SEARCH_UNAVAILABLE', 500, 'boom', {}),
    )

    const user = userEvent.setup()
    renderWithQueryClient(<SearchPage />, { initialEntries: ['/search'] })

    await user.type(screen.getByRole('searchbox', { name: /search instruments/i }), 'BB')

    expect(
      await screen.findByText(/Search unavailable/i, {}, { timeout: 2000 }),
    ).toBeVisible()
    expect(screen.getByRole('heading', { level: 1, name: 'Search' })).toBeVisible()
  })

  it('leaves the two unbuilt regions honestly Reserved, not fabricated', async () => {
    renderWithQueryClient(<SearchPage />, { initialEntries: ['/search'] })

    const reserved = screen.getByRole('region', { name: 'Reserved regions' })
    expect(reserved).toHaveTextContent('Search Filters')
    expect(reserved).toHaveTextContent('Search History')
  })

  it('debounces so it does not fire one request per keystroke', async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<SearchPage />, { initialEntries: ['/search'] })

    const input = screen.getByRole('searchbox', { name: /search instruments/i })
    await user.type(input, 'BB')

    await screen.findByText('BBCA', {}, { timeout: 2000 })
    const searchApi = await import('@api/search')
    // 'B' then 'BB' were typed; the debounce must never fetch the
    // intermediate 'B' keystroke, only the settled 'BB' value.
    const queried = vi.mocked(searchApi.searchInstruments).mock.calls.map((c) => c[0])
    expect(queried).not.toContain('B')
    expect(queried.every((q) => q === 'BB')).toBe(true)
  })
})
