import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithQueryClient } from '@tests/query-client-test-utils'
import { TradeFlowSection } from './trade-flow-section'
import type { TradeFlow } from '@models/ticker'

vi.mock('@api/ticker', () => ({
  getTickerDetail: vi.fn(() => Promise.resolve(null)),
  getRuntimeStatus: vi.fn(() => Promise.resolve(null)),
  getTickerTradeFlow: vi.fn(),
}))

import { getTickerTradeFlow } from '@api/ticker'

const mockFlow: TradeFlow = {
  symbol: 'TOWR',
  metric: 'value',
  requested: { start: '2026-09-01', end: '2026-09-01' },
  coverage: {
    first_available_session: '2026-08-25',
    last_available_session: '2026-09-01',
  },
  sessions: [
    {
      date: '2026-09-01',
      minutes: 2,
      buy_value: 2_530_000,
      sell_value: 1_420_000,
      net_value: 1_110_000,
      net_value_exact: 1_100_000,
      last_price: 102,
      first_bar: '09:00',
      last_bar: '09:01',
    },
  ],
  missing_sessions: ['2026-08-28'],
  session_marks: [{ date: '2026-09-01', index: 0 }],
  series: {
    points: 2,
    time: ['2026-09-01 09:00', '2026-09-01 09:01'],
    cum_buy: [1_000_000, 2_530_000],
    cum_sell: [400_000, 1_420_000],
    net_flow: [600_000, 1_110_000],
    price: [100, 102],
  },
  totals: {
    buy_value: 2_530_000,
    sell_value: 1_420_000,
    net_value: 1_110_000,
    net_value_exact: 1_100_000,
    net_side: 'accumulation',
    last_price: 102,
  },
  anomaly_minutes: 0,
  big_money: {
    available: false,
    reason: 'No production trade-size classification exists.',
  },
  filters_supported: {
    investor: ['all'],
    trade_type: ['regular'],
    metric: ['value'],
  },
  as_of: '2026-09-04T09:00:00+07:00',
}

function mockResolved(flow: TradeFlow | null) {
  vi.mocked(getTickerTradeFlow).mockResolvedValue(flow ?? mockFlow)
}

describe('TradeFlowSection', () => {
  it('renders the range chip, series legend and net state from the payload', async () => {
    mockResolved(null)
    renderWithQueryClient(<TradeFlowSection symbol="TOWR" />)

    expect(await screen.findByText('01 Sep 26 → 01 Sep 26')).toBeInTheDocument()
    expect(screen.getAllByText(/Net Accumulation/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/\+Rp1\.1M/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Buy (cum)').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Sell (cum)').length).toBeGreaterThan(0)
    expect(screen.getByLabelText(/Trade flow chart, 2 minutes/)).toBeInTheDocument()
  })

  it('disables Big Money with the backend reason and exposes single-option filters', async () => {
    mockResolved(null)
    renderWithQueryClient(<TradeFlowSection symbol="TOWR" />)

    const bigMoney = await screen.findByRole('button', { name: 'Big Money' })
    expect(bigMoney).toBeDisabled()
    expect(bigMoney).toHaveAccessibleDescription(/No production trade-size classification/)

    expect(screen.getByRole('combobox', { name: 'Metric' })).toHaveValue('value')
    expect(screen.getByRole('combobox', { name: 'Investor' })).toHaveValue('all')
    expect(screen.getByRole('combobox', { name: 'Trade type' })).toHaveValue('regular')
  })

  it('shows missing sessions as an explicit gap note', async () => {
    mockResolved(null)
    renderWithQueryClient(<TradeFlowSection symbol="TOWR" />)

    expect(
      await screen.findByText(/No intraday flow data \(shown, not fabricated\): 28 Aug 26/),
    ).toBeInTheDocument()
  })

  it('renders the error state with retry when the query fails', async () => {
    vi.mocked(getTickerTradeFlow).mockRejectedValueOnce(
      new Error('NETWORK_ERROR: failed to fetch'),
    )
    renderWithQueryClient(<TradeFlowSection symbol="TOWR" />)

    expect(await screen.findByRole('alert')).toHaveTextContent(/Trade Flow failed to load/)
  })
})
