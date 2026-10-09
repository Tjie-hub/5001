# HANDOFF G1 — market-stress reversal S1 (HYP-PM-0019, D-078/D-075) · 2026-10-09

**Branch:** `research/market-stress-reversal-2026-10` @ fa78700 (frozen) + this commit.
**Run:** ONE run 2026-10-09 ~08:49–09:00 WIB, `STRESS_G1_APPROVED=1`, frozen `g1_run.py`
unchanged. **Verdict: NULL (falsified)** — see `VERDICT.md`.

## Integrity checks (all BEFORE any outcome; all green)

- **Sidecar** `sha256sum -c PREDECLARATION.sha256`: 7/7 OK
  (`PREDECLARATION.md` = `23979b75a209ab2229ea9497befb0fec2fd9381d16c244fb7199435713c60a85`).
- **Snapshots re-hashed by me** and re-verified again inside the runner before any outcome:
  walkforward `a2d7e675e5c66387446b888287ebbe7cef563b278c48f1518a88c797bc4bbc47`,
  history_long `7d298068fbc5633277ef0c032ed0257f935c9ef902068b16daa75ac0ba5e5714` — both match
  `CENSUS_G0.json`.
- **Dataset fingerprint** recomputed read-only on the walkforward snapshot:
  max_date 2026-10-07, 1,102,829 rows, sha256 `9c26e0df2fdd4e4bec378ff9d38b4d4ccbbdeaa9a6176ca71b3fdb955f137c03` — matches.
- **Bar/N:** census `N_expected` 608, `bar_frozen_608` 3.2973 (exact 3.297294) — confirmed at
  run time; ledger rows counted 605 + HYP-PM-0017's 2 arms (D-076) + this arm (D-078) = 608.
  D-074 NOT registered → the 609 contingency is inapplicable (owner 2026-10-09).
- **Boundary tests:** `test_architecture_boundary.py` + `test_research_data_fence.py` — 8/8 pass
  (worktree, DB_PATH→tmp).
- Read-only DBs (mode=ro) on the pinned snapshots; no registry edits; `ops/hardening`, jurnal26,
  production and the 5001 service untouched; `logs/TELEGRAM_OFF` untouched; no secrets printed.

## Runtime

11.0 minutes (panel build + hash re-verification + 63 × s1_event), single-threaded, well inside
the G0 estimate (10–20 min).

## Headline numbers (pooled, n = 63; bar 3.2973)

- mean R **−2.1190%** (sd 2.7216%) → t **−6.180** · E1 (2007–2020, n 46) **−1.6584%** ·
  E2 (2021-07→, n 17) **−3.3654%** · next-day entry **−2.0102%** · Parkinson-60-matched
  **−2.4058%** · ex-big-4 **−2.1072%** · ex-ex-date **−2.1471%** · mean cost 2.0295% ·
  mean β 1.136 (baskets are high-β: losers on stress days).
- 2021-H1 "neither half" events: **0**.

## Per-event table (date · σ-multiple · basket k · ARB excluded · β · cost · R)

```
2007-01-10  -2.560 k= 7 arb=0 b=1.297 c=2.19% R= -3.494%
2007-03-05  -2.584 k= 7 arb=0 b=1.192 c=2.27% R= -5.001%
2007-08-01  -2.970 k=12 arb=0 b=1.024 c=2.07% R= -3.068%
2007-08-15  -4.350 k=12 arb=0 b=0.920 c=2.69% R= -2.436%
2008-01-16  -3.377 k=10 arb=0 b=0.946 c=2.90% R= -2.671%
2008-03-10  -2.523 k= 9 arb=0 b=0.996 c=1.59% R= -3.924%
2008-04-03  -2.576 k= 8 arb=0 b=1.216 c=1.77% R= -0.130%
2008-09-09  -2.634 k= 6 arb=0 b=1.212 c=2.00% R= -3.581%
2008-10-06  -6.962 k= 6 arb=0 b=1.280 c=1.30% R= +8.875%
2008-10-24  -3.143 k= 6 arb=0 b=0.983 c=1.68% R= -3.101%
2010-05-05  -2.513 k=14 arb=0 b=0.879 c=1.89% R= +0.126%
2010-05-25  -3.147 k=13 arb=0 b=0.967 c=2.11% R= +0.149%
2011-01-10  -3.195 k=15 arb=0 b=0.959 c=2.16% R= -1.392%
2011-08-05  -5.871 k=18 arb=0 b=0.944 c=2.17% R= +1.647%
2011-08-19  -3.702 k=18 arb=0 b=1.097 c=2.52% R= -3.060%
2011-09-22  -7.594 k=14 arb=0 b=1.208 c=1.59% R= +3.857%
2012-06-04  -3.326 k=15 arb=0 b=1.081 c=2.02% R= -2.399%
2013-06-03  -2.645 k=17 arb=0 b=1.120 c=2.16% R= -5.204%
2013-06-20  -3.379 k=15 arb=0 b=1.074 c=1.99% R= -1.776%
2013-07-03  -3.554 k=13 arb=0 b=1.183 c=2.19% R= -3.372%
2013-08-19  -5.780 k=16 arb=0 b=1.299 c=1.80% R= -4.191%
2014-04-10  -2.638 k=15 arb=0 b=1.596 c=1.48% R= -1.514%
2014-10-02  -2.838 k=15 arb=0 b=1.364 c=1.57% R= -0.602%
2014-12-16  -2.933 k=16 arb=0 b=1.158 c=1.72% R= -0.433%
2015-04-27  -4.217 k=15 arb=0 b=1.140 c=1.61% R= -0.050%
2015-06-08  -2.712 k=13 arb=0 b=1.122 c=1.92% R= -2.889%
2015-08-11  -3.354 k=12 arb=0 b=1.023 c=1.37% R= -3.364%
2015-08-21  -2.776 k=11 arb=0 b=1.287 c=1.99% R= -4.655%
2015-09-07  -2.577 k=12 arb=0 b=1.230 c=1.64% R= -1.523%
2015-10-29  -2.829 k=12 arb=0 b=1.223 c=2.05% R= -1.088%
2016-11-11  -3.157 k=17 arb=0 b=1.017 c=1.73% R= +0.258%
2017-05-10  -2.866 k=17 arb=0 b=1.005 c=1.57% R= +0.134%
2018-01-30  -3.236 k=19 arb=0 b=1.328 c=1.98% R= -1.957%
2018-03-07  -3.857 k=18 arb=0 b=1.291 c=2.71% R= -1.999%
2018-04-30  -4.744 k=16 arb=0 b=1.229 c=1.94% R= -4.009%
2018-06-20  -2.554 k=16 arb=0 b=1.035 c=1.77% R= -1.327%
2018-06-28  -3.987 k=17 arb=0 b=0.818 c=1.75% R= -5.511%
2018-07-31  -2.647 k=16 arb=0 b=1.217 c=1.55% R= -5.358%
2018-08-13  -4.264 k=16 arb=0 b=1.008 c=2.42% R= -0.400%
2018-09-05  -4.766 k=15 arb=0 b=1.296 c=1.77% R= -0.565%
2019-08-05  -2.756 k=18 arb=0 b=1.069 c=1.82% R= -0.169%
2020-01-27  -2.520 k=16 arb=0 b=1.386 c=1.66% R= -1.011%
2020-02-26  -2.724 k=13 arb=0 b=1.020 c=1.68% R= +4.256%
2020-03-06  -2.620 k=13 arb=0 b=1.156 c=1.81% R= -2.577%
2020-04-08  -2.540 k=14 arb=0 b=1.022 c=1.42% R= -5.217%
2020-09-10  -2.861 k=21 arb=0 b=1.040 c=1.83% R= -0.573%
2022-05-12  -3.285 k=31 arb=1 b=1.073 c=1.74% R= -1.590%
2023-01-05  -3.485 k=23 arb=0 b=1.034 c=2.31% R= -6.803%
2023-03-14  -2.914 k=23 arb=2 b=1.465 c=2.12% R= -3.351%
2023-08-01  -2.536 k=28 arb=1 b=1.135 c=1.93% R= -2.570%
2023-10-04  -3.032 k=28 arb=2 b=1.355 c=2.15% R= -1.645%
2023-10-30  -3.196 k=26 arb=0 b=0.981 c=2.10% R= -2.814%
2024-06-14  -2.635 k=23 arb=0 b=0.930 c=1.97% R= -0.184%
2024-08-05  -5.156 k=23 arb=2 b=1.004 c=1.69% R= +0.577%
2024-12-19  -3.486 k=22 arb=1 b=1.271 c=2.24% R= -5.513%
2025-02-25  -3.244 k=22 arb=3 b=1.125 c=2.19% R= -3.566%
2025-03-18  -3.720 k=23 arb=0 b=1.166 c=2.59% R= -3.180%
2025-10-17  -3.059 k=35 arb=4 b=1.099 c=3.08% R= -3.500%
2026-01-28  -5.785 k=47 arb=4 b=1.159 c=2.13% R= -9.045%
2026-03-02  -2.607 k=36 arb=1 b=1.137 c=3.66% R= -5.028%
2026-05-08  -2.702 k=36 arb=2 b=1.107 c=2.66% R= -4.855%
2026-05-21  -3.338 k=35 arb=2 b=1.250 c=2.46% R= -3.351%
2026-06-03  -3.453 k=33 arb=1 b=1.311 c=3.04% R= -0.792%
```

## Year table (n · mean R)

2007: 4 · −3.50% | 2008: 6 · −0.76% | 2010: 2 · +0.14% | 2011: 4 · +0.26% | 2012: 1 · −2.40%
| 2013: 4 · −3.64% | 2014: 3 · −0.85% | 2015: 6 · −2.26% | 2016: 1 · +0.26% | 2017: 1 · +0.13%
| 2018: 8 · −2.64% | 2019: 1 · −0.17% | 2020: 5 · −1.02% | 2022: 1 · −1.59% | 2023: 5 · −3.44%
| 2024: 3 · −1.71% | 2025: 3 · −3.42% | 2026: 5 · −4.61%. Positive years: 2010, 2011, 2016,
2017 — n = 8 events combined, all ≤ +0.26%.

## Five worst events

1. **2026-01-28** −9.045% (r_m −8.59%, −5.79σ, k 47, β 1.159, cost 2.13%)
2. **2023-01-05** −6.803% (−3.49σ, k 23, β 1.034, cost 2.31%)
3. **2024-12-19** −5.513% (−3.49σ, k 22, β 1.271, cost 2.24%)
4. **2018-06-28** −5.511% (−3.99σ, k 17, β 0.818, cost 1.75%)
5. **2018-07-31** −5.358% (−2.65σ, k 16, β 1.217, cost 1.55%)

Note the worst three are the three most recent years — the drag is not fading; if anything it
deepens as baskets widen (k 22–47 in 2023+ vs 6–19 earlier).

## ARB-excluded counts

Mean 0.41 per event (E1 pre-2021: 0 for all 46 events — structural, the builder dropped
zero-volume stale bars; E2 2021+: median 1, range 0–4; total E2 ARB exclusions 28 over 17
events). Match the census medians (E1 0 / E2 1).

## Report-only (not tested)

- **S2** (EW liquid market t→t+5 minus its trailing-250 mean 5-session return): mean
  **−1.369%** (n 63) — the market itself keeps falling short of baseline after stress days:
  continuation, not reversal, at the market level.
- **Horizons:** h1 −2.049% · h5 (= the arm) −2.119% · h10 −1.877% · h20 −1.800% — negative at
  every horizon; no reversal emerges later either.
- **Later-in-episode stress days:** **counts only (78, per the G0 census) — no outcome machinery
  was run on them.** The frozen `g1_run.py` books outcomes for episode FIRST days only; the
  predeclaration designated later days report-only, and no outcome for them was computed, printed
  or stored. (A later-day outcome study would be a new, owner-gated spec.)
- β fallback and short-exit members: recorded per event in `RESULT_*.json: per_event`
  (`beta_fallback`, `short_exit_basket/mkt`).

## Governance

One run, exactly as frozen; no fix needed (no crash). Registries NOT edited here — the planner
files the D-078 outcome. Branch pushed; nothing else touched.

*— ZCode, 2026-10-09*
