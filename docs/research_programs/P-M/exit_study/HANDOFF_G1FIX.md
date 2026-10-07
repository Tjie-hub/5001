# HANDOFF_G1FIX — P4 same-day top-up deleted, G1 re-derived, G1-bis finished (2026-10-07)

**Authority:** brief `ZCODE_BRIEF_EXIT_STUDY_P4_FIX_2026-10-07.md` (owner-approved 2026-10-07;
planner review of `HANDOFF_G1BIS_STOP.md`; the proposed "book the buy in the bottom block"
fix was REJECTED — the block is arming-day look-ahead and was deleted instead). Executed on
`research/exit-study-2026-10`, worktree `~/10 Projects/idx-walkforward-exitstudy`.
**Both runs executed once each; every gate passed; VERDICT.md and PRACTICE_NOTE.md updated;
this commit is the stop.**

## 1. What changed (re-freeze, commit `006ef6a`, pushed before any run)

1. `exit_study.py::simulate_trade` — the bottom-of-loop P4 fill block (old lines 553–558)
   DELETED. Nothing else touched.
2. `portfolio_v2.py::simulate_legs` — the same block (old lines 141–146) DELETED. Nothing else
   touched. (It booked the buy, but the fill itself was look-ahead: an order placed because of
   a close and filled at a low printed before that close.)
3. `test_pit_exit_study.py` — new `test_p4_topup_never_fills_on_the_arming_day`: an arming
   day whose low already touches entry − 0.5·ATR must not fill; the fill comes on the next
   touching day; exactly one top-up buy leg and one sell leg. Existing tests unchanged.
4. `test_portfolio_v2.py` — the same case at the leg/engine level (no top-up leg on the
   arming day; `topup_buy` fill day == 75 ≠ arming day 70; exactly one buy and one sell).
   Existing tests unchanged (one earlier edit that had clipped this file's last test was
   repaired before commit; the committed diff is additions only).
5. `PREDECLARATION.md` — dated **"Amendment 2026-10-07: P4 same-day top-up fill removed
   (look-ahead + unbooked buy)"** blockquote under §6, quoting the frozen rule text
   ("top-up of 50% at entry − 0.5·ATR **(limit, from the next session)**"). Nothing else in
   the trio edited.
6. Sidecars regenerated in the original file order and verified: `PREDECLARATION.sha256`
   (trio: `2ccbd25a…e0f2d` / `6b29b92c…c2bc` / `6ec96c2e…fdadc`) and `PORTFOLIO_FIX.sha256`
   (`PORTFOLIO_FIX.md` and `g1bis_run.py` unchanged; `portfolio_v2.py` `33b6be26…730df`,
   `test_portfolio_v2.py` `3ed677c0…254d6`).
7. Test suite: **38 passed, 1 skipped** (the real-corpus parity test skips without the
   census-runbook env, as always), including both new same-day tests.

## 2. The firing-count assertion (Step 1.4)

An instrumented throwaway copy of the OLD frozen driver (git `0abe6de`; module-level fire list
+ one append inside the bottom block; hardcoded REPO_ROOT so it loads under /tmp; NOT
committed, still at `/tmp/p4_fire_count/`) was run over all P4 calls in the three populations,
re-derived exactly as G1-bis does (panel pinned ≤ 2026-10-06, same seed):

- populations: E-SN 3,682 / E-RND 3,682 / E-BRK 5,141 (exactly G1's)
- bottom-block fires: **132 total — E_SN 33, E_RND 29, E_BRK 70 — and 132/132 fired with
  `k == armed_day`** (the arming day), matching the G1-bis parity-failure trade counts
  exactly. The block had no legitimate firing path: look-ahead by construction.

## 3. Step 2 — G1FIX, the one trade-level re-derivation

`g1fix_run.py` (new orchestration runner, not frozen; committed for provenance; gated on
`EXIT_STUDY_G1_APPROVED=1`): amended-trio + mini-freeze sidecar checks OK; fingerprint
`f42275e3…` = G1's exact fingerprint, zero drift; populations exactly G1's; then the frozen
`evaluate()` on the fixed driver → **`RESULT_G1FIX_20261007T034553Z.json`** (runtime 592.9 s).

**Non-P4 bit-identity gate: PASSED — 0 mismatches.** For every non-P4 arm × population × era:
metrics, portfolio, paired-vs-baseline, by-year, plus the recommendations rows, the
E-SN-vs-E-RND rows and the P2 tail block, all canonical-JSON identical to
`RESULT_20261006T142027Z.json`. Only P4 rows changed (the P2 worst-5% question therefore
needed no re-report — its rows are unchanged, as the brief expected).

Corrected P4 vs P0 (paired t / mean R diff):

| pop · era | G1 (superseded) | corrected |
|---|---|---|
| E_SN · E1 | +4.26 / +0.12 | **+0.65 / +0.0017** |
| E_SN · E2 | +3.25 / +0.05 | **−0.13 / −0.0003** |
| E_RND · E1 | +3.23 / +0.06 | **−2.90 / −0.0065** |
| E_RND · E2 | +3.46 / +0.08 | **+0.25 / +0.0008** |
| E_BRK · E1 | +6.01 / +0.13 | +0.03 / 0.0000 |
| E_BRK · E2 | +4.92 / +0.09 | +0.76 / +0.0013 |

The stop-report's interim sensitivity (E_SN t 2.31/2.32) still contained the same-day fills —
as the brief warned — and overstated P4. **P4's statistical leg fails in every population ×
era.**

## 4. Step 3 — G1-bis, the one portfolio run (the original brief, unchanged)

`g1bis_run.py` (mini-frozen, hash unchanged `f553c276…37c4`) against the fixed driver →
**`RESULT_G1BIS_20261007T035639Z.json`** (runtime 576.5 s):

- **Parity gate PASSED:** 150,060 trade × arm pairs, **max |Δnet%| = 0.0** (≤ 1e-9 required),
  0 exit day/reason mismatches.
- **Cash/caps:** min cash across all 72 portfolios ≥ −4.4e-16 (float noise; every buy leg is
  cash-limited) — cash never negative; 20% entry / 30% add caps enforced by the min-leg
  sizing and pinned by the test suite.
- **Portfolio tables + drawdown guard:** full tables in VERDICT.md addendum. P4 deepens the
  P0 max-DD only on E_RND E1 (−73.6% vs −73.5%) and is identical to P0 elsewhere — with the
  fix, the top-up almost never fills (E-SN E1: zero top-up fills), so P4's portfolio ≈ P0's.
  E-BRK X0 busts in both eras (no stop on breakouts; mark-to-market, not negative cash) — the
  G1 ruin finding survives the real-cash model.

## 5. Final recommendation per arm (Step 2 stats + Step 3 drawdown, frozen rule)

**No arm is RECOMMENDED — in either entry population, all ten non-baseline arms are
NO_RELIABLE_DIFFERENCE. P4 is NOT recommended: the swing-lot edge G1 recorded was phantom
proceeds plus look-ahead fills. A null P4 is the answer.** The runner-internal recommendation
block inside `RESULT_G1BIS_…json` feeds G1's pre-fix t-statistics (the mini-freeze's frozen
wording) and is superseded by the combined table in VERDICT.md. Everything else G1 said stands
bit-identically: keep the structure stop for ruin control; do not adopt P2; exit arms make no
reliable difference; the E-SN-vs-E-RND entry comparisons are unchanged.

## 6. Transparency: G1FIX runner crashes before the gate

The G1FIX runner crashed twice in its own gate/comparison code BEFORE the identity gate ran
and before any artifact was written: (a) KeyError — it compared the baseline arms X0/P0, which
`recommend()` does not emit; (b) the E-SN-vs-E-RND loop had not yet been restricted to
non-P4 arms. Both were bugs in the gate code, not in the study, the data, or the frozen
artifacts; the study computation is deterministic and identical across invocations; nothing
about inputs or frozen code changed between invocations; the run is counted once and completed
on the third invocation with the gate intact. The throwaway renderer for the addendum tables
also had two cosmetic defects fixed before its one successful execution.

## 7. Governance

- Frozen trio + mini-freeze: only the two deletions and the two new tests, plus the ordered
  amendment and sidecar regeneration. Sidecars verified before each run and at this commit.
- G1 artifacts (`RESULT_20261006T142027Z.json`, G1's VERDICT/PRACTICE_NOTE/HANDOFF sections)
  untouched and retained; superseded rows are marked, not deleted.
- Read-only data throughout (PKLs + `mode=ro` DB for the fingerprint); ~/jurnal26, registries,
  DECISION_LOG, production and other branches untouched; no secrets printed; service untouched.
- **Done per the brief: commit, push, STOP.** Further work on this design would be a new,
  separately-approved exercise.

*— ZCode, 2026-10-07*
