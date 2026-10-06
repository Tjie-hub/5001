# HANDOFF_G0 — exit & position-management practice study (owner's sniper entry)

> **§1 and §3 below are the HISTORICAL G0 freeze — superseded by the G0-bis re-freeze in §8
> (2026-10-06, planner review, before any outcome was read). The operative freeze table and
> census are in §8. The §6 G1 runbook is unchanged.**

**Date:** 2026-10-06 · **Branch:** `research/exit-study-2026-10` (from
`origin/research/new-order-2026-09-30` @ 062999d) · **Executor:** ZCode, per
`ZCODE_BRIEF_EXIT_POSITION_STUDY_2026-10-06.md` (551dc99). **G0 is complete: predeclaration,
driver and PIT tests frozen; the counts-only census is run and committed. No returns were
computed anywhere. The executor stops here; G1 runs only after owner/planner approval.**

## 1. Freeze (sha256, sidecar `PREDECLARATION.sha256` covers all three; two-method verified)

| artifact | sha256 |
|---|---|
| `PREDECLARATION.md` | `f2baf72470f3f95d7be03b80ad397c0ad9763e3504f6f6dc00ab4652d9541f33` |
| `exit_study.py` (driver) | `7f81feeec0f4821768f2fe7ecbc451c478277614b5df593ba88b7f8d80f72183` |
| `test_pit_exit_study.py` (PIT tests) | `40163ff46e54fa5f6a1fac60cc1b9f03332455f7f616cb983ecbf14c1b034ed9` |

Also committed: `CENSUS_G0.json` (counts only) and this handoff. Any change to the three frozen
artifacts after approval invalidates the freeze and re-opens G0.

## 2. Verification state

- PIT tests: **24/24 PASS** (synthetic only) — pivot 2-session confirmation lag, plateau-once,
  zone merge/tie rules, setup truncation identity, limit/stop/target fills with gap rules,
  stop-first same-day precedence, X0/X3/X4/X5 mechanics, P1–P4 leg rules, hand-computed cost/R
  arithmetic, the eager entry state machine (supersede / fill-lock / while-locked), seeded E-RND
  determinism, era split, portfolio sizing/cap, G1 gate refusal, `evaluate()` end-to-end smoke.
- Architecture boundary tests: **3/3 PASS**.
- Census run: read-only; the only DB access is `mode=ro`; nothing written but the census JSON.

## 3. Census (owner screen ADV20 ≥ Rp 10bn; counts only)

| | E1 (2001-01..2021-09) | E2 (2021-10..2026-09) | total |
|---|---|---|---|
| E-SN setups set | 55,713 | 29,962 | 85,675 |
| E-SN fills | **2,221** | **1,419** | **3,640** |
| — expired orders | 54 | 26 | 80 |
| — superseded orders | 6,663 | 3,102 | 9,765 |
| — setups while locked | 46,775 | 25,415 | 72,190 |
| — out-of-window (post-2026-09 signals, counted not enrolled) | 0 | 77 | 77 |
| E-SN stocks with ≥1 fill | — | — | 516 |
| E-RND matches | 2,221 | 1,419 | 3,640 (unmatched 0) |
| E-BRK signals | 3,129 | 2,012 | 5,141 (550 stocks) |

Per-era counters reconcile exactly: setups = fills + expired + superseded + while-locked (E1
55,713 ✓; E2 29,962 ✓). Parity universe (top-150 ADV60) counts are within ~0.5% of these and are
in `CENSUS_G0.json`. Census dataset fingerprint at run time:
`58d35b97b2c973574692e63aacd65045a4bbd504d4055ec3a393364bcfe0017c` (max_date 2026-10-06,
1,101,820 rows; panel 6,596 sessions × 958 tickers, 2000-03-30 → 2026-10-06).

Reading the numbers: the zone-top limit fills on only ~4% of setup days (price must come back to
the zone within 20 sessions, and the stock must not already be locked); ~72k setups fire while a
stock is locked out of a prior fill. The fill population for G1 is 3,640 trades — ample for the
arm comparisons; the E-RND control matches 1:1 with zero unmatched after the era-stratified
amendment (C-3, below).

## 4. Amendments made BEFORE the freeze (disclosed; both pre-first-hash)

1. **C-3 (E-RND matching):** the first implementation constrained control days to ≥20 sessions
   after the matched signal plus 20-session spacing per stock — it matched only 1,332/3,644
   fills (E1 starved: 275). Replaced with era-stratified matching (any liquid in-era day):
   3,640/3,640 matched, 0 unmatched. The census committed here is the post-amendment run.
2. **Era tagging + cap:** era membership is by SIGNAL month (the brief defines eras on signals);
   fills/matches are tagged by their setup's month, and signals after 2026-09 (the corpus now
   reaches 2026-10-06) are counted `out_of_window` and never enrolled (77 in E2; also caps
   E-BRK, 5,141 vs 5,143 unguarded).

## 5. Conventions the brief was silent on

All declared in PREDECLARATION §12 (C-1..C-10): the 60-session arm-independent fill lock, eager
watch semantics, E-RND market-entry mechanics, E-BRK structure-stop mapping, X3/X4 without fixed
targets, cost/net%/R anchoring, `eos` force-exits, the 250-session portfolio year, simple-mean
ATR14, and the panel-edge signal guard. **Object at approval if any of these is not what you
want — after approval they are frozen.**

## 6. How G1 runs (after approval — owner/planner only)

```bash
cd <worktree on research/exit-study-2026-10>
DB_PATH="<abs>/data/walkforward.db" \
EXIT_STUDY_HIST_PKL="<abs>/docs/research_programs/P-M/forward_volex/remeasure/work/hist_pre2021.pkl" \
EXIT_STUDY_SPLITS_PKL="<abs>/docs/research_programs/P-M/data_gaps/data/split_hist.pkl" \
EXIT_STUDY_G1_APPROVED=1 <venv python> -c "..."
```

`run_g1()` refuses without the env flag. One run reads both eras, runs the 12 arms × 3
populations, and writes RESULT/VERDICT/PRACTICE_NOTE. **Estimated runtime: the census pass
(entry machinery only) took ~150–210 s; G1 adds 12 arm simulations × ~3.6k–9k trades + portfolio
engines ≈ 10–20 min total.** The recommendation rule (both-eras, t ≥ 2, DD guard) is frozen in
`recommend()`; E-BRK and E-RND are reported, never recommended.

## 7. Governance state

- Practice study: no registry/family/DECISION_LOG edits (executor files nothing; the owner files
  a short D-entry at the end if anything is adopted).
- ~/jurnal26 untouched (the sniper was re-implemented from the brief's text); production
  untouched; no service restarts; `logs/TELEGRAM_OFF` untouched; other research branches
  (`research/ml-rank-2026-10`, `research/broad-search-v2-zcode`) untouched.
- Read-only data throughout; no secrets printed.

## 8. G0-bis re-freeze (2026-10-06, planner review — BEFORE any outcome was read)

The planner review authorized ONE disclosed re-freeze before G1; no outcome has ever been read
(the G0 census is counts-only; `run_g1()` has never been executed and stays gated). Change: the
E-SN level logic now matches jurnal26 exactly — `server.py::_levels` (w=5, tol=0.04) and
`watchlist._sniper`. The four changes are listed in PREDECLARATION §3's dated G0-bis note:
11-bar pivots with a **5-session** confirmation lag; pivot highs AND lows **pooled** into one
ascending list grouped at 4% anchored on each group's lowest price; **support = the
highest-mean group below the close**; **target = the min of the lowest-mean group above the
close**, with a `target ≤ zone-top → 52-week high` guard. Everything else is as frozen (arms,
mechanics, costs, recommendation rule, C-1..C-10). E-BRK inherits the pooled target machinery
anchored on the signal close (no zone-top guard); its frozen definition is otherwise unchanged.

**Operative freeze (supersedes §1's table):**

| artifact | sha256 |
|---|---|
| `PREDECLARATION.md` | `2207597f8d97a40b3a81473e3d212e1d8c9961db9d06630dbf1230f71d643a6f` |
| `exit_study.py` (driver) | `5a05df009e6559fd5476af826b9779d2016355386b9c8a548f7694998af37df6` |
| `test_pit_exit_study.py` (PIT tests) | `4fe464c40b4dc46a4ce626bc50c5e52fb33867d803ac6b61da1ce80e6953d652` |

- PIT tests: **25/25 PASS** (new vs G0: 5-session pivot lag, pooled-group chaining anchored on
  the group's lowest price, highs+lows pooling, the jurnal26 support/target selection with the
  zone-top fallback; the setup truncation identity re-verified under the new machinery).
  Architecture boundary tests: **3/3 PASS**.
- Census regenerated — counts only, `census_kind` unchanged — run at git HEAD 8437dc2 with the
  G0-bis working-tree code that this commit freezes (same runbook/env as §6's inputs):

| owner screen (ADV20 ≥ Rp 10bn) | E1 | E2 | total |
|---|---|---|---|
| E-SN setups set | 54,359 | 29,416 | 83,775 |
| E-SN fills | **2,232** | **1,415** | **3,647** |
| — expired / superseded / while-locked | 42 / 4,553 / 47,532 | 24 / 2,079 / 25,898 | 66 / 6,632 / 73,430 |
| — out-of-window (post-2026-09, counted) | 0 | 75 | 75 |
| E-RND matches | 2,232 | 1,415 | 3,647 (unmatched 0) |
| E-BRK signals | 3,129 | 2,012 | 5,141 |

Counters reconcile exactly per era (setups = fills + expired + superseded + while-locked).
**E-BRK signal counts are IDENTICAL to G0** — expected: the E-BRK signal rule (close above the
20-day high + liquidity + lock) uses no zones; only its recorded resistance targets change.
Parity universe (top-150 ADV60): 83,672 setups → 3,631 fills, E-RND 3,631/3,631 — in
`CENSUS_G0.json`. Fingerprint at run time `f42275e3…` (max_date 2026-10-06, 1,101,826 rows) —
**+6 rows vs the G0 fingerprint** (the live DB grows as bars finalize; disclosed per
PREDECLARATION §2; expect further drift at G1). Fill rate ≈ 4.35%.

- The G1 gate is unchanged: `EXIT_STUDY_G1_APPROVED=1` + the §6 runbook. **G1 remains NOT
  run.** The executor stops here, as before.
