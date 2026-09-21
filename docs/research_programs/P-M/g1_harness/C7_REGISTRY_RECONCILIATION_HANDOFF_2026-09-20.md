# HANDOFF — C7 / HYP-PM-0006 registry reconciliation (2026-09-20)

**For:** ZCode (or whoever picks this up next). Self-contained — no prior conversation context assumed.
**Repo:** `idx-walkforward-5001` (`D:\IDX` on tjiejet / `github.com/Tjie-hub/5001.git`), branch `ops/hardening-2026-07-10`, HEAD `9227f86`.
**Type of task:** mechanical bookkeeping fix to `docs/research_programs/HYPOTHESIS_REGISTRY.md`, plus one separate judgment call flagged for the Owner (not resolved here). No empirical work, no code change, no re-execution of anything.

---

## 1. What's wrong

`docs/research_programs/HYPOTHESIS_REGISTRY.md` (last updated per its own header: 2026-09-18) still lists **HYP-PM-0006 (C7 intensity-state)** as:

> **REGISTERED** 2026-09-11 (`C7_REGISTRATION_v1_2026-09-11.md`) · pending execution (gated)

This is stale. **C7 was already executed on 2026-09-14**, properly authorized (D-049 R-6), fully gated/sealed/provenance-verified, with a terminal, determinate-null result. The execution report exists at:

`docs/research_programs/P-M/g1_harness/C7_EXECUTION_REPORT_2026-09-14.md`

Key facts from that report (all sealed/hash-verified — do not re-derive, just cite):

- Registration act: `g1_config.json` `c7_registered: false → true`, authorized by **D-049 R-6** (`docs/roadmap/DECISION_LOG.md`).
- `run_id`: `RUN-20260914T015335Z-41bea166a025`
- Preflight gates: 13/13 PASS (Dataset B frozen + hash-verified, PIT alignment, no future leakage, production-DB isolation, etc.)
- Deterministic suites: 31/31 passed (C7 7/7, G1 16/16, provenance 8/8)
- **Primary result (k=5, registered primary horizon):** θ_mean = +0.001338 (+13.38 bp), Newey-West t = +0.5061, n=338 days, two-sided p = 0.612807, Holm p = 0.612807 (single-cell family, Holm = identity) → **not significant at α=0.05**
- Secondary horizons (k=3, k=10): also not significant (p = 0.768, 0.392)
- Cost-adjusted (0.60% RT floor, sensitivity only, never the verdict): net ranges from −31.34bp (k=10) to −54.08bp (k=3)
- **§J Final registered verdict, verbatim:** *"C7 = VALID execution → NOT CONFIRMED (determinate null)... the intensity-state (gross/ADV20 ≥ 2.0) contrast carries no detectable next-session directional return information at the registered horizons in Dataset B."*
- Report's own closing line: *"Stop: per registered-run discipline, no follow-up analyses, no C8 testing, no parameter changes follow this execution."*

So: nothing needs to be run. The registry just needs to be brought into agreement with a result that already exists, is already sealed, and is already terminal per this program's own rules.

## 2. Exact registry edits needed (scope: these three spots only)

### 2a. Main table row (currently ~line 15)

Current:
```
| **HYP-PM-0006** | P-M · C-family · **C7** intensity-state | gross/ADV20 ≥ 2.0 state → registered outcome (directional forward return; high vs non-high daily contrast) | **REGISTERED** 2026-09-11 (`C7_REGISTRATION_v1_2026-09-11.md`) · pending execution (gated) | `C7_REGISTRATION_v1_2026-09-11.md` · `C7_REGISTRATION_READINESS_2026-09-11.md` | **C-family registered** (3rd member — not yet executed) |
```

Replace with (style matched to the HYP-PM-0004/0005 rows immediately above it):
```
| **HYP-PM-0006** | P-M · C-family · **C7** intensity-state | gross/ADV20 ≥ 2.0 state → registered outcome (directional forward return; high vs non-high daily contrast) | **NOT CONFIRMED (VALID, determinate null)** — executed 2026-09-14 under D-049 R-6 (`run_id RUN-20260914T015335Z-41bea166a025`); was REGISTERED 2026-09-11 | `C7_REGISTRATION_v1_2026-09-11.md` · `C7_REGISTRATION_READINESS_2026-09-11.md` · [[C7_EXECUTION_REPORT_2026-09-14]] | **C-family consumed** (3rd member) |
```

### 2b. Family-slot ledger row (currently ~line 29)

Current (excerpt):
```
| **P-M · C-family** | {C2, C3, C7} | **3** — HYP-PM-0004 (C2, INVALID), HYP-PM-0005 (C3, NOT CONFIRMED), HYP-PM-0006 (C7, pending execution) | family opened per **D-048** (2026-09-11, Owner Option B): ... C7 execution gated (`c7_registered=false` + runs/<run_id> provenance wrapper per D-048) |
```

Replace `HYP-PM-0006 (C7, pending execution)` → `HYP-PM-0006 (C7, NOT CONFIRMED)`, and replace the trailing clause `C7 execution gated (...)` → `C7 executed 2026-09-14 under D-049 R-6 authorization, NOT CONFIRMED (Holm p=0.6128 at primary k=5) — see C7_EXECUTION_REPORT_2026-09-14.md`.

### 2c. Notes section — add a new paragraph

Immediately after the existing `HYP-PM-0004/0005/0006 (C-family, opened per D-048...)` note paragraph (currently ends `...C7 (\`HYP-PM-0006\`) is REGISTERED and execution-gated. Full receipts: DECISION_LOG **D-048** · ...`), append a new paragraph in the style of the existing HYP-PM-0003/HYP-PM-0009 notes:

```
- **HYP-PM-0006 (C7)** — **executed 2026-09-14** under **D-049 R-6** authorization (`g1_config.json`
  `c7_registered: false → true`, the only parameter change; spec fixed verbatim by
  `C7_REGISTRATION_v1_2026-09-11.md` §2/§3). Preflight: 13/13 gates PASS, Dataset B store sha256
  `21661f03…` re-verified unchanged, PIT-aligned, production DB isolation confirmed (ro + query_only).
  Deterministic suites 31/31 (C7 7/7, G1 16/16, provenance 8/8). **Primary k=5: θ = +13.38bp, NW t =
  +0.5061, n=338 days, Holm p = 0.6128 — NOT CONFIRMED.** Secondary k∈{3,10} also non-significant
  (p=0.768, 0.392). Cost-adjusted net −31.34bp to −54.08bp across horizons (sensitivity only, not the
  verdict). Sealed: `run_id RUN-20260914T015335Z-41bea166a025`, output sha256 `c1cc10a2…`,
  `valid_provenance=true`, `drifted_files=[]`. **Terminal per registered-run discipline — no rescue, no
  C8 testing, no parameter changes authorized.** Receipts: DECISION_LOG **D-049** R-6 ·
  `docs/research_programs/P-M/g1_harness/C7_EXECUTION_REPORT_2026-09-14.md`.
```

Also update the registry's own header line (`**Last updated:** 2026-09-18`) to today's date once this edit lands.

## 3. Separate issue — flagged, NOT resolved here (Owner call)

The entire `docs/research_programs/P-M/g1_harness/` directory has been sitting **uncommitted** since the last commit (`bf9f8ec`, 2026-09-11 — the D-048/D-049 governance commit). `git status` shows ~35 modified files plus several untracked files in that directory, including:

- The actual C7 execution artifacts: `C7_EXECUTION_REPORT_2026-09-14.md`, the `runs/runs/RUN-20260914T015335Z-.../` provenance-sealed directory, and the `g1_config.json` flip that triggered the run — i.e. the real evidence for §1/§2 above has never been committed, 6 days after the run.
- A pile of other modified/untracked files (`C3_REGISTRATION_READINESS_AUDIT_2026-09-14.md`, `NEXT_LAWFUL_HYPOTHESIS_AUDIT_2026-09-14.md`, `identity_audit.py`, etc.) whose individual provenance I have not audited.

I have **not** bulk-committed any of this — mixing ~35 files of unknown individual provenance into one commit is exactly the kind of scope call this project's own governance conventions (append-only, one dated act per commit) argue against making unilaterally. Recommend whoever picks this up either (a) commit the registry fix from §2 as its own isolated commit citing D-049 R-6, and separately triage the rest of the g1_harness pile with the Owner, or (b) ask Tjie directly how he wants the backlog committed.

One mechanical note: this session's `git status` calls left a stale `.git/index.lock` behind (the device-bridge mount here returns `Operation not permitted` on git's own attempt to `unlink` its lock after use — a mount-permission quirk, not a real concurrent-git-process problem; confirmed no git process running). I moved it aside once (`.git/index.lock.stale-20260920`) so reads aren't blocked, but the same stale-lock-on-unlink will likely recur on every git command run through this same mount. If a `git commit` here fails with "Unable to create '.git/index.lock': File exists", that's why — `mv` the stale lock aside (do not rely on `rm`, which is blocked by the connected-folder delete-permission gate) and retry.

## 4. What "done" looks like

- `HYPOTHESIS_REGISTRY.md` matches §2a/2b/2c above, header date bumped.
- A commit (scoped to just the registry file, or the registry file + the C7 execution artifacts it now cites — reviewer's call) with a message in this repo's existing style, e.g.:
  `docs(P-M): reconcile HYPOTHESIS_REGISTRY -- HYP-PM-0006/C7 NOT CONFIRMED, executed 2026-09-14 (D-049 R-6)`
- The broader g1_harness uncommitted backlog (§3) either committed separately with Owner sign-off, or explicitly left open with a note — not silently bundled into the registry commit.
