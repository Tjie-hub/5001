import { describe, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithQueryClient } from '@tests/query-client-test-utils'
import { MarketPage } from './market-page'
import { ApiRequestError } from '@api/client'
import type { MarketSummary } from '@models/market'

const mockSummary: MarketSummary = {
  date: '2026-08-20',
  risk_score: 14.0,
  tier: 'GREEN',
  components: { vpin: 0, accdist: 40, breadth: 0, technicals: 0, foreign_flow: 40 },
  ihsg: {
    close: 7250.5, ma5: 7230.1, ma20: 7190.4, death_cross: false,
    lower_high: false, support_breaks: [], ytd_pct: 3.2,
  },
  breadth: {
    date: '2026-08-20', advancers: 210, decliners: 150, unchanged: 30,
    adv_dec_ratio: 1.4, pct_advancing: 52.5, pct_above_ma20: 61.0,
    label: 'BULL_MARKET',
  },
  foreign_flow: { today: 1.2e9, net_5d: 5.3e9, net_20d: -2.1e9, trend: 'INFLOW' },
  vpin: { avg_vpin: 0.31, pct_above_08: 0, pct_above_095: 0, label: 'GREEN' },
  accdist: {
    date: '2026-08-20', total: 390, dist_count: 80, acc_count: 160,
    neutral_count: 150, dist_pct: 20.5, acc_pct: 41.0, avg_numeric_score: 0.4,
    label: 'NEUTRAL',
  },
}

const insufficientDataSummary: MarketSummary = {
  date: '2026-08-20',
  risk_score: 0,
  tier: 'GREEN',
  components: { vpin: 0, accdist: 0, breadth: 0, technicals: 0, foreign_flow: 0 },
  ihsg: {
    close: null, ma5: null, ma20: null, death_cross: false,
    lower_high: false, support_breaks: [], ytd_pct: null,
  },
  breadth: {
    date: '2026-08-20', advancers: 0, decliners: 0, unchanged: 0,
    adv_dec_ratio: 0, pct_advancing: 0, pct_above_ma20: 0,
    label: 'INSUFFICIENT_DATA',
  },
  foreign_flow: { today: null, net_5d: null, net_20d: null, trend: 'NEUTRAL' },
  vpin: { avg_vpin: null, pct_above_08: 0, pct_above_095: 0, label: 'INSUFFICIENT_DATA' },
  accdist: {
    date: '2026-08-20', total: 0, dist_count: 0, acc_count: 0,
    neutral_count: 0, dist_pct: 0, acc_pct: 0, avg_numeric_score: 0,
    label: 'NEUTRAL',
  },
}

vi.mock('@api/market', () => ({
  getMarketSummary: vi.fn(() => Promise.resolve(mockSummary)),
}))

describe('MarketPage', () => {
  it('renders the Market heading immediately', () => {
    renderWithQueryClient(<MarketPage />)

    expect(screen.getByRole('heading', { level: 1, name: 'Market' })).toBeVisible()
  })

  it('shows a loading skeleton before data arrives', () => {
    renderWithQueryClient(<MarketPage />)

    expect(screen.getByRole('status', { name: /loading market summary/i })).toBeVisible()
  })

  it('renders real market data from the API, not hardcoded values', async () => {
    renderWithQueryClient(<MarketPage />)

    expect(await screen.findByText('14.0')).toBeVisible()
    expect(screen.getByText('Green')).toBeVisible()
    expect(screen.getByText('Bull Market')).toBeVisible()
    expect(screen.getByText(/210/)).toBeVisible()
    expect(screen.queryByRole('status', { name: /loading market summary/i })).not.toBeInTheDocument()
  })

  it('leaves the other three regions honestly Reserved, not fabricated', async () => {
    renderWithQueryClient(<MarketPage />)

    await screen.findByText('14.0')

    const reserved = screen.getByRole('region', { name: 'Reserved regions' })
    expect(reserved).toHaveTextContent('Primary Region')
    expect(reserved).toHaveTextContent('Context')
    expect(reserved).toHaveTextContent('Activity Timeline')
  })

  it('shows an explicit insufficient-data notice, not a blank panel, when every sensor degrades', async () => {
    const marketApi = await import('@api/market')
    vi.mocked(marketApi.getMarketSummary).mockResolvedValueOnce(insufficientDataSummary)

    renderWithQueryClient(<MarketPage />)

    expect(await screen.findByText(/Insufficient market data/i)).toBeVisible()
  })

  it('shows an error state without crashing when the call fails', async () => {
    const marketApi = await import('@api/market')
    vi.mocked(marketApi.getMarketSummary).mockRejectedValueOnce(
      new ApiRequestError('API_ERROR', 500, 'boom', {}),
    )

    renderWithQueryClient(<MarketPage />)

    expect(await screen.findByText(/Market summary unavailable/i)).toBeVisible()
    expect(screen.getByRole('heading', { level: 1, name: 'Market' })).toBeVisible()
  })

  it('offers a retry action on error', async () => {
    const marketApi = await import('@api/market')
    vi.mocked(marketApi.getMarketSummary).mockRejectedValueOnce(
      new ApiRequestError('API_ERROR', 500, 'boom', {}),
    )

    renderWithQueryClient(<MarketPage />)
    await screen.findByText(/Market summary unavailable/i)

    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })

  it('refetches on refresh', async () => {
    renderWithQueryClient(<MarketPage />)
    await screen.findByText('14.0')

    const marketApi = await import('@api/market')
    const calls = vi.mocked(marketApi.getMarketSummary).mock.calls.length

    screen.getByRole('button', { name: /refresh/i }).click()

    await waitFor(() =>
      expect(vi.mocked(marketApi.getMarketSummary).mock.calls.length).toBeGreaterThan(calls),
    )
  })
})
