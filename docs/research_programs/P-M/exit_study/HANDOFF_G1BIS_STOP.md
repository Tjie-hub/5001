# HANDOFF_G1BIS — STOPPED at the parity gate (2026-10-07). No verdict written.

**Authority:** brief `ZCODE_BRIEF_EXIT_STUDY_G1BIS_PORTFOLIO_2026-10-07.md`; the run's own gate
(`g1bis_run.py`): "Any mismatch beyond 1e-9 → STOP and report; do not write a verdict."
**Outcome: the G1-bis run EXECUTED ONCE, PASSED its freeze/fingerprint/population gates, FAILED
the parity gate, and stopped before any portfolio number or verdict was produced.**
No `RESULT_G1BIS_*.json` exists; `VERDICT.md` and `PRACTICE_NOTE.md` are untouched.

## 1. What passed before the stop

- Frozen-trio sidecar and PORTFOLIO_FIX mini-freeze sidecar: verified before the run.
- Dataset fingerprint at run time: **`f42275e34cb4525d…` = G1's exact fingerprint, zero drift**
  (panel pinned to 2026-10-06 as specified).
- Populations re-derived: **E-SN 3,682 / E-RND 3,682 / E-BRK 5,141 — exactly G1's counts.**
- Exit parity: exit day and reason matched on all **150,060** trade × arm pairs.

## 2. The parity failure and its root cause

Parity: net % differences on **132 trades, all and only arm P4** — E_SN 33/3,682 (max Δ 0.703),
E_RND 29/3,682 (max Δ 0.619), E_BRK 70/5,141 (max Δ 1.167 = the gate's max). Every other arm ×
population: zero mismatches.

**Root cause — a defect in the FROZEN `exit_study.py` `simulate_trade`, not in the G1-bis
engine.** In the frozen day-loop's bottom-of-loop P4 top-up fill block (exit_study.py lines
553–558), the fill is recorded in the `topup` dict but **`buy()` is never called** — the top-up
purchase leg is not booked. The subsequent top-up sale (in-day or at exit, lines 521–525 /
566–568) then books proceeds for units that were never bought: **phantom proceeds, one-sided**
(frozen `net_pct` ≥ true `net_pct` on every affected trade). The block fires when the top-up
limit is touched on the arming day itself; the in-step fill path (lines 514–520, which does book
the buy) requires a later day. `portfolio_v2.simulate_legs` transcribed the rules faithfully and
books the buy (portfolio_v2.py line 144) — the divergence is the frozen bug surfacing, which is
precisely what the parity gate exists to catch.

Demonstrated on APIC s=5085 (E_SN, 2020-06): frozen legs = entry, sell 0.5 @845 (no buy), exit —
net_pct 0.4989; correct legs = entry, buy 0.5 @800, sell 0.5 @845, exit — net_pct 0.0070.

## 3. Sensitivity of G1's headline result (read-only diagnostic; no artifacts changed)

G1's verdict — "P4 swing lot RECOMMENDED" — rests on the P4-vs-P0 paired t. Recomputed with the
corrected legs (portfolio_v2 booking), same trades:

| population · era | G1 recorded t | corrected t | mean R diff (frozen → corrected) |
|---|---|---|---|
| E_SN · E1 | 4.2606 | **2.3124** | +0.047 → **+0.0069** |
| E_SN · E2 | 3.2487 | **2.3200** | +0.048 → **+0.0070** |
| E_RND · E1 | 3.2342 | **0.0406** | +0.066 → **+0.0001** |
| E_RND · E2 | 3.4592 | **1.6932** | +0.075 → **+0.0055** |

Reading: on corrected trade-level numbers the E_SN statistical leg would still clear t ≥ 2 in
both eras, but with ~7× smaller effect; and in the E_RND control population the P4 advantage
**collapses to ~zero** — the swing-lot edge G1 recorded was substantially phantom proceeds
(132 trades, 0.9% of all P4 trades, inflated by up to 117 percentage points of net % each).
The G1-bis portfolio drawdown guard — the fix this whole exercise was approved for — never ran.

## 4. State at stop (governance)

- The frozen trio is untouched: `PREDECLARATION.sha256` verifies (`sha256sum -c` OK before and
  after). The four mini-freeze files are untouched: `PORTFOLIO_FIX.sha256` verifies.
- G1's committed artifacts (`RESULT_20261006T142027Z.json`, `VERDICT.md`, `PRACTICE_NOTE.md`,
  `HANDOFF_G1.md`) are untouched, per "trade-level G1 results stand" — **but the P4 trade-level
  numbers they contain are now known to carry the phantom-proceeds defect**; superseding them is
  the owner's act, not the executor's.
- No secrets; read-only data; ~/jurnal26, registries/DECISION_LOG, production, other branches
  untouched.

## 5. Decision path (owner/planner)

1. **Fix (recommended):** a new disclosed re-freeze of the frozen trio — the one-line fix in
   `simulate_trade`'s bottom-of-loop block (book `buy(k, fpx, 0.5)` when the top-up fills
   there) — then re-derive G1's trade-level tables (12,505 sim calls, minutes) and re-issue
   VERDICT/PRACTICE_NOTE; G1-bis then re-runs its parity gate against the fixed frozen sim and
   produces the portfolio answer. The defect also touches the FROZEN PIT test file's
   `test_p4_swing_lot_topup_and_own_target` (it asserts the 4-leg outcome the in-step path
   produces — the same-day-fill path is untested there; extend it in the re-freeze).
2. **Scope-limit (not recommended):** accept the phantom as a known defect and let G1-bis
   replicate it (drop the buy in portfolio_v2's bottom block) — this would knowingly integrate
   phantom proceeds into the portfolio layer and defeat the purpose of the exercise.
3. Either way, the P4 RECOMMENDED headline should be treated as **suspended** until the
   corrected trade-level tables exist: the corrected paired-t still clears 2.0 in both E_SN
   eras, but the effect is ~7× smaller and the control population shows none of it.

*Executor stopped per the gate. — ZCode, 2026-10-07*
