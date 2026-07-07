"""engine/portfolio_backtest.py — Portfolio-level backtesting across N tickers."""
import sqlite3
import logging

import numpy as np
import pandas as pd

from research.walkforward_multi import STRATEGY_FUNCS, compute_metrics


def _load_ohlcv(ticker: str, db_path: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        'SELECT date, open, high, low, close, volume FROM ohlcv '
        'WHERE ticker=? ORDER BY date ASC',
        conn, params=(ticker,)
    )
    conn.close()
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)
    return df


def _drawdown_curve(equity_series: pd.Series) -> list:
    peak = equity_series.cummax()
    dd = (equity_series - peak) / peak * 100
    return [{'date': str(d)[:10], 'dd_pct': round(float(v), 2)} for d, v in dd.items()]


def _rolling_sharpe(daily_ret: pd.Series, window: int = 60) -> list:
    def _sharpe(x):
        s = x.std()
        return float((x.mean() / s) * np.sqrt(252)) if s > 0 else 0.0
    rs = daily_ret.rolling(window).apply(_sharpe, raw=False)
    return [
        {'date': str(d)[:10], 'sharpe': round(float(v), 2)}
        for d, v in rs.dropna().items()
    ]


def _concurrent_positions(all_trades: list, dates: list) -> list:
    date_index = {d: i for i, d in enumerate(dates)}
    counts = [0] * len(dates)
    for ticker_trades in all_trades:
        for trade in ticker_trades:
            try:
                rng = pd.date_range(trade.entry_date, trade.exit_date, freq='B')
                for d in rng:
                    ds = d.strftime('%Y-%m-%d')
                    if ds in date_index:
                        counts[date_index[ds]] += 1
            except Exception:
                pass
    return [{'date': d, 'count': counts[i]} for i, d in enumerate(dates)]


def _correlation_matrix(ticker_returns: dict) -> dict:
    tickers = list(ticker_returns.keys())
    if len(tickers) < 2:
        return {'tickers': tickers, 'matrix': [[1.0]]}
    df = pd.DataFrame(ticker_returns).dropna()
    corr = df.corr()
    # Fill NaN on diagonal with 1.0 (zero-variance series), off-diagonal with 0.0
    corr_arr = corr.to_numpy(copy=True)
    np.fill_diagonal(corr_arr, 1.0)
    corr = pd.DataFrame(corr_arr, index=corr.index, columns=corr.columns).fillna(0.0)
    matrix = [
        [round(float(corr.loc[t1, t2]), 3) for t2 in tickers]
        for t1 in tickers
    ]
    return {'tickers': tickers, 'matrix': matrix}


def run_portfolio_backtest(
    tickers: list,
    strategy: str,
    capital: float,
    db_path: str,
) -> dict:
    """Run strategy on each ticker with equal capital split; return combined portfolio metrics.

    Raises:
        ValueError: Unknown strategy, or no tickers with sufficient data.
    """
    if strategy not in STRATEGY_FUNCS:
        raise ValueError(f'Unknown strategy: {strategy}')

    func = STRATEGY_FUNCS[strategy]
    n = len(tickers)
    per_cap = capital / n

    ticker_equity: dict = {}
    ticker_daily_ret: dict = {}
    all_trades: list = []
    per_ticker_out: list = []
    tickers_used: list = []
    tickers_skipped: list = []

    for ticker in tickers:
        try:
            df = _load_ohlcv(ticker, db_path)
        except Exception as e:
            logging.warning('portfolio_backtest: failed to load %s: %s', ticker, e)
            tickers_skipped.append(ticker)
            continue

        if len(df) < 60:
            tickers_skipped.append(ticker)
            continue

        raw = func(df, capital=per_cap)
        dates = [str(d)[:10] for d in df['date']]
        eq = pd.Series(raw['equity'], index=dates)
        daily_ret = eq.pct_change().dropna()

        metrics = compute_metrics(raw)
        ticker_equity[ticker] = eq
        ticker_daily_ret[ticker] = daily_ret
        all_trades.append(raw['trades'])
        tickers_used.append(ticker)

        per_ticker_out.append({
            'ticker':           ticker,
            'allocation':       round(per_cap),
            'equity_curve':     [{'date': d, 'value': round(float(v))} for d, v in eq.items()],
            'drawdown_curve':   _drawdown_curve(eq),
            'total_return_pct': metrics['total_return_pct'],
            'sharpe':           metrics['sharpe'],
            'max_drawdown_pct': metrics['max_drawdown_pct'],
            'total_trades':     metrics['total_trades'],
            'win_rate':         metrics['win_rate'],
        })

    if not tickers_used:
        raise ValueError('No tickers with sufficient data')

    # Merge equity curves on date intersection
    common_dates = sorted(
        set.intersection(*[set(s.index) for s in ticker_equity.values()])
    )

    portfolio_eq = sum(s.loc[common_dates] for s in ticker_equity.values())
    port_daily_ret = portfolio_eq.pct_change().dropna()

    peak = portfolio_eq.cummax()
    dd_series = (portfolio_eq - peak) / peak * 100
    total_return = (
        (float(portfolio_eq.iloc[-1]) - float(portfolio_eq.iloc[0]))
        / float(portfolio_eq.iloc[0]) * 100
    )
    std = port_daily_ret.std()
    sharpe = float((port_daily_ret.mean() / std) * np.sqrt(252)) if std > 0 else 0.0

    return {
        'tickers_used':    tickers_used,
        'tickers_skipped': tickers_skipped,
        'portfolio': {
            'equity_curve':         [{'date': d, 'value': round(float(v))} for d, v in portfolio_eq.items()],
            'drawdown_curve':       [{'date': str(d)[:10], 'dd_pct': round(float(v), 2)} for d, v in dd_series.items()],
            'rolling_sharpe':       _rolling_sharpe(port_daily_ret),
            'concurrent_positions': _concurrent_positions(all_trades, common_dates),
            'total_return_pct':     round(total_return, 2),
            'sharpe':               round(sharpe, 2),
            'max_drawdown_pct':     round(float(dd_series.min()), 2),
        },
        'per_ticker':  per_ticker_out,
        'correlation': _correlation_matrix(ticker_daily_ret),
    }
