# PROVENANCE BASELINE COMMIT — 2026-09-12

**Authority:** generated point-in-time record. Supersedes `PROVENANCE_BASELINE_COMMIT_2026-09-11.md`
**on the blocker diagnosis only** (§A) — that document's staging inventory and exclusion list remain
accurate and are not contradicted here. Per append-only discipline the 09-11 record is retained
unedited.

**Mode:** investigation + verified restoration + staged-set verification. **No commit performed.**
No C7 execution, no `c7_registered` change, no C7 methodology change, no Dataset B change, no
`research.db` write, no new hypothesis, no empirical test, no change to the staged governance patch,
and **no security check weakened, disabled, or scope-excluded.**

---

## A. WHY THE COMMIT IS BLOCKED

### A.1 Headline: the recorded blocker is a misdiagnosis. `git commit` was never blocked by Mimosa.

`PROVENANCE_BASELINE_COMMIT_2026-09-11.md` §F records the mechanism as:

> *"Mimosa L3 PreToolUse hook intercepts the `git commit` Bash command and scans the **entire session
> workspace** … It found **39 high-severity findings** …"*

**The hook log does not support this.** Measured directly against
`~/.zcode/mimosa-debug.log` (840 KB, 2026-09-02 → 2026-09-11T13:12:47Z):

| Check | Command | Result |
|---|---|---|
| Any Bash tool event reaching the scanner | `grep -c '"toolName":"Bash"'` | **0** |
| Any `git commit` string anywhere in the log | `grep -n 'git commit'` | **0 matches** |
| Distinct `toolName` values ever logged | `grep -o '"toolName":"[A-Za-z]*"' \| sort \| uniq -c` | `Edit` 1066 · `Write` 674 — **nothing else** |
| Blocking events (`pretool_blocking_finding`, `mode=deny`) | — | **every one is a `Write`/`Edit` of a `.py` file.** None is a Bash/commit event |

**`git commit` was never dispatched to the gate, never scanned, never denied.** There is no commit
denial in the record, and no "39 findings" figure appears anywhere in the log, the finding ledger, or
the Stop report.

### A.2 What actually happened (reconstructed from the log, chronologically)

1. **2026-09-10 23:00–23:03Z** — six `deny` events, `findingCount = 5`, on `Write` of
   `…/idx-walkforward-5001/docs/research_programs/P-M/g1_harness/build_freeze_candidate_manifest.py`
   and `freeze_candidate_manifest.py`. These are **inside this repository**, and they were abandoned:
   **neither file exists in the 69-file staged set** (verified §D.2). The scanner did its job on
   *new code being authored*, which is exactly its documented purpose.
2. **2026-09-11 04:59Z → 13:10Z** — the remediation loop. `deny` events, `findingCount = 1` each, on
   `Edit` of `ZCodeProject/pm_data_audit/02_index_inventory.py`, then `03_table_stats.py`. **The
   scanner was blocking the cleanup edits themselves** — each attempted remediation is a pending
   write, and is content-scanned before it lands. This is the "whack-a-mole" the 09-11 record
   describes, but its cause is the remediation activity, not a commit gate.
3. **2026-09-11 13:07:57Z** — `[bash-guard] deny direct Bash write targets=$Z/03_table_stats.py、
   $Z/04_broker_flow_deep.py、$Z/05_semantics_probe.py` — an attempt to route around the Edit
   scanner using Bash was correctly denied. (This is the **only** deny the Bash-matched git-gate hook
   ever issued, and it is a file-write guard, not a commit gate.)
4. **2026-09-11 13:12:43–47Z** — session Stop review, rooted at `project=/home/tjiesar/ZCodeProject`,
   `touched=4 bashDiscovered=7 baselineFiles=35 candidateFiles=7`. All seven scans failed with
   `scanner_failed: spawnSync /usr/bin/node ETIMEDOUT`. Final state: **`findings=0
   status=inconclusive`** (`.mimosa/reports/task-review-sess_6ec6492a….json`).

**So the terminal state is `findings=0`, produced by a scanner infrastructure timeout — not a
security detection.** And per Mimosa's own documented default (§B.4), an inconclusive/incomplete
scan does **not** deny.

### A.3 The real, structural cause

**The ZCode workspace root is not the git repository being committed.**

- ZCode workspace root: `/home/tjiesar/ZCodeProject` (`~/.zcode/v2/setting.json` →
  `recentProjects[0]`, `lastWorkspaceSession[0].workspacePath`, and every hook log line
  `project=/home/tjiesar/ZCodeProject`).
- Commit target: `/home/tjiesar/10 Projects/idx-walkforward-5001` — a **different tree, outside that
  root**, and `ZCodeProject` is not a git repository at all (`git rev-parse` → *"not a git
  repository"*).

Every Mimosa surface is anchored to the workspace root. Work performed on a repository outside that
root is scanned file-by-file as loose authored code, while the session's *project* baseline, Stop
review and finding ledger all describe the side corpus. The two never coincide. That mismatch — not
a findings verdict — is what produced the appearance of an un-clearable gate.

---

## B. EXACT MIMOSA SCOPE BEHAVIOR

**Component:** `mimosa@zcode-plugins-official` v1.0.3, installed at
`~/.zcode/cli/plugins/cache/zcode-plugins-official/mimosa/1.0.3`. **A ZCode CLI plugin — not a Claude
Code hook.**

### B.1 Registered hook surfaces (`hooks/hooks.json`, verbatim)

| Event | Matcher | Handler |
|---|---|---|
| PreToolUse | `Edit\|Write\|MultiEdit` | `scan-hook.mjs` — scans **the content of the single pending write** (`filePath`, `inputSha256`, `inputBytes`) |
| PreToolUse | `Bash` | `git-gate-hook.mjs` — "L3" command + git gate |
| PostToolUse | `Edit\|Write\|MultiEdit` | `scan-hook.mjs` |
| PostToolUse | `Bash` | `git-gate-hook.mjs` |
| UserPromptSubmit | — | `prompt-hook.mjs` |
| SessionStart | — | `session-hook.mjs` |
| Stop | — | `stop-hook.mjs` — incremental L2 review of the turn's changed files |

### B.2 Declared scan scopes (`payload/contracts/scan-profiles.json`, verbatim)

```json
"gate":  { "scope": "diff-only",       "performance": { "preToolUse": { "maxDiffLines": 500, "hardTimeoutMs": 1000 } },
           "incompleteOutcome": "partial/INCONCLUSIVE" }
"audit": { "scope": "full-repository", "incompleteOutcome": "partial/INCONCLUSIVE" }
```

**The gate profile's scope is `diff-only`, not workspace-wide.** The 09-11 record's claim that the
scanner "scans the entire session workspace" describes the `audit` profile, which runs only on
explicit `/mimosa-deep-audit`, not on a gate. The Stop review's own coverage block reports
`"scope": "hook_observed_diff"` — likewise a diff scope, rooted at the workspace project.

### B.3 Configuration surface — **no path scoping exists**

`payload/README.md` §userConfig documents the complete configuration surface. It is **environment
variables only**:

`MIMOSA_HOOK_BLOCK` · `MIMOSA_HOOK_FAILURE_MODE` / `MIMOSA_HOOK_STRICT` ·
`MIMOSA_GIT_GATE_FAILURE_MODE` · `MIMOSA_GIT_GATE_MODE` · `MIMOSA_NO_GIT_GATE` ·
`MIMOSA_HOOK_STATUS` · `MIMOSA_HOOK_PROJECT` · `MIMOSA_NO_PROMPT_GUARD` · `MIMOSA_SESSION_WELCOME` ·
`MIMOSA_PROJECT_MAXFILES` · `MIMOSA_NO_TASK_REVIEW` · `MIMOSA_TASK_REVIEW_MODE` ·
`MIMOSA_HOOK_REVIEW_MAX_ATTEMPTS` · `MIMOSA_HOOK_REVIEW_LEASE_STALE_MS` · `MIMOSA_GIT_GATE_GLM`

**There is no `exclude`, `ignore`, `scope`, `path`, `allowlist`, or per-repository setting of any
kind.** The plugin data directory (`~/.zcode/cli/plugins/data/mimosa@zcode-plugins-official/`) is
**empty** — no user config file is created or read.

Nor can scope be patched in: `payload/manifest.json` declares
`hooksEncrypted: true`, `rulesEncrypted: true`, `encryption: "AES-256-GCM"`,
`integritySignatureRequired: true`, with a per-file sha256 manifest. The hooks and the 8,145 rules
ship only as sealed `.mimosa` artifacts. **Altering them is tampering, not configuration**, and is
excluded by Owner instruction 4.

### B.4 Failure-mode defaults (material — and they favour the commit)

- `MIMOSA_HOOK_FAILURE_MODE` default **`open`**: on scanner-infrastructure failure or partial
  coverage, Mimosa reports `INCONCLUSIVE` and defers to the Stop review. It does **not** deny.
  (`strict` would deny — it is not set.)
- `MIMOSA_GIT_GATE_FAILURE_MODE` is unset and **inherits `open`**.
- `MIMOSA_GIT_GATE_MODE` default **`graded`**: only *high* severity forces a deny.

Verified in the live environment: **no `MIMOSA_*` variable is set** (`env | grep -i mimosa` → none).

**Consequence:** the 2026-09-11 Stop outcome (`findings=0`, `status=inconclusive`, caused by
`spawnSync … ETIMEDOUT`) would **not** have denied a commit under the active defaults.

### B.5 This session is outside Mimosa's observation entirely

- `grep -c 'C8_MECHANISM_AUDIT' ~/.zcode/mimosa-debug.log` → **0** (this session's file writes are
  absent from the log).
- The log's last entry is `2026-09-11T13:12:47.885Z`; this session wrote after that and produced no
  entries.
- This repository's Claude Code settings register **no hooks**: `.claude/settings.json` contains only
  `permissions`; `.claude/settings.local.json` contains only `permissions` (hooks object empty).

**Stated plainly, because it must not be used silently:** a `git commit` issued from this Claude Code
session is **not gated by Mimosa**. That is a property of the harness, not a resolution of the scope
problem, and this record treats it as an Owner decision (§G), not as a route to take unilaterally.

---

## C. SIDE-CORPUS STATUS

**Owner instruction 1 (stop editing `ZCodeProject/`) is in force.** No cleanup edit was made in this
session. The only writes performed were the restorations instruction 2 directs.

### C.1 What the cleanup attempt had modified (7 files, all outside the repo)

Identified from the Stop-hook `changedRanges` record of session `sess_6ec6492a…`. `ZCodeProject` is
**not** version-controlled, so git could not serve as the restore source. A byte-exact source was
located instead: Mimosa's own pre-change snapshot store,
`.mimosa/hook-state/sess_971d51e8….baseline/` (32 content-addressed `*.source` files, captured
2026-09-10 11:16 — after the discovery runs, before the 2026-09-11 cleanup).

Corroboration that the snapshots are the correct pre-cleanup state: the per-file diff hunk counts
reproduce the Stop hook's independently recorded `changedRanges` (01→3/3, 03→2/2, 04→2/2, 05→2/2,
assemble→2/2).

### C.2 Restoration performed and verified

| File | Baseline sha256 (prefix) | Restored | Verification |
|---|---|---|---|
| `pm_data_audit/01_schema_inventory.py` | `72e3fd6c…` | **YES** | byte-identical to baseline · `ast.parse` OK |
| `pm_data_audit/02_index_inventory.py` | `19c27ddc…` | **YES** | byte-identical · `ast.parse` OK |
| `pm_data_audit/03_table_stats.py` | `3539ab32…` | **YES** | byte-identical · `ast.parse` OK |
| `pm_data_audit/04_broker_flow_deep.py` | `6d8b5c44…` | **YES** | byte-identical · `ast.parse` OK |
| `pm_data_audit/05_semantics_probe.py` | `0a51859c…` | **YES** | byte-identical · `ast.parse` OK |
| `hliq_liquidity_shock/assemble_lq45_dataset.py` | `959fa700…` | **YES** | byte-identical · `ast.parse` OK |
| `hliq_liquidity_shock/execute_hliq.py` | **none exists** | **NO — see C.4** | `ast.parse` OK (left as found) |

The as-modified versions were preserved before overwriting, at
`…/scratchpad/sidecorpus-precleanup-backup-2026-09-12/*.ASMODIFIED`, so the restoration is itself
reversible.

**`pm_data_audit/17_family_passD.py` — the C8/C7 descriptive-evidence generator — was never touched**
(mtime unchanged at 2026-09-10 10:41:06). The C8 audit of 2026-09-11 read it only.

### C.3 What the cleanup edits actually were (now reverted)

Purely scanner-appeasement, with no research purpose:
- `PRAGMA table_info('{name}')` f-string → `SELECT … FROM pragma_table_info(?)` (and the same for
  `index_list` / `index_info`), where the interpolated value came from `sqlite_master`, never user
  input;
- absolute output paths → `__file__`-relative / `os.path.join(...)`;
- `import os` prepended as **line 1**.

**Why reverting matters beyond tidiness:** these are the frozen evidence generators behind published
P-M descriptive results. Silently rewriting them breaks the byte-provenance of numbers already
cited in governance documents — the exact reproducibility defect recorded as **G-9** in
`C8_MECHANISM_AUDIT_2026-09-11.md` §9. Restoration repairs it.

### C.4 `execute_hliq.py` — NOT restored, Owner decision required

No baseline snapshot for this file exists in any of the three retained `.baseline` stores (searched
all 32 snapshots across all sessions for its `H-LIQ` signature — zero hits). Its current state
carries three cleanup changes, reconstructed from the file itself:

1. **`import os` inserted as line 1, above the `#!/usr/bin/env python3` shebang** — the shebang is no
   longer line 1 and is now an inert comment, so the file can no longer be executed directly.
2. line 468 — `open(f"{BASE}/12_HLIQ_RESULTS.json", "w")` → `open(os.path.join(BASE, "12_HLIQ_RESULTS.json"), "w")`
3. line 480 — the same transformation for `13_HLIQ_EVENT_LEVEL.csv`

Changes 2–3 are behaviour-preserving and did not even remove the flagged pattern (`BASE` remains an
absolute path). Change 1 is a defect.

**It was left untouched deliberately.** This file is a **pre-registered execution script** — its own
header reads *"H-LIQ — SINGLE PRE-REGISTERED EXECUTION (2026-08-29) … Implements
08_HLIQ_PREREGISTRATION.md exactly. No post-hoc variation."* Reconstructing a frozen prereg script
from inference rather than from a verified baseline is not restoration, and a partial fix is worse
than none: deleting line 1 alone would break lines 468/480, which now depend on `os`. This is the
Owner's call (§G.3).

---

## D. STAGED 69-FILE INTEGRITY

All checks re-run in this session against the live index.

### D.1 Count — **PASS**
`git diff --cached --name-only | wc -l` → **69**.

### D.2 No unintended files — **PASS**

| Check | Result |
|---|---|
| Any staged path outside `docs/` | **NONE** |
| Any staged path matching `zcode` (case-insensitive) | **NONE** |
| Distribution | `g1_harness/` 35 · `dataset_b/` 31 · `DECISION_LOG.md` · `HYPOTHESIS_REGISTRY.md` · `FAILURE_REGISTRY.md` |
| Abandoned files from the 09-10 deny events (`build_freeze_candidate_manifest.py`, `freeze_candidate_manifest.py`) | **absent from the index** — confirmed not staged |
| Binary store (`*.sqlite`, `-shm`, `-wal`), `__pycache__` | **absent** (per 09-11 exclusion list, re-verified) |

### D.3 No external side-corpus files — **PASS**
Zero staged paths resolve outside the repository. The restorations in §C are entirely outside this
repository and therefore **cannot** and **do not** appear in the staged set or in any future commit
from it.

### D.4 Governance patch contents unchanged — **PASS**

| File | Staged diff | Assessment |
|---|---|---|
| `docs/roadmap/DECISION_LOG.md` | **+643 / −0** | strictly append-only — D-048 (§2i) and D-049 (§2j). No existing entry altered. |
| `docs/research_programs/HYPOTHESIS_REGISTRY.md` | +40 / −2 | the two removed lines are the `**Last updated:** 2026-08-19` header and the P-M family-ledger **counter row** (`**1** — HYP-PM-0001` → recomputed). No hypothesis record deleted or rewritten. |
| `docs/research_programs/FAILURE_REGISTRY.md` | +9 / −3 | removed lines are the `Last updated` header, the **F2 tally row** (`**2**` → recomputed), and the superseded `N=2` commentary block. No failure entry deleted or rewritten. |

Every deletion is a header date or a derived counter/commentary that must be recomputed when members
are appended. **Append-only discipline (HL-1/R12, D-028) holds.**

### D.5 C7 remains `c7_registered=false` — **PASS**

Staged blob (`git show :…/g1_config.json`) and working tree agree exactly:

```
c7_registered   = false
synthetic       = false
freq_resolution = "withdrawn"
gates = { dataset_b_frozen: true, prereg_confirmed: true,
          freq_semantics_ratified: true, net_flow_source_ratified: true }
```

> Noted, no action taken and none proposed: DECISION_LOG **D-049 R-6** records that
> `c7_registered = true` was *authorized* and lists `g1_config.json` among its changed files, while
> the file carries `false`. Setting it is an Owner act explicitly outside this task (instruction 8).

### D.6 No empirical execution occurred — **PASS**

| Evidence | Result |
|---|---|
| C7 output artifact of any kind | **does not exist** — C7 has never produced one |
| `G1_REAL_OUTPUT_RUN1_2026-09-11.json` / `G1_RUN_MANIFEST_RUN1…` | unchanged, mtime `2026-09-11 09:34` (Run 1) |
| `data/research.db` | unchanged, mtime `2026-09-11 18:30` — **read-only access only** (`mode=ro` + `PRAGMA query_only`) |
| Dataset B store | unchanged, mtime `2026-09-11 04:24` |
| Dataset B store sha256 | **`21661f033145ef90…` — matches freeze manifest v1 exactly** |

---

## E. MINIMAL SAFE RESOLUTION

### E.1 Rejected outright (Owner instruction 4)

| Option | Why rejected |
|---|---|
| `MIMOSA_NO_GIT_GATE=1` | Globally disables the L3 git gate — the precise prohibition. |
| `MIMOSA_GIT_GATE_MODE=warn` / `MIMOSA_HOOK_BLOCK=warn\|ask` | Downgrades deny-on-high everywhere. Weakens the check globally. |
| Editing/repacking the sealed hooks or rules | Tampering with an integrity-signed, encrypted artifact. Not configuration. |
| Any path/file exclusion | **No such mechanism exists** (§B.3) — and inventing one would be "silently exclude arbitrary files". |
| Continuing side-corpus remediation | Countermanded by the Owner decision opening this task. |

### E.2 The one correct scope correction — **re-root the ZCode workspace to the repository**

Mimosa's scope is *derived*, not configured: every surface anchors to the ZCode workspace root
(§A.3). Therefore the scope is corrected by pointing the workspace at the repository being
committed, rather than by excluding anything:

> Open the ZCode workspace at **`/home/tjiesar/10 Projects/idx-walkforward-5001`** instead of
> `/home/tjiesar/ZCodeProject`.

Why this is the *smallest safe* correction, and satisfies instruction 5 exactly:

- **It changes no security setting.** No env var, no mode, no rule, no severity threshold. Every
  check keeps its current strength; `graded` deny-on-high stays in force.
- **Staged files remain fully scanned** — more so, not less: the L3 git gate's project scan and the
  Stop review would then cover the repository and its diff, which is presently *not* their subject.
- **Nothing is excluded.** The side corpus leaves scope because it is genuinely a different project,
  not because a rule was written to skip it. It regains its own gate whenever its own workspace is
  opened.
- **What is "excluded" and why, stated explicitly as instruction 5 requires:** only
  `/home/tjiesar/ZCodeProject` — an unrelated, non-git, legacy research corpus that contributes zero
  files to this commit — and only for the duration of work on this repository.

**It is nevertheless not something this task may perform.** It is a ZCode application-state change
(`~/.zcode/v2/setting.json`, live app state, Owner-owned), not a repository configuration, and this
repository exposes no setting that can effect it. Per instruction 6, that lands as **STOP**.

### E.3 Also available to the Owner, and lower-cost

Because the true terminal state was `findings=0 / inconclusive` from a **scanner timeout** (§A.2)
and the active failure mode is `open` (§B.4), the gate may simply pass on a clean retry. The
timeout (`spawnSync /usr/bin/node ETIMEDOUT`, 7/7 files, against a 1,000 ms `hardTimeoutMs` gate
budget) points at host load at 13:12Z, not at the code. **Re-running the commit in a correctly-rooted
ZCode session is the cheapest complete test of the whole theory**, and it needs no override at all.

---

## F. IS THE BASELINE COMMIT NOW POSSIBLE?

### **NO — and the commit was deliberately not made.**

- **Repository-scoped *configuration* is NOT supported** (§B.3 — no scope/exclude/ignore setting
  exists; hooks and rules are encrypted and integrity-signed). Instruction 5's precondition is
  therefore unmet, and instruction 6 applies: **STOP. Do not continue fixing the external corpus.**
- The scope correction that *is* correct (§E.2) is an Owner act on ZCode application state, outside
  this repository and outside this task's authority.
- No Owner override has been given for a specific baseline commit.

**Everything else is ready.** The blocker is a scope/authority question, not a data, code,
governance, or security question:

- staged set verified at exactly **69** files, no unintended or external paths (§D.1–D.3);
- governance patch verified append-only and unchanged (§D.4);
- `c7_registered=false` verified in both index and working tree (§D.5);
- no empirical execution; Dataset B store sha `21661f03…` matches the freeze manifest (§D.6);
- the side corpus is restored to its authentic pre-cleanup state, 6 of 7 byte-exact (§C.2).

**Honest disclosure, per instruction 4's spirit rather than its letter:** as established in §B.5, a
commit issued from this Claude Code session would not pass through Mimosa at all, because Mimosa is a
ZCode plugin and this harness registers no such hook. Committing from here would therefore *work* —
and would amount to routing the baseline commit around a control the Owner installed, without
authorization. **That is recorded as an available fact and explicitly declined as a unilateral
action.** It is offered as Owner option §G.2, not taken.

---

## G. EXACT OWNER ACTION REQUIRED

Choose one. Options 1 and 3 need no override; option 2 does.

### G.1 — Re-root the ZCode workspace (recommended; no override, no weakening)
Open the ZCode workspace at `/home/tjiesar/10 Projects/idx-walkforward-5001`, then re-issue the
commit there. Mimosa's gate and Stop review then scope to this repository and its staged diff — the
outcome instruction 3 asks for — with every check at full strength and every staged file scanned.
If the earlier `ETIMEDOUT` was transient host load (§E.3), this alone resolves it.

### G.2 — Authorize the baseline commit explicitly
State, for this specific commit: *"Commit the staged 69-file governance baseline on
`ops/hardening-2026-07-10`."* On that authorization the commit is made from this session, and this
document is updated with the hash and the post-commit verification checklist. The 09-11 record's
`--no-verify` framing is moot — there is no hook here to bypass.

### G.3 — `hliq_liquidity_shock/execute_hliq.py` (independent of the commit)
No verified baseline exists (§C.4). Decide between:
 (a) leave as-is and record the three changes as an accepted post-hoc modification to a pre-registered
     script; or
 (b) authorize reconstruction — remove the line-1 `import os`, restore the shebang to line 1, and
     revert lines 468/480 to their f-string form — as a documented reconstruction, not a restoration.
Option (b) must be explicit, because it edits a frozen pre-registration artifact on inference.

### G.4 — Not requested and not to be inferred from this document
`c7_registered=true` · any C7 execution · any C7 methodology change · any Dataset B or `research.db`
change · any further HYPOTHESIS_REGISTRY change beyond the already-approved governance patch.

---

## POST-COMMIT VERIFICATION CHECKLIST (carried forward, unexecuted)

- [ ] `git log -1 --format=%H` — record hash
- [ ] `git status` — clean for the committed paths
- [ ] store sha256 `21661f033145ef90…` — re-verify (currently **matching**)
- [ ] G1 suite 16/16 · C7 suite 7/7 · provenance suite 8/8
- [ ] `c7_registered=false` confirmed post-commit
- [ ] No C7 empirical execution

---

**Commands of record for §A–§B** (all read-only):
`grep -c '"toolName":"Bash"' ~/.zcode/mimosa-debug.log` → 0 ·
`grep -o '"toolName":"[A-Za-z]*"' … | sort | uniq -c` → Edit 1066, Write 674 ·
`grep -n 'git commit' ~/.zcode/mimosa-debug.log` → no matches ·
`cat …/mimosa/1.0.3/hooks/hooks.json` · `cat …/payload/contracts/scan-profiles.json` ·
`grep -niE 'MIMOSA_[A-Z_]+' …/payload/README.md` · `env | grep -i mimosa` → none ·
`cat /home/tjiesar/ZCodeProject/.mimosa/reports/task-review-sess_6ec6492a….json` ·
`git -C /home/tjiesar/ZCodeProject rev-parse` → not a git repository.
