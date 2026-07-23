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
