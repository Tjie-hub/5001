# ZCODE REVIEW V2 — FINDINGS (executed 2026-09-28)

**Reviewer:** main-session fallback (cold subagent backend unavailable — model-not-found,
twice; the 2026-09-21 owner-accepted precedent applied and is recorded here as the review's
independence deficit: the reviewer shares session context with the program, though not
authorship of the claims under review, which pre-date this session).
**Brief:** `docs/research_programs/P-M/ZCODE_FORWARD_REGIME_REVIEW_V2.md` (e47955c). Contract
honored: read-only, all writes under `/tmp/frz_review/`, no pytest, `run_formation.py` never
executed, `git status --short` byte-identical before/after.

**Headline.** One systemic finding (F-1): **the frozen evidence chain cannot regenerate its own
inputs.** Section 6's recipe names build drivers (`t1.py`, `t2.py`) that exist neither in
`forward_regime/scripts/` nor in `SHA256SUMS.txt`; the forward-window columns (`f5, f20, m5, m20,
bad20`) consumed by every pattern arm and by `zvguard.py` are produced by no script in either
frozen manifest; and the post-opening execution audit behind PROTOCOL limitation 9 (C-2's
concentration figures) has no staged script. Nothing recorded is contradicted — every number that
could be re-derived from frozen scripts came out within documented forward drift — but C-2
(figures), C-3, C-4 and C-5 are **NOT TESTED as-frozen** for lack of their producers, and C-1's
exact-freeze reproduction is likewise blocked. Recommendations are the owner's alone (§1.4.3).

## Per-claim verdicts

- **C-1 — STANDS (as the claim about what `audit2.py` computes), with two recorded qualifiers.**
  Reproduction on current data (`audit2.py`, drift to 2026-09-25: 7,287 trades vs 7,194 claimed):
  D/EX-2025 **+1.22%, t 3.84** vs claimed +1.26/3.90; A/EX-2025 **+0.97%, t 2.98** vs claimed
  +0.928/2.83 — consistent with appended sessions, `min(date)` unchanged (extract.log:
  1,093,873 rows, 959 tickers, 2021-07-05 → 2026-09-25 vs fingerprint 1,087,436 @2026-09-16).
  Qualifier 1: exact-freeze reproduction is **blocked by F-1** — this reviewer's reconstruction
  driver produced 7,523 trades at the 09-16 cutoff (more than the full-sample run), proving the
  reconstruction ≠ the lost driver; that attempt is discarded as invalid per §3 and recorded as
  the finding. Qualifier 2 (already on record): D-057's overlap-robust re-reading puts the
  headline's robust t at **1.5–1.8** — the t 3.90 is the overlapping-hold estimator
  (`AUDIT_2026-09-24_RESULT_VALIDITY.md`, rules check R-1).
- **C-2 — NOT TESTED (the concentration figures).** `exit3.py`/`exit2.py`/`exit.py` reproduce the
  by-exit-rule tables (atr3 ALL +2.27%, t 6.57; six rules × six years) but the limitation-9
  figures (top 1% of 7,194 trades carrying 85%; 237 cap-exits at +45.93%) have **no frozen
  producer** — the post-opening execution audit was never staged. The live question (is t-based
  inference valid on that tail?) retains its recorded current-repo answer in D-057's robust
  estimators.
- **C-3 — NOT TESTED (as-frozen).** `patterns.py` and `wedge2.py` crash on missing `f5/f20/m20`
  columns (`AttributeError`, logs in `/tmp/frz_review/ps_*.log`); `sweep.py` scans all 752
  tickers with the production detector then dies at aggregation on `KeyError: 'f5'`.
  Independently, the claim as stated is already amended on the record: D-057 withdrew "every
  mean-reversion pattern is significantly negative" as stated (failed breakdown and falling
  wedges survive gross vs the EW book at h5/h20; failed breakout is null — its anti-edge was the
  cost charging error R-2).
- **C-4 — NOT TESTED (as-frozen).** `why.py`/`brpt_all.py` crash on the same missing columns.
- **C-5 — NOT TESTED (as-frozen).** `zvguard.py` requires `f20/m20/bad20` (`AttributeError`:
  no attribute `f20`); no frozen script produces them. The 0.951%/4.778% shares and the
  0.78/0.85/0.83/0.80 guard-variant figures were not re-derived.
- **C-6 — STANDS.** `regime.py`/`regime_perf.py` reproduce exactly: BULL **9 episodes / 98
  sessions**, BEAR 13/145, SIDEWAYS 23/950; `regime_config.yaml` min_n = 100 across 12 cells.
  The brief's live question (episodes vs sessions) is answered arithmetically: even on the
  sessions reading BULL has 98 < 100 — infeasible by two sessions; on episodes it is hopeless.
  (Observation, not a refutation: the sessions reading makes the margin 2, so a longer corpus
  flips this claim's first cell.)
- **C-7 — STANDS (within recorded drift).** `table27.py`: 6,515 onset trades with full 3-tier
  state; 27-state table reproduced; score ladder ex-2025 net **−6.79 / −4.21 / −0.70 / +0.63 /
  +1.11** vs claimed −6.79/−4.21/−1.10/+0.62/+1.11 (drift deltas ≤ 0.40 on scores −1/0); **score
  +2 inverts ex-2025 at −4.43 net, exactly as claimed**. The post-hoc-collapse concern (27 cells
  searched before the score collapse) remains a design critique carried by LIM-7's multiplicity
  disclosure, not a numeric refutation.
- **C-8 — STANDS (within recorded drift).** Dated states **1,104** (2022-02-07 → 2026-09-23) vs
  claimed 1,099 @09-15 (+5 sessions of drift); **ALL-THREE-BULL = 0**; **LONG&MID both BULL = 1**;
  ALL-THREE-BEAR = 35. The SHORT-tier parameter-fork question is a design critique
  (`fast_regime` docstring concedes research-variant status); no differing number produced.
- **C-9 — STANDS (all four fronts executed).**
  1. Provenance: working-tree `PROTOCOL.md` = `4063752e…` ✓; blob at `2e416f6` = `6e7e1a7b…` ✓;
     cumulative diff `2e416f6..HEAD` = **+88/−0, zero deletions** (the §6 "+89/−1" instruction is
     stale — §2.1's drafting-note correction is the true state).
  2. Content: all 88 added lines are limitation 9–10 prose and the two regime-attribute notes
     with their "never filters, gates or sizes anything" language; no appended text redefines any
     §2/§3 term.
  3. Code (`run_formation.py`): `detect_regime` appears only in `ihsg_regimes`/`weekly_regimes`,
     consumed solely as recorded attributes (lines 156–157); entries are onset transitions
     `up & ~prev(up) & liq` on t-1 state (line 127 — §5 self-correction #5 confirmed);
     exits are the 3×ATR trail and 60-cap, never regime-aware; a None regime is recorded
     fail-soft (`.get`, never raises, never drops); missing IHSG **prices** dropping a trade
     (lines 143–145) is the pre-existing `market_return` spec behavior, distinct from the
     amendments. The frozen blob's §2 exit wording ("close < highest high since entry − 3×ATR14,
     60-session cap") matches the implementation, including peak-includes-own-bar-high and
     own-bar ATR14; amendments added nothing to exit wording.
  4. No look-ahead: `weekly_at` selects the last W-FRI bar strictly before entry (arithmetic
     identity re-verified; the live ledger's first trade MARK entered Wednesday 2026-09-17 and
     carries weekly regime from the week closing 2026-09-11 — consistent).

## Governance claims

- **G-1 — STANDS.** `ledger_001_superseded.json` holds **0 trades**, superseded 2026-09-17T06:53:30Z
  → the re-spec could not be outcome-driven; the owner-override flag is present (PROTOCOL line
  319). Retention over re-registration remains a governance judgment, flagged as such.
- **G-2 — STANDS.** `HYPOTHESIS_REGISTRY.md` shows no pre-existing price-feature family;
  FWD-PM-VOLEX-001 is an unregistered prospective record holding no slot. Widening-permitted /
  narrowing-forbidden is recorded.
- **G-3 — STANDS.** `BOOK_OVERLAY_POLICY.md` binding rule: the endpoint is computed on **every**
  signal; the overlay never filters the ledger nor alters the endpoint — consistent with the
  `run_formation.py` trace (no overlay in the trade builder).
- **G-4 — STANDS.** `FAILURE_REGISTRY.md` (N=6) contains no pattern-scan entry; the scan's
  multiplicity is carried by the HYP-PM-0012 registration (Bonferroni-18, registry {R1} row).
  Defensible under the registry's registered-hypotheses-only scope.

## §5 self-corrections — verification one-liners

1. Verified: zero-volume carry-forward → 001→002 supersession (ledger 001: 0 trades; NZ_MIN=18
   guard in `run_formation.py`). 2. Verified: `PATTERN_SCAN_2026-09-17.md` line 154 — resistance
   breakout +0.66 → **−0.30** (t −2.67) with the entry-timing note. 3–4. Present in the scan doc;
   not independently re-executed (their scripts are outside §6's frozen set). 5. **Verified in
   code**: `starts = up & ~prev(up)` (onset, not level). 6. **Not located** in any artifact
   (3.37×) — one-line gap. 7–11. Recorded claims about the originating session's reasoning; the
   artifacts carry the corrected conclusions; no contradicting evidence found.

## §7 deferred observations

1. F-1 (systemic): lost build drivers (`t1.py`, `t2.py`); `f*/m*/bad20` producers absent;
   limitation-9 audit script absent; §6's loop also swallows failures ("FAILED rc=2" was
   file-not-found for `t1.py`).
2. §6 retains the stale "+89/−1" instruction despite §2.1's correction — a brief-internal
   inconsistency that cost one tool-round.
3. Corpus drift is consistent with recorded events: +6,437 final-bar rows (to 09-25) and +136
   rows dated ≤ 09-16 vs the 09-18 fingerprint — the latter matches the recorded 09-23
   provisional-bar repair (2,488 bars across 09-16..22) and is repair-provenance, not silent
   mutation.
4. Reviewer's own discarded artifact, per §3 honesty: the /tmp reconstruction driver
   (`audit2_cut.py`) produced 7,523 trades at cutoff vs 7,287 full-sample — impossible for a
   subset, therefore the reconstruction is not the frozen driver and its numbers are evidence of
   nothing except F-1.
5. `git status` hygiene: start snapshot = end snapshot (16 untracked lines, byte-identical);
   the repository contains nothing of the reviewer's.

**Success bar (§3):** three genuine refutation attempts executed to the bar — C-9 four-front
attack (claim survived), C-1 exact-freeze reproduction attempt (blocked, produced F-1), C-6/C-7
sessions-vs-episodes and post-hoc-collapse attacks (claim survived, margin-2 observation recorded).
