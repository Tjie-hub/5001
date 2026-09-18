# ZCODE ADVERSARIAL REVIEW BRIEF V2 — FWD-PM-REGIME-002 + 2026-09-17 PATTERN SCAN

**Date:** 2026-09-18 · **Status:** REVIEW BRIEF, V2 — supersedes
`ZCODE_FORWARD_REGIME_REVIEW_2026-09-18.md` (96067a8), which is retained unedited as
evidence. Do not edit, move or delete the V1 file; it documents a failure mode this
brief exists to prevent.
**Branch:** `ops/hardening-2026-07-10` (HEAD at drafting: `cf18e43`). Every commit on
this branch is authored by `Tjie <you@globalgatecustoms.com>`.
**Protocol under review:** `docs/research_programs/P-M/forward_regime/PROTOCOL.md`,
sha256 `4063752ef76bae840b0ff007ec2d4b3bdf9325a2b18ece0779e2fa737ec58870`.

---

## 0. Why V2 exists

V1 asked for adversarial attack on eight ranked research claims. The reviewer who
received it read it as an engineering task list: it fixed 16 failing tests, tracked
four untracked route modules, hardened an SSRF finding, and made three commits
(`5f2c630`, `78f3d09`, `f2f7b4c`). All competent work, later accepted by the owner —
and not one of the eight claims was examined. Zero.

The root cause was not carelessness. V1 contained a mandate ("reviewer mandate:
refute") but not a single prohibition. Nothing told the reviewer the repository was
mid-review by owner decision, that broken things were intentionally left broken, or
that repairs were outside the assignment. Given a repo with visible failures and a
brief silent on scope, the path of least resistance won. V2 carries its scope lock
inside itself, addressed to you, so it survives being handed to a cold agent with no
other context.

---

## 1. Reviewer contract — read this twice before touching anything

### 1.1 Your deliverable

A findings report, delivered as your final message (a copy under `/tmp/` is fine).
For every claim C-1..C-9 in §2 and every governance claim G-1..G-4, exactly one
verdict:

- **REFUTED** — per the §3 bar, or
- **STANDS** — you reproduced the evidence and the number came out as claimed, or
- **NOT TESTED** — with the specific reason you could not test it.

An omitted claim is a failed review. "Looks reasonable" is not a verdict.

### 1.2 What you may and may not do

You **may**: read any file; read git history (`git log`, `git show`, `git diff`);
run the frozen analysis scripts read-only exactly as specified in §6, with all
output directed to a `/tmp` scratch directory; compute hashes; query the production
database read-only (`mode=ro`) to reproduce the §6 fingerprint.

You **may not**:

- Commit, stage, amend, or push anything. Not one file.
- Edit or create any file inside the repository. Including this brief, V1, the
  protocol, the ledger, the registries, and any code or test.
- Run pytest, fix a failing test, or "just tidy up" anything. The suite was green
  at 3,245 passed / 3 skipped / 0 failed as of HEAD `cf18e43`; its state is not
  your problem and re-running it wastes your session (it takes ~7 minutes and
  proves nothing about the claims).
- Run `run_formation.py` (§6). It appends to the live append-only ledger; the
  09:30 WIB cron owns it. Running it as a "check" is a write to a production
  research record.
- Touch crontab, services, or any process state.
- Act on any bug, risk, drift, or untracked file you happen to notice. It goes in
  §7 as a one-line note. It does not get fixed, tracked, hardened, or reported
  anywhere else.

**If you find yourself editing code, you have misread this brief.** Stop, re-read
§1, and resume the review.

### 1.3 Hygiene

Snapshot `git status --short` at session start and compare at session end. The
tree has pre-existing uncommitted owner state (`.stignore`, `Audit/` deletions,
and more) — it must be byte-identical before and after you. A changed `git status`
at your session end means you wrote something; that is a contract breach even if
the write was "helpful".

### 1.4 Traps that have already caught someone

1. **This repo syncs via Syncthing, and a test run can execute a stale copy of
   the working tree.** The last reviewer hit an "impossible" test failure — the
   failing assertion contradicted the source on disk — debugged it for three
   tool-rounds, then saw a commit it did not remember (`5f2c630`) and concluded a
   parallel agent was working in the repo. There is no parallel agent: every
   commit on this branch is authored by `Tjie <you@globalgatecustoms.com>` (verify:
   `git log --format='%an <%ae>' origin/ops/hardening-2026-07-10..HEAD | sort -u`).
   Rule: when an anomaly contradicts the disk, re-run in isolation and check
   `git log` freshness before concluding anything. Never infer a second actor from
   a commit you do not remember.
2. **Single-ticker validation is worthless here, and "checking the signal on a
   chart" is how reviewers fool themselves.** Every refuted mean-reversion pattern
   looks profitable on BRPT (+4.41% to +6.09%); BRPT sits at the 91st percentile
   of the universe, where only 35% of tickers are positive. A chart impression on
   one ticker — especially BRPT — has reproduced C-4's trap, not refuted anything.
   Cross-ticker, pooled, or per-ticker-demeaned evidence only.
3. **Governance constraints bind you too.** Multiplicity families are append-only
   and may be widened but never narrowed. A REJECTED gatekeeper decision is never
   reversed retroactively. `DECISION_LOG`, `HYPOTHESIS_REGISTRY` and
   `FAILURE_REGISTRY` are corrected only by a superseding entry. You therefore
   cannot and must not edit any of them: your findings are recommendations to the
   owner, who alone disposes. A finding that requires you to rewrite a registry to
   "fix" it is a finding about the registry's process — report it, don't perform it.

---

## 2. The claims to attack

Ordered by how much rests on each. C-1 and C-2 are coupled: C-2's tail
concentration is the fastest legitimate route to drawing blood on C-1's headline —
attack the standard error, not the mean. C-9 is the only claim whose refutation
ends the test immediately.

| # | Claim | Evidence | Where it would break |
|---|---|---|---|
| **C-1** | Trend-regime onset + 3×ATR exit earns **+1.26%/trade (t 3.90)** ex-2025, next-open entry vs equal-weight book; on the declared endpoint basis (0.60% round trip, the repo cost authority) ≈ **+9.40%/yr excess, Sharpe 0.68**; breakeven round trip **1.47%**. (PROTOCOL §2.1 also records +10.46%/0.75 at the operator-stated 0.50% — a sensitivity row, NOT the endpoint. Attack the 0.60% figures; if you attack 0.50% you are attacking a number the spec does not measure on.) | `forward_regime/scripts/audit2.py` | Survivorship (LIM-1, §4); entry-date clustering insufficient for overlapping 60-session holds; equal-weight benchmark construction |
| **C-2** | **Top 1% of trades carry 85%** of total excess; 3.3% cap-exits average **+45.93%** vs +0.64% for the 96.7% | `forward_regime/scripts/exit3.py`, PROTOCOL limitation 9 | If true, is t-based inference valid at all on this distribution? Re-derive C-1's SE under the actual dependence structure; a t of 3.90 built on 1% of the mass is the single softest number in the program |
| **C-3** | Every mean-reversion pattern is a significant **anti-edge**: sweep −1.33%, failed breakdown −1.94%, wedge −1.89% (ex-2025, t to −12) | `pattern_scan/scripts/{sweep,patterns,wedge2}.py` | Detector fidelity (arm 1 used production `engine/smc.py`); definition invariance already tested (6 wedge variants, ex-5% stable −1.16 to −1.22) — find a dependence the variants did not span |
| **C-4** | **Single-ticker validation is worthless**: BRPT (+4.41% to +6.09%) sits at the **91st percentile** where only 35% of tickers are positive | `pattern_scan/scripts/{brpt_all,why}.py` | Is the ticker-demeaned −1.02% (t −3.97) itself an artifact of unbalanced per-ticker N? This claim is the shield behind C-3 — if it falls, chart-checks re-inflate the refuted arms |
| **C-5** | The 001→002 supersession was necessary hygiene: zero-volume carry-forward bars are **0.951%** of liquid ticker-days but **4.778%** of regime-UP days; the ≥18/20 guard was chosen on hygiene, not performance (variants moved ex-2025 only 0.78/0.85/0.83/0.80) | `forward_regime/scripts/zvguard.py` | Re-derive both percentages; test whether any guard variant in {16,18,20} changes the C-1 endpoint materially — if the chosen guard is quietly performance-optimal, "hygiene" is a cover story |
| **C-6** | Regime **conditioning is infeasible** on this corpus: BULL has 9 episodes / 98 sessions; `research/regime/regime_config.yaml` needs min_n=100 across 12 cells | `forward_regime/scripts/{regime,regime_perf}.py` | Is episodes the right N, or sessions? If sessions, min_n=100 may be satisfiable and "infeasible" collapses |
| **C-7** | Three-tier alignment score is **monotonic** (−6.79 / −4.21 / −1.10 / +0.62 / +1.11 ex-2025) but score +2 **inverts** (2025 artifact) | `forward_regime/scripts/{tiers,table27}.py` | 27 cells were searched before collapsing to a score — is the collapse pre-specified or post-hoc selection dressed as aggregation? |
| **C-8** | **All-three-BULL has never occurred** (0 of 1,099 sessions); LONG&MID both BULL occurred once | `forward_regime/scripts/tiers.py` | Is SHORT (ADX 7 / MA 10 / slope 3) a legitimate tier or a parameter fork that manufactures the impossibility? Re-derive all 27 cells and the 1,099 denominator |
| **C-9** | **The three post-opening protocol amendments are observability/disclosure-only** — §2 specification and §3 decision rule unchanged — so the in-flight test is not contaminated and the standing invariant ("never retroactively change an in-flight forward test's rule") holds | `ledger.json` `_amendment_note` + `protocol_sha256_at_open`; protocol git history; `run_formation.py` | See the dedicated checklist below |

### 2.1 C-9 examination checklist (new in V2 — test the claim, do not accept it)

The ledger carries `protocol_sha256_at_open = 6e7e1a7b632ef591…` but
`protocol_sha256 = 4063752e…`. The protocol was amended **after the test opened**
(2026-09-17T06:53:30Z), three times, all claimed observability-only:

- `d53b130` — "limitations 9 and 10 appended" (+44 lines, 0 deletions)
- `a54b4e8` — `ihsg_regime_at_entry` added (+23, 0 deletions)
- `77e81f6` — `ihsg_weekly_regime_at_entry` added (+21, 0 deletions)

Provenance to verify first (§6 has the commands): the blob at `2e416f6` must hash
to `6e7e1a7b…` and the working tree to `4063752e…`. Then attack on four fronts:

1. **Additivity — verify it, then distrust what it proves.** Confirm for
   yourself that the amendments are purely additive; as of HEAD `cf18e43` the
   cumulative diff `2e416f6..HEAD` is **+88/−0**, with zero deletions in all
   three commits (`git diff --numstat`, and `git diff … | grep -E "^-[^-]"`
   returning empty). Do not take that from this brief — re-run it, and re-run it
   against current HEAD, since the protocol may be amended again while you work.
   Then note what additivity does NOT establish: every original line surviving
   proves no line was *removed*, not that none was *overridden*. An appended
   limitation or schema note can redefine a term that §2 or §3 depends on, and
   the diff will look innocent. If any added text changes the meaning of frozen
   rule text without touching it, C-9 is REFUTED just as surely as by a deletion.
   (V2 drafting note: an earlier draft of this brief asserted "+89/−1, exactly
   one deleted line — find it." That was false; no such line exists. It is
   recorded here rather than quietly removed, because a review instruction that
   invents an artifact and orders a reviewer to locate it is precisely the
   pressure this program is trying to keep out of its evidence.)
2. **Diff content beyond the claim.** Every added line must be: limitations 9–10
   prose, the two ledger schema attributes, or their "never filters, gates or
   sizes anything" language. Anything else that touches §2/§3 substance is a
   refutation.
3. **The code, not the comment.** In `run_formation.py`, `detect_regime` output
   must appear **only** as recorded attributes. Trace it: entry starts are
   `up & ~prev(up) & liq` (slope/ER/PA state + liquidity), exits are the 3×ATR
   trail and 60-session cap, and neither may consult a regime value; a classifier
   failure (null) must never drop a trade. Distinguish carefully: missing IHSG
   **prices** (`ie`/`ix`) *do* drop a trade — that is pre-existing spec behavior
   for `market_return`, not an amendment effect; do not conflate the two, and do
   not let the code's `"observability only"` comments substitute for your trace.
4. **No look-ahead in the new attributes.** `weekly_at()` must select the last
   weekly bar **closed strictly before** the entry date (V1 recorded that
   2026-09-14/15/16 entries all resolve to the week closing 2026-09-11 —
   re-verify). A mid-week entry seeing its own in-progress bar would contaminate
   the 2029 regime-conditioning evidence even though it never gates anything.
   While in the exit logic: the trail compares the exit bar's close to a peak
   that already includes that bar's high, using that bar's own `atr14` — confirm
   the frozen §2 exit definition (in the `6e7e1a7b` blob) actually specifies
   this, and that the amendments did not touch exit wording.

**Severity:** if C-9 falls, the in-flight test is contaminated, the standing
invariant is broken, and the owner must decide supersession or restart. Nothing
else in this brief carries that consequence.

### 2.2 C-7 and C-8 — evidence recovered and re-verified during V2 drafting

An earlier V2 draft marked these two claims UNSUPPORTED. That was wrong and is
recorded here rather than silently dropped.

`tiers.py` and `table27.py` had genuinely never been committed — they were
missed in the 2026-09-17 staging pass, so at V2 drafting time they were absent
from `forward_regime/scripts/`, from `SHA256SUMS.txt`, and from every branch
(`git log --all --diff-filter=A` returned nothing). They were recovered intact
from the originating session's scratch directory, staged alongside the other
33 scripts, and added to the manifest (now 35 entries, `sha256sum -c` clean).

Both were then re-run end to end against the same inputs. Every cited figure
reproduced exactly:

| | claimed | reproduced |
|---|---|---|
| dated 3-tier states | 1,099 | 1,099 (2022-02-07 → 2026-09-15) |
| ALL THREE BULL | 0 | 0 |
| LONG & MID both BULL | 1 | 1 |
| score ladder ex-2025 | −6.79 / −4.21 / −1.10 / +0.62 / +1.11 | identical |
| score +2 | inverts | −4.43 |

**Reviewer instruction.** C-7 and C-8 are in scope and fully attackable on the
normal terms. Note that reproduction is not corroboration: re-running these
scripts confirms the arithmetic, not the inference. The live questions remain
the ones in the table — whether collapsing 27 searched cells into a score is
pre-specified or post-hoc, and whether the SHORT tier (ADX 7 / MA 10 / slope 3)
is a legitimate timeframe or a parameter fork that manufactures the
impossibility. The `fast_regime()` docstring in `tiers.py` concedes it is "a
research variant, not the frozen production fn"; decide whether that concession
is sufficient. Note also that score +2 inverting ex-2025 (+4.26% all-era vs
−4.43% ex-2025, on 403 → 187 trades) is the same 2025-dependence that C-1 is
measured to avoid — ask why the score survives an era check that its own top
bucket fails.

### 2.3 Governance claims open to challenge (carried from V1 §3 — challenge the reasoning, do not edit the registries)

- **G-1** HYP-PM-0010 was retained through the 001→002 supersession rather than
  re-registered as HYP-PM-0011, on the reasoning that 001 closed with zero
  recorded trades so the re-spec cannot be outcome-driven, and
  mechanism/thresholds/exit/horizon/benchmark/endpoint are unchanged. The
  conservative reading advances {T1} to two members. Flagged for owner override
  in PROTOCOL §7.
- **G-2** A new family {T1} was opened rather than joining a price-feature
  family: none existed (FWD-PM-VOLEX-001 is an unregistered prospective record
  holding no slot). Widening {T1} later is permitted; narrowing is not.
- **G-3** The volatility exclusion was placed at book level
  (`docs/research_programs/BOOK_OVERLAY_POLICY.md`), not in the spec, to avoid
  irreversibly widening {T1}. Challenge: does the overlay contaminate the 002
  endpoint in practice? Design says no — the endpoint is computed over every
  signal regardless of overlay.
- **G-4** The pattern scan was deliberately NOT filed in `FAILURE_REGISTRY`: its
  counts feed family denominators and the registry records only registered
  hypotheses.

---

## 3. What counts as a refutation

A refutation names **all four**, in order:

1. **The claim** — by ID (C-4, G-2, …).
2. **The artifact** — the exact file (and function/line where relevant) that
   carries the claim.
3. **The reproduction** — the exact command sequence a cold reader can rerun:
   script path, environment (`SP` scratch dir), and input state. If you cannot
   reproduce, you have not refuted; you have a §7 observation.
4. **The differing number** — what came out, what was claimed, and the direction
   of the difference. Numbers only. Percentages, t-statistics, counts, dates.

Explicitly **not** refutations:

- "This seems fragile" / "the sample feels small" — fragility assertions without
  a differing number.
- A chart impression on one ticker — that is trap §1.4.2, and on BRPT it is the
  trap working as designed.
- Re-stating a disclosed limitation from §4 — that is re-finding, and re-finding
  produces volume, not findings.
- An unexecuted suspicion about data quality. Execute it or defer it.
- Anything whose "difference" you cannot attach a number to. If your finding has
  no number, it is a §7 one-liner, not a finding.

Upholds are worth little; only refutations survive (LIM8/R2/D-019). A review that
ends with all claims STANDS and three genuine refutation attempts, each executed
to the bar above, is a success. A review that ends with twenty prose concerns and
no numbers is a failure.

---

## 4. Limitations already disclosed — do not spend the review here

These nine are on the record (V1 §4, and the protocol's own limitations section).
Re-deriving them adds nothing. The single sanctioned exception is noted below.

| ID | Limitation |
|---|---|
| LIM-1 | **Survivorship unmeasured.** Corpus holds only names listed as of 2026-09; max ticker-end lag 61 days. Bias optimistic, magnitude unknown. **Largest open threat.** |
| LIM-2 | 2025 dominance throughout. Full-sample Sharpe 1.13 vs ex-2025 0.51. Ex-2025 is the planning basis everywhere. |
| LIM-3 | Close-triggered exits; a real intraday stop fires earlier at a different price. |
| LIM-4 | Effective breadth ~10 (ρ 0.089) from ~131 nominal positions. |
| LIM-5 | Sector neutrality untested and unenforceable — no ticker→sector map for 77% of the universe; `engine/sector_rotation.py` maps 82 of 959 and returns permissive "sector unknown" for the rest. |
| LIM-6 | Long-only, beta 0.95. Alpha +2.258% (t 6.43) survives beta adjustment. |
| LIM-7 | Multiplicity: ~12 scan arms + 6 wedge variants + 6 entry filters + 48 threshold cells + 27 alignment cells, all on one corpus in one session. |
| LIM-8 | `stockbit_flow.composite_score` is **unpopulated** — a ≥70 filter returns zero rows. The engine's composite flow score has never been testable. |
| LIM-9 | Flow-confirmation arm covers 2025-01+ only, inside the outlier regime. |

**Sanctioned exception:** a *quantification* of LIM-1 (survivorship) that moves
C-1 materially is a refutation attempt, not a re-find — V1 §6 invited it and V2
re-invites it. "Survivorship might matter" is the re-find; "survivorship costs
C-1 X points, here is the reconstruction" is the refutation.

---

## 5. The eleven self-corrections already made — verify resolution, do not re-litigate

Each was a self-caught error, corrected in the artifacts. Your job is to confirm
the correction actually landed where claimed — one line each, verified-or-not:

1. `delist.py` checked only calendar gaps and missed zero-volume suspensions — forced the 001→002 supersession (see C-5).
2. Resistance-breakout 5d was an entry-timing artifact: +0.66% → −0.30% when fixed.
3. The first Episodic Pivot test entered at the close and was not Qullamaggie's rule (+3.77% at the true ORB entry).
4. "Downtrend gating is harmful" was measured on excess and needed re-testing on absolute — conclusion survived.
5. UP-state vs episode-onset were conflated in BEAR (+2.58% vs **−2.42%**); the onset figure is what 002 trades — confirm in `run_formation.py`: `starts` must use the transition `up & ~prev(up)`, not the level.
6. TUGU's "4.7× volume" was actually 3.37×.
7. "ER peaks at tops" was wrong — it is steepness.
8. "Never exit on the entry indicator, it lags 20%" was the wrong mechanism.
9. "Stop at 50 positions" was wrong — Sharpe improves out to 131.
10. "Skip slope-Q5" was overstated (small sample).
11. A regime-map proposal was initially misread as regime gating.

Re-opening any of these as a debate is re-litigation. Verifying that, e.g., #5's
onset semantics are really what the recorder implements is the review.

---

## 6. Reproduction — read-only, exactly this way

All scripts read the production DB read-only and write **only** under `$SP`. Work
from the repo root (the scripts hardcode `data/walkforward.db` relative to it) and
use the repo venv:

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"

# 1. Freeze-check the evidence before trusting any of it (both script dirs):
( cd docs/research_programs/P-M/forward_regime/scripts && sha256sum -c SHA256SUMS.txt )
( cd docs/research_programs/P-M/pattern_scan/scripts && sha256sum -c SHA256SUMS.txt )
# A mismatch is a §7 note and a stop for that script — do not repair it.

# 2. Protocol provenance (C-9):
sha256sum docs/research_programs/P-M/forward_regime/PROTOCOL.md   # expect 4063752e…
git show 2e416f6:docs/research_programs/P-M/forward_regime/PROTOCOL.md | sha256sum   # expect 6e7e1a7b…
git diff 2e416f6..77e81f6 -- docs/research_programs/P-M/forward_regime/PROTOCOL.md   # +89/−1; the −1 line is yours to judge

# 3. Panels, then any arm — output only to scratch:
export SP=/tmp/frz_review && mkdir -p "$SP"
for s in extract panel t1 t2 ma; do
  venv/bin/python "docs/research_programs/P-M/forward_regime/scripts/$s.py"
done
venv/bin/python docs/research_programs/P-M/forward_regime/scripts/audit2.py    # C-1
# pattern-scan arms likewise: venv/bin/python docs/research_programs/P-M/pattern_scan/scripts/<arm>.py
```

**Corpus fingerprint** (from V1; re-derive via `extract.py`): `ohlcv` `is_final=1`,
1,087,436 rows, 959 tickers, 2021-07-05 → 2026-09-16; `corporate_actions` 2,171
rows (101 splits). Guards: splits excluded; single sessions beyond ±35% excluded
(305 bars). The database is live and appends forward daily — a row count **above**
the fingerprint with an unchanged `min(date)` and unchanged pre-2026-09-17 history
is expected drift (record it); changed historical rows or a moved `min(date)` is
mutation — a §7 note and a stop.

**Forbidden:** `run_formation.py` — it writes the live ledger (cron 09:30 WIB
daily; crontab verified 0-drift against `deploy/crontab` on 2026-09-18). Read it
for C-9; never execute it.

**Other artifacts, for completeness:** superseded spec
`docs/research_programs/P-M/forward_regime/PROTOCOL_001_SUPERSEDED.md` and
`ledger_001_superseded.json` (closed, zero trades, preserved unedited);
`docs/research_programs/P-M/pattern_scan/PATTERN_SCAN_2026-09-17.md` (~12
unregistered arms); `docs/research_programs/BOOK_OVERLAY_POLICY.md`;
`research/regime/regime_config.yaml`.

At session end: `git status --short` matches your §1.3 snapshot, `$SP` contains
your outputs, the repo contains nothing of yours.

---

## 7. Deferred observations

*(Empty at issue. The drafting pass deferred nothing: the anomalies noticed while
verifying facts — the mid-session commit `5f2c630` and a transient stale-copy test
failure — are documented in §1.4 as traps, not as defects. Reviewer: one line per
observation, no fixes, no commits, no pull requests. These are read by the owner,
who alone decides.)*
