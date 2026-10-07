# POWER MEMO v2 — detectability in IR terms (supersedes v1) · 2026-09-30

**Framing (C2):** long–short factor premia and long-only book tracking error are different units.
Detectability of an effect with annual information ratio `IR` over `T` years is
`expected t = IR·√T`; years needed at bar `b` = `(b/IR)²`. No TE-unit mixing.
**C1 applied:** tradeability = real print at entry (`volume>0`, no carry-forward); a position
untradeable at `t+1` is **carried to its next real print**; delisting exits at the last print
(no true delists occur in-corpus; a −100% sensitivity is noted, not scored).
**Window:** 59 months ≈ 4.9 years, `√T = 2.21`.

## 1. Realized local rows under C1 (re-measurement, not a discovery)

Panel as v1 (zoo filters), C1 rule applied, plus removal of rows with `fwd < −95%`
(mechanical corporate-action drops — 0.2–0.4% of rows; the corpus carries unadjusted drops per
the D-064 rights audit). 19,332 clean name-months, 50 book months:

| row | book %/yr | universe %/yr | excess | t | TE (ann.) |
|---|---|---|---|---|---|
| hi52 top-20% (no volex) | +14.73 | −5.35 | +20.08 pp | **3.91** | 10.0% |
| hi52 tercile | +8.45 | −5.35 | +13.80 pp | 3.56 | 7.7% |
| EW universe itself | −5.35 (books window) / −3.90 (57 mo) | — | — | — | — |

**Read with care — three honest flags.**
1. The old benchmark (+30.5%/yr in v1) was inflated by the exit-volume look-ahead (C1) and by
   mechanical-drop rows; corrected, the universe earns ≈ −4 to −5%/yr, consistent with XP-001's
   "EW ≈ IHSG −6.7pp". The book's own absolute return (+14.7%) is close to FINDINGS' +13.7% net.
2. t = 3.91 / 3.56 are **convention-hopped re-measurements of already-disclosed arms** (hi52 was
   inside the 92-trial census). They clear the old bars only because the benchmark bias was
   removed after the fact. They are not bankable as discoveries; they ARE the reason D-065 §2
   freezes the C1 tradeability rule going forward — any test under the frozen rule starts fresh.
3. The book-vs-EW excess rides on the universe benchmark (UNIVERSE_BENCHMARK_MEMO); vs IHSG the
   same book is ≈ +13pp/yr over a falling index — a beta/regime statement, not alpha.

## 2. Detectability table (literature IRs vs our 4.9-year window)

`expected t = IR·√4.9`; `years needed = (bar/IR)²`. XP-001 rule B (planner reference): TE
≈ 0.78%/mo (≈2.7%/yr), IR ≈ 1.6.

| effect | source | annual IR (basis) | expected t @4.9y | years @ t 1.65 | @ 2.00 | @ 2.8575 | verdict |
|---|---|---|---|---|---|---|---|
| value — IDX | LWZ 2023 · 0.37%/mo | PENDING-EXTERNAL (files absent — Task 1 not runnable) | — | — | — | — | **PENDING** `priors/external/lwz/` |
| size — IDX | LWZ · 0.28%/mo | PENDING-EXTERNAL | — | — | — | — | PENDING |
| quality — IDX | LWZ · 0.26%/mo | PENDING-EXTERNAL | — | — | — | — | PENDING |
| profitability — IDX | LWZ · 0.24%/mo | PENDING-EXTERNAL | — | — | — | — | PENDING |
| momentum — IDX | LWZ · n.s. | — (no prior) | — | — | — | — | nothing to detect |
| B/M — IDX 1990–97 | Rouwenhorst WP (verified via NotebookLM) t=1.74/8y | **0.61** | 1.36 | 7.2y | 10.6y | 21.6y | **NO** in-window |
| E/P — IDX 1990–97 | Rouwenhorst t=2.11/8y | **0.75** | 1.65 | 4.9y | 7.2y | 14.7y | **NO** at census bar; marginal at 1.65 |
| size — IDX 1990–97 | Rouwenhorst t=−0.77/8y | **−0.27** | −0.60 | never (sign contrary) | never | never | **NO** — local sign test is the only use |
| value — EM agg 1987–97 | Rouwenhorst t=3.82/11y (EW) | **1.15** | 2.55 | 2.1y | 3.0y | 6.1y | **MAYBE** — ~6y needed at census bar |
| E/P — EM agg | Rouwenhorst t=4.46/11y | **1.34** | 2.98 | 1.5y | 2.2y | 4.5y | **YES in-window** at census bar (4.5y) |
| size — EM agg | Rouwenhorst t=3.09/11y | **0.93** | 2.06 | 3.1y | 4.6y | 9.4y | **NO** at census bar |
| XP-001 rule B (vol-excl top-200 tilt) | program record | **1.6** | 3.54 | 1.1y | 1.6y | 3.2y | **YES** — already measured |

## 3. Verdict

- The only rows detectable **in-window at the census bar** are the EM-aggregate E/P prior (4.5y)
  and XP-001-B (already measured). IDX-specific single-country priors (IR 0.6–0.75) need 7–22
  years — our panel can never confirm them; local tests can only fail to reject.
- Consequence for D-065 §1 unchanged from v1: the external prior carries the weight; local
  confirmation is not a reachable standard for IDX-specific factors.
- LWZ rows activate the moment the Owner drops the paper/data in `priors/external/lwz/`
  (Task 1 then computes: per factor, mean %/mo, t, annual IR — full sample and era splits).

## 4. Evidence added 2026-09-30 (research consolidation) — both support D-065 §2's frozen-rule-going-forward stance

- **XP-001 rule B re-measured under the corrected C1 rule: IR 1.6 → 1.19, ~5.8 years needed at
  the D-064 census bar (2.8575)**, down from row 12's original 1.1y. This is a planner-record
  figure (not independently re-derived in this pass — the `forward_volex/remeasure/` scripts on
  disk cover the pre-2021 extension gate, not this specific rule-B re-measurement); recorded here
  as directed. **Consequence for §3's verdict table:** row 12 ("XP-001 rule B ... YES — already
  measured") should be read as **downgraded, not overturned** — 5.8y still clears a 4.9-year
  in-window panel less comfortably than the 1.1y figure implied, another instance of §3's own
  point 2 (convention-hopped re-measurements read more optimistic pre-correction than post).
- **NR7's local passes were look-ahead artifacts (P4-1, `fix/p4-evidence-honesty` 46656f6,
  2026-09-30).** A separate audit found `research/studies/nr7_generalization_study.py`'s
  `liquid_universe()` filtered its whole 5-year study by *today's* ADV rather than gating each
  trade at its own entry date. Corrected: T1 pooled expectancy +0.099%/trade → **−1.150%/trade**;
  the T2 chronological-CV pass (retention 0.74) → **fail** (retention −1.90); the one passing
  regime stratum (BULL, +1.44%) → **fail** (−0.35%). The DECISION was already DO-NOT-WIDEN before
  and after (T1 never cleared the bar), but the only two locally-passing signals in that study
  were a look-ahead artifact, not edge — a second, independent confirmation (after this memo's own
  hi52 finding) that convention-hopped/uncorrected local re-measurements on this corpus read
  systematically more optimistic than the frozen-rule truth. Directly supports D-065 §2's "any
  test under the frozen rule starts fresh" stance and §1's "local tests can only fail to reject."

## Method

Same panel code as v1 (month-end snapshots, zoo filters), C1 carry-to-next-real-print returns,
mechanical-drop screen at −95%, Gaussian detectability math. Computations ran as one-off heredocs
on the 2026-09-30 DB copy; the conventions above are the specification.
