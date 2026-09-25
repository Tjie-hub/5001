# Result-validity audit — every executed test, and the rules they were judged by

**Date:** 2026-09-24 · **Status:** RECORDED (diagnostic, Owner-requested: "perluas audit … cek rule nya
dulu, apakah sudah benar") · **Changes nothing frozen.** No protocol, ledger, registry entry or decision
rule is edited by this document.

**Updated 2026-09-24 06:38 UTC** with the DB run of `validity_audit.py`
(`P-M/validity_audit/RESULT_20260924T063842Z.json`). The figures are in §7. The verdicts in §0–§2
are revised in place. **One correction to the first version:** §1.1 printed FADE h20 vs IHSG
calendar-time t as "—". It is −3.13. The overlap audit reported it under the net row, and the
calendar-time portfolio is gross by construction.

**Inputs:**
- `P-M/overlap_audit/overlap_audit.py`, run on the Owner's DB on 2026-09-24. The FADE and T1
  reproductions matched their registrations.
- A code read of every script behind a recorded number (§6).
- Synthetic demonstrations: `tests/test_overlap_audit.py` and `tests/test_validity_audit.py`.
- `P-M/validity_audit/validity_audit.py`, run on the DB at 06:38 UTC (§3, §7). It settles what code
  reading cannot settle.

---

## 0. Answer

1. **Every negative verdict stands.** This covers:
   - HYP-PM-0001, -0003, -0004, -0005, -0006 and -0009;
   - HYP-PA-0001 (pooled);
   - BROKER-001, NR7-P0, LIQUIDITY-SWEEP, VOLEX-SN and RC-0001.

   Each was reached with a standard error that was, if anything, too small. Correct inference only
   widens the intervals, so a null stays a null. The only negative verdict that read defective input is
   VOLEX-SN, which is already recorded in D-056. Its affected months carried the *higher* mean.
2. **The positive in-sample numbers that the forward tests and policies cite are not valid at their
   quoted size.** One rule flaw is shared by all of them: a t-statistic clustered on entry date while
   the holding windows overlap. On a simulated null, that t rejects 39% of the time at a nominal 5%.
   - **T1 (REGIME-002 reference), ex-2025:** +0.93%/trade, registered t 2.83. Robust t is **1.5–1.8**.
     **Not established in-sample.**
     Removing the look-ahead guard puts back 33 ex-2025 trades the guard had dropped: +1.06%, robust
     t **1.8–2.2**. That is still borderline (§7-E).
   - **FADE against IHSG, h20:** the net t of −5.7 hides a gross −0.86%. The robust estimators
     **disagree**: month −1.65, DK −1.86 to −1.98, calendar-time −3.13. **Mixed.**
   - **FADE against the EW-book:** h20 gross −0.89%, robust t −3.6 to −4.4; h5 −0.45%, robust t −3.7
     to −4.5. **Survives.** Removing the guard, removing corporate-action windows, and guarding the
     benchmark symmetrically each move it by 0.01 percentage point or less.
   - **The pattern scan's "every mean-reversion pattern is significantly negative"** is withdrawn as
     stated. Its endpoint scores a no-information pattern at −0.60% with an inflated t (§1.2).
     - **Re-measured gross (§7-F), three arms survive against the EW-book at both h5 and h20:** failed
       breakdown, falling wedge + break, and falling wedge.
     - **Failed breakout:** the scan's anti-edge was the cost; gross, the arm is null.
     - **Resistance breakout:** significant trade-weighted, **not** day-weighted (calendar t 0.9–1.3).
       The effect sits on crowded signal days.
3. **Two frozen decision rules are miscalibrated.**
   - **REGIME-002.** The PASS rule's real false-pass rate is **≈13–17%**, not 5%. Detecting the planning
     effect needs **≈6–9 years**, not 36 months.
   - **FADE-001.** The PROMOTE rule promotes a pattern with **no information at all** with probability
     **≈3–14%**. A t < −3 rule should give about 0.1%.

   Fixing either rule is an Owner call (§4). Nothing is changed here.
4. **Data (measured, §7).**
   - **Survivorship is confirmed.** 0 of 958 names stop trading before the end of the corpus, so no
     delisted name is present.
   - **Unadjusted rights, bonus and split ex-dates exist, but they are few:**
     - rights-issue ex-dates fall more than 10% at 10× the base rate, about 10 events in 5 years;
     - **3 of 81 DB splits are still gapped**, now repaired in the Rule Card loader.
     - Measured effect: FADE unchanged; T1 −0.06%/trade.
   - **The contamination guard** is immaterial for FADE. For T1 it removed 40 **winners**, mean excess
     +26%, 36 of them only because an already-adjusted split fell in the window. The look-ahead made T1
     look worse, not better.
   - **The DB has no holiday rows (ZV-2 = 0).**

---

## 1. Rules check — is each rule right?

| # | Rule, as used | Used by | Verdict | Evidence |
|---|---|---|---|---|
| R-1 | t clustered on **entry date**, overlapping multi-session holds | T1/REGIME-002, FADE-001, pattern scan, filter table F0–F5, SIDEWAYS S/R, T1 limitation-10 table | **WRONG** | Simulated null: rejects 39% (month cluster 11%, DK 12%, calendar-time 6%). Real data: t shrinks ×0.44–0.78 (§1.1) |
| R-2 | 0.60% round trip charged to the **signal leg only**, gross benchmark, null = 0 | FADE-001, pattern scan, SIDEWAYS S/R | **WRONG for avoid/relative claims** (right for a long strategy's own P&L, i.e. T1) | A no-information pattern scores −0.60%. Test: `test_overlap_audit.py::test_net_endpoint_scores_noise_as_anti_edge` (§1.2) |
| R-3 | Drop a trade if **any session in its holding window** has \|ret\| > 35% or a split | T1, FADE, pattern scan (`panel.py` `bad`/`badh`) | **LOOK-AHEAD**. Measured (§7-E): immaterial for FADE; for T1 it dropped 40 winners (conservative) | The drop uses the future window. FADE applies it to the signal leg and not to its EW-book (§1.3) |
| R-4 | Newey-West, Bartlett, lag = k on a daily series of k-day returns | G1 (C2, C3), C7 | **Slightly lenient** | Bartlett at L = k captures ≈ 73% of the variance of an MA(k−1) overlap at k = 5 (70% at k = 10), so t is ×1.17–1.20 too large. Nulls are unaffected |
| R-5 | i.i.d. bootstrap CI on overlapping k = 7 returns | HYP-PM-0003 | **WRONG** (CI too narrow) | Disclosed in the registration (`dependence_treatment`). The result was a null, so it stands |
| R-6 | Event study, market model, CR1 by review date plus wild cluster bootstrap | HYP-PA-0001 | **RIGHT** (13 clusters is fragile, and that is disclosed) | Common review-date shocks are exactly what the clusters absorb |
| R-7 | Monthly formation, non-overlapping hold, t on the monthly series | VOLEX-001, VOLEX-SN, Rule Card engine | **RIGHT** | One observation per month and no overlap. `research/rulecard` uses NW on that series |
| R-8 | Entry fill | FADE and scan §7: next open (right). T1: close of the onset session, with state from t−1 (right). G1/C7: close(t) with flow dated t, which is published after the close (**not executable**; irrelevant for nulls). HYP-PM-0009: close(t+1) (right). Extended panel: close(t) (wrong; already superseded) | mixed | file:line in §6 |
| R-9 | Benchmark IHSG only | T1 primary, scan | **Biased** (flatters long signals by ≈ +0.35%/20d; hides that bias for anti-edges) | FADE and the Rule Card use the EW liquid book. T1 limitation 10 reports both |
| R-10 | Power and decision horizon computed from the R-1 standard error | REGIME-002 §3, FADE-001 §3.1 | **WRONG** | §1.4 |
| R-11 | Survivorship: corpus = names listed in 2026-09 | every study on the DB | **Present, confirmed**: 0 of 958 names stop trading (§7-B). Direction: optimistic for long T1, probably conservative for FADE | HYP-PM-0010 limitation 1; `checks.py` docstring; §3-B measures it |
| R-12 | Prices split-adjusted only. Rights, bonus and stock dividends unadjusted | every study on the DB | **Measured (§7-C/D): small.** Rights ex-dates < −10% at 6.9% vs a 0.67% base; bonus 9.8%; 3 of 81 DB splits gapped (now repaired in the Rule Card loader). Dividends are unadjusted by design (price return, not total return) | `data/adjustments.py:1-20` (split basis, gap-verified); no loader reads `corporate_action_events`. §3-C/D measure it |
| R-13 | Walk-forward `wf_edge`: fixed parameters; the 12-month "train" is only an indicator warm-up tail; per-ticker, per-strategy pooled expectancy with ≥ 20 trades, no inference, best per ticker | legacy production channel (D-031 Option C) | **Not evidence** | `research/walkforward_multi.py:129-178, 253-300`; `engine/wf_edge.py:17, 190-225`. Pattern scan §5: per-ticker 20d excess spans −9.2% to +4.2% (10th–90th percentile), so 20 trades per ticker cannot rank strategies |
| R-14 | Rule Card SPL-1: INVALID if more than 0.5% of holdings contain a > 35% session | `research/rulecard` | **Was too lax; fixed today** | DATA-1 contamination was 0.38% and would have passed. Now ≤ 0.1%, and any single session ≥ 100% fails (2 regression tests) |

### 1.1 Overlap (R-1), the quantified case

The registered estimator is `cluster_t(x, entry_date)` in `fade_failed_breakdown.py:122-139`. It is
reused verbatim by `panel.py`, `patterns.py` and `filt.py`. It treats trades entered on consecutive days
as independent clusters, although their 20- to 60-session windows share most of their days.

**Overlap audit, real data, 2026-09-24:**

| series | mean | registered t | month t | DK t | calendar t | shrink |
|---|---|---|---|---|---|---|
| T1 FULL | +2.2%/trade | 6.19 | 3.44 | 2.73 (L60) | 2.69 | 0.44–0.56 |
| **T1 ex-2025** (planning basis) | +0.93% | 2.70 | 1.84 | 1.55 | 1.71 | 0.57–0.68 |
| FADE h20 vs IHSG, GROSS | −0.86% | −3.34 | −1.65 | −1.86 | −3.13 | 0.49–0.94 |
| **FADE h20 vs EW-book, GROSS** | −0.89% | −4.96 | −3.56 | −3.85 | −4.42 | 0.72–0.89 |
| FADE h20 vs IHSG ex-2025, GROSS | −1.28% | — | −2.23 | −2.55 | — | — |
| **FADE h5 vs EW-book, GROSS** | −0.45% | — | −3.71 | −4.33 | −4.48 | — |

- The IHSG legs shrink more than the EW-book legs. IHSG is a single common series across all
  overlapping trades, and that is exactly the correlation entry-date clustering ignores.
- The protocol's T1 figure is t 2.83. The audit's 2.70 uses data to 2026-09-16.

### 1.2 One-leg cost (R-2) plus overlap: what a pattern with no information scores

**Algebra.** The registered endpoint is `stock − 0.006 − benchmark`. With no information, E[stock −
benchmark] = 0, so the endpoint's expectation is −0.60%. The FADE docstring also records that the liquid
EW book beats IHSG by ≈ +0.35%/20d, so against IHSG the expectation is ≈ −0.25%.

**Synthetic demonstration.**
- **Setup.** `tests/test_validity_audit.py` corpus: 40 random-walk names, 2 years, **no effect planted**,
  one seed. This is an illustration, not an estimate.
- **Method.** The pattern-scan arms re-run through `validity_audit.py` §F.
- **Result.** The registered net endpoint gives every arm t between −1.9 and **−9.7**. Gross with
  calendar-time t, all arms sit between −1.6 and +1.5.
- **Also shown.** With cost removed, entry-date clustering alone gives the falling-wedge arm (h20)
  t −4.3 on this noise. Its calendar-time t is −1.0.

**Consequence.** The scan's column of t −3 to −12 cannot be read as anti-edges. Section F of the DB
script re-measures the arms gross, with calendar-time and DK t.

### 1.3 The holding-window contamination guard (R-3)

`panel.py:27, 35`, `fade_failed_breakdown.py:100, 112-113`, `filt.py` `bad[i+1:j+1]` and
`t1_trades` all drop a trade when **any session inside its future holding window** moves more than 35%
or carries a split.

**What a > 35% session is.** No IDX band allows a one-session move beyond 35%
(`research/rulecard/engine.py:37`). Such a session is therefore one of three things:
- an unadjusted corporate action;
- a post-suspension print;
- a data error.

**Why it is look-ahead.** The rule decides inclusion on what happens after entry.

**Bias direction.**
- If the dropped windows hold real crashes, such as reopenings after a suspension, the drop flatters
  T1 (it removes real losers) and understates FADE.
- If they hold fake gaps, the drop cleans the data.
- **FADE asymmetry.** The EW-book benchmark (`fade_failed_breakdown.py:148`) is *not* guarded. Names
  with fake gaps stay in the benchmark and are removed from the signal leg.

**Magnitude.** Unknown from code. §3-E measures it:
- the dropped count and each dropped trade's outcome;
- the up/down direction of each triggering move;
- the FADE contrast against a symmetric-guard EW-book;
- both FADE and T1 with every rights, bonus, split or warrant window removed.

**The correct construction** is ex-ante: repair the data, or use the Rule Card's stale-exit convention.
Never filter on the holding window (the D-053 lesson, `REMEASUREMENT_RESULT` §2.4).

### 1.4 What R-1 and R-10 do to the two frozen decision rules

**Normal approximation.** Robust SE = registered SE ÷ observed shrink. Numbers are for the in-sample
dependence structure carried forward.

**FWD-PM-REGIME-002.**
- **PASS rule** (PROTOCOL §3): mean ≥ +0.46% **and** entry-date t > 1.65 at 36 months (registered SE
  0.363%).
- **Robust SE at 36 months:** 0.53–0.63%.

| effect assumed | P(PASS) under the frozen rule |
|---|---|
| true effect 0 (false PASS; nominal 5%) | **13–17%** |
| true effect +0.928% (planning) | 70–73% |

- **Horizon.** Needed for 80% power at +0.928% with robust SE: **73–103 months** (month-cluster to DK),
  against the 36 planned.
- **Reading.** A 36-month PASS would carry a likelihood ratio of about 5, not the 16 the rule implies.
  The test is not useless, but it is weaker than its protocol states. The 2025-dominated full sample is
  not the basis (PROTOCOL §3).

**FWD-PM-FADE-001.**
- **PROMOTE rule at 18 months:** net-of-cost t < −3.0 against both IHSG and the EW-book, entry-date SE.
- **Setup.** About 348 signal dates. Robust SEs are scaled from the full-sample audit.
- **Result.** A pattern with **no information** promotes with probability **≈ 3–14%**:
  - the range spans a benchmark correlation of 0.5–0.85 and a liquid-over-IHSG drift of 0 to +0.35%;
  - the low end (≈3–5%) holds if calendar-time is the right SE for the IHSG leg (shrink 0.94) rather
    than month or DK (0.49–0.59);
  - each leg alone passes 17–20% of the time;
  - the intended rate is about 0.1%.
- **Cause.** Both flaws push the same way, toward PROMOTE:
  - the one-leg cost gives the null a head start of −0.60%;
  - the entry-date SE inflates |t|.

### 1.5 The Rule Card framework (`research/rulecard/`)

| aspect | verdict | note |
|---|---|---|
| Estimand, inference, noise floor | **right** | monthly non-overlapping spreads, NW t on the monthly series, random-bucket floor that never calls `signal()`; next-open entry, stale exits, no holding-window filter |
| SPL-1 split band | **was too lax; fixed** | §1 R-14. `engine.run_months` now records `max_abs_move_in_hold` |
| DATA-3 (rights, bonus) and DB splits | **split repair done; rights/bonus small** (§7) | No check reads `corporate_action_events`. If §3-D shows material ex-date drops, a gap-verified rights/bonus adjustment must go in `load_panel()` **before** the next card is frozen |
| Survivorship | declared, not measured | §3-B answers whether delisted names exist at all |

---

## 2. Result register

**Verdict key:**
- **TRUSTED-NEGATIVE:** a null or failure that stays one under every correction found.
- **TRUSTED:** stands as recorded.
- **NOT ESTABLISHED:** a positive in-sample reading that does not clear a 5% two-sided bar once
  inference is corrected.
- **SURVIVES:** clears it under all three robust estimators, pending §3-E.
- **AT-RISK:** positive, and not yet re-measured.
- **INVALID:** the input or construction is defective.

| # | Result | Recorded | Data | Rule flaws | Fixing them makes it | Verdict |
|---|---|---|---|---|---|---|
| 1 | HYP-PM-0001 (EXP-PM-0001) | FAILED F2: gross −0.0008%, t −0.35 | `stockbit_flow_bars` (intraday) | R-5 type (i.i.d. deflation ladder) | a wider CI | **TRUSTED-NEGATIVE** |
| 2 | HYP-PM-0003 (EXP-PM-0003) | FAILED F2 → INVALID-DATA (predictor degenerate, ID-1) | Dataset A | R-5 | a wider CI | **TRUSTED-NEGATIVE** (substantively untested, D-049) |
| 3 | BROKER-001 / BFI-001 | primary INVALID-DATA; secondaries NOT CONFIRMED (CONC t −2.65, Holm 0.097) | Dataset A | not re-read | — | **stands** (not re-audited) |
| 4 | HYP-PM-0004 (C2), G1 Run 1 | INVALID-governance; Holm p 1.0 | Dataset B + DB, 2025-01 → 2026-08 | R-4, R-8 (close(t) entry) | weaker | **TRUSTED-NEGATIVE** |
| 5 | HYP-PM-0005 (C3) | NOT CONFIRMED: k=5 +5.8 bp, t 0.32 | same | R-4, R-8 | weaker | **TRUSTED-NEGATIVE** |
| 6 | HYP-PM-0006 (C7) | NOT CONFIRMED: Holm p 0.61 | same | R-4, R-8 | weaker | **TRUSTED-NEGATIVE** |
| 7 | HYP-PM-0009 (EXP-PM-0009/R2) | FAILED F2: +0.034%, t 0.11 | v004 cohort | none (k = 1, close(t+1) entry, NW lag 5) | — | **TRUSTED-NEGATIVE** (no power claim, D-050) |
| 8 | HYP-PM-0009 R1 | INVALID (exit-index defect) | — | correctly voided | — | **TRUSTED** (void) |
| 9 | HYP-PA-0001 pooled (EXP-PA-0001) | FAILED F2: +0.73%, t 1.45 (13 clusters, WCB agrees); DELETE net −0.85% | DB close prints, 13 review dates | R-6 is right | — | **TRUSTED-NEGATIVE** |
| 10 | HYP-PA-0001 ADD-side | +1.89%, CI [+0.67, +3.11], WCB p 0.013, 11 of 13 dates | same | none. Gross only, not capturable (C-4) | — | **TRUSTED as a description**; not an edge |
| 11 | NR7-P0 | FALSIFIED → SHADOW (D-029) | `wf_edge` walk-forward | R-13 | — | **TRUSTED-NEGATIVE** |
| 12 | LIQUIDITY-SWEEP (strategy) | falsified | `wf_edge` | R-13 | — | **TRUSTED-NEGATIVE** |
| 13 | T1 reference FULL (HYP-PM-0010) | +2.17%, t 6.29 | DB 2021-07 → 2026-09 | R-1, R-3, R-9, R-11 | smaller: robust t 2.7–3.4, 2025-driven | **AT-RISK** (not the planning basis) |
| 14 | **T1 ex-2025** (planning basis) | +0.928%, t 2.83 | same | R-1, R-3 (removed winners), R-11 (optimistic) | registered set: robust t 1.5–1.8. With the guard's 33 trades back: +1.06%, robust t 1.8–2.2 | **NOT ESTABLISHED (borderline)** |
| 15 | T1 limitation 10 (next-open +0.85%, t 2.60; vs EW-book +1.26%, t 3.90) | — | same | R-1 | shrink ≈ 0.6 | **AT-RISK** (the EW-book row may survive; not yet measured) |
| 16 | Filter table F0–F5 (BOOK_OVERLAY §5) | F2/F3/F5 rejected; F1/F4 "do not destroy the edge" | same | R-1 | the rejections get stronger; F4's t 3.36 falls to ≈ 1.9 | **rejections TRUSTED-NEGATIVE**; nothing positive claimed |
| 17 | REGIME-002 pre-registration overlays (wider stops, SIDEWAYS S/R, IHSG-downtrend gate) | rejected; S/R "t −4.8 to −7.3" | same | R-1, R-2 | the rejections stand; S/R is **not** "significantly negative" | **TRUSTED-NEGATIVE** as rejections only |
| 18 | TREND-001 v1–v4 | superseded by REGIME-001/002 | — | not re-read | — | superseded |
| 19 | **FADE-001 reference vs IHSG h20** (HYP-PM-0012) | net −1.46%, t −5.6 | DB 2021 → 2026-07 | R-1, R-2, R-3 (immaterial, §7-E) | gross −0.86%; month −1.65, DK −1.86, calendar −3.13 | **MIXED** (trade-weighted no, day-weighted yes) |
| 20 | **FADE-001 vs EW-book h20** | net −1.47%, t −8.20 | same | R-1, R-2, R-3 (asymmetric guard) | gross −0.89%, robust t −3.6 to −4.4 | **SURVIVES** (pending §3-E) |
| 21 | FADE h5 vs EW-book | net −1.05%, t −11.9 | same | same | gross −0.45%, robust t −3.7 to −4.5 | **SURVIVES** (pending §3-E) |
| 22 | FADE ex-2025 vs IHSG h20 | net −1.88%, t −6.80 | same | same | gross −1.28%, robust t −2.2 to −2.6 | **weak** |
| 23 | Pattern scan arms and "every mean-reversion pattern is negative" | t −2.6 to −12.3 | DB 2021-07 → 2026-09 | R-1, R-2, R-8 (close fill; §7 self-audit), R-9 | re-measured gross, next-open (§7-F) | **Withdrawn as stated.** Failed breakdown, falling wedge + break and falling wedge **survive vs the EW-book** (h5 and h20). Failed breakout is **null** (the cost was the effect). Resistance breakout is trade-weighted only. Liquidity sweep, wedge pop and EP-daily are **not re-measured** (they need production detectors) |
| 24 | Pattern scan §2 flow filters | net, entry-date | same | R-1, R-2 | — | moot (no claim) |
| 25 | Pattern scan §3 Episodic Pivot faithful re-test | t 1.30 (null) | 1-minute bars | R-1 | weaker | **TRUSTED-NEGATIVE** |
| 26 | Pattern scan §5: per-ticker dispersion (BRPT) | 35% of names positive; 10th–90th percentile −9.2% / +4.2% | same | no inference used | — | **TRUSTED** |
| 27 | Pattern scan §7: resistance-breakout h5 was a close-fill artifact | +0.66% → −0.11% | same | — | — | **TRUSTED** |
| 28 | VOLEX-001 backtest reference | +0.394%/mo, t 3.74 → ex-ante month-end **+0.30%, t 2.59** (2026-09-23 audit) | DB 2022-07 → 2026-08 | R-11, R-12. Parkinson uses only intraday high/low, so overnight gaps don't touch the signal, but the returns carry DATA-3 | survivorship probably conservative here; DATA-3 direction depends on who issues rights | **AT-RISK (moderate)**; the forward test is valid as frozen |
| 29 | VOLEX-SN re-measurement (D-053) | REFUSED at G1: t 1.39 | pre-2021 backfill + DB | DATA-1, ZV-2 (D-056) | affected months had the higher mean | **TRUSTED-NEGATIVE**; not re-run (D-053) |
| 30 | EXTENDED_PANEL 2026-09-19 volatility overlay "out-of-sample" (pre-2021 t 3.48–4.22) | superseded 09-23 (z_fwd look-ahead, close(t) entry) | pre-2021 backfill via the same `split_hist` double adjustment + holiday rows + glitches | R-3-class look-ahead, DATA-1, ZV-2, DATA-2 | — | **INVALID** |
| 31 | EXTENDED_PANEL §4 dividend yield (pre-2021 t 2.53) | "unresolved" | same | same | — | **INVALID** |
| 32 | BOOK_OVERLAY §3 book numbers (CAGR 16.6 → 19.6%, Sharpe 0.60 → 0.76) and §4 prior ("high-vol decile −2.93%/mo vs +0.78%") | operating rule, not evidence | DB 2021–26 | in-sample book; the prior's source was not found in the files read | — | **UNVERIFIED**; the prior should cite VOLEX-001's audited +0.30% |
| 33 | RC-0001-MAX | NOT TESTED, underpowered (floor 6.33, 245 months) | corrected backfill + DB | none (noise floor, no signal call) | — | **TRUSTED** |
| 34 | Production `wf_edge` / NR7_BULL SHADOW / Trend Following Breakout (D-031 Option C) | legacy scan authorisation | DB | R-13 | — | **NOT EVIDENCE**; zero APPROVED registry entries |
| 35 | Overlap audit itself | T1 and FADE numbers above | DB ≤ 2026-09-16 | self-test: calendar 6%, month 11%, DK(L20) 12% at a nominal 5% | — | **TRUSTED**, and month/DK are themselves slightly lenient, so they are upper bounds on \|t\| |

---

## 3. What `P-M/validity_audit/validity_audit.py` settles on the DB

    venv/bin/python -m pytest -q tests/test_validity_audit.py
    venv/bin/python docs/research_programs/P-M/validity_audit/validity_audit.py

| § | Question | Changes which verdict |
|---|---|---|
| A | is_final share, weekend rows, partial sessions, IHSG gaps, **ZV-2 holiday rows in the DB** | all DB studies (if holiday rows exist, the ZV-1/ZV-2 guards were load-bearing everywhere) |
| B | Does the corpus hold **any** name that stopped trading? | R-11 for every study; T1 (optimistic), FADE (conservative) |
| C | Every \|ret\| > 25% session classified: split, stocksplit, bonus, rightissue, warrant, dividend, suspension, after zero volume, unmatched. Plus DB split continuity | R-3 and R-12: what the guard was removing |
| D | Ex-date return per `corporate_action_events.action_type` against ordinary sessions; raw_json key census | **DATA-3**: whether rights and bonus need an adjustment factor, and which fields hold the ratio and price |
| E | FADE and T1: trades the guard dropped (count, outcome, up/down trigger); FADE against a symmetric-guard EW-book; both with CA windows removed | rows 14, 19–22 |
| F | Pattern-scan arms P2, P3a, P3b, P4, P4b: gross, next-open, both benchmarks, h5/h20, with entry-date, month, DK and calendar t | row 23 and RULE_FIRST §4 |

The script is descriptive and read-only (`data.db.connect(read_only=True)`). It reads the
registration-era corpus (≤ 2026-09-16), before both forward tests opened.

---

## 4. What this means for the running forward tests (nothing changed)

**FWD-PM-REGIME-002 and FWD-PM-FADE-001.** Both keep running under their frozen protocols. The Owner
has three options for each:
- **(a)** Leave both as they are, and read any 36-month PASS or 18-month PROMOTE using §1.4's error rates.
- **(b)** *Recommended.* Add an observability-only `deviation_log.md` entry to each. It would report,
  next to the frozen statistic, the **calendar-time t** and the **DK t (L = hold)**, and for FADE the
  **gross** contrast as well.
  - The decision rule is untouched.
  - REGIME-002 already has three observability-only amendments as precedent (limitations 9–10 and the
    IHSG regime fields).
  - A future Owner can then see whether a PASS or PROMOTE survives correct inference without the rule
    having moved.
- **(c)** Issue new spec ids with robust inference and honest horizons. For T1 that means about 6–9
  years, which effectively ends it as a decision test. This is a spec change, and not recommended now.

**FWD-PM-VOLEX-001.** Its inference is right.

**Corrected 2026-09-24.** The first version of this paragraph said runner hazard 1 (exits on partial
sessions) was still open. **That was wrong.** DEV-002 (`forward_exclusion/deviation_log.md`,
2026-09-23) had already closed it: the scorer now waits for complete entry and exit sessions. Two
items are still open:
- hazard 2 (run-time `suspension_events` look-ahead into forward formations);
- the stranded provisional bars. This audit's §7-A found 814 `is_final=0` rows dated 2026-09-16 →
  09-24, and IHSG missing on 2026-08-25 and 2026-09-16.

**Decisions taken 2026-09-24 (D-057, "approve all"):**
- option (b) for REGIME-002 and FADE-001: `forward_regime/deviation_log.md` DEV-001 and
  `forward_fade/deviation_log.md` DEV-001, both implemented by `P-M/forward_robust/robust_report.py`;
- this audit recorded as D-057.

---

## 5. Owner decisions requested (all approved 2026-09-24 → D-057)

1. **Record this audit.** Proposed as D-057, RECORDED type, in the same shape as D-056. No verdict is
   changed by it; rows 14, 19, 23, 30 and 31 are re-read.
2. **Choose (a), (b) or (c) of §4** for REGIME-002 and FADE-001.
3. **Done, 06:38 UTC (§7).** The rights and bonus effect is small and does not move FADE or T1. The 3
   gapped DB splits are repaired in the Rule Card loader (`research/rulecard/data.py::repair_db_splits`,
   gap-verified through `data/adjustments.py`, 2 tests). A rights/bonus TERP adjustment is deferred
   until a card is sensitive to it. Original text follows. If §3-D shows material rights or bonus
   ex-date drops, a gap-verified
   rights/bonus adjustment goes into the Rule Card loader before any new card is frozen (a D-055
   framework change, tested like DATA-1).
4. **Already done under D-055/D-056 authority**, as a framework fix with tests: SPL-1 is tightened
   (`checks.py`, `engine.py`, 2 tests), and RULE_FIRST_PROTOCOL §4's in-house evidence paragraph is
   corrected.

---

## 6. Receipts (file:line)

- **Entry-date cluster:**
  - `P-M/forward_fade/scripts/fade_failed_breakdown.py:122-139` (definition), `:171`, `:176`
    (registered t);
  - `P-M/forward_regime/PROTOCOL.md:56` (primary endpoint), `:103-119` (power and PASS);
  - `P-M/forward_fade/PROTOCOL.md:99` (inference), `:120-126` (PROMOTE);
  - `P-M/pattern_scan/scripts/patterns.py:44, 47`; `P-M/forward_regime/scripts/filt.py:45`.
- **One-leg cost:** `fade_failed_breakdown.py:170, 175`; `patterns.py:43, 47`;
  `PATTERN_SCAN_2026-09-17.md:6`.
- **Holding-window guard:**
  - `fade_failed_breakdown.py:100, 112-113, 163`;
  - `forward_regime/scripts/panel.py:27, 35`; `filt.py:28`;
  - `P-M/forward_regime/PROTOCOL.md:58`; `P-M/forward_fade/PROTOCOL.md:97`.
- **Unguarded FADE EW-book:** `fade_failed_breakdown.py:148`.
- **NW lag = k:** `P-M/g1_harness/g1_harness.py:115-131, 420, 458, 488, 720`.
- **Close(t) entry with flow dated t:** `g1_harness.py:168-193, 226-231`.
- **i.i.d. bootstrap:** `P-M/HYP-PM-0003_REGISTERED.md:69-81`.
- **Split basis, gap-verified:** `data/adjustments.py:1-20, 57-82`.
- **No rights/bonus adjustment:** no reader of `corporate_action_events` outside
  `stockbit_corporate_actions.py`.
- **Walk-forward:** `research/walkforward_multi.py:129-178, 253-300`; `engine/wf_edge.py:17, 190-225`.
- **Extended panel:** `P-M/data_gaps/scripts/ext_panel.py:24-50` (pre-2021 split adjustment), `:68`
  (`z_fwd`), `:69` (close(t) entry).
- **Overlap audit:** `P-M/overlap_audit/overlap_audit.py` and its `RESULT_*.json` (Owner run
  2026-09-24); `tests/test_overlap_audit.py`.
- **Calculations in §1.4:** normal approximation from the audit's shrink ratios. Reproducible from the
  numbers in §1.1. For FADE: G ≈ 348 signal dates at 18 months, from 1,154 dates over the registration
  window.

---

## 7. DB results — `validity_audit.py`, 2026-09-24 06:38 UTC

Output: `P-M/validity_audit/RESULT_20260924T063842Z.json`. Corpus ≤ 2026-09-16; FADE signals ≤ 2026-07-29.
31 tests passed on the Owner's machine before the run.

### A — Corpus

- 958 tickers, 1,250 sessions, 2021-07-05 → 2026-09-16.
- `is_final=0`: 814 rows, all dated 2026-09-16 → 09-24. These are provisional bars at the edge.
- Weekend rows 0; partial sessions 3; sessions missing IHSG 2.
- **ZV-2 holiday rows in the DB: 0.** The ZV-2 defect is specific to the pre-2021 backfill.
- Zero-volume share of liquid rows: 0.35–1.5% per year, peaking in 2024–25.

### B — Survivorship

- 724 names start at the corpus start and 234 start later (listings).
- **0 names stop trading more than 60 sessions before the end.** The corpus holds no delisted name, so
  survivorship is certain.
- The size of the bias cannot be read from this table. Its direction:
  - optimistic for long strategies (T1, VOLEX's held book);
  - probably conservative for anti-edges (FADE), if delisted names were the weak names that
    underperformed.

### C — Single-session moves above 25%

| set | n | up | down | explained (split, CA event, suspension, zero-volume day, gap) | unmatched |
|---|---|---|---|---|---|
| all, \|ret\| > 25% | 2,101 | 1,936 | 165 | 204 | 1,897 |
| all, \|ret\| > 35% | 206 | 143 | 63 | 31 | 175 |
| liquid, \|ret\| > 35% | 37 | 28 | 9 | 9 | 28 |

- The 25–35% moves are mostly real upper-limit (ARA) hits on low-priced names, which is legal under the
  band.
- Moves above 35% fit no band. 175 are unmatched to any recorded event (list in the JSON,
  `unmatched_top`). They are the guard's real target, and they are rare: 37 on liquid names in 5 years.
- **DB split continuity:** 81 verifiable splits; **78 continuous (adjusted at source); 3 gapped.** The
  3 are listed in the JSON and are now repaired in the Rule Card loader.

### D — Ex-date returns by corporate-action type

| type | n | median | P(< −10%) | P(< −20%) | reading |
|---|---|---|---|---|---|
| baseline, all sessions | — | — | 0.67% | — | — |
| rups (shareholder meeting, placebo) | 5,779 | 0.00% | 0.9% | 0.1% | ≈ baseline, so the method is sane |
| tenderoffer | 134 | 0.00% | 0.0% | 0.0% | no basis change |
| rightissue | 144 | −0.29% | **6.9%** | 2.1% | a minority of deep-discount rights are unadjusted (≈ 10 events) |
| bonus | 41 | +1.17% | **9.8%** | 4.9% | ≈ 4 unadjusted |
| stocksplit | 58 | −1.63% | 8.6% | **6.9%** | ≈ 4, consistent with the 3 gapped splits |
| warrant | 18 | −0.88% | 5.6% | 5.6% | 1 event |
| dividend | 2,136 | −2.22% | 5.1% | 0.2% | real ex-dividend drops. The DB is a **price** series; dividends are not in any return in this program |

**Consequence.** DATA-3 exists but is small. Measured against the two live references (§E), it changes
FADE by less than 0.01% and T1 ex-2025 by −0.06%/trade. The dividend convention (price return) is a
standing limitation, not a defect:
- it understates long-book returns;
- it biases relative tests against high-yield names.

### E — The holding-window guard and corporate-action windows

**FADE (the h20 gross contrast; h5 behaves the same):**

| construction | vs IHSG | t month / DK20 / DK40 | vs EW-book | t month / DK20 / DK40 |
|---|---|---|---|---|
| registered set (guard on) | −0.858% | −1.65 / −1.86 / −1.98 | −0.886% | −3.56 / −3.85 / −3.96 |
| guard off (+57 signals) | −0.868% | −1.67 / −1.89 / −2.02 | −0.896% | −3.60 / −3.89 / −3.99 |
| no corporate-action window | −0.863% | −1.66 / −1.86 / −1.97 | −0.889% | −3.60 / −3.90 / −4.03 |
| EW-book with the same guard | — | — | −0.890% | −3.57 / −3.86 / −3.96 |

- All 57 dropped FADE signals were dropped by the split flag alone. None of their windows had a > 35%
  session, so the guard was removing clean (already-adjusted) windows.
- **Verdict: R-3 is immaterial for FADE**, and so is the benchmark asymmetry.

**T1 (ex-2025 unless stated):**

| construction | N | mean | t registered | t month | t DK60 | t DK20 |
|---|---|---|---|---|---|---|
| FULL, registered set | 7,191 | +2.14% | 6.19 | 3.44 | 2.73 | 3.45 |
| ex-2025, registered set | 5,388 | +0.887% | 2.70 | 1.84 | 1.55 | 1.90 |
| ex-2025, **guard off** (no look-ahead) | 5,421 | **+1.059%** | 3.18 | **2.16** | **1.78** | **2.25** |
| ex-2025, no corporate-action window | 5,373 | +0.824% | 2.52 | 1.73 | 1.46 | 1.79 |

**What the guard removed.** It dropped 40 trades (all years) with a **mean excess of +26.3%**:
- 36 only because a recorded split fell inside the window. The series was continuous: 78 of 81 DB splits
  are adjusted at source.
- 3 with a > 35% up-move;
- 1 with a > 35% down-move.

Companies tend to split after a run-up, so conditioning on a future split removed winners. **The
look-ahead biased T1 down, not up.** The honest no-look-ahead ex-2025 reading is +1.06%/trade with
robust t 1.8–2.2:
- that is borderline at 5%;
- it still carries certain survivorship (optimistic) and close fills;
- calendar-time t was not computed for this set.

### F — Pattern-scan arms, re-measured

Gross, next-open entry, guard as in the scan, signals ≤ 2026-07-29. The registered net endpoint is shown
for reference.

| arm | h | bench | gross | t entry-date | t month | t DK | t calendar | verdict |
|---|---|---|---|---|---|---|---|---|
| failed breakdown (P3a) | 5 | EW | −0.45% | −5.09 | −3.71 | −4.33 | −4.48 | **survives** |
| failed breakdown | 20 | EW | −0.89% | −4.96 | −3.56 | −3.85 | −4.42 | **survives** |
| failed breakdown | 5 | IHSG | −0.54% | −4.21 | −3.03 | −3.26 | −4.22 | survives |
| failed breakdown | 20 | IHSG | −0.86% | −3.34 | −1.65 | −1.86 | −3.13 | mixed |
| falling wedge + break (P4) | 5 | EW | −0.56% | −5.81 | −4.21 | −4.52 | −6.31 | **survives** |
| falling wedge + break | 20 | EW | −1.21% | −6.37 | −4.70 | −4.81 | −6.03 | **survives** |
| falling wedge + break | 5 / 20 | IHSG | −0.48% / −0.72% | −3.85 / −2.73 | −2.23 / −1.29 | −2.51 / −1.23 | −5.25 / −2.96 | h5 survives; h20 mixed |
| falling wedge (P4b) | 5 | EW | −0.26% | −6.76 | −3.13 | −3.62 | −4.23 | **survives** |
| falling wedge | 20 | EW | −0.63% | −7.40 | −2.42 | −2.54 | −3.23 | **survives** |
| falling wedge | 20 | IHSG | −0.39% | −2.52 | −0.74 | −0.74 | −1.30 | no |
| failed breakout (P3b) | 5 / 20 | EW | +0.14% / +0.50% | 1.33 / 2.37 | 1.12 / 1.45 | 1.15 / 1.55 | 0.31 / 0.52 | **null** (the scan's −0.30%, t −2.71 was the cost) |
| resistance breakout (P2) | 20 | EW | +1.58% | 6.61 | 3.06 | 3.31 | **1.27** | trade-weighted only; crowded days (2025) carry it |
| resistance breakout | 5 | IHSG | +0.57% | 4.49 | 2.42 | 2.78 | 0.87 | trade-weighted only |

**Readings:**
1. **Every surviving anti-edge fires on names in a decline** (below the 20-day low; a falling wedge).
   Every one survives against the EW-book and is weaker against IHSG, which is the noisier benchmark for
   these names.
   - **The rule-first question** is whether each pattern adds anything to the characteristic it
     conditions on: recent weakness, or distance below the 20-day high or low.
   - **How to test it.** A card on the characteristic itself.
     - It is an event-time rule, which needs the v2 engine (`card.py` accepts `month_end` only).
     - A monthly decile sort of the same characteristic would face the 6.3%/mo noise floor.
2. **Day-weighted and trade-weighted can disagree** (resistance breakout; failed breakdown vs IHSG h20).
   A card must declare which estimand it claims before it runs. For an avoidance overlay the relevant one
   is the day-weighted book (calendar time).
3. **The scan's arms 1, 7 and 8 are still unmeasured on this basis:** liquidity sweep, wedge pop, and
   Episodic Pivot daily.
