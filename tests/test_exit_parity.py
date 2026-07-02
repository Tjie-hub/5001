"""Backtest exits must match the engine/exits kernel (plan 1B Tasks 5-6).

The C-8 scenario: a bar makes a new high AND a deep low. The old percent
trail ratcheted from the same bar's high and exited on that bar's low —
look-ahead (no guarantee the high printed first). The kernel only trails
from the PRIOR bar's extreme.
"""
import numpy as np
import pandas as pd
import pytest


def _flat_df(n=20, close=1000.0, rng=20.0):
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "date": dates,
        "open": np.full(n, close), "high": np.full(n, close + rng / 2),
        "low": np.full(n, close - rng / 2), "close": np.full(n, close),
        "volume": np.full(n, 1_000_000.0),
    })


def test_trailing_stop_does_not_ratchet_from_same_bar_high():
    """Audit C-8. Signal at bar 18 -> entry bar 19. Bar 20 spikes high=1100
    then low=1041 (still above every stop derived from PRIOR extremes).
    Old code: stop ratchets to ~1100*(1-2%)=1078 intrabar -> bogus exit.
    New kernel: stop for bar 20 comes from prior extreme (1010) -> hold,
    and the trade closes EOD on the last bar."""
    from engine.strategies import run_strategy

    df = _flat_df(22)                       # bars 0..21, ATR14 = 20 everywhere
    df.loc[19, ["open", "high", "low", "close"]] = [1000, 1010, 995, 1005]
    df.loc[20, ["open", "high", "low", "close"]] = [1050, 1100, 1041, 1050]
    # bar 21 stays above the LEGITIMATE prior-extreme stop (1100 - 20 = 1080)
    df.loc[21, ["open", "high", "low", "close"]] = [1090, 1095, 1085, 1092]

    signals = pd.Series(False, index=df.index)
    signals.iloc[18] = True                 # entry at bar 19 open

    result = run_strategy(df, signals, atr_sl_mult=1.0, atr_tp_mult=100.0,
                          min_rr=1.0, trail_sl=True, strategy_name="t")
    assert len(result["trades"]) == 1
    t = result["trades"][0]
    assert t.exit_reason == "EOD", (
        f"expected EOD hold-through, got {t.exit_reason} @ {t.exit_price} "
        f"on {t.exit_date} — same-bar trail ratchet (C-8) still present"
    )
    assert t.exit_date == "2026-01-22"      # last bar


def _trending_df(seed=7, n=160):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    close = 1000 + np.cumsum(rng.normal(3, 12, n))
    close = np.maximum(close, 200.0)
    high = close + rng.uniform(5, 25, n)
    low = close - rng.uniform(5, 25, n)
    vol = rng.uniform(1e6, 2e6, n)
    vol[::7] *= 2.5                          # periodic volume spikes -> entries
    return pd.DataFrame({"date": dates, "open": close - 2, "high": high,
                         "low": low, "close": close, "volume": vol})


def test_tfb_exits_match_kernel_replay():
    """Differential parity: replay every TFB trade's bars through the shared
    kernel (+ MA20-break rule) and demand identical exits."""
    from engine.strategies import strategy_trend_following_breakout, apply_costs
    from engine.indicators import calc_atr
    from engine.exits import PositionView, Bar, evaluate_exit, get_policy

    df = None
    trades = []
    for seed in range(30):                   # first seed producing trades wins
        df = _trending_df(seed)
        trades = strategy_trend_following_breakout(df)["trades"]
        if trades:
            break
    assert trades, "no TFB trades in 30 seeds - loosen _trending_df"

    policy = get_policy("Trend Following Breakout")
    atr = calc_atr(df, 14)
    ma20 = df["close"].rolling(20).mean()
    dates = df["date"].astype(str).str[:10].tolist()

    for t in trades:
        i0 = dates.index(t.entry_date)
        sig_atr = float(atr.iloc[i0 - 1])
        hi = lo = t.entry_price              # extremes seeded at cost-adjusted entry
        replay = None
        for i in range(i0, len(df)):
            row = df.iloc[i]
            bar = Bar(date=dates[i], open=float(row["open"]), high=float(row["high"]),
                      low=float(row["low"]), close=float(row["close"]))
            view = PositionView(policy=policy, direction="LONG", entry=t.entry_price,
                                atr=sig_atr, highest_seen=hi, lowest_seen=lo, hold_days=0)
            d = evaluate_exit(view, bar)
            if d is not None:
                replay = (dates[i], d.reason, apply_costs(d.fill_price, "SELL"))
                break
            if bar.close < float(ma20.iloc[i]):
                replay = (dates[i], "MA20_BREAK", apply_costs(bar.close, "SELL"))
                break
            if i == len(df) - 1:
                replay = (dates[i], "EOD", apply_costs(bar.close, "SELL"))
                break
            hi = max(hi, bar.high)
            lo = min(lo, bar.low)

        assert replay is not None
        assert (t.exit_date, t.exit_reason) == (replay[0], replay[1]), (
            f"trade {t.entry_date}: strategy exited {t.exit_reason}@{t.exit_date}, "
            f"kernel replay says {replay[1]}@{replay[0]}"
        )
        assert t.exit_price == pytest.approx(replay[2], rel=1e-9)


def _steep_trend_with_spike_dip(n=110):
    """Deterministic 2%/bar riser; volume-spike signal at bar 90 (entry 91);
    bars 92-94 keep rising; bar 95 dips BETWEEN the high-anchored stop
    (highest-3xATR, hits) and the old close-anchored stop (close-3xATR,
    misses) while staying far above MA20 -> only Chandelier trailing exits."""
    idx = np.arange(n, dtype=float)
    close = 1000.0 * 1.02 ** np.minimum(idx, 94)
    close[95:] = close[94] * (1.003 ** (idx[95:] - 94))   # gentle drift after
    open_ = close * 0.995
    high = close * 1.005
    low = close * 0.99
    vol = np.full(n, 1_000_000.0)
    vol[90] = 2_500_000.0                                  # signal bar
    c90 = 1000.0 * 1.02 ** 90
    # bar 95: the discriminating dip
    open_[95] = 1.075 * c90
    high[95] = 1.080 * c90
    low[95] = 1.020 * c90       # < high-anchored stop (~1.0228*c90), > close-anchored (~1.0176*c90)
    close[95] = 1.055 * c90
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    return pd.DataFrame({"date": dates, "open": open_, "high": high,
                         "low": low, "close": close, "volume": vol})


def test_tfb_trail_is_high_anchored_chandelier():
    """Plan 1B semantic unification: TFB's trail anchors on the running HIGH
    (as the ft kernel always did), not the close. The dip bar pierces
    highest-3xATR but not close-3xATR: only the Chandelier convention exits,
    on the dip bar, with reason TRAIL."""
    from engine.strategies import strategy_trend_following_breakout
    df = _steep_trend_with_spike_dip()
    trades = strategy_trend_following_breakout(df)["trades"]
    assert len(trades) == 1, [f"{t.entry_date}->{t.exit_date}:{t.exit_reason}" for t in trades]
    t = trades[0]
    assert t.exit_reason == "TRAIL", f"got {t.exit_reason} @ {t.exit_date}"
    assert t.exit_date == str(df['date'].iloc[95])[:10]
