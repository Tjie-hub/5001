# Pattern scan scripts — 2026-09-17

Run from the repo root with `SP=<scratch dir>` pointing at a directory holding `ohlcv.pkl`,
`panel2.pkl` and `ma.pkl` as built by `../../forward_regime/scripts/{extract,panel,t1,t2,ma}.py`.

| script | arm |
|---|---|
| `patterns.py` | resistance breakout, failed breakdown, failed breakout, falling wedge (x2) |
| `sweep.py` | liquidity sweep via the **production** `engine/smc.py::detect_liquidity_sweep` (~450s) |
| `sweepflow.py` | sweep + order-flow confirmation from `stockbit_flow` (2025+) |
| `side.py` | sideways support/resistance mean reversion (5 specs) |
| `kell_qulla.py` | Wedge Pop (Kell) and Episodic Pivot (Qullamaggie) daily proxy |
| `ep_orb.py` | Episodic Pivot with the **faithful** 09:00-09:30 opening-range-breakout entry |
| `wedge2.py` | six wedge-strictness definitions (detector-invariance test) |
| `brpt_all.py` | every pattern re-run on BRPT alone — the single-ticker trap |
| `why.py` | ticker-demeaned panel + per-ticker effect distribution |
| `verify.py` | bar-level verification that detectors fire on genuine instances |

`SHA256SUMS.txt` fixes the content as staged.

## Known limitations

- `sweep.py` loops per ticker and takes ~7.5 minutes over 749 tickers; output is buffered, so run
  it with `python -u` if progress is needed.
- The flow arm (`sweepflow.py`) covers **2025-01 onward only** — the era this session established as
  an outlier — so even its positive cells carry little weight.
- `stockbit_flow.composite_score` is unpopulated; any filter on it returns zero rows.
- `ep_orb.py` uses `stockbit_flow_bars.price` as the intraday trade price and approximates the exit
  with a fixed horizon rather than Qullamaggie's trailing 10 SMA with partial profit-taking.
