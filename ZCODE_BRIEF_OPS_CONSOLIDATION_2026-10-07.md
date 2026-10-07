# ZCode brief — consolidate the side branches into ops/hardening, prepare the J1–J5 crons (2026-10-07)

**Category:** Infrastructure / Governance. **Owner-requested 2026-10-07** ("write the brief").
**Target branch:** `ops/hardening-2026-07-10` (origin tip `e7ddd8c`), the deploy branch per
CLAUDE.md.

## Why

The work of the last week is spread over side branches. Production runs from the working tree at
`~/10 Projects/idx-walkforward-5001`, currently checked out on `fix/telegram-curation`. As a
result:

- **Production is missing 21 commits that are only on hardening.** These include:
  - P3-2: live paper fills staged to the next open
  - P4-1 and P4-2: ADV as-of, ARA/ARB fillability
  - P4-6: opt-in slippage
  - NR7_BULL retirement (D-066)
  - the test-suite DB quarantine
- **Hardening is missing** the Telegram curation work, the forward ledgers, the J1–J5 jobs, the
  P0/P1 ground truth, and the HYP-PM-0015 filing (D-067 / D-068).
- **The J1–J5 jobs are written** (`ops/owner-todo-jobs`) **but not installed.**
- **J4's branch guard** (`BRANCH = "ops/hardening-2026-07-10"`) skips every run while production
  sits on another branch.

## Branches and merge order

Do all of this in a **separate worktree** (`git worktree add ../idx-walkforward-consolidate
origin/ops/hardening-2026-07-10`). **Do not touch the production working tree**: no checkout, no
stash. It has uncommitted brief edits and untracked `Claude outputs/` dirs that belong to the
owner.

Merge with `--no-ff`, one merge commit each, in this order:

| # | Branch | Tip | Planner dry-run result |
|---|---|---|---|
| 1 | `fix/p0-p1-ground-truth` | `0973074` | clean |
| 2 | `ops/owner-todo-jobs` | `18f6833` | clean |
| 3 | `fix/telegram-curation` | `1a8d6df` | **conflicts:** `scheduler/scanner.py`, `DECISION_LOG.md`, 5 add/add docs |
| 4 | `research/ml-rank-2026-10` | `b6c3545` | after #3 should only add `ml_rank/` and the registries and D-067 / D-068; verify |
| 5 | `research/exit-study-2026-10` | `0b30e49` | touches only `docs/research_programs/P-M/exit_study/` beyond #3; verify |

Not in scope: `master` (21 commits ahead of hardening; leave it), `research/broad-search-v2-zcode`,
and deleting any branch.

## Conflict resolution rules

**1. `scheduler/scanner.py`** (one hunk, around the AutoTrade block).
- Hardening (P3-2) replaced the immediate `open_trade(...)` and its "Auto Paper Trade Opened"
  message with `stage_entry(...)` plus a later `staged` summary.
- Curation changed the same lines it was replacing (`notify=False`, `event="trade.paper_opened"`).
- **Take hardening's `stage_entry` path.** It's the owner-approved execution model (PR #27).
- Then make the `staged` summary `send_telegram(...)` carry an `event=` that `utils/notify_policy.py`
  classifies. Use the tier the curation policy gives paper-trade events; read the policy, don't
  invent a new tier.
- Search the merged tree for any other `send_telegram` added on the hardening side without an
  `event=`, and classify those the same way. List them in the handoff.

**2. `docs/roadmap/DECISION_LOG.md`: append-only.** Keep every entry from both sides **verbatim**.
The merged log must contain each of these exactly once:
- D-060 to D-064
- D-066 (NR7, 1 Oct)
- D-065
- D-066 (Price-Reversal / HYP-PM-0014, 5 Oct)
- D-067 and D-068 (from #4)

Order: hardening's entries first where they conflict, then the research lineage's, each block
unchanged. No entry text is edited, renumbered or reordered internally. **Then append D-069**,
exactly this text with today's date:

> ### D-069 · Decision-number collision recorded: D-066 was assigned twice (2026-10-07)
> Two different decisions were filed as D-066 on separate branches and met at the 2026-10-07
> consolidation merge:
> (a) **2026-10-01, NR7_BULL retired from SHADOW**: ops/hardening-2026-07-10, cited by the
> CLAUDE.md invariant #10 amendment.
> (b) **2026-10-05, P-M Price-Reversal widened {R1} → {R1, R2}; HYP-PM-0014 registered;
> FWD-PM-BANK-001 opened**: research lineage.
> Both entries stay verbatim and in place. From here on they are cited as **D-066** (a) and
> **D-066-B** (b). An unqualified "D-066" in a document dated before 2026-10-07 resolves by its
> subject. D-065, D-067 and D-068 are unaffected. No decision content changes. Next free number:
> D-070.

**3. The five add/add docs** (`data_acquisition/06_…`, `07_…`, `priors/D-065_PROPOSAL_…`,
`NOTEBOOKLM_PRIORS_…`, `POWER_BENCHMARK_MEMO_…`).
- Diff the two versions. If they differ only in whitespace or metadata, take the research-lineage
  version.
- If the content differs, keep the research-lineage version as the file. Save hardening's as
  `<name>.hardening-variant.md` next to it, and list each case in the handoff.
- Don't merge prose by hand.

**4. Anything else that conflicts:** STOP and report. Don't resolve it.

## Verification (all required before pushing)

- Full `pytest -q` on the merged tree. Report pass / fail / skip counts against both parents'
  last known tallies.
- These specific files must be green:
  - `test_architecture_boundary.py`
  - `test_research_data_fence.py`
  - `test_cron_contract.py` (every `deploy/crontab` script exists)
  - `security/test_route_policy.py`
  - `test_config_validation.py`
  - the curation tests
  - `test_ops_owner_todo_jobs.py`
- Frozen research sidecars must verify unchanged in the merged tree:
  - `ml_rank/*.sha256`
  - `exit_study/PREDECLARATION.sha256`
  - `exit_study/PORTFOLIO_FIX.sha256`
- `git diff origin/fix/telegram-curation <merged>` lists only:
  - hardening-side changes
  - the J-jobs
  - the P0/P1 docs
  - the two research doc trees
  - D-069
  - the scanner resolution

  Attach it as a file list.
- Then push `ops/hardening-2026-07-10` as a fast-forward of origin. **No force.** Verify with
  `git ls-remote`.

## J1–J5 crons: prepare only, do not install

The scripts aren't in the production tree until the owner checks out hardening, so installing
now would make every job fail. In the handoff, deliver:

1. **The exact crontab block to install**, taken from `deploy/crontab` with **J2 removed**. J2 is a
   past one-shot for 2026-10-01; it would fire again on 1 Oct 2027.
2. **Telegram routing for the J-jobs.** After the merge, `send_ops` goes through
   `utils/telegram.send_telegram` and so through the curation policy, `TELEGRAM_OFF` included.
   - Give each job an `event=`.
   - **J1** (owner reminders) goes to the **digest** tier, not an immediate send.
   - **J4 and J5** failures go to the alert tier.
   - Commit this as part of the consolidation, with tests.
3. **`ops/owner_todo.json` pruning:**
   - Items dated before 2026-10-07 are done or stale. Move them to a `done` list; don't delete them.
   - Keep 23 Oct, 28 Oct and 31 Oct.
4. **J4:** no code change. The guard is correct once production runs on hardening. Confirm with
   `ledger_push_weekly.py --dry` in the merged worktree.
5. **The owner's switch procedure**, for the next 5001 restart:
   - which tracked files in the production tree have uncommitted edits that a
     `git checkout ops/hardening-2026-07-10` would hit, using `git diff --name-only` against
     the merged tip (read-only)
   - the exact commands
   - what changes in production behaviour at restart: P3-2 staged fills, NR7_BULL retired, the
     curation tiers

## Deliverables

- the merge commits plus the D-069 append, pushed to `ops/hardening-2026-07-10`
- `HANDOFF_OPS_CONSOLIDATION_2026-10-07.md` at the repo root on that branch, covering:
  - the merge log
  - each conflict and how it was resolved
  - the test tallies
  - the sidecar checks
  - the file list
  - the cron block
  - the switch procedure
- STOP.

## Hard constraints

- Don't touch the production working tree, its checkout or the running service. Don't edit the
  crontab. Don't lift `logs/TELEGRAM_OFF`.
- No force-push, no rebase of published branches, no branch deletion.
- Registries and DECISION_LOG are append-only. The only new text is D-069 as given.
- Don't edit frozen research files.
- Read-only on all databases. Never print secrets.

## Amendment 2026-10-07 (after ZCode's stop at merge 3/5)

Planner error: the dry-run merged curation straight into `e7ddd8c`, not on top of merges 1–2. A
composed replay (1→2→3→4→5, in a throwaway worktree) shows the **complete** conflict set. All of it
is in merge 3; **merges 4 and 5 are clean on top of a resolved merge 3**. Rules for the three files
not covered above:

**5. `.gitignore`: union.** Take the `ebe7c3e` (P0-5) block. It's a superset: it adds
`Claude outputs/` and `atr_plan/` to curation's `.fuse_hidden*` and `data/ajaib_raw/`. Check that
every curation pattern is present once, and don't duplicate any.

**6. `deploy/crontab`: union, both blocks verbatim.**
- The J1–J5 block (from owner-todo-jobs) goes first, then the `FWD-PM-BANK-001` recorder block
  (from curation; it's already live in the installed crontab at 09:40).
- J2 stays in the *file*. It's only left out of the install block, per the cron section.
- `test_cron_contract.py` must pass.

**7. `TODO.md` (status notes, not a governance record).** For each conflicting item (P0-2, P0-3,
P0-4, P0-5, P2-3):
- Keep the `ebe7c3e` (P0/P1 ground-truth) text.
- Mark it `[x]` if either side has it `[x]`.
- Then append curation's dated "2026-10-01 (XPS-13)" sentences **verbatim** beneath it, as an
  indented `_Also recorded on fix/telegram-curation (2026-10-01, XPS-13):_` note.
- Drop curation's superseded pre-closure prose (the "[ ]" task descriptions). Nothing else is
  rewritten.
- P0-5 closes: `atr_plan/` and `Claude outputs/` are gitignored by the P0-5 decision. They stay
  untracked on disk.

**Merge-3 tip:** use `origin/fix/telegram-curation` as pushed (it now also carries the two brief
commits `64cdd1f` and `04d412b`, docs only). Keep your merges 1–2 (`f085c21`, `ebe7c3e`); don't
redo them.

**If DECISION_LOG conflicts again at merge 4** (D-067 / D-068 next to the D-069 append), rule 2
applies: keep the entries verbatim, in number order, with D-069 last.

Rule 4 still stands: anything outside these files → STOP and report.
