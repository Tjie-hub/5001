"""P4-2 regression: backtest/walk-forward fills respect IDX ARA/ARB bands.

TODO.md P4-2: price-limit bands existed only in the live path
(paper_trade.open_trade) — every historical expectancy assumed each computed
SL/TP was fillable at any distance. These tests pin the shared model
(engine/exits/price_limits) and the two properties that close the defect:

- a backtest exit can never fill beyond the entry-day auto-rejection band;
- an entry whose band-capped levels can't deliver the policy's min_rr is not
  taken (the same capped-level re-gate live open_trade applies).
"""
import pandas as pd
import pytest

from engine.exits.costs import apply_costs
from engine.exits.price_limits import (
    ARA_ARB_SAFETY, ara_arb_levels, cap_levels, capped_rr_ok,
)


# ── the shared model ─────────────────────────────────────────────────────

@pytest.mark.parametrize("price,pct", [
    (50, 0.35), (200, 0.35),          # tier 1 boundary inclusive
    (200.01, 0.25), (5000, 0.25),     # tier 2
    (5000.01, 0.20), (50_000, 0.20),  # tier 3
])
def test_tier_table_matches_live_rule(price, pct):
    lv = ara_arb_levels(price)
    assert lv["ara_pct"] == pct and lv["arb_pct"] == pct
    assert lv["ara_price"] == pytest.approx(price * (1 + pct))
    assert lv["arb_price"] == pytest.approx(price * (1 - pct))


def test_live_path_delegates_to_the_same_authority():
    from paper_trade import calc_ara_arb_levels
    for price in (100.0, 1500.0, 9000.0):
        assert calc_ara_arb_levels(price) == ara_arb_levels(price)


def test_cap_levels_pulls_levels_inside_the_band():
    out = cap_levels(1000.0, tp_price=1300.0, sl_price=700.0)   # ±25% tier
    assert out["tp_capped"] and out["sl_capped"]
    assert out["tp_price"] == pytest.approx(1250.0 * (1 - ARA_ARB_SAFETY))
    assert out["sl_price"] == pytest.approx(750.0 * (1 + ARA_ARB_SAFETY))


def test_cap_levels_noop_when_fillable():
    out = cap_levels(1000.0, tp_price=1150.0, sl_price=900.0)
    assert not out["tp_capped"] and not out["sl_capped"]
    assert out["tp_price"] == 1150.0 and out["sl_price"] == 900.0


def test_capped_rr_gate_mirrors_live():
    # capped reward 0.2438 vs risk 0.22 -> 1.11 < 2 -> refuse
    assert not capped_rr_ok(1000.0, 1243.75, 780.0, min_rr=2.0)
    # no TP or no SL -> the question does not apply, keep the entry
    assert capped_rr_ok(1000.0, None, 780.0, min_rr=2.0)
    assert capped_rr_ok(1000.0, 1243.75, None, min_rr=2.0)


# ── synthetic-fixture helpers ────────────────────────────────────────────

from datetime import datetime, timedelta


def _d(i):
    return (datetime(2026, 1, 1) + timedelta(days=i)).strftime("%Y-%m-%d")


def _bar(i, o, h, l, c, v=1_000_000):
    return {"date": _d(i), "open": o, "high": h,
            "low": l, "close": c, "volume": v}


def _wide_then_signal_df(entry_open=1060.0):
    """Wide swings (ATR ≈ 20% of price) into an NR7 setup whose entry-day
    ATR-implied target sits far beyond ARA — the phantom-fill geometry.

    Bars 0..19 oscillate ±10% with ~200-wide ranges (ATR14 ≈ 200), bar 21 is
    the NR7 bar (narrowest range of the last 7, volume on par), bar 22 opens
    above its high (the trigger), then two rally bars reach past the band.
    """
    rows = []
    c = 1000.0
    for i in range(20):
        o = c
        c = c * (1.10 if i % 2 == 0 else 0.90)
        rows.append(_bar(i, o, max(o, c) + 50, min(o, c) - 50, c))
    rows.append(_bar(20, 1040, 1052, 1048, 1050))          # NR7 bar
    rows.append(_bar(21, entry_open, entry_open + 5, entry_open - 5, entry_open + 2))
    rows.append(_bar(22, 1330, 1420, 1320, 1350))          # rally through the band
    rows.append(_bar(23, 1340, 1700, 1330, 1400))          # reaches past the cap
    rows.append(_bar(24, 1380, 1420, 1340, 1360))
    return pd.DataFrame(rows)


# ── the pinned properties ────────────────────────────────────────────────

def test_nr7_backtest_never_fills_beyond_ara():
    """The headline P4-2 case: NR7 with 2×ATR target beyond ARA(entry).

    Pre-fix, the TP sat at entry + 2×ATR ≈ +38% — beyond the +25% band, a
    price the exchange never prints — and the backtest booked it as a fill.
    Post-fix the level is capped just inside ARA and fills there.
    """
    from engine.strategies import strategy_nr7_breakout
    df = _wide_then_signal_df()
    res = strategy_nr7_breakout(df)
    trades = res["trades"]
    assert len(trades) == 1
    tr = trades[0]
    entry = tr.entry_price
    ara = ara_arb_levels(entry)["ara_price"]
    # the uncapped target really is beyond the band — this IS the defect case
    assert entry + 2 * 200 > ara
    assert tr.exit_reason == "TP"
    # the fill can never sit beyond (or at) the auto-rejection ceiling
    assert tr.exit_price <= ara * (1 - ARA_ARB_SAFETY) + 1e-6
    assert tr.exit_price == pytest.approx(
        apply_costs(ara * (1 - ARA_ARB_SAFETY), "SELL"), rel=1e-4)


def test_run_strategy_caps_kernel_policy_levels():
    """run_strategy (the kernel path momentum/liquidity-sweep/etc. use, and
    walk-forward with them) gets the same cap via the policy's levels."""
    from engine.strategies import run_strategy
    df = _wide_then_signal_df()
    signals = pd.Series(False, index=df.index)
    signals.iloc[-3] = True          # enter at next bar's open (1060 area)
    res = run_strategy(df, signals, atr_sl_mult=0.5, atr_tp_mult=2.0,
                       min_rr=1.0, strategy_name="cap-test")
    assert len(res["trades"]) == 1
    tr = res["trades"][0]
    ara = ara_arb_levels(tr.entry_price)["ara_price"]
    assert tr.exit_reason == "TP"
    assert tr.exit_price <= ara * (1 - ARA_ARB_SAFETY) + 1e-6


def test_run_strategy_skips_entry_when_capped_rr_below_min_rr():
    """Live open_trade's capped-level min_rr gate, on the backtest side: with
    a stop 1×ATR wide, min_rr 2 and a target capped to just inside ARA, the
    entry no longer delivers the R/R the policy demands — so it is not taken.
    Pre-fix the uncapped levels gave exactly 2.0 and the trade existed."""
    from engine.strategies import run_strategy
    df = _wide_then_signal_df()
    signals = pd.Series(False, index=df.index)
    signals.iloc[-3] = True
    res = run_strategy(df, signals, atr_sl_mult=1.0, atr_tp_mult=2.0,
                       min_rr=2.0, strategy_name="skip-test")
    assert res["trades"] == []
    assert res["final_capital"] == res["initial_capital"]


def test_crash_recovery_caps_retracement_target_beyond_ara():
    """Counter-trend geometry: after a deep drop the retracement target can
    sit beyond ARA(entry) even though it is below the pre-crash price."""
    from engine.strategies import strategy_crash_recovery
    rows = []
    c = 2000.0
    for i in range(30):                      # long steady climb
        o, c = c, c * 1.01
        rows.append(_bar(i, o, c * 1.005, o * 0.995, c))
    for i in range(30, 36):                  # the crash: -30% over 6 bars
        o, c = c, c * 0.945
        rows.append(_bar(i, o, c * 1.005, c * 0.995, c))
    for i in range(36, 41):                  # resume: modest up bars
        o, c = c, c * 1.03
        rows.append(_bar(i, o, c * 1.01, o * 0.99, c))
    df = pd.DataFrame(rows)
    res = strategy_crash_recovery(df)
    for tr in res["trades"]:
        ara = ara_arb_levels(tr.entry_price)["ara_price"]
        if tr.exit_reason == "TP":
            assert tr.exit_price <= ara * (1 - ARA_ARB_SAFETY) + 1e-6
