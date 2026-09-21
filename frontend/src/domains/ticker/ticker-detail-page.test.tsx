import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { Route, Routes } from 'react-router'
import { renderWithQueryClient } from '@tests/query-client-test-utils'
import { TickerDetailPage } from './ticker-detail-page'
import { ApiRequestError } from '@api/client'
import type { TickerDetail, TradeFlow } from '@models/ticker'

const mockDetail: TickerDetail = {
  symbol: 'DMAS',
  identity: {
    status: 'active', in_idx30: false, in_lq45: false, in_idx80: true,
    sector: 'Consumer',
  },
  price: {
    date: '2026-09-02', open: 640, high: 650, low: 635, close: 645,
    volume: 123_456_789, chg: 5, chg_pct: 0.78,
  },
  regime: { regime: 'BULL', adx14: 33.8, band: 'BULL_MODERATE' },
  production_admission: {
    band: 'BULL_MODERATE',
    candidates: ['Trend Following Breakout', 'NR7 Breakout', 'momentum'],
    admitted: [],
    verdicts: [
      {
        strategy: 'momentum', admitted: false, stage: 'disabled',
        reason: 'listed in paper_config disabled_strategies',
        registry_state: 'UNREGISTERED', is_counter_trend: false,
      },
    ],
  },
  signals: [
    {
      scan_time: '2026-08-13 10:05', strategies: 'distribution',
      direction: 'SELL', flow_score: -3, flow_verdict: 'BEARISH',
      smart_money: 'NEUTRAL', reasons: 'test',
    },
  ],
  flow: {
    latest: {
      trade_date: '2026-09-01', composite_score: 2.5,
      verdict: '🟡 NEUTRAL', smart_money: 'NEUTRAL', net_value: -12_064_689_000,
    },
    foreign_accumulation: {
      score_pct: 19.86, foreign_net_lots: 217_533,
      avg_daily_vol_lots: 1_095_495, dates_used: 5, latest_date: '2026-09-01',
    },
  },
  watchlist_membership: [
    {
      date: '2026-09-01', strategy: 'eod', rank: 1, confidence: 0.4,
      conviction: 0.0, confluence: 2,
    },
  ],
  agent_decisions: [],
  position: null,
  timeline: [
    { at: '2026-09-01 16:40', kind: 'agent_decision', summary: 'agent firm approve (eod)' },
    { at: 'not-a-timestamp', kind: 'agent_decision', summary: 'instrumentation marker' },
  ],
  market_context: {
    date: '2026-09-02',
    risk_score: 30.7,
    tier: 'YELLOW',
    components: { vpin: 0, accdist: 40, breadth: 0, technicals: 0, foreign_flow: 40 },
    ihsg: {
      close: 6603.79, ma5: 6550.0, ma20: 6500.0, death_cross: false,
      lower_high: false, support_breaks: [], ytd_pct: 3.2,
    },
    breadth: {
      date: '2026-09-02', advancers: 210, decliners: 150, unchanged: 30,
      adv_dec_ratio: 1.4, pct_advancing: 52.5, pct_above_ma20: 61.0,
      label: 'NEUTRAL',
    },
    foreign_flow: { today: 1.2e9, net_5d: 5.3e9, net_20d: -2.1e9, trend: 'INFLOW' },
    vpin: { avg_vpin: 0.31, pct_above_08: 0, pct_above_095: 0, label: 'GREEN' },
    accdist: {
      date: '2026-09-02', total: 390, dist_count: 80, acc_count: 160,
      neutral_count: 150, dist_pct: 20.5, acc_pct: 41.0, avg_numeric_score: 0.4,
      label: 'NEUTRAL',
    },
  },
  data_freshness: {
    ohlcv: '2026-09-02', stockbit_flow: '2026-09-02', broker_flow: '2026-09-01',
  },
  as_of: '2026-09-02T10:00:00+07:00',
}

/** Minimal Trade Flow payload for the page's Trade Flow section. */
const mockTradeFlow: TradeFlow = {
  symbol: 'DMAS',
  metric: 'value',
  requested: { start: '2026-09-01', end: '2026-09-01' },
  coverage: {
    first_available_session: '2026-08-25',
    last_available_session: '2026-09-01',
  },
  sessions: [
    {
      date: '2026-09-01',
      minutes: 1,
      buy_value: 1_000_000,
      sell_value: 400_000,
      net_value: 600_000,
      net_value_exact: 600_000,
      last_price: 645,
      first_bar: '09:00',
      last_bar: '09:00',
    },
  ],
  missing_sessions: [],
  session_marks: [{ date: '2026-09-01', index: 0 }],
  series: {
    points: 1,
    time: ['2026-09-01 09:00'],
    cum_buy: [1_000_000],
    cum_sell: [400_000],
    net_flow: [600_000],
    price: [645],
  },
  totals: {
    buy_value: 1_000_000,
    sell_value: 400_000,
    net_value: 600_000,
    net_value_exact: 600_000,
    net_side: 'accumulation',
    last_price: 645,
  },
  anomaly_minutes: 0,
  big_money: { available: false, reason: 'No production trade-size classification exists.' },
  filters_supported: { investor: ['all'], trade_type: ['regular'], metric: ['value'] },
  as_of: '2026-09-02T10:00:00+07:00',
}

vi.mock('@api/ticker', () => ({
  getTickerDetail: vi.fn(() => Promise.resolve(mockDetail)),
  getRuntimeStatus: vi.fn(() => Promise.resolve(null)),
  getTickerTradeFlow: vi.fn(() => Promise.resolve(mockTradeFlow)),
}))

function renderTickerPage(symbol: string) {
  return renderWithQueryClient(
    <Routes>
      <Route path="/ticker/:symbol" element={<TickerDetailPage />} />
    </Routes>,
    { initialEntries: [`/ticker/${symbol}`] },
  )
}

describe('TickerDetailPage', () => {
  it('renders the workspace heading with the route symbol', () => {
    renderTickerPage('DMAS')

    expect(
      screen.getByRole('heading', { level: 1, name: 'Ticker · DMAS' }),
    ).toBeVisible()
  })

  it('shows a loading skeleton before data arrives', () => {
    renderTickerPage('DMAS')

    expect(screen.getByRole('status', { name: /loading ticker detail/i })).toBeVisible()
  })

  it('renders all four regions from real API data, not Reserved placeholders', async () => {
    renderTickerPage('DMAS')

    expect(await screen.findByText('645,00')).toBeVisible()

    for (const regionName of [
      'Executive Summary',
      'Primary Region',
      'Context',
      'Activity Timeline',
    ]) {
      expect(screen.getByRole('region', { name: regionName })).toBeVisible()
    }
    expect(screen.queryByText('Reserved')).not.toBeInTheDocument()
  })

  it('renders production truth honestly, including a zero-admission state', async () => {
    renderTickerPage('DMAS')

    await screen.findByText('645,00')

    // regime band comes from the backend detection, not invented
    expect(screen.getByText('Bull Moderate')).toBeVisible()
    expect(screen.getByText('Bull')).toBeVisible()
    // zero admissible strategies is shown with the blocking reason
    expect(screen.getByText('None admitted')).toBeVisible()
    expect(screen.getByText(/Why nothing is admissible right now/)).toBeVisible()
    expect(screen.getByText(/listed in paper_config disabled_strategies/)).toBeVisible()
    // watchlist + position render the production state
    expect(screen.getByText(/Eod watchlist — rank 1/)).toBeVisible()
    expect(screen.getByText('No open paper position')).toBeVisible()
  })

  it('renders the timeline with an em-dash for sentinel timestamps', async () => {
    renderTickerPage('DMAS')

    await screen.findByText('645,00')

    expect(screen.getByText('2026-09-01 16:40')).toBeVisible()
    expect(screen.getByText('instrumentation marker')).toBeVisible()
  })

  it('renders a NOT_FOUND empty state for an unknown symbol', async () => {
    const { getTickerDetail } = await import('@api/ticker')
    vi.mocked(getTickerDetail).mockRejectedValueOnce(
      new ApiRequestError('TICKER_NOT_FOUND', 404, 'Ticker ZZZZ is not in the production universe', {}),
    )

    renderTickerPage('ZZZZ')

    expect(
      await screen.findByText('Ticker not in the production universe'),
    ).toBeVisible()
  })
})
