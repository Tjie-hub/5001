# ZCODE HANDOFF — P0/P1 ground truth (branch `fix/p0-p1-ground-truth`)

**Date:** 2026-09-30 · **Branch:** `fix/p0-p1-ground-truth` off `ops/hardening-2026-07-10` @ `8fe7659`
**Brief:** `ZCODE_BRIEF_P0_P1_GROUND_TRUTH_2026-09-30.md` · Amended mid-task by the planner's
queue change (P2 mooted — NR7_BULL already SHADOW per D-029/`4f3098f`; new priority order).

## Closed

- **P0-2** — real tally on this branch (WSL, Python 3.12.13, CI-matching venv):
  **12 failed / 3438 passed / 3 skipped in 475.72s** (`logs/pytest_full_20260930_p0p1.log`).
  All 12 pre-existing/environmental, each root-caused or reproduced on a pristine `8fe7659`
  worktree with the same `.env`: 7× config/provider tests ← the synced production `.env`
  (XPS-13 paths/keys); 4× `test_value_format` ← no `node` in WSL; 1× `test_secret_hygiene` ←
  untracked vendored packages in the tree (P0-5 class, `.winvenv/`). Zero collection errors.
  **Standing quirk:** run the suite with `DB_PATH=data/walkforward.db` exported — the synced
  `.env` points `config.py` at the XPS-13 production path (`/home/tjiesar/10 Projects/...`).
- **P0-3** — `tests/agent_firm/test_client.py` was deliberately deleted with DeepSeekClient
  (`85cab31`); ZAIProvider replacement covered under `tests/agent_firm/providers/`.
- **P0-4** — converged: 359 tracked = 359 on disk; all 5 named files now tracked (post-2026-09-22).
- **P0-5** — TODO.md's enumerated pile already tracked; remainder triaged in `d7ca641`
  (POC deliverables committed; `1}` deleted; `Claude outputs/`, `atr_plan/`, `data/ajaib_raw/`,
  `.fuse_hidden*` gitignored with reasons). Untracked count → 0. `backups/` confirmed ignored.
- **P1-1/P1-2 (LOCAL — the P1 rehearsal for the production cutover)** — backup first
  (`walkforward-20260930-113213.db.gz`, 719.7 MB, integrity=ok), then dry-run → `--apply`.
  `data/research.db` created; `research_runs` 25 / `gate_decisions` 5 / `gate_evidence` 40
  migrated with exact row-count match, then dropped from `walkforward.db`; both files pass
  `PRAGMA quick_check`. **Local-copy caveat:** only 3 of the 8 Tier-1 tables ever existed on
  this copy — the other 5 (`regime_profiles`, `regime_profile_cells`, `hypotheses`,
  `hypothesis_links`, `failure_registry`) are production-only and were no-ops here. The empty
  destination tables are NOT pre-created by the migration; `research.db`'s own schema init
  creates them on first research connect (`connect_research()`).
- **P2-1/P2-2/P2-3** — **mooted by the planner mid-task**: NR7_BULL was demoted APPROVED→SHADOW
  2026-08-19 (D-029, `4f3098f`); TODO.md P2-3 now records the supersession. Gatekeeper re-eval
  and shadow-N check deliberately not run.
- **P5-1/P5-2/P5-3** — checked off with pointers; EXP-PA-0001 outcome (FAILED, F2) already in
  both registries (`HYPOTHESIS_REGISTRY.md:18`, `FAILURE_REGISTRY.md:13`). Registries untouched
  (append-only; HL-1/R12).

## Needs XPS-13 (production) — human-run

1. **P1-3 cutover**: stop `idx-walkforward` service → run
   `python scripts/migrate_r5_tier1.py` (dry-run) → `--apply` → restart → `/health` green.
   It will move the 5 tables this local copy never had. Local rehearsal ran clean end-to-end.
2. **P1-4**: code defaults already resolve `RESEARCH_DB_PATH` → `<repo>/data/research.db` on
   both hosts (no `.env` edit needed or made — the `.env` is production's and syncs). Verify
   on XPS-13 that nothing sets a conflicting `RESEARCH_DB_PATH`/`DB_PATH` in `.env`/systemd.
3. **P1-5**: `scripts/db_backup.py` verified working as designed (online-backup API +
   integrity_check + row counts + zstd compression) — I ran it locally, same code path the
   production systemd timer runs. **The WSL research copy still has no defined refresh path**
   (confirmed — TODO.md P1-5 stays open as an infra decision). Note: run under
   `PRAGMA mmap_size=0` on WSL (below).

## Findings worth keeping

- **WSL/DrvFS + SQLite:** any read of the 3.3 GB `walkforward.db` through `/mnt/d` fails with
  `disk I/O error` unless `PRAGMA mmap_size=0` is set on the connection (Python 3.12 build has
  a nonzero default mmap). Affects ad-hoc research queries on this box; production unaffected.
- **`.git` syncs between the two machines** (Syncthing): refs can time-travel mid-operation —
  an `ops/hardening-2026-07-10` rebase landed on `0607c30` mid-flight because the remote ref
  moved backward under me. Re-check refs immediately before push; never force-push.
- **Windows git `core.filemode=true`** is the source of the exec-bit `M` noise; every fresh
  checkout on DrvFS self-dirties. Per-task `-c core.filemode=false` keeps status clean without
  touching the shared config the Linux side needs.
- A pre-existing stash (`stash@{1}`: "Post-RC1 tracked work" + a `.env.example` revert of the
  2026-09-15 provider-hierarchy flip) was left in place — looks like a Syncthing backward-sync
  artifact, not work; Owner should confirm and drop.
