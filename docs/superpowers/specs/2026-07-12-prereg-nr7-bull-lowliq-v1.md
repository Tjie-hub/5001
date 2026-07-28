# Pre-Registration — `NR7_BULL_LOWLIQ_v1`

**Status:** REGISTERED — UNCONFIRMED (forward evidence pending) · **Registered:** 2026-07-12
**Provenance (frozen):**
- `registered_at_commit`: `002dca46eff7`
- `gate_config`: v2, hash `c74e1b67a1918c54ef3271e6ebbff8f5f0a4aa38c00a7e4ea8fb491ab13c933a`
- `prereg_hash`: `6b46d7ee967b68a0f0f91aa45f0e1cee1e4e3b40579357c352ff442e3bb64c2e`
- `seed`: 20260711

This document freezes a **post-hoc discovery** as a testable hypothesis *before* any
confirmation is run. It exists to contain the specific research-integrity risk raised by
the Phase D finding: a floating "+2.29%" number that could (a) be hand-authored into the
edge registry without forward evidence (the R-10 shadow-approval door), or (b) be
"rediscovered" later with its trial count silently reset to N=1. See
[[project_phase_d_market_regime_engine]].

## 1. Origin (why this is post-hoc)

Phase D's regime engine, run over the canonical 187-ticker `liquid_universe` (1108 NR7
trades), declared a **liquidity axis** on the `BULL` cell:

| Sub-cell | n | mean net %/trade |
|---|---|---|
| `BULL ∧ LOW_LIQ` (ADV Rp 5–10bn) | 201 | **+2.29** |
| `BULL ∧ HIGH_LIQ` (ADV ≥ Rp 10bn) | 132 | **−0.47** |
| `BULL` pooled | 333 | +1.20 |

This cell is the **winner of a search** (axis-declaration over the taxonomy). It carries
**post-hoc selection bias** and is **not evidence of an edge**. It is a hypothesis only.

## 2. Hypotheses (frozen)

Let **μ** = true mean per-trade net (full round-trip costs) of `nr7_breakout` in
`C = {regime=BULL ∧ liq_tier=LOW_LIQ}` on data **not used in discovery**.
Let **SR\*** be the selection-adjusted Sharpe given a search over **N** configurations.

- **H₀ (post-hoc mirage):** μ ≤ τ **and** SR\* ≤ 0.
- **H₁ (genuine edge):** μ > τ **and** the selection-adjusted gate clears.

where **τ = +0.50 %/trade** (`promotion_bar_pct`).

## 3. Decision gate (frozen — Phase C mathematics, no post-hoc adjustment)

All four must hold. Thresholds copied from `gate_config` v2; **may not be tuned after any
evaluation** — changing any value voids this registration and starts a new `*_v2`.

| Gate | Threshold |
|---|---|
| Economic significance | bootstrap CI **lower bound** of net > **+0.50 %** |
| Deflated Sharpe (selection-adjusted) | **DSR ≥ 0.90** |
| Probabilistic Sharpe | **PSR ≥ 0.95** (benchmark SR = 0) |
| Sample adequacy | **n ≥ 100** |

**Trial count (anti-inflation — frozen):** `N_trials = 15` =
`{BULL,BEAR,SIDEWAYS} × {POOLED,HIGH_VOL,LOW_VOL,HIGH_LIQ,LOW_LIQ}`. DSR uses
`n_trials = 15` and `sr_trials_std` = std of the 15 configuration Sharpes measured on the
**discovery** block. Computing DSR with N=1 is expressly prohibited.

## 4. Confirmation design (frozen)

- **Decisive — forward test (primary).** `split_date = 2026-07-12`. Only trades with
  `entry_date > split_date`, accrued through the existing paper-trade pipe, count toward
  the verdict. Verdict issued at `n ≥ 100` (else INSUFFICIENT — never force a verdict).
  This is the only path that yields genuinely un-snooped data (the corpus is fully
  snooped; §5).
- **Advisory — nested purged/embargoed WF (non-decisive).** Re-run Phase D discovery on a
  chronological discovery block only; if `BULL∧LOW_LIQ` re-declares there, evaluate on a
  later holdout block separated by a **1-quarter embargo** (whole-window partition, no
  boundary-straddling trades). Reported as a stability probe **only** — it cannot confirm,
  because the original discovery already used the whole corpus.

**PIT invariants (must hold in any evaluation):** regime = `detect_regime(df[date≤entry]
.tail(250))`; `liq_tier` from `get_adv_value_30d(conn, ticker, entry)`; no future bar in
any tag.

## 5. Standing injunctions (the actual containment)

1. **No registry entry — not even SHADOW — may be authored for this cell off the
   retrospective numbers.** Promotion requires the forward verdict of §4 clearing §3.
   This closes the R-10 shadow-approval door *for this hypothesis specifically*.
2. **This registration is the single record of the hypothesis.** Any future work on a
   liquidity-conditioned NR7 cell must cite `NR7_BULL_LOWLIQ_v1` and inherit `N_trials=15`
   — it may not be treated as a fresh N=1 discovery.
3. Retrospective statistics reduce inflation; they do **not** erase selection. Only
   out-of-time data confirms.

## 6. Relationship to the roadmap

This is **not** a change to the frozen Research Master Plan v2 — it is an instance the plan
already anticipated: it becomes the first entry of the **Phase E** Failure/Hypothesis
Registry when built, and its forward test is the **Phase H** revalidation loop in miniature.
The finding does argue for **pulling R-10 (registry-lifecycle enforcement) ahead of Phase F**,
because Phase D widened the post-hoc surface — a *sequencing* recommendation, logged here,
not a redesign.
