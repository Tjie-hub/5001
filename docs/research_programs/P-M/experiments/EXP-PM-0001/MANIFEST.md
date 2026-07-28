# EXP-PM-0001 — Execution Manifest (frozen)

> Immutable pre-execution manifest for the confirmatory experiment of **HYP-PM-0001**. Every field below was consistency-checked against the frozen registered record (`540c2d52…`) **before** execution — **12/12 PASS** (§Consistency). No hypothesis amendment; no parameter changed.

## Identity

| Field | Value |
|---|---|
| Registered Hypothesis ID | **HYP-PM-0001** |
| Registration timestamp | 2026-07-17T07:15:03Z |
| Registration receipt (HL-1) | [[HYP-PM-0001_REGISTERED]] §Registration receipt |
| Registration hash | `540c2d52dd8751dbda2a6b39ea7935860e12078c666a81e2156ff199ee885199` |
| Experiment ID | **EXP-PM-0001** |
| Dataset version | `stockbit_flow_bars` 2025-07-07 → 2026-07-17, **12,956,970 rows, 867 tickers**; `ohlcv` 2021-07-05→2026-07-17; `broker_flow` 2026-04-01→2026-07-17; `walkforward.db` 3,207,892,992 bytes |
| Code commit hash | `b970224738b218ccdd08cc99cc7b8fd375d39a8c` |
| Pipeline version | standalone research script `run_exp_pm_0001.py` (sha256 `8cba58b6932837abf8d28c110132fa2df98cba8b38bd6842f267224a8caa2e96`); **no gatekeeper pipeline invoked** — in-sample confirmatory test per the registered history-maturity gate |

## Experimental Specification (from the frozen record — verbatim intent)

| Field | Value |
|---|---|
| Mechanism under test | **M1.1** inventory-imbalance mean reversion (I5), tested vs **M2.1** (I7) |
| Hypothesis statement | price displacement conditional on signed OFI in a 1-min bar **partially reverts** over the following k=15 min; **signed reversal > 0** |
| Structural barrier | inventory risk-bearing (M1) |
| Friction model | **0.60% round-trip** (buy 0.25% + sell 0.35%, incl. 0.10%/leg slippage — `engine/exits/costs.py`) |
| Statistical methodology | OFI=δ/(buy+sell); signed_reversal = −sign(OFI)·rev_k; **cluster-by-day** inference (daily-mean t-test); reversal regression (rev~OFI); decile sort; **bid-ask-bounce guard** (1-bar entry gap); robustness gradient k∈{5,15,30} (consistency, not selection); friction-net evaluation |
| Inclusion criteria | bars with valid OFI (buy+sell>0), valid contemporaneous return, and a k-ahead price within the same (ticker, day) |
| Exclusion criteria | \|1-min return\| > 20% (bad prints); boundary bars (no t−1, or no t+k in day). **No liquidity/parameter filter** beyond data validity — none was registered |
| Observation window | 2025-07-07 → 2026-07-17 (full flow history; **IN-SAMPLE** per the maturity gate) |
| Outcome variables | signed_reversal_k, net-of-cost signed_reversal, OFI-decile forward-return spread |
| Refutation criteria | net-of-cost signed reversal ≤ 0 **or** < MDE (0.60%) ⇒ **M1.1 refuted** (→ M2.1 permanence / F4 friction / F1 bid-ask-bounce) |
| Expected evidence products | terminal **C2** — a provisional inventory-reversal edge **or** a competent refutation; both first-class |

## Reproducibility

| Field | Value |
|---|---|
| Input datasets | `data/walkforward.db` → `stockbit_flow_bars`, `ohlcv`, `broker_flow` (read-only) |
| Configuration | in-script constants matching the registration: `FRICTION=0.0060`, `KS=[5,15,30]`, `KPRIMARY=15`, `RET_CLIP=0.20`. No external config file; no tunable parameters |
| Software versions | python 3.12.3 · numpy 2.4.4 · pandas 3.0.2 · scipy 1.17.1 |
| Randomness policy | **N/A — fully deterministic.** No sampling, no seeds, no stochastic estimator; qcut deciles and daily aggregation are deterministic functions of the frozen inputs |
| Output artifact locations | `EXP-PM-0001/results.json` · `EXP-PM-0001/execution.log` · `EXP-PM-0001/EVIDENCE_PACKAGE.md` |

## Consistency check (pre-execution gate)

**Result: 12/12 PASS — cleared to execute.** Verified: registration seal intact; k=15; robustness gradient {5,15,30}; ofi_interval 1-min; friction 0.60%; mechanism M1.1; α=0.05; OFI=δ/(buy+sell); signed_reversal=−sign(OFI)·rev; required_data stockbit_flow_bars; null mean signed-reversal=0; net-of-cost evaluation present. Had any field mismatched the frozen record, execution would have been **STOPPED** and the mismatch reported instead.

**Immutability:** this manifest is frozen; it is sealed by git commit alongside the script (`8cba58b6`) and the registration record (`540c2d52`). Any re-run with a changed parameter is a **new experiment**, never an edit.

**Lineage:** [[HYP-PM-0001_REGISTERED]] · [[HYP-PM-0001_POWER]] · [[HYPOTHESIS_REGISTRY]] · [[EVIDENCE_PACKAGE]].
