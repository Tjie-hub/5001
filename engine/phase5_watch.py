"""Phase 5 instrumentation (spec 2026-07-08): surface the moment the market
finally lets NR7_BULL trade — BULL-band entry/exit for governed tickers
(state-change only) and a distinctive first-signal alert."""


def band_changes(prev: dict, cur: dict, eligible=("BULL_MODERATE", "BULL_STRONG")):
    """Transitions in/out of NR7-eligible bands. Returns [(ticker, old, new)]."""
    out = []
    for t, new in sorted(cur.items()):
        old = prev.get(t)
        was = old in eligible
        now = new in eligible
        if was != now:
            out.append((t, old or "UNKNOWN", new))
    return out


def nr7_signal_alert_msg(ticker: str, n_signals_to_date: int) -> str:
    return (f"🎯 PHASE 5: NR7 live signal #{n_signals_to_date} — {ticker}. "
            f"The GO/NO-GO clock is running (rule: N>=15, >=+0.5%/trade net).")
