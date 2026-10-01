# HANDOFF RECONCILE — P3/P4 finish: provenance fix, branch reconciliation, D-066, merge prep · 2026-10-01

**Brief:** `ZCODE_BRIEF_RECONCILE_RATIFY_DEPLOY_2026-10-01.md` · **§5 (deploy) NOT executed — hard
STOP, awaiting explicit Owner "go".** · Author identity verified before every commit
(`user.email = sarjono.pmr@gmail.com`, repo-local). Nothing pushed from WSL (no credentials), per
the brief's push rule.

## Branch → tip → push-needed (for the Windows session)

| Branch | Local tip | Origin | Push needed |
|---|---|---|---|
| `fix/p4-evidence-honesty-on-p3` | `c3375e0` (2043332 + §1 provenance fix) | `2043332` | **yes** |
| `gov/d066-retire-nr7-bull` | `7491d6f` (new, off local `ops/hardening` `8fe7659`) | — | **yes** |
| `ops/hardening-2026-07-10` | `8fe7659` | `3ec8011` | **yes** — 4 unpushed docs commits (below) |
| `spec/external-strategy-intake` | `022cfe3` (fetched from XPS-13, unmodified) | — | **yes** |
| `fix/p3-execution-model-mismatch` | `db585d8` | `b1d96d4` | optional — fully contained in the P4 branch |
| `research/new-order-2026-09-30` | `17ec02e` | `db3b61a` | **NO — see §2 stop; pushing local would clobber nothing (it has no unique commits) but is pointless** |
| `docs/research-notes-2026-09` | (no local branch) | `976815b` | nothing to push |

Local branch `fix/p4-evidence-honesty-on-p3` was reset to origin's `2043332` before §1 (my WSL
`2f94fab` had been re-authored as `1f7d346` by the Windows session — same tree, expected).

## §1 — Provenance regression fixed (`c3375e0` on the P4 branch)

The defect was exactly as the brief states (and it originated in my own WSL `2f94fab`, carried
through the re-author): v1's approval-time `config_hash` was overwritten; the 2026-09-02 precedent
was mis-cited (it pinned a TEST CONSTANT and never touched a manifest); v1/v2 manifests disagreed.

Fixed: v1 `config_hash` restored to `8845c57b…`; the current backtest source hash (`a87badb0…`,
recomputed, not copied) is pinned as `_NR7_BACKTEST_HASH` next to `_NR7_LIVE_CHECKER_HASH` and the
backtest-pin test points at it; new guard test `test_nr7_bull_manifests_pin_the_approval_time_hash`
freezes BOTH manifests at the approval-time hash; the T7 docstring correction paragraph and a
superseded-not-deleted correction note were added to `HANDOFF_P4_2026-10-01.md`.

**Test counts (§1.4):** `tests/test_t7_execution_model_pinning.py` +
`tests/test_price_limit_fillability.py` → **17 passed**; `pytest -q -k registry` → **76 passed**.

## §2 — research/new-order three-way reconciliation: analysis complete, merge STOPPED per policy

XPS-13 reached read-only over LAN SSH via Windows interop (`ssh.exe tjiesar@192.168.31.214`,
hostname `tjiesar-XPS-13-9343` — WSL itself is NAT'd and cannot reach it directly). Fetched
`+refs/heads/*:refs/remotes/xps/*`; nothing was checked out, pulled, or committed on the XPS-13.

**Unique-commit table (built BEFORE any merge, per the brief):**

| Tip | Commits unique to it |
|---|---|
| WSL `17ec02e` | **none** — it is an ancestor of the XPS tip (it was pushed to XPS before origin's reconciliation) |
| origin `db3b61a` | 11 — the canonical P-M line (`5780b07` new-order package … `32aab22` content-reconciliation of the WSL package … `c1177aa` D-066 draft … `db3b61a` relabel) |
| XPS-13 `f6d5477` | **1** — `f6d5477` P0 ground truth 2026-10-01 (touches only `.gitignore` +5 and `TODO.md` +31) |

Merge-base of all three: `8fe7659`. The XPS tip's ancestry carries WSL's `17ec02e` P-M priors
package; the origin line carries its *evolved* versions (not patch-equivalent: `git cherry` shows
`+`, tree diff 13 files +1381/−271). Trial merge → **5 add/add conflicts, all under
`docs/research_programs/P-M/**`** (06/07 feasibility memos, D-065 proposal, NOTEBOOKLM priors,
POWER_BENCHMARK memo). Per the brief's explicit policy — *"do not resolve by hand … stop and
report"* — **the merge was aborted; the branch is untouched at `17ec02e`.**

For the Owner/planner, the mechanical resolution that preserves every unique commit would be:
merge `db3b61a` + `f6d5477` (base `8fe7659`), resolving every P-M path to the origin/canonical
side wholesale (`git checkout db3b61a -- docs/research_programs/P-M`), `.gitignore` auto-merges,
and `TODO.md` per the closure-canonical policy (`0973074` on `fix/p0-p1-ground-truth`). That is a
side selection, not hand-editing — but it is exactly the call the brief reserved, so it was not made.

**§2.4 done:** `spec/external-strategy-intake` created locally at `022cfe3`, unmodified.
**§2.5 — the 4 unpushed ops commits:** `3e62547` (P3 brief), `90e1238` (briefs bundle),
`0607c30` (P-M scoping memos), `8fe7659` (Mimosa correction) — all docs, no code, and every
subsequent branch (P3, P4, gov) builds on them. **They belong on origin**; push `ops/hardening`
first, then the rest.

## §3 — D-066 ratified: NR7_BULL v2 SHADOW → RETIRED (`7491d6f` on `gov/d066-retire-nr7-bull`)

- Proposal read and cited (`docs/research_programs/P-M/priors/D-066_PROPOSAL_NR7_RETIRE_2026-09-30.md`
  via `c1177aa`); file untouched.
- `DECISION_LOG.md`: **D-066 appended** (number was free — log ends at D-064; D-065 is claimed by
  the pending P-M data-acquisition proposal). Status DECIDED, Owner 2026-10-01, corrected numbers,
  pointers to the P4 handoff/branch. No existing entry edited.
- `registry/edge_registry.yaml`: v2 status → RETIRED + appended changelog sentence (the D-029
  shape); v1 SUPERSEDED untouched; provenance fields untouched.
- **Loader safety (the load-bearing part):** a naive flip makes `registry_governance()` return
  `None` (UNREGISTERED) — licensing the D-031 Option C legacy `wf_edge` fallback, re-exposing a
  retired strategy to live selection; D-029's own commit message documented that exact trap. So
  `load_registry()` now collects lifecycle-state records, `registry_governance()`/`admission_path()`
  return a **RETIRED** sentinel (same T7 contract as SHADOW: exclude outright, never fall back),
  `admission.py` maps it to hard non-admission, `startup_summary()` reports "1 retired".
  Verified live on the real registry: governance `'RETIRED'`, path `RETIRED`, summary
  `0 approved, 0 shadow, 1 retired, 0 skipped, 0 debt, 0 unverified`.
- `_LIFECYCLE_DEBT` `("NR7_BULL", 2)` **removed**: lifecycle states skip loading before the debt
  check, so the grandfather was unreachable dead code; removal is the allowlist's allowed shrink
  direction, and `test_lifecycle_debt_allowlist_is_empty` pins it.
- **§3.5 consumers confirmed:** D-029's production canary
  (`test_nr7_breakout_excluded_from_live_selection_after_demotion`) passes against a positive
  legacy `wf_edge` row on the real registry — nothing can admit NR7_BULL for trading. One live
  behavior change: the phase5 regime-band watch job now no-ops cleanly
  (`approved_universe()` → `None` → early return), so its "NR7-eligible now" Telegram alerts stop.
  Detection-side surfaces still fire and are recorded as directed follow-ups in D-066 §D
  (`_REGIME_STRATEGY_MAP` membership, `_DEFAULT_DISABLED`, stale "one approved edge" copy) —
  flagged for a deliberate pass, not silently changed here.
- `CLAUDE.md` NOT edited (frozen); its invariant #10 row naming NR7_BULL as the sole
  lifecycle-debt exception is **now stale** — amending it is the Owner's call.

**§3.7 full-suite tally (WSL, Python 3.12.13 venv, `DB_PATH=data/walkforward.db`,
`/tmp/pytest_gov_full.log`): 8 failed / 3442 passed / 3 skipped in 364.15s.** The 8 are the
known environmental set, item-for-item identical to the established baseline (6×
`test_config_validation` + 1× `test_provider_hierarchy` + 1× `test_secret_hygiene` — production
`.env` on the 777-mode drvfs mount + untracked `.winvenv/`; all pass without `.env`, re-verified
for §1's branch in the P4 handoff). Count sanity: the gov branch sits on the ops base (no P3/P4
code), so 3442 = ops baseline + my net-zero test rewrites; the P4 branch's 3474 minus this
branch's 3442 = 32 = P3/P4's tests that don't exist here. (An earlier full-suite run of this
branch lost its tally line to pytest tmp-garbage warning spam — the re-run above is the recorded
one.)

## §4 — Merge plan dry-runs (throwaway worktree, no real branch touched)

Cumulative order into `ops/hardening-2026-07-10` (local tip `8fe7659`):

| Step | Branch | Conflicts |
|---|---|---|
| 1 | `fix/p4-evidence-honesty-on-p3` (`c3375e0`; contains P3) | **0 — clean** |
| 2 | `docs/research-notes-2026-09` (`976815b`) | **0 — clean** |
| 3 | `gov/d066-retire-nr7-bull` (`7491d6f`) | **0 — clean** |
| 4 | reconciled `research/new-order-2026-09-30` | **not attempted** — the tip does not exist (§2 policy stop) |

Sanity on the merged tree (all three steps applied): the 52 tests of
`test_registry_lifecycle` + `test_registry_loader` + `test_t7_execution_model_pinning` +
`test_price_limit_fillability` + `test_nr7_live_pipeline_e2e` **all pass** — P4's pins and gov's
RETIRED state are coherent together. Worktree removed afterwards. *Correction, recorded for
honesty: committing the dry-run merges inside the worktree briefly advanced the real local
`ops/hardening-2026-07-10` ref (the worktree had it checked out) to the last dry-run merge; it was
reset to `8fe7659` immediately on discovery and verified — the dry-run commits are dangling
reflog entries only. No remote was ever touched.*

## §5 — Deploy checklist (PREPARED ONLY — not executed; requires explicit Owner "go")

1. Timing: Mon–Fri **after 15:30 WIB** only; not within ±15 min of the 08:40 WIB Stockbit token cron.
2. Push/merge from Windows: `ops/hardening-2026-07-10` (+4), then P4 branch, gov branch,
   `spec/external-strategy-intake`; open PRs in the §4 order into `ops/hardening`.
3. Production (XPS-13): `git pull` the merged `ops/hardening-2026-07-10`; `systemctl --user …
   idx-walkforward` restart; Gunicorn stays at 1 worker.
4. Confirm the `staged_entry_fills_0910`/`staged_entry_fills_1010` jobs are registered in the
   scheduler log.
5. Owner-approved schema addition: after the FIRST staged signal, confirm `staged_entries` exists
   in production `walkforward.db` (lazy `CREATE TABLE IF NOT EXISTS` — additive only).
6. P3-3: reset the forward-test clock at cutover so forward N counts post-fix fills only.
7. First 5 trading sessions: inspect every staged fill (first-bar fills on illiquid names, ARA/ARB
   at the open, session breaks, holidays). If any fill looks wrong: pause and report — no
   in-production patching. Rollback per the `repo-ops` skill / `docs/OPERATIONS.md`.

## Could not do, and why

- **§2 merge itself** — stopped by the brief's own P-M conflict policy (5 add/add conflicts under
  `P-M/**`); proposed mechanical resolution documented above for the policy owner.
- **§4 step 4** — depends on the §2 merge that was stopped.
- **Push** — WSL has no git credentials (by design); the Windows session pushes.
- **XPS-13 fetch from native WSL** — WSL2 is NAT'd; worked around via Windows `ssh.exe` interop
  (192.168.31.214). Worth persisting as the access path if this recurs.
