# ZCODE BRIEF — Ground truth: test suite, DB fence cutover, NR7 mechanical re-check (P0 + P1 + P2-1/2-2)

**Issued:** 2026-09-30, by Claude (planner role, Owner's request) · **Branch:** `fix/p0-p1-ground-truth`
off `ops/hardening-2026-07-10` (or off `3e62547` if that's current HEAD when you start) ·
**Repo:** `D:\IDX` (WSL mirror) · **Runs alongside, not instead of:** the P3 brief
(`ZCODE_BRIEF_P3_EXECUTION_MODEL_FIX_2026-09-30.md`, branch `fix/p3-execution-model-mismatch`) —
this brief touches no file P3 touches, so there is no reason to wait for it.

**Authority:** P0/P1 are mechanical — "no research judgement required" per TODO.md's own P0 header.
P2-3 is explicitly marked **🔑 OWNER DECISION** in TODO.md — do the two mechanical sub-items
(P2-1, P2-2) and stop; do not revoke or re-affirm NR7's registry status yourself.

---

## 0. Why, in order

TODO.md's own sequencing note: *"P1 must complete before any gatekeeper run, or the append-only
evidence ledger forks silently."* Right now `data/research.db` doesn't exist and
`data/walkforward.db` still holds `research_runs`/`gate_decisions` directly — I verified this on
HEAD just before writing this brief. Do P0 first anyway (it's hours, and P1's migration script
should run against a codebase with a known-good test baseline, not an unknown one).

## 1. P0 — ground truth (do first, all WSL)

- **P0-2.** Run `python -m pytest -q 2>&1 | tee logs/pytest_full_20260930.log` and report the real
  tally. TODO.md is explicit that the existing `.pytest_cache` count is not trustworthy (cumulative
  across partial/cross-platform runs) — don't reuse it.
- **P0-3.** Resolve the 3 collection errors. `tests/test_auto_token.py` and
  `tests/test_stockbit_fetcher_ensure_valid_token.py` were reported clean as of 2026-09-22 — re-verify.
  `tests/agent_firm/test_client.py` was reported **missing from disk** as of 2026-09-22 — find out
  if it was renamed under `tests/agent_firm/` or genuinely dropped, and close the item either way
  (rename references or confirm the drop is intentional).
- **P0-4.** `git ls-files 'tests/**test_*.py' | wc -l` vs the on-disk count (283 vs 278 tracked as
  of 2026-09-22 — re-count). For each untracked test file
  (`tests/test_news_filter.py`, `tests/test_filter_exploration.py`,
  `tests/agent_firm/providers/test_quota_{hydration_edge_cases,scenarios,state_persistence}.py`):
  commit it if it's real coverage, delete it if it's scratch. State which for each, one line.
- **P0-5.** Triage the 64-file untracked pile (enumerated in TODO.md right after this item — read
  that list in the source file, it's cut off in this brief). Same rule: commit or delete, one line
  each. **Do not `git add -A`** — `backups/` (8.5GB) already bit this once (2026-09-22 incident);
  check `.gitignore` covers it before touching this item.

## 2. P1 — activate the research-DB fence (WSL local first, then flag for production)

- **P1-1.** `python scripts/migrate_r5_tier1.py` dry-run → review output → `--apply`. Migrates
  `research_runs`, `gate_decisions`, `gate_evidence`, `regime_profiles`, `regime_profile_cells`,
  `hypotheses`, `hypothesis_links`, `failure_registry` out of `walkforward.db` into `research.db`.
- **P1-2.** Verify no orphans: `scripts/db_backup.py` first (backup), then per-table row-count diff
  between old and new location must be zero.
- **P1-4 (config only, do this even though P1-3 is production-side).** Check `.env` /
  `RESEARCH_DB_PATH` so the WSL config already points at the new location post-migration — leave a
  clear note for the production (XPS-13) cutover (**P1-3**) since that's a separate, human-run
  action on the live box (stop the service first) — **do not attempt P1-3 yourself; you don't have
  XPS-13 access and DBs don't sync between the two machines.**
- **P1-5.** Don't implement the proposed second Syncthing folder for `~/backups/` yet — that's an
  infra decision, not code. Just confirm `scripts/db_backup.py`'s online-backup approach
  (`src.backup(dst, pages=4096)` + integrity check) is still what's running nightly on production
  via the systemd timer, and note in your handoff whether the WSL research copy has any documented
  refresh path today (I suspect not — that's fine, just say so).

## 3. P2 — mechanical re-check only (needs P1-2 done first)

- **P2-1.** `python -m research.gatekeeper.cli evaluate --strategy "NR7 Breakout" --report out/nr7_gate_20260930.md`
  — a *current* decision against a July one. Memory-heavy; WSL only.
- **P2-2.** Run `research/studies/phase5_tracker.py` against **production data** to check whether
  NR7's shadow-forward N has moved off zero (it read 0 as of 2026-07-04, six-plus weeks stale by
  the last TODO.md update). If you can't reach production data from WSL, say so explicitly rather
  than guessing — this may need to run on XPS-13 instead; flag it.
- **Stop here.** Write P2-1/P2-2's results into a short note and hand `P2-3` (revoke NR7 to SHADOW,
  or re-affirm APPROVED) back as an Owner decision. Do not touch `registry/edge_registry.yaml`.

## 3b. Housekeeping — P5 is actually done, TODO.md just never got told

Before you touch P5 at all: **don't.** I checked — `HYP-PA-0001` was registered 2026-07-19,
`EXP-PA-0001` executed 2026-08-19, REFUTED (F2, both pre-registered tests failed), and both
`docs/research_programs/HYPOTHESIS_REGISTRY.md:18` and `FAILURE_REGISTRY.md:13` already carry the
outcome. `FAILURE_ENTRY.md` is explicitly append-only/immutable (HL-1, R12) — touching
`EXP-PA-0001/**` to "finish" P5 would violate the no-re-run rule on an already-closed hypothesis.
**All you should do:** in `TODO.md`, check off P5-1/P5-2/P5-3 and add a one-line note pointing at
the registry entries above, so the next person doesn't make the same mistake I almost avoided only
by checking `git ls-files` before briefing it. Do not open `EXP-PA-0001/` for anything else.

## 4. Boundaries (same as the P3 brief)

WSL only for anything compute- or memory-heavy. `git pull --rebase` before pushing, never
force-push. Do not touch `docs/research_programs/P-M/**`, `DECISION_LOG.md`, any `ledger.json`, or
anything the P3 branch is mid-editing (`data/loaders.py`, `scheduler/scanner.py`,
`paper_trade.py`) — if P0/P1 work happens to need a one-line touch in one of those files, coordinate
by rebasing onto the P3 branch once it lands rather than editing it blind in parallel.

## 5. Deliverables

A real pytest tally (not a claim). A closed P0-3/P0-4/P0-5 triage with one line per item on what
happened. `data/research.db` existing with the 8 migrated tables, row-count-verified against the
old location, with `.env`/`RESEARCH_DB_PATH` updated for WSL. A current NR7 gate decision + shadow-N
check, handed to the Owner as P2-3 rather than resolved. TODO.md's P5 checkboxes closed out with a
pointer to the existing registry entries (no re-run). A handoff note flagging anything you found
that needs XPS-13 (production) access you don't have from WSL.
