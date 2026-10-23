# ZCODE BRIEF — Fix the live/backtest execution-model mismatch (P3)

**Issued:** 2026-09-30, by Claude (planner role, Owner's request, reviewed via `tjiejet` device
bridge) · **Branch:** work off `ops/hardening-2026-07-10` (current HEAD `3ec8011`), branch as
`fix/p3-execution-model-mismatch` · **Repo:** `D:\IDX` (WSL mirror) · **Scope:** this fix only —
do not touch `docs/research_programs/P-M/**`, `docs/roadmap/DECISION_LOG.md`,
`HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`, any `PROTOCOL.md`/ledger under `forward_*`, or
`data/research.db` / `data/walkforward.db` schemas. Those are a separate, governed research
program — out of bounds for this brief.

**Authority:** implementation only, per TODO.md's own recorded recommendation (see §1). You may
not decide P3-3 (resetting the forward-test clock) — that is called out below as a separate Owner
act. Mimosa gates every commit as usual.

---

## 0. Why this exists

`TODO.md` §P3 (🔴, logged 2026-08-19, still unchecked as of today) documents a real, currently
active discrepancy, not a hypothetical:

- Backtest/research strategy logic runs on **completed** bars (`is_final=1`), one-bar delayed
  (Donchian `.shift(1)`, trailing-stop lag in `engine/exits/evaluator.py`) — audited clean of
  look-ahead.
- The **live** scanner reads **still-forming** bars (`is_final=0`) by design —
  `data/loaders.py::_load_ohlcv_bulk` docstring says so explicitly: *"Live scans keep the default:
  partial bars ARE their signal input"* — and feeds that price straight into `paper_trade.py`'s
  entry insert, with no re-fetch and no delay.
- Net effect: **paper-trade P&L today is evidence for a different, never-validated execution
  model**, not for the backtested edge. This has been true since at least 2026-08-19 and is still
  true on HEAD.

I verified the docstring and the `is_final` branching still stand on HEAD (`3ec8011`), so the bug
is live, not stale. I could not re-locate the exact `paper_trade.py:439` insert-site TODO.md cites
for the *scanner's* call into it — `scheduler/scanner.py` has grown substantially since 2026-08-19
(Agent Firm gate, edge-veto stage added 2026-09-21, commit `e06e229`), so **line numbers in
TODO.md's P3 section are stale; re-locate call sites by function/symbol, not by line number.**

## 1. The one decision already made for you

TODO.md's own P3-1 already narrows this to two options and recommends one:
**(a) delay live fills to next-bar-open** to match what was actually validated (cheap, preserves
the whole existing evidence base) vs. (b) re-validate every strategy against a partial-bar model
(expensive, invalidates prior WF results).

**Ruling (planner, standing in for the Owner on this narrow point): go with (a).** It's the
recommendation TODO.md itself already reasoned through, it's reversible, and it doesn't touch the
P-M research program's evidence. If you find a concrete reason (a) is wrong once you're in the
code, stop and write it up instead of silently switching to (b).

## 2. What to do (P3-2 scope only — see §3 for what NOT to do)

1. Find every live call site that currently reads `is_final=0` / partial bars and feeds a price
   into a trading decision or a `paper_trade.py` insert. Start from
   `data/loaders.py::_load_ohlcv_bulk` (the `final_only` flag) and
   `scheduler/scanner.py` (search for `final_only=False` and everywhere the scanner is invoked —
   TODO.md said 5×/day via `scheduler/__init__.py`, re-verify that count on HEAD), then trace
   forward into `paper_trade.py`'s open-trade insert path.
2. Align the live path so an entry/exit price is only taken from a bar once it is final
   (`is_final=1`), matching the backtest's one-bar delay semantics — i.e., a live signal detected
   intraday fills at the **next completed bar's open**, not the forming bar's current price.
   Don't change anything about how signals are *detected upstream* of the fill (strategy logic,
   thresholds, filters) — this is a fill-timing fix, not a strategy change.
3. Add a regression test that pins live entry-price semantics to the backtest's (a same-day
   forming-bar price must never reach a fill; assert the fill price equals the next final bar's
   open for a synthetic fixture). Put it next to the existing `tests/test_walkforward_*` /
   `tests/test_watchlist*` tests.
4. Run the full suite in WSL (`python -m pytest -q`) and paste the tail of the result into your
   commit message or a short `P3_2_IMPLEMENTATION_NOTE.md` next to `TODO.md` — TODO.md's own P0-2
   says there's currently "no trustworthy number" for the suite, so a bare "tests pass" claim
   without the actual tally is not acceptable evidence here.
5. Do **not** touch `P3-3` (resetting the forward-test/shadow clock) — flag it as ready in your
   handoff note instead. Restarting any forward-tracking window is an Owner call because it
   affects live-running paper-trade history Tjie may already be looking at.

## 3. Boundaries

- WSL only for implementation/testing (per the repo's own execution-environment rule — the XPS-13
  is production-only and OOMs under load).
- Branch `fix/p3-execution-model-mismatch` off `3ec8011`; `git pull --rebase` before pushing; never
  force-push; commit only files this fix touches.
- Do not modify `docs/research_programs/P-M/**`, `DECISION_LOG.md`, any `ledger.json`, or
  `data/research.db` — unrelated governed research program, not in scope.
- Do not deploy to production (XPS-13) or touch `deploy/crontab` — this brief is code + tests only;
  deployment is a separate, later, deliberate act (per the repo's own standing rule).
- If the live/backtest gap turns out to be bigger than the cited call sites (e.g. other consumers
  of partial bars you find along the way), list them in the handoff rather than silently expanding
  scope to fix them all now.

## 4. Deliverables / "done" looks like

- A branch + PR/commit implementing (a): live fills wait for `is_final=1` and use the next bar's
  open, with the call sites you actually found listed explicitly (not the possibly-stale line
  numbers above).
- A new regression test proving same-day forming-bar prices can no longer reach a fill.
- The real pytest tally (pass/fail/error counts), not a claim.
- A short handoff note: what you changed, what you deliberately left alone (P3-3, and anything
  found but out of scope), and one line confirming the Owner ruling in §1 was followed or why not.

## 5. Queued next (not this brief)

`TODO.md` §P1 — the `data/research.db` Tier-1 migration (`scripts/migrate_r5_tier1.py --apply`)
is still not run: `data/walkforward.db` still holds `research_runs`/`gate_decisions` directly, and
a plain `data/research.db` connect on this machine creates an empty file with zero tables. TODO.md
calls this "blocks all research work" and warns the next gatekeeper run would silently fork the
ledger. I have not verified whether the P-M program's `research/tracking.py` writes are landing
somewhere else (e.g. a WSL-native path this Windows-side check can't see) — that ambiguity is
itself worth closing before P1 is actioned. Will brief separately once P3 ships.
