# HANDOVER — idx-walkforward (5001) → VS Code on Windows

**Date:** 2026-10-01 (WIB) · **Owner:** Tjie · **Repo:** `github.com/Tjie-hub/5001`
**Purpose:** everything a fresh session (human or agent) needs to continue without re-deriving state.
Facts marked **[verified]** were seen in command output or files this session; **[unverified]** were
reported by an agent or inferred. Do not treat [unverified] as ground truth.

---

## 1. Where the code lives (three copies, they do NOT sync)

| Copy | Path | Role | Notes |
|---|---|---|---|
| Production | XPS-13 Ubuntu `/home/tjiesar/10 Projects/idx-walkforward-5001` | Live service, port 5001, systemd, cron | **Do not edit/switch branches here.** `walkforward.db` ≈ 14.4 GB [verified]. Gunicorn must stay 1 worker. |
| Windows mirror | `D:\IDX` (= `/mnt/d/IDX` in WSL) | Dev + research | Git has `core.autocrlf=true`; ~1,677 files show `M` from CRLF/file-mode noise only (0 real diff) [verified]. Do not `git add -A` / `checkout .` blindly. |
| GitHub | `Tjie-hub/5001` | Source of truth for commits | WSL has no git credentials → **push from Windows** (`cd /d D:\IDX` — the `/d` is required in CMD). |

Databases are gitignored and not synced between machines. `data/research.db` exists on both, with different contents (see §4).

## 2. Open in VS Code (Windows)

- Workspace file in repo: `idx-walkforward-5001.code-workspace`.
- Recommended: **VS Code → Remote-WSL** window on a WSL-native clone (e.g. `~/IDX`) — SQLite on `/mnt/d` is slow/lock-prone.
  Quick option: open `D:\IDX` directly, but run tests from a WSL terminal.
- Python: WSL `venv/` is **Python 3.12.13** [verified] (CI uses 3.12; system Python is 3.14.4 — don't use it). Windows-native has an untracked `.winvenv/` (breaks `test_secret_hygiene`) and gives a much noisier test tally.
- Before running anything: read `CLAUDE.md` (frozen operating manual) and `TODO.md`.

## 3. Branch map

| Branch | Where | State |
|---|---|---|
| `ops/hardening-2026-07-10` | origin + WSL, tip `8fe7659` | Integration base for fixes |
| `fix/p3-execution-model-mismatch` | **pushed**, tip `db585d8` | P3-2 implemented + verified; NOT merged, NOT deployed |
| `research/new-order-2026-09-30` | WSL `17ec02e`; origin `db3b61a` (11 ahead, mostly P-M docs); XPS-13 has own unpushed `f6d5477` | **Diverged three ways** — reconcile before merging |
| `fix/p0-p1-ground-truth` | WSL, commit `0973074` | P0/P1 closure docs (local Tier-1 cutover, P2 superseded, P5 closed) |
| `spec/external-strategy-intake` | XPS-13 only, `022cfe3` | Contains `BLOCKED_NO_SOURCE.md`; not pushed |

Reconciliation plan (not yet done): keep WSL/Windows closure (`0973074`) as canonical for `TODO.md`; cherry-pick only the unique XPS-13 bits (`.gitignore` entries for FUSE artifacts + `data/ajaib_raw/`, cross-box note). Expect a `TODO.md` conflict.

## 4. Work status (P0–P5 from TODO.md)

- **P0 ground truth — done.** XPS-13: 3,450 passed / 3 skipped / 0 failed [verified by agent log, suite finished before final `.gitignore`/TODO edits]. WSL: 8F/3451P/3S (see §6).
- **P1 research-DB fence — done in practice.** Production `research.db`: 95 runs, 6 gate decisions, 48 evidence, 1 hypothesis (`BROKER-001`), 3 failure_registry entries; `walkforward.db` no longer holds the 8 tables [verified]. **Canonical ledger = XPS-13 `research.db`.** WSL's copy (25/5/40) is a stale fork from a July snapshot — **never run gatekeeper/research cron there**; to refresh, copy the ~106 KB XPS file. `TODO.md` P1 boxes are still unchecked on XPS-13 (stale).
- **P2 NR7:** gatekeeper evidence already persisted; failure_registry says NR7 "falsified as a strategy-level edge". Draft **D-066** (retire `NR7_BULL` to SHADOW) is on origin (`c1177aa`). **P2-3 is an Owner decision.**
- **P3 execution-model mismatch:** option (a) implemented — live fills stage to the next session's open; 9/9 staging tests pass; mutation check proved the regression test fails on the old behavior [verified]. Also fixed `stage_entry()` dropping its `note` arg. **Not deployed. P3-3 (reset forward-test clock) is an Owner decision** — do it at deploy time.
- **P4 evidence honesty:** not started. Worth doing only P4-1 (as-of-date ADV), P4-2 (ARA/ARB fillability), P4-6 (liquidity-scaled slippage) — they change numbers. Brief: `ZCODE_BRIEF_P4_EVIDENCE_HONESTY_2026-09-30.md`.
- **External strategy (YouTube/NotebookLM) intake:** blocked — no source material anywhere. Needs transcript / NotebookLM export / Owner's written rules in `docs/research_intake/external_strategy_2026-10/SOURCE/`. It enters as a hypothesis → gatekeeper, **never** cloned into `engine/`.

## 5. Open questions / unverified (close these before merge or deploy)

1. **Windows tally 26F/3180P** (handoff `b1d96d4`) — claimed environmental, list of 26 failures not seen. [unverified]
2. **8 WSL failures** (6× `test_config_validation`, 1× `test_provider_hierarchy`, 1× `test_secret_hygiene`) explained as `.env` mode-777 on drvfs + `.winvenv/`; claim "passes in CI without `.env`" not reproduced. Re-run in a clean clone without `.env`. [unverified]
3. Does `stage_entry()`/`resolve_staged_entries()` add a **table/column to `walkforward.db`**? Brief forbids DB schema changes — if yes, needs Owner approval.
4. Did the full suite touch **live tokens** (Telegram/Z.ai) because production `.env` sits in the Windows mirror? Does `.env` need to be there at all?
5. **Mimosa** returned `inconclusive` on every recent commit (`ETIMEDOUT`, file-budget overflow, `scanner_enobufs`) — infra errors, zero findings, but no commit has passed a full scan. Fix the scanner; don't normalize it. Check `.mimosa/history/run-*.json` `errors` before assuming a block.
6. P3 live behavior never observed: first-bar fills on illiquid tickers, ARA/ARB at open, session breaks, holidays, overnight entry delay. Prefer a shadow period before relying on staged fills.
7. Known deferred: `monitor.py::_get_current_price` reads latest close without `is_final` (stop-loss timing) — separate risk-profile decision.
8. P1-2 zero-orphan proof is weak: no pre-migration backup exists; only checked against the 22 Jul backup (0 missing). Nightly backup retention vs a 14 GB DB — check `df -h` / `du -sh ~/backups` on XPS-13.
9. Owner decisions pending on untracked dirs: `atr_plan/` (recommend commit) and `Claude outputs/` (commit `.md`, drop scratch `.py`/`.pine`).

## 6. Deploy rules (production = XPS-13)

- Only after §5 items 1–4 are answered and Owner approves.
- Only **after 15:30 WIB** (IDX hours 09:00–15:30 Mon–Fri); avoid the 08:40 WIB Stockbit token cron.
- Production is run by `systemctl --user ... idx-walkforward`; after pull, restart the service and confirm the new scheduler job is registered.
- Then reset the forward-test clock (P3-3) so forward N counts post-fix fills only.

## 7. Guardrails (from CLAUDE.md — enforced by CI tests)

- Never `sqlite3.connect()` outside `data/db.py`; production never imports `research.*` and vice versa; production never writes research-owned tables.
- Never edit existing entries in `DECISION_LOG.md`, `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`; never touch `docs/research_programs/P-M/**` or any `ledger.json` or in-flight protocol.
- New routes must be classified in `security/route_policy.py`. Secrets only in `.env` / `.stockbit_token` (mode 600), read via `config.py`.
- Commits: Conventional Commits, `type(scope): description`. Re-runs of any study must report **before/after numbers**.

## 8. Candid note on direction

Pipeline outcomes so far: NR7 falsified, EXP-PA-0001 refuted, exclusion-portfolio screen FAIL at modeled cost, BRPT/pattern playbooks "no reliable edge". P0/P1/P3/P4 make evidence trustworthy; they do not find edge. Don't add more governance before there is a candidate worth testing — the external-strategy source is the cheapest unblock.

## 9. Tooling

- ZCode (Windows app) → Remote Connection → WSL `Ubuntu`, user `tjies`. Agent runs in WSL; **the Windows PC must stay on** (no sleep, app in tray, WSL alive). Remote Control from phone also needs the desktop online.
- Briefs live at repo root: `ZCODE_BRIEF_P0_P1_...`, `ZCODE_BRIEF_P3_...`, `ZCODE_BRIEF_P4_...`, `ZCODE_BRIEF_EXTERNAL_STRATEGY_INTAKE_2026-10-01.md` (the last was authored in the planning session and may exist only under `Claude outputs/`).

## 10. Immediate next steps

1. `cd /d D:\IDX` → confirm `fix/p3-execution-model-mismatch` at `db585d8` (already pushed).
2. Ask the WSL agent to answer §5 items 1–4 (prompt in the P4 hand-off).
3. Then P4-1/2/6 on a new branch from `fix/p3-execution-model-mismatch`, reporting before/after numbers.
4. Owner: decide P2-3 (D-066), P3-3 timing, and the two untracked dirs; supply the strategy source.
