# HANDOFF G1 — HYP-PM-0017 (dividend clientele D1/D2) · 2026-10-08

**One frozen run** of `g1_run.py` at `0309cc6`, gate `DIVIDEND_G1_APPROVED=1`, snapshot
`/home/tjiesar/scratch/g0_snapshots_2026-10-08/walkforward_snapshot_2026-10-08.db`.
**Verdict: NULL — FAILED** (see VERDICT.md). No parameter, window, population or filter
changed from the frozen G0; no fix was needed; this is the one run.

## Integrity checks (all BEFORE any outcome)

- Tree at `0309cc6` exactly; clean.
- `PREDECLARATION.sha256` sidecar: all 7 files OK (predeclaration `50c91491…`).
- Walkforward snapshot sha256 `a2d7e675e5c66387446b888287ebbe7cef563b278c48f1518a88c797bc4bbc47` ✓.
- Dataset fingerprint recomputed = `9c26e0df2fdd4e4bec378ff9d38b4d4ccbbdeaa9a6176ca71b3fdb955f137c03`
  = `CENSUS_G0.json` value ✓ (max date 2026-10-07, 1,102,829 final rows).
- Census: N = 607, bar_exact 3.296828, bar_frozen 3.2968 ✓.
- The runner's own gates re-verified the snapshot sha and fingerprint before writing RESULT.

## Runtime

**95.8 minutes** single-threaded (HANDOFF_G0 estimated 15–30 — the Parkinson-decile control
recomputes the cross-section per member per event, which dominates; the estimate was wrong,
the run was not). Per-event worst-5 tables below were tabulated post-run by re-driving the
SAME frozen functions (`g1_run.load_world` → `populations` → `outcomes.d1/d2_event_return`),
purely for reporting; the verdict uses only `RESULT_20261008T085015Z.json`.

## Report-only tables

**Year table (mean excess per event):**

| year | D1 n | D1 mean | D2 n | D2 mean |
|---|---|---|---|---|
| 2021 | 19 | +2.2655% | 7 | +10.2992% |
| 2022 | 105 | +0.0028% | 61 | +1.8714% |
| 2023 | 99 | −1.1502% | 60 | +4.7148% |
| 2024 | 102 | −0.5494% | 60 | +0.3695% |
| 2025 | 116 | −0.7100% | 78 | −0.5470% |
| 2026 | 106 | −0.6710% | 58 | −0.3003% |

**AGM season (May–Jul) vs rest:** D1 −0.7721% (n 334) vs −0.1040% (n 213); D2 +1.4889%
(n 185) vs +1.1207% (n 139). **Foreign-ownership proxy:** none PIT; not reported (as
predeclared). **D1 window distribution:** {3:13, 4:26, 5:474, 6:4, 7:3, 9:1, 10:26} (median
5 sessions — the `dividend_created` anchor binds). **D2 yield terciles:** t1 +0.0860% (n 108),
t2 +0.3330% (n 108), t3 +3.5738% (n 108); edges 3.48%/6.23%. **D2 gross-of-tax mean:**
+1.9958%. **D2 drop ratio (close_cum − open_ex)/dividend:** median **0.6947**, IQR
0.4385–0.8553 — the ex-drop averages ~69% of the dividend (clientele direction), but the
residual capture does not survive the bar and has decayed. **D2 lower-two-terciles mean:**
+0.2095% (passes "not top-tercile-only", thin). Win rates: D1 42.2%, D2 51.9%. Medians:
D1 −0.9828%, D2 +0.0357%.

**Report-only gap, disclosed:** the brief's ex-close exit row is not implemented in the
frozen runner; it is a report-only row and does not touch the verdict. Filling it would be a
code change and therefore a new re-frozen run (owner-gated).

## Five worst events per arm (excess per event)

**D1** (post-run tabulation, n = 547):

| ticker | cum | yield | excess | decile-control |
|---|---|---|---|---|
| TPIA | 2026-05-25 | 0.30% | −44.23% | −42.29% |
| ELIT | 2023-06-05 | 1.58% | −31.99% | −24.13% |
| BREN | 2024-06-06 | 0.03% | −26.80% | −26.23% |
| HRTA | 2026-06-11 | 1.92% | −21.37% | −19.26% |
| GPRA | 2025-07-08 | 3.97% | −19.30% | −20.43% |

**D2** (post-run tabulation, n = 324):

| ticker | cum | yield | excess | decile-control |
|---|---|---|---|---|
| PTBA | 2025-06-20 | 11.12% | −3.98% | −4.25% |
| ADRO | 2024-05-27 | 7.17% | −3.69% | −3.72% |
| BJTM | 2025-06-03 | 9.68% | −3.21% | −3.00% |
| JSMR | 2023-05-19 | 2.16% | −2.82% | −3.06% |
| MPMX | 2025-06-10 | 11.11% | −2.71% | −2.24% |

## Anything surprising

1. **D1 is negative, not merely null** (−0.51% mean, both halves negative, decile control
   negative): buying liquid names before the cum date LOSES against the book. Whatever
   yield-seeking flow exists, it either arrives before our 5-session windows open or is
   already priced by the announcement anchors.
2. **D2's decay is the story**: +3.67% → −0.19% across the halves and a monotone year decay
   to negative in 2025-26 — the same era-flip/decay pattern the program keeps finding. The
   clientele mechanism (drop ≈ 69% of dividend < 100%) is real on average but no longer pays
   net of tax and cost, and never cleared the bar.
3. D2's decile control is POSITIVE (+1.38%) — the capture is not a low-volatility artifact;
   it is a real-but-decayed premium concentrated in the top yield tercile.
4. Population parity: n = 547 / 324 exactly match the G0 census counts; zero drift.

Per PREDECLARATION §8: no arm proceeds to a forward test. This closes HYP-PM-0017 as FAILED
under D-073's falsification rules; filing in the registries is the owner's act (not this
branch).

*— ZCode, 2026-10-08*
