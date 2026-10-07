# HANDOFF_OPS_CONSOLIDATION — side branches merged into ops/hardening (2026-10-07)

**Authority:** `ZCODE_BRIEF_OPS_CONSOLIDATION_2026-10-07.md` + its **Amendment 2026-10-07**
(composed dry-run; rules 5–7 for `.gitignore` / `deploy/crontab` / `TODO.md`). Executed in the
worktree `~/10 Projects/idx-walkforward-consolidate` (created from `origin/ops/hardening-2026-07-10`
@ `e7ddd8c`); the production working tree was never touched (read-only checks only). **All merges
done, all gates green, hardening pushed as a fast-forward. Nothing installed; crontab, service and
`logs/TELEGRAM_OFF` untouched.**

## 0. Provenance notes (two deviations, both owner-relevant)

1. **Merge 3 used the LOCAL curation tip `3322795`, not `origin/fix/telegram-curation`.** The
   amendment says "use origin/fix/telegram-curation as pushed (it now also carries the two brief
   commits)" — but at merge time origin still pointed at `1a8d6df` (the brief and amendment commits
   `64cdd1f`, `04d412b`, `3322795` existed only locally; ls-remote verified before and after the
   fetch). I did not push the owner's branch myself; I merged the local tip, whose content is
   exactly what the amendment describes (origin + the three docs commits). The pushed hardening
   tip therefore carries those three docs commits too.
2. **The Amendment's conflict list was complete.** My 2026-10-07 stop report flagged `.gitignore`
   and `TODO.md` as the unexpected conflicts but failed to also flag `deploy/crontab`, which was
   equally conflicted in the aborted merge — the amendment adds rules for all three; rule 6's
   resolution below follows it. (Executor omission, recorded here for the audit trail.)

## 1. Merge log (one `--no-ff` merge commit each, in the brief's order)

| # | Branch (tip as merged) | Merge commit | Conflicts |
|---|---|---|---|
| 1 | `fix/p0-p1-ground-truth` @ `0973074` | `f085c21` | clean |
| 2 | `ops/owner-todo-jobs` @ `18f6833` | `ebe7c3e` | clean |
| 3 | `fix/telegram-curation` @ local `3322795` (see §0.1) | `248abc9` | 10 files → rules 1–3, 5–7 |
| 4 | `research/ml-rank-2026-10` @ `b6c3545` | `0567052` | `DECISION_LOG.md` → rule 2 as amended |
| 5 | `research/exit-study-2026-10` @ `0b30e49` | `666161b` | clean (verified: touches only `docs/research_programs/P-M/exit_study/`, 22 files) |

Merge 3 also carries the brief's cron-section item 2 (J1–J5 telegram routing + tests) and the
`ops/owner_todo.json` pruning — folded in so the merged tree is green on the curation
classification gate it introduces (documented in the merge message). Merge 5's scope was verified:
`git diff 0567052 666161b` = `docs/research_programs/P-M/exit_study/` only.

## 2. Conflicts and resolutions

**Merge 3 (10 conflicted files):**

- **`scheduler/scanner.py` (rule 1).** Took hardening's `stage_entry(...)` / `staged.append(...)`
  path (P3-2, owner-approved execution model, PR #27); curation's `open_trade(...)` + per-trade
  "Auto Paper Trade Opened" message dropped. The staged summary `send_telegram(...)` now carries
  `event="trade.paper_staged"`, registered in `utils/notify_policy.EVENTS` at
  `(TIER_DIGEST, RULE_NONE)` — the tier the curation policy gives paper-trade events
  (`trade.paper_opened`); no new tier invented. Subject = the staged tickers.
- **Other hardening-side `send_telegram` without `event=` (rule 1, step 3).** The classification
  CI test found exactly one: `scheduler/jobs.py:1015` (P3-2 "Staged Entries Filled" notify) —
  classified as `event="trade.paper_opened"` (digest tier; a staged fill IS the paper trade
  opening at the next-session open), subject = filled tickers. List = that one call site.
- **`docs/roadmap/DECISION_LOG.md` (rule 2).** Append-only; hardening's **D-066 (NR7_BULL retired,
  1 Oct)** first, then the research lineage's **D-065** and **D-066 (Price-Reversal / HYP-PM-0014,
  5 Oct)**, every entry verbatim; then **D-069 appended exactly as given** in the brief.
  Post-merge-4 count check: D-060…D-065 ×1 each, **D-066 ×2 (the two distinct entries)**,
  D-067 ×1, D-068 ×1, D-069 ×1. No entry text edited, renumbered or reordered internally.
- **Five add/add docs (rule 3).** The curation side is the research lineage (commits `5780b07`
  "new research order package", `32aab22` "reconcile the second-run package", `c2bfe1a` "mark
  POWER_BENCHMARK_MEMO + D-065 v1 superseded → v2"). Research-lineage version kept as each file;
  hardening's version preserved as `<name>.hardening-variant.md` next to it:
  - `data_acquisition/06_PIT_FUNDAMENTALS_FEASIBILITY_2026-09-30.md` (+ variant, 63 lines)
  - `data_acquisition/07_OHLCV_PRE2021_FEASIBILITY_2026-09-30.md` (+ variant, 48 lines)
  - `priors/D-065_PROPOSAL_2026-09-30.md` (+ variant = D-065 v1, 89 lines; the kept file is the
    research lineage's superseded-by-v2 pointer)
  - `priors/NOTEBOOKLM_PRIORS_2026-09-30.md` (+ variant, 82 lines; kept file 388 lines)
  - `priors/POWER_BENCHMARK_MEMO_2026-09-30.md` — **no variant**: the hardening copy is a strict
    subset of the research version (the research side only prepended its SUPERSEDED banner), so
    taking the research version loses nothing.
  No prose was merged by hand. (Executor note: the first extraction pass created four empty
  variant files because `git add` had collapsed the conflict stages; repaired from the merge
  parent `ebe7c3e` — stage-2 content is byte-identical to it — and verified against
  `3322795`'s blobs.)
- **`.gitignore` (rule 5).** Union = the `ebe7c3e` P0-5 block, which is a superset: `Claude
  outputs/`, `atr_plan/`, `data/ajaib_raw/`, `.fuse_hidden*` — every curation pattern present
  exactly once, nothing duplicated (staged blob = `ebe7c3e`'s blob, `ea81906b…`). The file's
  historical executable bit (100755, present at `e7ddd8c` and `ebe7c3e`) was kept.
- **`deploy/crontab` (rule 6).** Union, both blocks verbatim: the J1–J5 block first (from
  owner-todo-jobs), then the `FWD-PM-BANK-001` recorder block (from curation). **J2 stays in the
  file**; it is only left out of the install block below.
- **`TODO.md` (rule 7).** For P0-2, P0-3, P0-4, P0-5: the `ebe7c3e` ground-truth text kept,
  `[x]` (hardening side), and curation's dated **"2026-10-01 (XPS-13)"** sentences appended
  verbatim beneath each as an indented `_Also recorded on fix/telegram-curation (2026-10-01,
  XPS-13):_` note; curation's superseded `[ ]` task prose dropped. **P2-3:** hardening's
  SUPERSEDED-by-D-029 text kept; curation's side carried no 2026-10-01 sentences, so nothing was
  appended. Nothing else rewritten. P0-5 closes with `atr_plan/` and `Claude outputs/` gitignored;
  they stay untracked on the production disk.

**Merge 4 (`DECISION_LOG.md` only):** exactly the conflict the Amendment anticipated (D-067/D-068
landing next to the D-069 append). Resolved by rule 2 as amended: D-067 and D-068 verbatim, in
number order, **D-069 last** (its "Next free number: D-070" remains correct).

**Anything else that conflicted:** none — merge 5 was clean.

## 3. Verification

- **Full `pytest -q`** on the merged tree (venv Python 3.12.3, `DB_PATH` pointed at a tmp file;
  the worktree has no `.env` — CI-like conditions): **3578 passed, 8 skipped, 0 failed** in
  750.4 s. Against the parents' last known tallies: curation side 3450 passed / 3 skipped
  (2026-10-01, XPS-13) and hardening side "suite 3463 pass" (D-065, 2026-10-05) — the merged tree
  is above both (it adds the J-job routing tests, the curation suite, the P3-2/P4 test files, and
  the ops routing tests). The 8 skips are the gated/guarded tests (real-corpus research parity
  tests without their runbook envs, the crontab-not-installed contract guard, etc.).
- **Required-green files, run explicitly: 139 passed, 1 skipped** (the skip = the
  crontab-not-installed guard, correct while nothing is installed):
  `tests/test_architecture_boundary.py` · `tests/test_research_data_fence.py` ·
  `tests/test_cron_contract.py` · `tests/security/test_route_policy.py` (the brief's
  `security/…` path) · `tests/test_config_validation.py` ·
  `tests/test_notify_policy_classification.py` · `tests/test_ops_owner_todo_jobs.py` ·
  plus `tests/test_notify_policy.py`, `tests/test_fetcher_policy.py`,
  `tests/test_telegram_util.py` (the curation tests).
- **Frozen research sidecars, verified in the merged tree:**
  - `ml_rank/PREDECLARATION.sha256` = `5d4dd3d81563…` = `sha256sum PREDECLARATION.md` ✓, and the
    D-067 freeze condition holds: `ml_rank_model.py` = `47752c25fcea…` ✓
  - `exit_study/PREDECLARATION.sha256` (trio) — all three OK ✓
  - `exit_study/PORTFOLIO_FIX.sha256` (mini-freeze incl. `g1bis_run.py`) — all four OK ✓
- **`git diff origin/fix/telegram-curation <merged>` = 130 files**, all inside the brief's
  allowed categories: hardening-side changes (P3-2 staging, P4 ADV/ARA/ARB/slippage, NR7 retirement
  + registry/CLAUDE.md, test-suite quarantine — `conftest.py`, `tests/conftest.py`, engine/scheduler
  changes, HANDOFF_P3/P4/RECONCILE, registries), the J-jobs (`scripts/ops/`, `ops/owner_todo.json`,
  `deploy/crontab`), the P0/P1 docs (`TODO.md`, `.gitignore`, `ZCODE_P0P1_HANDOFF…`,
  `docs/research_intake/external_strategy_2026-10/**`), the two research doc trees
  (`P-M/exit_study/**`, `P-M/ml_rank/**`, `P-M/data_acquisition/` POC files, the 4
  `.hardening-variant.md` files), D-069 (`docs/roadmap/DECISION_LOG.md`), the scanner resolution
  (`scheduler/scanner.py`, `scheduler/jobs.py`, `utils/notify_policy.py`), the amendment-sanctioned
  brief docs (`ZCODE_BRIEF_OPS_CONSOLIDATION…`, `ZCODE_BRIEF_SNIPER_FILTER…`), and the
  curation-side tracked `atr_plan/` + `Claude outputs/` files that ride in with the brief commits
  (gitignored on disk, tracked upstream — untouched per the amendment). Full list committed in the
  audit file `_consolidation_file_list.txt` next to this handoff.
- **J4 guard confirm:** `scripts/ops/ledger_push_weekly.py --dry` in the merged worktree on
  `ops/hardening-2026-07-10` → `no tracked ledger modifications — nothing to commit or push`
  (guard passes on the branch; the real ledger appends live uncommitted in the production tree and
  will be picked up only after the switch — by design, never force-pushed).
- **Push:** `ops/hardening-2026-07-10` pushed as a **fast-forward** of origin (`e7ddd8c` → the
  merged tip), no force; verified with `git ls-remote`. The stale local `ops/hardening-2026-07-10`
  ref (strictly behind origin) was fast-forwarded to the merged tip before the push so the branch
  name is coherent locally.

## 4. J1–J5 crons — the exact block to install (J2 removed)

Take from `deploy/crontab` (the file keeps J2; the install block drops it — it is a 2026-10-01
one-shot that would otherwise re-fire on 1 Oct 2027). Requires the no-space symlink
`/home/tjiesar/idx-walkforward-5001` and `scripts/cron_wrap.sh`. Install with `crontab -` after the
owner switches the production tree:

```
D=/home/tjiesar/idx-walkforward-5001
W=/home/tjiesar/idx-walkforward-5001/scripts/cron_wrap.sh

# ── Owner to-do scheduled jobs (J1–J5; installed 2026-10-XX, J2 omitted — one-shot) ──
# Box timezone is Asia/Jakarta (WIB): every time field below is WIB-local.
# J1 08:30 WIB daily — owner to-do reminders (digest tier via ops.owner_reminders)
30 8 * * * cd $D && $W owner_reminders venv/bin/python3 scripts/ops/owner_reminders.py
# J3 17:15 WIB weekdays — {FQ} month-end keystats snapshot (ops.fq_snapshot, digest)
15 17 * * 1-5 cd $D && $W fq_snapshot_monthend venv/bin/python3 scripts/ops/fq_snapshot_monthend.py
# J4 17:30 WIB Fridays — forward-ledger push, branch-guarded (ops.ledger_push, alert tier)
30 17 * * 5 cd $D && $W ledger_push_weekly venv/bin/python3 scripts/ops/ledger_push_weekly.py
# J5 17:10 WIB weekdays — ops health; Telegram only on anomaly (ops.health_daily, alert tier)
10 17 * * 1-5 cd $D && $W ops_health_daily venv/bin/python3 scripts/ops/ops_health_daily.py
```

**Telegram routing after the merge (committed with tests):** every J-job message goes
`send_ops(event=…)` → `utils.telegram.send_telegram` → the curation policy gate
(`TELEGRAM_OFF` included). Events registered: `ops.owner_reminders`, `ops.p1_3_preflight`,
`ops.fq_snapshot` = **digest tier** (J1's owner reminders ride the 17:45 evening digest, not an
immediate send); `ops.ledger_push`, `ops.health_daily` = **alert tier** (J4/J5 send only on
failure/anomaly). All keep `category="alert"` so `TELEGRAM_MUTE` can never silence them.
While `logs/TELEGRAM_OFF` exists, J1/J2/J3 items still buffer for the digest and J4/J5 immediate
sends are suppressed-and-logged — lifting the blackout resumes both. **Nothing was installed and
no crontab was touched.**

**`ops/owner_todo.json` pruning (committed):** the five pre-2026-10-07 items moved to a `done`
list (not deleted); `items` keeps exactly 23 Oct, 28 Oct, 31 Oct.

## 5. The owner's switch procedure (for the next 5001 restart)

State checked read-only in the production tree (`~/10 Projects/idx-walkforward-5001`, on
`fix/telegram-curation`, service `idx-walkforward.service` running):

> **Addendum (same day, after the push):** the production HEAD moved again during execution —
> `3322795` → `eba109b` (a docs-only commit by the owner's session, descendant of `3322795`).
> Every claim below was re-verified against `eba109b`: same five modified files, all ride along;
> the 101 tip additions still have zero collisions with the production disk. The conclusions are
> unchanged; only the HEAD hash cited above is stale.

- **Tracked files with uncommitted edits:** the five brief docs (`ZCODE_BRIEF_P0_P1…`,
  `ZCODE_BRIEF_P3…`, `ZCODE_BRIEF_P4…`, `ZCODE_NOTE_MIMOSA…`,
  `docs/research_programs/P-M/ZCODE_BRIEF_DATA_ACQUISITION_SCOPING…`). All five are **unchanged
  between the production HEAD and the merged tip**, so a checkout carries the edits along — **no
  stash, no commit needed** (verified mechanically).
- **Untracked files:** no collisions — of the 101 files the merged tip adds relative to the
  production HEAD, every one is either absent from the production disk or byte-identical
  (verified per file). The on-disk `atr_plan/` scripts and `Claude outputs/` stay untracked
  (gitignored); the brief commits also track a handful of those paths, and checkout will simply
  materialize the missing ones.
- The local branch `ops/hardening-2026-07-10` in the production repo already points at the merged
  tip (fast-forwarded by the consolidation), and origin holds the same commit after the push.

Exact commands:

```bash
cd ~/10\ Projects/idx-walkforward-5001          # production tree
git fetch origin
git checkout ops/hardening-2026-07-10           # the 5 brief edits ride along; nothing stashed
git status --short                               # expect: only the 5 brief edits (M) + untracked dirs
systemctl --user restart idx-walkforward.service
systemctl --user status idx-walkforward.service  # active, :5001 green
```

Then, and only then, install the J1–J5 block from §4 (`crontab -` with the existing crontab's
non-J entries preserved — the recorder/fetcher/watchdog lines all remain in `deploy/crontab`).

**What changes in production behaviour at restart:**

1. **P3-2 staged fills:** the 16:00 scan no longer opens paper trades at the provisional bar's
   price — signals are staged and filled at the NEXT session's open (09:10/10:10 jobs); the
   "Momentum Signals Staged" and "Staged Entries Filled" messages replace "Auto Paper Trade
   Opened", both digest-tier.
2. **NR7_BULL retired (D-066 a):** the registry entry is RETIRED — excluded from live selection
   outright, no legacy `wf_edge` fallback; `startup_summary()` reports "1 retired".
3. **Curation tiers live:** every Telegram send is classified (send / digest / log-only), the
   17:45 WIB evening digest (and 20:45 late flush) carry the tier-2 items, dedup state lives in
   `logs/notify_state.json`, and `logs/TELEGRAM_OFF` still suppresses immediate sends while it
   exists (J1/J2/J3 items buffer for the digest meanwhile). Lifting the blackout is the owner's
   separate decision.
4. J4's branch guard starts passing (production on `ops/hardening-2026-07-10`), so Friday 17:30
   pushes the week's forward-ledger appends — after the switch, expect the first real push on the
   next Friday run.

## 6. Governance

- No force-push, no rebase of published branches, no branch deletion, no edits to frozen research
  files, registries/DECISION_LOG append-only with D-069 as the only new text. `master` untouched
  (21 commits ahead — out of scope per the brief); `research/broad-search-v2-zcode` untouched.
- Read-only on all databases (the suite ran against tmp DBs); no secrets printed; `~/jurnal26`,
  the crontab, the service, and `logs/TELEGRAM_OFF` untouched. The owner's uncommitted brief edits
  and untracked `Claude outputs/` in the production tree were never staged anywhere.
- Per the brief: **STOP.**

*— ZCode, 2026-10-07*
