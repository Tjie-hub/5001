# G1 GOVERNANCE UNBLOCK RECORD — 2026-09-11

**Task:** Execute owner-approved governance unblock (prereg recovery attempt · freq vendor probe · NF registration + validation).
**Mode:** READ-ONLY investigation + governance record + gate updates strictly per the owner's gate rules. **No G1 execution. No methodology changes.**

---

## 1. PREREGISTRATION — NOT RECOVERED (STOP CONDITION TRIGGERED FOR G1)

- Fresh bounded recovery check (new files since 2026-09-11 08:00 across `idx-walkforward-5001/docs/**` and `ZCodeProject/**`): **no `BROKER_FLOW_PREREGISTRATION.md` or sibling appeared.**
- Standing evidence unchanged: the 2026-09-11 exhaustive retrieval (`G1_AUTHORITATIVE_PREREG_RETRIEVAL_2026-09-11.md`) established the corpus lives on the Windows/ZCode machine (`C:\Users\tjies\ZCodeProject\`), which is physically absent from this environment; D-032's scope note corroborates; `HYPOTHESIS_REGISTRY.md` has zero broker-flow-v002/H0–H3 references.
- **`prereg_confirmed` remains FALSE.** No replacement registration was created (not separately authorized). Per the stop condition, this is an **exact remaining blocker for G1 execution** regardless of the items below.

## 2. FREQ — VENDOR SEMANTIC PROBE PERFORMED (Option A); MEANING NOT ESTABLISHED → GATE STAYS CLOSED

Probe: `g1_harness/freq_probe.py` (read-only; frozen store `broker_flow_b` full population + production `stockbit_flow` + production `ticks` trade tape). Findings:

| Test | Result |
|---|---|
| T1 cross-side balance at full population (30,877 cells with both sides) | median buy/sell freq ratio **1.0031**; exact equality only **0.05%** of cells; within 1%: 2.16%; tails p01 0.38 / p99 2.37 |
| T2 magnitude vs `stockbit_flow.buy_freq+sell_freq` (30,156 matched cells) | aggregate ratio **0.0074**; per-cell stockbit/broker ratio p50 = **123.8×**, IQR ≈ 91–165 (tight, structural — not noise) |
| T3 magnitude vs `ticks` trade tape rows (5,829 matched cells, 2026-04-18+) | SUMfreq/ticks-rows p50 = **24.7**; SUMfreq > tape rows in 5,828/5,829 cells |
| T4 implied clip size \|value\|/freq/avg_price (1,518,727 rows) | p05 = **exactly 100 shares (1-lot floor)**, p50 = 2,416, p95 = 38,000; **3.94% of rows below 100 shares/freq-unit**; freq==1 rows: 12.04% |

**Interpretation (evidence only):**
- The near-1:1 cross-side balance (T1) and the exact 1-lot floor (T4) are consistent with freq being a **per-side, transaction-like count** whose minimum clip is one regular-board lot.
- Exact balance fails, and the probe **cannot distinguish orders vs fills vs vendor-netted transaction counts** — the dominant-side netting convention (register: `side` = sign of the broker's net) makes per-side matched-event identity unattainable from this data.
- The consistent **~124× discrepancy** against `stockbit_flow`'s own frequency fields is unexplained by any market quantity and means neither vendor field currently provides an external anchor for the other. The `ticks` tape (per-second rows ≤ fills) bounds freq as ≥ tape rows but cannot pin the unit.
- `lot=0` (odd-lot) treatment remains only partially characterized via the 3.94% sub-1-lot rows.

**Gate rule application:** the probe narrowed the candidate space but did **not** establish the unit to the standard the semantic register requires ("orders vs fills; side-specific; lot=0 treatment"). Therefore **`freq_semantics_ratified` remains FALSE**; C1a/C1b remain `BLOCKED_FREQ_SEMANTICS`; owner Option B (withdraw freq-dependent arms, proceed freq-free) remains available and unexercised.

## 3. NF — OWNER-REGISTERED CANDIDATE VALIDATED → GATE SET TRUE

**Registered definition (owner, verbatim construction):**
`NF_t = (aggregate_buy_value_t − aggregate_sell_value_t) / (aggregate_buy_value_t + aggregate_sell_value_t)`
- **Source:** Stockbit full-market flow data (`stockbit_flow`, production, read-only).
- **Fields:** `buy_lot`, `sell_lot` (shares) with `last_price` as the single deflator — under one price applied to both sides the owner's value ratio reduces exactly to the **share ratio** `NF = (buy_lot − sell_lot) / (buy_lot + sell_lot)`, which is the construction validated here (side-specific VWAPs are not published; the single-price reduction is recorded as an approximation).
- **Aggregation:** full observable market flow for the PIT grid (per ticker-session).
- **Timing/availability:** T+1 per the owner's definition — session-t flow is economically known at close t; the vendor file materializes T+1 morning, before the t+1 session and within every outcome window. Market-flow **control only** — never to be described as foreign/institutional/investor-class flow.
- **Zero denominator:** invalid/excluded.

**Validation results (`g1_harness/nf_validate.py`):**

| Check | Result |
|---|---|
| Coverage over frozen grid (30,880 cells) | **30,709 matched = 99.45%**; 171 uncovered cells are recent listings (ENRG/HEAL/SSIA/TAPG/PNLF/ELSA/MAPA/INDY, 8 each) |
| Zero-denominator cells | **443** (1.4%) — excluded per the owner's rule |
| Bounds | 0 cells outside [−1, +1] |
| **Non-degeneracy (the decisive check vs broker_flow)** | \|NF\|: p50 **0.175**, p90 0.410, p99 0.655; only **3.10%** of cells have \|NF\| < 0.01 — the control is genuinely informative (broker_flow NF was identically 0) |
| Both-sides volume identity `(buy_lot+sell_lot)/(2×ohlcv volume)` | p50 **0.79** (p10 0.51 / p90 1.05) — stockbit_flow approximates, but does not exactly equal, double-counted market volume. Recorded caveat, not disqualifying for a directional control |
| Content pin (drift control) | `stockbit_flow` window extract sha256 **`60f5f91c33b929cd9ff0403ec49ce3dd07545062a0560da359d61846638f98cf`** (42,912,339 bytes; 366,725 rows, 972 tickers). **Run-time requirement:** re-verify this digest immediately before the real G1 run; if it differs, the run must be halted and re-pin recorded (the table is production-live) |

**Gate rule application:** definition explicitly registered (owner) + validated (above) → **`net_flow_source_ratified = TRUE`** (set 2026-09-11, per the owner's gate rule "after the NF definition is explicitly recorded and validated"). The loader's existing provisional wiring implements exactly this construction, so no code change was needed.

## 4. OWNER AUTHORIZATION

Owner directive, this task ("ZCODE — EXECUTE OWNER-APPROVED GOVERNANCE UNBLOCK", items 1–7): recovery attempt (item 1), freq probe via captured raw data (item 2), NF candidate registration + validation (items 3, 5), gate rules (item 6), stop conditions (item 7). The NF candidate formula, source family, aggregation, timing, denominator rule, zero-denominator treatment, and interpretation restriction are quoted from that directive.

## 5. AFFECTED G1 GATES — RESULTING STATES

| Gate | State | Basis |
|---|---|---|
| `dataset_b_frozen` | **TRUE** (unchanged) | Freeze manifest v1 (2026-09-11) |
| `prereg_confirmed` | **FALSE — BLOCKING** | Original preregistration not recovered; §1 above |
| `freq_semantics_ratified` | **FALSE — BLOCKING** | Probe performed; meaning NOT established; §2 above |
| `net_flow_source_ratified` | **TRUE — SET THIS TASK** | Owner-registered definition + validation passed; §3 above |
| `synthetic` | stays `false` | per task |

## 6. EXACT REMAINING BLOCKERS FOR G1

1. **`prereg_confirmed`** — recover the authoritative preregistration (Windows/ZCode machine) or issue a separately authorized dated replacement registration. **This alone keeps G1 blocked.**
2. **`freq_semantics_ratified`** — owner must either extend the probe to a unit-establishing method (the ~124× cross-vendor inconsistency must be explained) or explicitly choose Option B (withdraw C1a/C1b, proceed freq-free with C2/C3).

`net_flow_source_ratified` is resolved. No G1 execution occurred in this task, per instruction.
