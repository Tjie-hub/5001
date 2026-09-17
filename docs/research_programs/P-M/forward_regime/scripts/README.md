# Verification scripts — FWD-PM-REGIME-001 and the refuted absorption hypothesis

Session 2026-09-17. Run order and purpose. All scripts expect `SP` in the environment pointing at a
scratch directory and are run with the repo venv from the repo root:

    SP=/path/to/scratch venv/bin/python <script>.py

| # | script | produces / answers |
|---|---|---|
| 1 | `extract.py` | pulls `ohlcv` (is_final=1) + `corporate_actions` to `ohlcv.pkl` / `ca.pkl` |
| 2 | `panel.py` | panel features, contamination guards, one-way date-clustered t (`cluster_t`) |
| 3 | `detect.py` | absorption-consolidation detector (the **refuted** hypothesis) |
| 4 | `grid.py` | 1,296-cell parameter grid over the absorption spec |
| 5 | `surge2.py` | conditional surge probability with event separation — lift 1.04x, t=0.31 |
| 6 | `ma.py` | EMA20 / VWMA20 / ATR14 / Kaufman ER / slope / participation / crossings |
| 7 | `bounce.py` | MA-touch test vs within-regime control — touch subtracts ~1.2% in uptrend |
| 8 | `reg.py` | regime effect and era stability |
| 9 | `exit.py` `exit2.py` `exit3.py` | 9 exit rules over 7,769 non-overlapping episodes |
| 10 | `breadth.py` | pairwise correlation, effective breadth N_eff ~= 10.4 |
| 11 | `sec.py` | beta-adjusted alpha, sector coverage of the signal set |
| 12 | `port.py` `port2.py` | portfolio equity curve, Sharpe, position-cap sweep |
| 13 | `power.py` | monthly vs per-trade endpoint power — 128 mo vs 24.5 mo |
| 14 | `delist.py` | survivorship / suspension-gap audit |
| 15 | `cost.py` `cost2.py` | gross-vs-net decomposition, round-trip sensitivity, breakeven 1.47% |
| 16 | `tune.py` `tune2.py` | 48-cell split-sample threshold tuning; IS->OOS rank corr 0.779 |
| 17 | `policy.py` | ATR-multiple sweep + IHSG downtrend filter (both rejected) |
| 18 | `side.py` | SIDEWAYS support/resistance mean reversion (rejected, t = -4.8 to -7.3) |
| 19 | `zvguard.py` | zero-volume contamination + traded-days guard variants (002) |
| 20 | `ref002.py` | re-derives the 002 reference effect and power under the guard |

`SHA256SUMS.txt` fixes the content of each script as staged.

## Corpus fingerprint

- source: `data/walkforward.db`, table `ohlcv`, `is_final = 1`
- rows 1,087,436 · tickers 959 · span 2021-07-05 to 2026-09-16
- corporate_actions: 2,171 rows (2,070 dividend, 101 split)
- contamination guards: split dates excluded; single-session moves beyond +/-35% excluded (305 bars)

## Known defects in these scripts

- `delist.py` checks **calendar-date gaps only**. IDX suspensions print zero-volume
  carry-forward bars on consecutive dates, which it never detects — this is the defect that
  caused spec 001 to be superseded. Use `zvguard.py` for suspension/staleness auditing.

- `port.py` contains a first-pass position cap that selects `names[:cap]` in insertion order
  (alphabetical, persistent). **That row is invalid.** `port2.py` supersedes it with seeded random
  selection across 5 seeds; use `port2.py` for any cap result.
- `sec.py`'s random-basket correlation baseline (rho = 0.123) samples alphabetically, not randomly.
  Treat it as approximate.
