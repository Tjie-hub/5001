# EXEC-DECISIONS — Implementation Decision Log

**Owner lane:** QA (EXEC-001 §13)
**Rule:** append-only, chronological, one entry per event (EXEC-001 §8). Entries are never edited — a correction is a new entry. This log is distinct from the *trading* Decision Log (ADR §9.4), which is a runtime object.

Format per entry: `{TYPE}-{nnn} — {date} — {one-line summary}` followed by the required fields for that type (EXEC-001 §8 table).

---

## IMPL-DEC-001 — 2026-07-23 — User-space Node.js for `tests/test_value_format.py`

**Type:** Implementation decision
**Context:** EXEC-001 §15 bring-up requires the legacy test suite (1,193 tests) green locally before Phase 0 work starts. First run: 1,191 passed, 4 failed, 1 skipped. All 4 failures in `tests/test_value_format.py` (`FileNotFoundError: node`) — the test shells out to a Node.js binary that was not installed in this WSL environment. Not a code regression; pre-existing environment gap, unrelated to Production Engine v2 scope.
**Options considered:**
1. Leave failing, log as DEBT with a payoff task — but this would make QG-1 permanently red and block every future gate run for a one-line environment gap.
2. `sudo apt-get install nodejs` — blocked: sudo requires interactive authentication, unavailable in this session.
3. User-space Node.js install (no sudo, no system package changes) — fully reversible (`rm -rf ~/.local/node`).
**Choice:** Option 3. Installed Node v22.14.0 LTS to `~/.local/node` (binary tarball from nodejs.org), added to `PATH` for test runs and the pre-merge gate script (`scripts/pre_merge_gate.py`). Re-ran full suite: **1,195 passed, 1 skipped, 0 failed.**
**Reversibility:** fully reversible; `~/.local/node` is outside the repo and outside system package management. Does not touch `.venv`, does not add a project dependency (test still shells out the same way; only the environment now satisfies it).
**Consequence:** anyone running the legacy suite or the gate script on a fresh box needs `node` on `PATH`. Noted in `scripts/pre_merge_gate.py`'s preflight check (fails with a clear message + the install command above, rather than the original opaque `FileNotFoundError`) and in `docs/ops/deployment.md`.

---

## IMPL-DEC-002 — 2026-07-23 — Task card location and format

**Type:** Implementation decision
**Context:** EXEC-001 §3.1 step 1 requires a task card per task (intent, evidence list, rollback lever) but does not specify its file format or location — OPEN latitude (EXEC-001 §7: "file paths" is explicitly OPEN).
**Options considered:** a separate `docs/tasks/` tree vs. co-locating the card with the task's evidence bundle (`docs/evidence/P<phase>/<task-id>/`, already defined by §3.2).
**Choice:** co-locate. Each task gets `docs/evidence/P<phase>/<task-id>/TASK-CARD.md` (trace tag, intent, evidence checklist mirroring §3.2, rollback lever, status line). One location per task instead of two, and the evidence-presence gate check (QG-5) can walk a single directory tree.
**Reversibility:** trivial to relocate later (files, not schema); no code depends on the path yet.

---

## IMPL-DEC-003 — 2026-07-23 — Pre-merge gate script scope for Phase 0 bring-up

**Type:** Implementation decision
**Context:** EXEC-001 §15 requires "a pre-merge gate script (runs: full test suite, schema-drift check, grep-audits appropriate to phase, evidence-presence check)" as the one tooling deliverable bring-up adds. At bring-up time, no Phase 0 task has executed yet.
**Choice:** `scripts/pre_merge_gate.py` implements all four checks now, but scoped honestly to what exists:
- Full test suite: real, runs `pytest` (QG-1).
- Schema-drift check: reports `N/A — no schema module yet (Phase 1 deliverable, P1.E1.S1)`, not a silent pass, until P1.E1.S1 lands.
- Grep-audit (AN-8, unregistered jobs): reports `PENDING — implemented by P0.E1.S2.T4`, not a silent pass, until that task's grep-audit script exists at the conventional path (`scripts/audits/an8_unregistered_jobs.py`); once present, the gate wires it in and enforces it.
- Evidence-presence check: real now — walks `docs/evidence/P*/*/TASK-CARD.md`, and for any card whose `Status:` line is `done`, requires at least one evidence artifact beyond the card itself (QG-5).
**Rationale:** building the AN-8 audit logic or the schema-drift diff inside the bring-up script would be doing P0.E1.S2.T4 / P1.E1.S1 work under the "tooling" label — scope creep past EXEC-001 §15's remit (ER-2). The script's job at bring-up is to exist, run what already has a real target, and honestly flag what is pending rather than fake a green check.
**Reversibility:** script is additive; each placeholder becomes a real check when its owning task lands, no rewrite needed.

---

## IMPL-DEC-004 — 2026-07-23 — `fail_closed_alarm` as a sibling function, not a reuse of `fail_open_alarm`

**Type:** Implementation decision
**Context:** P0.E1.S1.T1 (fix VPIN gate `_db_connect` NameError, fail closed with alarm — H-8, AN-5) needs to alarm on a gate that fails closed (blocks a candidate). The existing `engine/fail_open_alarm.py` module has exactly this alerting plumbing (WARNING log + best-effort Telegram, never raises) already used at 3 other sites in `scheduler/scanner.py`, but its message format is hardcoded `"⚠️ FAIL-OPEN [{source}]: ..."`.
**Options considered:**
1. Call `fail_open_alarm()` as-is for the VPIN fail-closed case — zero new code, but the alert text would read "FAIL-OPEN" for an event that is actually a block (the opposite polarity) — misleads an operator reading the alert about what the pipeline just did.
2. Add a generic `polarity` parameter to `fail_open_alarm()` — one function, two behaviors selected by a flag.
3. Add a sibling `fail_closed_alarm()` / `format_fail_closed_alarm()` in the same module, reusing `send_telegram` and the log-at-WARNING-never-raise contract verbatim.
**Choice:** Option 3. Matches the existing module's own shape exactly (a `format_*` pure function + a side-effecting wrapper), reads correctly at the call site and in the alert text, and needs no call-site flag to get right. Rejected option 2 as needless indirection for two call sites with fixed, known polarity each — a boolean/enum parameter buys nothing here (ER-12 thinness: prefer the plainer shape).
**Reversibility:** trivial — an additive pair of functions in an existing module; no call site depends on internal reuse between them.
**Consequence:** `engine/fail_open_alarm.py` now names two polarities. If a third polarity-adjacent need appears, reconsider consolidating — not before.

---

## IMPL-DEC-005 — 2026-07-26 — Registration time for `daily_fetch_report` (P0.E1.S2.T3)

**Type:** Implementation decision
**Context:** P0.E1.S2.T3 (register-or-delete the three H-2 dead report functions) found `flow_broker_report` and `auto_trade_status_report` each name an explicit intended time in their own docstring ("Report at 17:15", "Report at 09:00") — used verbatim, no decision needed. `daily_fetch_report` names no time; its schedule slot is OPEN latitude (ADR §14: stage micro-order/schedule time is not a frozen surface).
**Options considered:**
1. Register right after the day's OHLCV fetch — but the report's `stockbit_flow`/`broker_flow` ticker counts would read as stale/zero, since those fetches (hourly to 16:05, and 20:15) haven't run yet.
2. Register immediately after `broker_flow_fetch` (20:15) — flow counts complete, but the report's OHLCV latest-date/stale-ticker figures would predate the 21:00 `ohlcv_reconciliation` pass.
3. Register at 21:05, five minutes after `ohlcv_reconciliation` (21:00) — every data source the report reads (`ohlcv`, `stockbit_flow`, `broker_flow`) has completed its day's fetch/reconciliation pass by this time.
**Choice:** Option 3 — 21:05 WIB, `mon-fri`, matching this file's existing `id`/`name` convention (`daily_fetch_report`, "Daily Fetch Report 21:05").
**Reversibility:** trivial — a `CronTrigger` literal in `scheduler/__init__.py`; changing it later is a one-line diff with no data or contract implication.

---

## DEBT-001 — 2026-07-26 — `auto_trade_status_report`'s query is not scoped to auto-trade-originated trades

**Type:** Technical debt
**What:** `auto_trade_status_report` (`scheduler/reports.py:466-512`, registered this task at 09:00 WIB — P0.E1.S2.T3) queries `SELECT ... FROM paper_trades WHERE entry_date >= yesterday` — every `paper_trades` row opened in the last day, regardless of whether `run_premover_eod`'s enforce-mode auto-trade path (`paper_trade.open_trade`, called from `scheduler/jobs.py`) or a different path (manual, agent-firm) created it. Its Telegram header reads "🤖 Auto-Trade Status", which would misrepresent non-auto-trade entries as auto-trade activity the moment another entry path is active alongside `auto_trade_from_premover`.
**Why deferred:** T3's scope is register-or-delete (H-2/AN-8), not report-content correctness. Investigation for this task found `auto_trade_from_premover` (`run_premover_eod`, 16:30 WIB) is the only path in the current codebase shown to write `paper_trades`, and the report is not duplicated by any other registered job — so its content is not wrong *today*, only imprecisely scoped for the general case. Correcting the query's scope is a content change to a report body, not a wiring decision; making it inline here would be exactly the "drive-by change — split it into a task" ER-2 / review checklist §5.1 discipline this protocol forbids.
**Payoff task:** add a `source`/provenance-style column (or equivalent join) distinguishing auto-trade-opened `paper_trades` rows from other entries, and scope this report's `WHERE` clause to it.
**Payoff task ID:** **not yet assigned.** This is a task-decomposition addition to PLAN-001's living §16/task-decomposition section (EXEC-001 §7 change control: "task addition/split within a phase's frozen scope"), which is an Arch-lane action — flagging here rather than assuming a task ID as Eng-lane. Needs a PLAN-001 task ID (Phase 1 or later; not a Gate-0 blocker, since the report's content is accurate under present conditions) before this entry can be considered closed per protocol ("debt with no payoff task is rejected at review").
**Deadline phase:** unassigned pending the above.

**Update — 2026-07-26 (appended, entry not edited per §8 rule):** Payoff task assigned — **`P0.E1.S2.T5`** (PLAN-001 §18 changelog, same date). No new schema column needed: `P0.E1.S2.T3`'s cold review found the existing `premover_auto_log` table already records which tickers/dates were auto-trade-evaluated, so `P0.E1.S2.T5` scopes via a join against it rather than the originally-proposed provenance column. Deadline phase: Phase 0 (same story as T3, T4 — not deferred to Phase 1). Entry now meets EXEC-001 §8's payoff-task requirement.

**Update — 2026-07-30 (appended, entry not edited per §8 rule): payoff implemented, pending merge.** `P0.E1.S2.T5` on branch `p0/e1-s2-t5-auto-trade-scope`: `auto_trade_status_report`'s query now requires `EXISTS (SELECT 1 FROM premover_auto_log WHERE ticker=pt.ticker AND detected_at=pt.entry_date AND mode='enforce' AND would_trade=1)` — exactly the join proposed above, against the existing table, no schema change. Verified with 3 new named tests (manual-entry exclusion, shadow-mode exclusion, would_trade=0 exclusion), each confirmed to fail against the pre-fix query before the fix, then pass after. Evidence: `docs/evidence/P0/P0.E1.S2.T5/`. **This entry closes once T5 is cold-reviewed and merged (EXEC-001 §4), not before.**

**Update — 2026-07-30 (appended, entry not edited per §8 rule): CLOSED.** T5 cold-reviewed (1 Minor doc-wording finding, fixed before merge; adversarial edge-case probing found no functional defects) and merged to `master`.

---

## DEBT-002 — 2026-07-26 — `auto_trade_status_report` mixes naive and WIB-aware `datetime.now()`

**Type:** Technical debt
**What:** `auto_trade_status_report` (`scheduler/reports.py:466-512`) computes its display timestamp with `datetime.now(WIB)` (line 470) but its `yesterday` cutoff with bare, timezone-naive `datetime.now()` (line 475) — inconsistent with every other function in the same file (`daily_fetch_report`, `flow_broker_report`, `open_trades_status_report` all use `datetime.now(WIB)` throughout for date/time reference points) and inconsistent within its own body.
**Why deferred:** Found during `P0.E1.S2.T3`'s cold review, after T3 registered this function (making a previously-dead code path live for the first time). Pre-existing code T3 did not touch (`scheduler/reports.py` had zero diff in T3) — fixing it inline would itself be the "drive-by change" ER-2 forbids. At the function's registered time (09:00 WIB = 02:00 UTC same calendar date), the inconsistency is dormant regardless of server clock, because 09:00 WIB always falls after the UTC midnight boundary relative to WIB's day — but this is incidental to the chosen hour, not a designed safeguard, and has zero test coverage.
**Payoff task:** fix the `yesterday` computation to use `datetime.now(WIB)`, matching the file's own convention.
**Payoff task ID:** **`P0.E1.S2.T5`** (PLAN-001 §18 changelog, 2026-07-26) — same payoff task as `DEBT-001`, since both are in the same function and the same follow-up task fixes both.
**Deadline phase:** Phase 0 (same story as T3, T4).

**Update — 2026-07-30 (appended, entry not edited per §8 rule): payoff implemented, pending merge.** `P0.E1.S2.T5` on branch `p0/e1-s2-t5-auto-trade-scope`: `yesterday` now computed via `datetime.now(WIB) - timedelta(days=1)` (local `timedelta` import, matching this file's own convention at lines 38/64/76), replacing the naive `datetime.now() - __import__('datetime').timedelta(days=1)`. Verified with a frozen-time regression test asserting the WIB-derived cutoff, not a naive one, gates inclusion — confirmed failing against the pre-fix code, passing after. Evidence: `docs/evidence/P0/P0.E1.S2.T5/`. **This entry closes once T5 is cold-reviewed and merged (EXEC-001 §4), not before.**

**Update — 2026-07-30 (appended, entry not edited per §8 rule): CLOSED.** T5 cold-reviewed (1 Minor doc-wording finding, fixed before merge; adversarial edge-case probing found no functional defects) and merged to `master`.

---

## DEBT-003 — 2026-07-26 — `run_vpin_backfill` is an unwired capability (new AN-8 finding)

**Type:** Technical debt (AN-8 class — same defect type as H-1/H-2, newly discovered)
**What:** `run_vpin_backfill(days=90)` (`scheduler/jobs.py:894`) — a complete, working N-day VPIN historical backfill utility, complementary to the registered daily `run_vpin_daily_batch` — is imported into `scheduler/__init__.py` but is referenced nowhere else in the entire repository: not `add_job`-ed, no route, no CLI entry point, no test. Found by `P0.E1.S2.T4`'s repository-wide grep-audit (`scripts/audits/an8_unregistered_jobs.py`), which checked all 37 names re-exported from `scheduler/__init__.py` and found exactly this one unaccounted for.
**Why deferred:** T4's scope is "audit and document," explicitly not "disposition" (its own task-card intent, mirroring T1–T3's register-or-delete pattern but for a *newly found* instance rather than one of the Audit's originally-named 6). Deciding register-vs-delete requires the same kind of investigation T1–T3 did (is it superseded? does a schedule make sense for a backfill utility, or is it meant to stay a manual/CLI tool?) — out of scope for an audit task.
**Payoff task:** decide `run_vpin_backfill`'s fate (register on a schedule, or delete, or expose via a documented manual/CLI path) using the same methodology as T1–T3; remove the corresponding `ALLOWLIST` entry in `scripts/audits/an8_unregistered_jobs.py` once dispositioned.
**Payoff task ID:** **`P0.E1.S2.T6`** (PLAN-001 §18 changelog, 2026-07-26).
**Deadline phase:** Phase 0 (same story as T1–T3/T5).

**Update — 2026-07-30 (appended, entry not edited per §8 rule): payoff implemented, pending merge.** `P0.E1.S2.T6` on branch `p0/e1-s2-t6-vpin-backfill-register`: registered `run_vpin_backfill` daily mon-fri at 18:15 WIB (15 min after `run_vpin_daily_batch`, its data source) — not superseded by anything (the daily batch only ever covers "today"; this is the only gap-healing path), idempotent (skips dates already fully scored), matching the existing daily cadence of `run_ohlcv_reconciliation`/`run_ohlcv_coverage_check`. `ALLOWLIST` entry removed from `scripts/audits/an8_unregistered_jobs.py` per its own citation's instruction. Verified with 3 new named tests plus T4's own real-repo integration test (still passing with an empty allowlist). Evidence: `docs/evidence/P0/P0.E1.S2.T6/`. **This entry closes once T6 is cold-reviewed and merged (EXEC-001 §4), not before.**

**Update — 2026-07-30 (appended, entry not edited per §8 rule): CLOSED.** T6 cold-reviewed (0 findings — isolated diff, registration correctness re-derived from source, all 3 new tests independently confirmed to fail pre-fix/pass post-fix) and merged to `master`, reconciled against T5's already-merged doc changes.

---
