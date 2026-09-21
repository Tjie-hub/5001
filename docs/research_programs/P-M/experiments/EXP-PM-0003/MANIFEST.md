# EXP-PM-0003 — Execution Manifest (frozen)

> Immutable pre-execution manifest for the confirmatory experiment of **HYP-PM-0003**. Every field below was consistency-checked against the frozen registered record (`a2db9204…`) **before** execution — **11/11 PASS** (§Consistency check, run live this session). No hypothesis amendment; no parameter changed. **The experiment has NOT been executed** — no `results.json`, `execution.log`, or any flow-vs-return statistic exists yet.

## Identity

| Field | Value |
|---|---|
| Registered Hypothesis ID | **HYP-PM-0003** |
| Registration timestamp | 2026-09-09T09:22:00Z |
| Registration receipt (HL-1) | [[HYP-PM-0003_REGISTERED]] §Registration receipt |
| Registration hash | `a2db92047e5e23f8c0bb8949797e7750706b6bfe33fa744509ef6a782f6f53f5` |
| Experiment ID | **EXP-PM-0003** |
| Dataset version | `broker_flow` (Dataset A, FROZEN D-043) — 79-ticker IDX80 roster, 2025-01-02 → 2026-08-27 excl. 2026-08-25, **1,222,713 rows**, `provenance_hash 329b22e49f0ef882b6da031f437e9d87084d2863837ebf8c830de362b7942558`; `ohlcv` (formation-day and forward-return close series, same roster) |
| Code commit hash | **N/A — uncommitted.** Working-tree HEAD is `9b6e3800c3dbdd0e717b00da91f0eccfda0f7226`, but this script and manifest are not part of any commit. Per instruction, nothing is committed by this task. |
| Pipeline version | standalone research script `run_exp_pm_0003.py` (sha256 `b32fde97ca1666d8166738f9250d78b446697f22f0a31a173fa73fd05283c55b`); **no gatekeeper pipeline invoked** — in-sample confirmatory test per the registered history-maturity gate (D-046/D-047), mirroring EXP-PM-0001's precedent |

## Experimental Specification (from the frozen record — verbatim intent)

| Field | Value |
|---|---|
| Mechanism under test | **M2.1** adverse-selection permanence (I7) — no competing-mechanism test is registered within this hypothesis (unlike HYP-PM-0001's I5-vs-I7 structure); HYP-PM-0002 (unregistered) separately targets the same I7 entry via a different instrument |
| Hypothesis statement | price displacement conditional on signed daily net broker-flow imbalance on formation day t **does not revert** over the following k=7 trading days; **signed continuation > 0** |
| Structural barrier | information asymmetry itself — cannot be arbitraged away |
| Friction model | **0.60% round-trip** (`engine/exits/costs.py` — same authority as EXP-PM-0001, verified identical: COMMISSION_BUY 0.15% + SLIPPAGE 0.10% buy leg; COMMISSION_SELL 0.25% + SLIPPAGE 0.10% sell leg) |
| Statistical methodology | **`research/statistics.py::bootstrap_ci`** on the pooled k=7 signed-continuation sample (CRO-adopted, Option A) — percentile bootstrap, `n_boot=10000`, `ci=0.95`, fixed `seed=20260711` (`research.statistics.SEED`, reused from `regime_config.yaml`). **No clustered inference, no double-clustering, no new statistical method** — `research/statistics.py` contains no clustered-inference implementation anywhere in this repository, and none is introduced here. Dependence sensitivity diagnostic (HYP-PM-0001's deflation ladder, N/N-10/N-100) reported alongside, explicitly labeled as a diagnostic, not a correction |
| Inclusion criteria | `(ticker, formation-date)` pairs with `net_flow = SUM(lot) != 0` and a valid k-trading-day-ahead close in `ohlcv` for the same ticker |
| Exclusion criteria | `2026-08-25` (Dataset A's own exclusion, structural — not a statistical filter). **No liquidity/parameter filter beyond Dataset A's own defined population** — none was registered |
| Observation window | 2025-01-02 → 2026-08-27 (Dataset A's frozen window; **IN-SAMPLE** per the history-maturity gate, D-046/D-047 — no OOS/Blind partition exists) |
| Outcome variables | `signed_continuation_k` (gross and net-of-cost) for k ∈ {3,7,15}; dependence-sensitivity diagnostic at N/N-10/N-100 |
| Refutation criteria | bootstrap CI on net-of-cost signed continuation at k=7 does not exclude zero, or the point estimate does not clear 0.60% ⇒ **M2.1 permanence REFUTED** for this data source and horizon |
| Expected evidence products | terminal **C2** (EV-9, N=1) — a provisional permanence signature **or** a competent refutation; both first-class (R12, PG-11) |

## Reproducibility

| Field | Value |
|---|---|
| Input datasets | `data/walkforward.db` → `broker_flow`, `ohlcv` (read-only, `mode=ro` URI + `PRAGMA query_only=ON`, belt-and-suspenders beyond EXP-PM-0001's plain `sqlite3.connect`) |
| Configuration | in-script constants matching the registration: `FRICTION=0.0060`, `KS=[3,7,15]`, `KPRIMARY=7`, `WIN_START/WIN_END`, `EXCLUDED_DATE`. No external config file; no tunable parameters |
| Software versions | python 3.12.3 · numpy 2.4.4 · pandas 3.0.2 |
| Randomness policy | **Deterministic given a fixed seed** (`SEED=20260711`, `research.statistics.SEED`, reused — not invented). This differs from EXP-PM-0001's fully seed-free design (a plain daily-mean t-test has no stochastic step); `bootstrap_ci`'s percentile-bootstrap resampling is inherently seeded, and reusing the corpus's existing fixed seed satisfies G2's determinism requirement via fixed-seed reproducibility, matching how the gatekeeper/regime pipeline already treats `bootstrap_ci` |
| Output artifact locations (on execution) | `EXP-PM-0003/results.json` · `EXP-PM-0003/execution.log` — **neither exists yet; not executed** |

## Consistency check (pre-execution gate)

**Result: 11/11 PASS — cleared to execute**, run live this session via `run_exp_pm_0003.py --consistency-check` (computes no flow-vs-return statistic):

```
[PASS] roster == 79 tickers (got 79)
[PASS] roster sha256 matches registration (got 7d4eb1004e7d1e83…)
[PASS] dataset fingerprint matches registration (got 329b22e49f0ef882…)
[PASS] row count matches registration (1,222,713) (got 1222713)
[PASS] 2026-08-25 exclusion clean (0 rows) (got 0)
[PASS] 388 canonical trading dates in window (got 388)
[PASS] k_primary == 7 (registered) (got 7)
[PASS] friction == 0.60% (registered) (got 0.006)
[PASS] robustness gradient == {3,7,15} (registered) (got [3, 7, 15])
[PASS] statistical test == bootstrap_ci (registered, no clustered inference) (static check)
[PASS] bootstrap seed reused from research.statistics.SEED (20260711) (got 20260711)
```

**A real defect was caught and fixed during preparation, disclosed rather than silently corrected:** the script's first draft computed the roster SHA-256 via comma-joined ticker text, reproducing `5f2afa70…` — matching a *different*, uncorrected hash a prior session-turn had produced via the same wrong method, and **mismatching** the roster hash actually sealed in `HYP-PM-0003_REGISTERED.md` (`7d4eb1004e7d1e83153eede9a5d4e458ab5298ac1a4a4d7fa301f095f665eee0`, which was computed via newline-joined text with a trailing newline — the original R-3 receipt's method, matching a `sqlite3 ... > file.txt` CLI redirect). The script was corrected to reproduce the newline-joined method, which now matches the sealed value exactly. **This was a hashing-method inconsistency across prior turns, not a data change** — the underlying dataset fingerprint (`329b22e49f0ef882…`) matched on the very first run, confirming Dataset A itself never drifted.

**Immutability:** this manifest is frozen once committed; sealed alongside the script (`b32fde97…`) and the registration record (`a2db9204…`). Any re-run with a changed parameter is a **new experiment**, never an edit. **Not yet committed** (see Code commit hash above).

**Lineage:** [[HYP-PM-0003_REGISTERED]] · [[HYP-PM-0003_DRAFT]] · [[HYP-PM-0003_POWER]] · [[HYPOTHESIS_REGISTRY]] · Dataset A: `BROKER_FLOW_DATASET_A_EMPIRICAL_READY_HANDOFF_2026-09-09.md`, `BROKER_FLOW_DATASET_A_FINGERPRINTED_GATE_2026-09-09.md`.
