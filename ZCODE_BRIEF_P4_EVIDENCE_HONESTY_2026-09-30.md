# ZCODE BRIEF — Make the evidence honest: 9 integrity fixes to the backtest/live evidence base (P4)

**Issued:** 2026-09-30, by Claude (planner role, Owner's request) · **Branch:** `fix/p4-evidence-honesty`
· **Repo:** `D:\IDX` (WSL mirror).

**Sequencing — read before starting, this is the one that can conflict:**
- **P4-3 depends on P1** (`fix/p0-p1-ground-truth`) — it's a `gate_config` version bump that only
  makes sense once `research.db` exists. Do it last, after that branch lands.
- **P4-2, P4-4, P4-5, P4-9 touch `scanner.py` / `paper_trade.py` — the same files the in-flight
  `fix/p3-execution-model-mismatch` branch is editing.** Branch this work off `fix/p3-...` once it
  merges, not off `main`/`ops/hardening-2026-07-10` directly, or you will silently reintroduce the
  bug P3 just fixed when the two get merged out of order. If P3 hasn't merged yet when you reach
  these four, do everything else in this brief first and come back.
- P4-1, P4-6, P4-7, P4-8 have no such conflict — safe to start immediately.

**Authority:** implementation + re-running affected studies. None of this touches
`docs/research_programs/P-M/**` or any registered hypothesis's frozen protocol — P4 is about the
NR7/legacy strategy evidence base, a different system from the P-M forward tests.

---

## 0. Why this exists

TODO.md's own framing: *"Each item independently undermines the 2026-07-04 approval that P2's
grandfather rests on."* These are nine separate, verified-real defects in how NR7 and its sibling
strategies were evaluated — not a hypothetical audit list.

## 1. The nine items (safe-to-start-now first)

- **P4-1.** `research/studies/nr7_generalization_study.py:77-90` — `liquid_universe()` filters the
  whole 5-year study by **today's** ADV, not per-trade-date. Fix to compute ADV as-of each trade's
  entry date; re-run the study; report how much the headline number moves.
- **P4-6.** `engine/exits/costs.py:9-11,28-31` — flat 0.10%/leg slippage with no volume scaling, on
  a mostly-illiquid roster. Add liquidity-scaled slippage (ADV-bucketed, consistent with the
  0.60% RT / D-059 modeled-cost approach already used elsewhere in this repo — check
  `docs/research_programs/P-M/` for that cost model rather than inventing a new one, but do **not**
  edit anything under that directory).
- **P4-7.** `data/fetcher.py:10-36` — static current-membership snapshot used as if it were the
  historical universe. Reconstruct membership per historical date if the data supports it; if it
  doesn't, say precisely what's missing (this may be a data-acquisition item, not a code item —
  don't force a fix that fabricates history). Also check why only 14/959 tickers are flagged
  inactive in `idx_tickers` — that's implausibly low for 5 years of IDX history; report what you
  find, fix if it's a simple query bug, flag if it's a data gap.
- **P4-8.** Fix the "AI-powered market regime detection" docstring/claim — the real mechanism is
  rule-based ADX/MA-slope with an under-gated ML overlay (see P4-4). One-line-ish fix, low risk, do
  it early to get it off the list.

## 2. Once P3 has merged (or if you're doing this after P3 ships)

- **P4-2.** Model ARB/ARA price-limit fillability in backtest + walk-forward, not just live
  (`paper_trade.py:211-228`/`:372` currently). TODO.md flags this as *"likely the single largest
  correction to OOS expectancy"* since every historical SL/TP is currently assumed fillable, which
  structurally inflates the breakout/momentum family (NR7, ORB, Inside Bar, TFB) — the strategies
  most likely to hit a limit freeze. Re-run affected backtests after the fix and report the delta.
- **P4-4.** `scanner.py:476-478` trains a fresh ML regime model per ticker per day and calls
  `.predict()` without ever checking `holdout_accuracy` / `beats_baseline`. Wire that gate in —
  don't let the model influence live signals if it can't beat a majority-class baseline.
- **P4-5.** Remove the unreachable `UNCERTAIN` branch at `scanner.py:492` (regime_filter.py:106's
  3-class refactor already folded it into `SIDEWAYS` — dead code, contradicts its own comment).
  Also delete the dead `strategy_regime_adaptive` body (`regime_filter.py:304`) — already removed
  from dispatch for whole-window look-ahead (audit C-7); only a defunct migration script still
  references it. Confirm that script is really defunct before deleting its target.
- **P4-9.** `_COUNTER_TREND_BOOK` (`scanner.py:732`: Crash Recovery, Panic Rebound) bypasses the WF
  consistency gate. This needs an explicit decision, not silent inheritance — **write up the
  question for the Owner rather than deciding it yourself** (should it keep the exemption, or lose
  it?), since removing the exemption could stop these two strategies from firing live.

## 3. Deferred (needs P1 first)

- **P4-3.** Wire V3-1 (family scoping + effective-N) into `gate_config`
  (`research/gatekeeper/stages.py:87`, `candidate.py:169-180`). DSR's trial count currently counts
  3–6 regime cells, not the ~14 strategies × tickers × optimizer grids actually searched —
  undercounted by 2–3 orders of magnitude. Already designed in `RESEARCH_MASTER_PLAN.md` §3.1
  (scope by `(dataset epoch, feature_space_hash)`, Kish-style `N_eff`) — implement what's there,
  don't redesign it. Per §3.1(c) this is a major config version bump and **non-retroactive** — say
  so explicitly in the handoff so old decisions aren't misread as having used the new count.

## 4. Boundaries

WSL only. `git pull --rebase`, never force-push. Every re-run of an existing study/backtest must
report the before/after number, not just "fixed" — these are evidence-integrity fixes, so the
delta they produce *is* the deliverable, not a side note. Don't touch anything under
`docs/research_programs/P-M/**`, `DECISION_LOG.md`, or any `ledger.json`.

## 5. Deliverables

Nine items closed or explicitly deferred with a one-line reason each. For P4-1/P4-2/P4-6: the
re-run delta on the affected study/backtest. For P4-7: either a fix or a precise data-gap
statement. For P4-9: a written question for the Owner, not a unilateral call. For P4-3: implemented
last, behind P1, with the non-retroactive note.
