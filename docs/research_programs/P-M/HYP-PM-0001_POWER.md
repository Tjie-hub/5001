# HYP-PM-0001 · Power Analysis (pre-registration)

> **Purpose:** fix the ex-ante `MDE` and confirm the test *can fail* (R2) for [[HYP-PM-0001_DRAFT|HYP-PM-0001]]. **Pre-registration preparation, not experiment execution** — uses only the panel size N and a 1-min return volatility σ. **The order-flow-imbalance → reversal effect was NOT computed** and stays sealed until the test runs post-registration under custody (R5, §7.3).

**Date:** 2026-07-17 · **Inputs:** `stockbit_flow_bars` (1-min, `price` + signed `delta`), 2025-07-07 → 2026-07-16 · **Status:** MDE computed — **statistical power is not the binding constraint; friction is** (§3).

## 1. Method (custody-clean)

- **N** = 1-min bar count in the flow panel (no effect involved): **12,728,445 bars over ~1 year**.
- **σ** = median 1-min log-return volatility across the 25 most-active tickers, from `flow_bars.price` (a volatility nuisance parameter; the imbalance→reversal relation was not touched). Measured: **σ₁ₘᵢₙ = 0.287%/min**.
- **MDE** = 2.802 · σ / √N_eff (two-sided α=0.05, power=0.80), reported across effective-N deflations for autocorrelation/clustering.

## 2. Results — per-bar MDE at 80% power

| N_eff | interpretation | per-bar MDE |
|---|---|---|
| 12,728,445 | naive raw bars | **0.023 bps** |
| 127,284 | ÷100 (autocorrelation-deflated) | 0.225 bps |
| 12,728 | ÷1,000 (heavy clustering) | 0.712 bps |

## 3. Interpretation — power is abundant; **friction is the wall**

- Even under an aggressive ÷1,000 clustering deflation, the detectable effect is **< 1 bp per bar**. Statistically, HYP-PM-0001 is **massively over-powered** — the panel is enormous.
- **The binding constraint is transaction cost, not detectability.** IDX round-trip friction (spread + fees + impact) is on the order of **tens of bps**, orders of magnitude above the sub-bp statistical MDE. A reversal can be *statistically real* and *economically worthless* — this is **F4** (destroyed by cost), the dominant failure mode here.
- **Therefore the ex-ante MDE must be economic, not statistical.** The registered threshold should be a **friction floor** — the reversal must exceed round-trip cost (net-of-cost > 0) to be an edge — taken from the versioned cost model, **not** the 0.02–0.7 bp power floor.
- **The real limits are the two already declared in the draft**, not power: **F4 friction** and the **history-maturity gate** (only ~1 year / one regime of flow data → no regime-stratified or walk-forward validation yet, DFS §5.3).

## 4. Recommended ex-ante criteria (for CRO ratification — R5)

| Parameter | Recommendation | Rationale |
|---|---|---|
| `MDE` | **≥ round-trip friction** (from the versioned cost model), **not** the statistical floor | power is abundant; the edge must clear cost (F4) |
| Horizon `k` | short (e.g. 5–30 min), fixed at registration | inventory offload is fast; longer horizons dilute |
| Inference | double-clustered (ticker × time) + bid-ask-bounce control | guard the F1 category hazard and autocorrelation |
| Validation scope | **in-sample only until history matures** | ~1 yr, one regime — regime/walk-forward deferred (gate) |

> **R2 verdict:** the test **can fail** — indeed it is *most likely* to fail at F4 (a real reversal that does not survive cost) or as permanence (M2.1/I7). Power does not threaten R2; **the friction floor does the work of making the test severe.** This closes the last statistical G1 item; **registration still needs the CRO to fix the friction-based `MDE` and `k` ex ante (R5), and the history-maturity gate keeps validation in-sample until the flow history lengthens.**

## 5. What this does and does not do
- ✅ Computes N, σ, statistical MDE; identifies the true binding constraint (friction).
- ❌ Does **not** register, run the test, or compute any imbalance/reversal effect.
- **Next:** CRO ratifies a **friction-anchored** `MDE` + `k` → `DRAFT → REGISTERED` → sealed in-sample test under custody, with regime validation deferred to the maturity gate.

**Lineage:** [[HYP-PM-0001_DRAFT]] · [[DATA_FEASIBILITY_STUDY]] §5.3 (history-maturity gate) · [[HYPOTHESIS_LIFECYCLE]] §4.1 (R2/R5) · [[ECONOMIC_MECHANISM_TAXONOMY]] §3 (F4/M2.1) · [[EVIDENCE_MODEL]] EV-9 (C2 ceiling).
