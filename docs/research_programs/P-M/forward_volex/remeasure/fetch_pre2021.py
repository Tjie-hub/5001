"""Regenerate the pre-2021 OHLCV backfill for the D-053 re-measurement.

The original `data_gaps/scripts/hist_pre2021.pkl` (1,414,611 bars) was never
committed (73MB, README: "regenerate rather than store") and no copy survives.
This re-runs the SAME fetch logic as `data_gaps/scripts/fetch_history.py`
(yfinance `period=max`, `auto_adjust=False`, bars before 2021-07-05) over the
SAME ticker list — the 772 tickers recorded in `data_gaps/data/hist_meta.pkl`
(its `zoo.pkl` input is also gone). The source may have revised history since
2026-09-19, so the output is fingerprinted and its bar count reported against
the original 1,414,611; any difference is disclosed, not reconciled.

Fetching raw prices is not a look at the outcome: no return, signal or overlay
is computed here.
"""
import sys, os, time, json, hashlib
import yfinance as yf, pandas as pd, warnings; warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
META = os.path.join(HERE, "..", "..", "data_gaps", "data", "hist_meta.pkl")
OUT = os.path.join(HERE, "work", "hist_pre2021.pkl")
CUT = pd.Timestamp("2021-07-05")

tk = sorted(pd.read_pickle(META).ticker.unique())
out, fails = [], []
print(f"fetching {len(tk)} tickers (bars before {CUT.date()})", flush=True)
for i, t in enumerate(tk, 1):
    for attempt in range(3):
        try:
            h = yf.Ticker(f"{t}.JK").history(period="max", auto_adjust=False)
            break
        except Exception as e:
            h = None; err = type(e).__name__; time.sleep(2 * (attempt + 1))
    if h is None or h.empty:
        fails.append((t, 'empty' if h is not None else err))
    else:
        h.index = pd.to_datetime(h.index).tz_localize(None)
        old = h[h.index < CUT]
        if len(old):
            out.append(pd.DataFrame({'ticker': t, 'date': old.index,
                'open': old['Open'].values, 'high': old['High'].values,
                'low': old['Low'].values, 'close': old['Close'].values,
                'volume': old['Volume'].values}))
    if i % 100 == 0:
        print(f"  {i}/{len(tk)} kept={sum(len(x) for x in out):,} fails={len(fails)}", flush=True)
    time.sleep(0.2)
H = pd.concat(out, ignore_index=True).sort_values(['ticker', 'date']).reset_index(drop=True)
H.to_pickle(OUT)
json.dump(fails, open(os.path.join(HERE, "work", "fetch_fails.json"), "w"))
fp = hashlib.sha256(pd.util.hash_pandas_object(H, index=False).values.tobytes()).hexdigest()
print(f"DONE bars={len(H):,} (original 1,414,611) tickers={H.ticker.nunique()} fails={len(fails)}")
print(f"content fingerprint sha256={fp}")
