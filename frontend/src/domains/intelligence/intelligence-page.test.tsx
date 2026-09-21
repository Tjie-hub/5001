import { describe, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithQueryClient } from '@tests/query-client-test-utils'
import { IntelligencePage } from './intelligence-page'
import type { InvestmentSummary } from '@models/investments'
import type { MarketSummary } from '@models/market'
import type { CurrentWatchlist, PersistentWatchlist } from '@models/watchlist'
import type { RegistryStatus } from '@models/registry'

const mockSummary: InvestmentSummary = {
  portfolio_value: 232_182_500,
  equity_cost_basis: 398_690_440,
  unrealized_pl: -166_507_940,
  unrealized_pct: -41.76,
  realized_equity_pl: 1_467_573,
  realized_fund_pl: 1_006_159,
  realized_pl: 2_473_732,
  closed_equity_count: 3,
  closed_fund_count: 7,
  dividends_gross: 0,
  dividends_tax: 0,
  dividends_net: 0,
  dividend_count: 0,
  fund_open_value: 0,
  fund_open_cost: 0,
  fund_open_count: 0,
  total_return: -164_034_208,
  total_return_pct: -41.14,
  allocation: [{ ticker: 'ARNA', value: 179_073_000, pct: 77.1 }],
  open_positions: 1,
  fees: { buy_fee_pct: 0.15, sell_fee_pct: 0.25, default_div_tax_pct: 10 },
}

const mockMarket: MarketSummary = {
  date: '2026-09-03',
  risk_score: 14.0,
  tier: 'GREEN',
  components: { vpin: 0, accdist: 40, breadth: 0, technicals: 0, foreign_flow: 40 },
  ihsg: {
    close: 7250.5,
    ma5: 7230.1,
    ma20: 7190.4,
    death_cross: false,
    lower_high: false,
    support_breaks: [],
    ytd_pct: 3.2,
  },
  breadth: {
    date: '2026-09-03',
    advancers: 210,
    decliners: 150,
    unchanged: 30,
    adv_dec_ratio: 1.4,
    pct_advancing: 52.5,
    pct_above_ma20: 61.0,
    label: 'BULL_MARKET',
  },
  foreign_flow: { today: 1.2e9, net_5d: 5.3e9, net_20d: -2.1e9, trend: 'INFLOW' },
  vpin: { avg_vpin: 0.31, pct_above_08: 0, pct_above_095: 0, label: 'GREEN' },
  accdist: {
    date: '2026-09-03',
    total: 390,
    dist_count: 80,
    acc_count: 160,
    neutral_count: 150,
    dist_pct: 20.5,
    acc_pct: 41.0,
    avg_numeric_score: 0.4,
    label: 'NEUTRAL',
  },
}

const mockWatchlist: CurrentWatchlist = {
  strategy: 'eod',
  date: '2026-09-03',
  watchlist: [
    {
      ticker: 'BBRI',
      rank: 1,
      confidence: 0.81,
      conviction: 0.7,
      confluence: 3,
      sources: ['flow', 'technicals'],
    },
  ],
}

const mockPersistent: PersistentWatchlist = {
  status: 'active',
  watchlist: [
    {
      ticker: 'BBRI',
      first_added_date: '2026-08-28',
      last_seen_date: '2026-09-03',
      status: 'ACTIVE',
      consecutive_days: 5,
      total_appearances: 9,
    },
  ],
  count: 1,
}

const mockRegistry: RegistryStatus = {
  hash: 'abc123',
  approved: 2,
  shadow: 1,
  entries: [
    { id: 'vol_weighted', version: 1, status: 'APPROVED', strategy_fn: 'vol_weighted', regimes: ['trend'] },
  ],
  skipped_count: 0,
  debt_count: 0,
  violation_count: 0,
}

vi.mock('@api/investments', () => ({
  getInvestmentSummary: vi.fn(() => Promise.resolve(mockSummary)),
}))
vi.mock('@api/market', () => ({
  getMarketSummary: vi.fn(() => Promise.resolve(mockMarket)),
}))
vi.mock('@api/watchlist', () => ({
  getCurrentWatchlist: vi.fn(() => Promise.resolve(mockWatchlist)),
  getPersistentWatchlist: vi.fn(() => Promise.resolve(mockPersistent)),
}))
vi.mock('@api/registry', () => ({
  getRegistryStatus: vi.fn(() => Promise.resolve(mockRegistry)),
}))

function renderPage() {
  // renderWithQueryClient already provides the Router + QueryClient context.
  return renderWithQueryClient(<IntelligencePage />)
}

describe('IntelligencePage', () => {
  it('renders the Investment Intelligence heading immediately', () => {
    renderPage()

    expect(
      screen.getByRole('heading', { level: 1, name: 'Investment Intelligence' }),
    ).toBeVisible()
  })

  it('renders the canonical portfolio summary on the Dashboard tab', async () => {
    renderPage()

    expect(
      await screen.findByRole('region', { name: 'Investment dashboard' }),
    ).toBeVisible()
    // portfolio value is formatted IDR, tabular — assert the distinctive total return pct
    await waitFor(() => expect(screen.getByText('-41.1%')).toBeVisible())
    expect(screen.getByText('ARNA')).toBeVisible()
  })

  it('shows watchlist signals on the Signals tab', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('tab', { name: 'Signals' }))

    expect(await screen.findByRole('region', { name: 'Signals' })).toBeVisible()
    await waitFor(() => expect(screen.getByText('BBRI')).toBeVisible())
  })

  it('shows market risk on the Risk tab', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('tab', { name: 'Risk' }))

    expect(await screen.findByText('14.0')).toBeVisible()
    expect(screen.getByText('Green')).toBeVisible()
  })

  it('shows registry state on the Decisions tab', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('tab', { name: 'Decisions' }))

    expect(await screen.findByText('vol_weighted')).toBeVisible()
  })
})
