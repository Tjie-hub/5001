# ZCode brief — exit study: fix the P4 top-up defect, re-derive P4, then finish G1-bis (2026-10-07)

**Branch:** `research/exit-study-2026-10` (tip `0abe6de`, your G1-bis stop record). Work in
`~/10 Projects/idx-walkforward-exitstudy`.
**Owner-approved 2026-10-07** ("give to zcode") after planner review of `HANDOFF_G1BIS_STOP.md`.

## Planner review of your stop

The stop was correct and the diagnosis of the missing `buy()` is confirmed. **The proposed fix
(option 1, "book the buy in the bottom block") is rejected.** Reason:

- The bottom-of-loop block (`exit_study.py` 553–558) can only ever fire on the **arming day**.
  - On any later day, the in-step path (514–520, `k > armed_day`) runs first.
  - If the in-step path fills, `entry_px` is set and the bottom block is skipped.
  - If it doesn't fill, the low didn't touch, so the bottom block doesn't fire either.
- The top-up arms on a **close** at or above entry + 1·ATR. Filling it at **the same day's low**, at or
  below entry − 0.5·ATR, means placing an order because of the close and filling it at a price
  printed before that close. **That is look-ahead.**
- The frozen rule reads "the first pullback to entry − 0.5·ATR **after** a close ≥ entry + 1·ATR",
  so the fill can come no earlier than the next session.
- **Correct fix: delete the bottom block.** It isn't missing a buy; it shouldn't exist.
  `portfolio_v2.py` 141–143 copies the same block and must be deleted too. Your sensitivity
  table (E_SN t 2.31 / 2.32) still includes these same-day fills, so it overstates P4.

## Step 1 — disclosed re-freeze, before any portfolio output is read

1. **`exit_study.py`:** delete the bottom-of-loop P4 fill block (lines 553–558 plus its comment).
   No other change.
2. **`test_pit_exit_study.py`:** add a test. A synthetic P4 trade where the arming close and a
   low ≤ the top-up price occur on the **same day** must:
   - not fill on that day
   - fill on the next day that touches the price
   - book exactly one buy leg and one sell leg for the top-up

   Keep the existing test unchanged.
3. **`portfolio_v2.py`:** the same deletion. Extend `test_portfolio_v2.py` with the same case.
4. **Assertion before the re-run:** instrument a throwaway copy of the *old* driver (not
   committed). Show that across all P4 calls in all three populations the bottom block fired
   only when `k == armed_day` (expect 132 fires, all on the arming day). Report the count in the
   handoff.
5. **Re-freeze:**
   - Add a dated "Amendment 2026-10-07: P4 same-day top-up fill removed (look-ahead + unbooked
     buy)" section to `PREDECLARATION.md`, quoting the frozen rule text that justifies it.
   - Regenerate `PREDECLARATION.sha256` (the trio) and `PORTFOLIO_FIX.sha256`.
   - The old sidecars stay in git history.
   - Commit and push **before** running anything.

## Step 2 — re-derive G1's trade level (one run)

- Rerun the G1 trade simulation with the fixed driver: same pinned panel, fingerprint
  `f42275e3…`, and the same populations (3,682 / 3,682 / 5,141).
- **Non-P4 identity gate:** every non-P4 arm × population must be **bit-identical** to G1's
  `RESULT_20261006T142027Z.json`. Any difference → STOP and report.
- Write `RESULT_G1FIX_<utc>.json` and the recomputed recommendation table. The rule is the frozen
  one: paired t ≥ 2 in both eras plus the drawdown leg. The drawdown leg is still pending; that's
  Step 3.
- Also report the P2 worst-5% question again only if P2 rows changed. They should not.

## Step 3 — G1-bis single run (the original brief, unchanged otherwise)

- Rerun `g1bis_run.py` against the fixed driver.
  - Parity must now pass at 1e-9 for every arm.
  - Cash never negative; the 20% and 30% caps hold.
  - Then the portfolio tables and the drawdown guard per arm, both eras.
- **Final recommendation per arm** = the statistical leg from Step 2 plus the drawdown leg from
  Step 3.
- **State explicitly whether P4 is still recommended.** If it isn't, say so plainly. A null P4 is a
  valid answer.

## Deliverables

- **`VERDICT.md`:** append the section "P4 fix and G1-bis (2026-10-07)". In it:
  - mark G1's P4 rows and the G1 portfolio tables **superseded** (don't delete them)
  - the corrected P4 table
  - the portfolio tables
  - the final recommendation per arm
- **`PRACTICE_NOTE.md`:** one dated paragraph in plain language. Swing lot: keep / drop / no
  evidence either way.
- **`HANDOFF_G1FIX.md`:** what changed, the firing-count assertion, both gates, the results.
- Commit, push, STOP.

## Hard constraints

- No other change to the frozen trio or the mini-freeze beyond the two deletions and the new tests.
- No new arms and no parameter changes. One run each for Steps 2 and 3; any gate failure → STOP and
  report.
- Do not touch `~/jurnal26`, the registries / DECISION_LOG, production or other branches.
  Read-only data. Never print secrets.
