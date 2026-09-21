# ZCODE Adversarial Review — factor_zoo FINDINGS_2026-09-18

**Reviewer:** ZCODE (cold, scope-locked) · **Date:** 2026-09-18 · **Artifact:** commit `26f1048`
**Scope-lock compliance:** read-only analysis (inline re-implementations of the staged
logic, `mode=ro` DB connections); this file is the only write; nothing staged, committed,
amended or pushed; suite not re-run. `SHA256SUMS.txt` verified OK for all 5 scripts;
working tree clean for all `factor_zoo/` paths; every commit on the branch authored by
Tjie — no second actor inferred.

**Method note.** `zoo_run.py`/`zoo_era.py` read/write pickles next to themselves, so they
were re-implemented inline (same filters, same quantile logic) rather than executed
in-place; `port52.py` and the staged `/tmp` scratchpad `zoo.pkl` (14:00, pre-commit) were
used as-is. Staged outputs reproduce the committed FINDINGS exactly.

---

## Executive verdicts

| claim | verdict | one-line basis |
|---|---|---|
| A-1 headline chain | **REFUTED as committed** (defect real; corrected magnitude disputed) | 21-session windows mis-tile the calendar: 35/62 overlaps, 18 gaps, 9 exact; exact re-chain gives **+20.76%/yr** (51 links) or **+21.81** (52), not +13.67, and not the brief's +14.32 either |
| A-2 "ex-2025 +2.03%, below deposit" | **REFUTED** | the ex-2025 collapse is a chaining artefact; exact chain ex-2025 = **+6.03%/yr** (51 links) / +7.58 (52) |
| A-3 multiplicity (92 trials, bar t=3.46) | **UPHELD, strengthened** | 92 is a defensible floor (wide count 122 → bar 3.53; t-dist bar at 92 is 3.70); nothing found clears robustly |
| A-4 median test | **UPHELD as screen / internally inconsistent as used** | equal-weight earns the mean (killed books netted +19–27%/yr mean-based), but the concentrated tail is real and partly untradeable — see A-5 |
| A-5 "no artefact survives" | **REFUTED — artefact found** | frozen/suspended rows carry the edge: book gross +1.51%/mo (t 1.69) → **+0.57 (t 0.70)** ex-frozen; non-frozen rows alone earn **+0.14%/mo** |
| A-6 benchmark correction | **UPHELD exactly; corrected strategy CAGR UNPROVEN** | reproduced −9.97%/yr sampled vs **−3.43%/yr** exact over the book window; but the +14.32 corrected headline does not reproduce (mine: +20.76/+21.81) |
| A-7 data gaps | **UPHELD in full** | every table row verified against the DB, including "median 1 obs/ticker" (median 1, mean 9.09, bimodal) |
| A-8 fundamentals (in flight) | **UNPROVEN — not reviewed** | design-level notes only; numbers do not exist yet |

**Net effect on the FINDINGS' headline answer** ("no 6-7%/yr result survives"): **UPHELD —
but for different and stronger reasons than the document gives.** The document's own
reasoning is compromised in two places (chaining artefact inflates the 2026-crash smearing
that produced "ex-2025 collapse"; the survivor's mean is carried by untradeable frozen
rows). The conclusion survives; two of its pillars do not.

---

## A-1 — The chain

**Reproduced (staged, as committed):** `port52.py` on the staged panel → hi52 top-20% +
vol-exclusion: **NET +13.67%/yr, Sharpe 0.69, maxDD −34.5%, t 1.44**, 52 book month-ends
(2022-04 → 2026-07), ~58 names, turnover 0.39/mo. Exact match to FINDINGS §4.

**The chaining defect is real and quantified.** `zoo_build.py` computes every forward
return as `close.shift(-21)/close` — a fixed 21-*own-row* window from each month-end
snapshot. Actual month-end spacing on this corpus runs **13–23 sessions** (modal 20–22;
two Eid months at 13–14). Consecutive-month audit: the 21-session window **overlaps the
next month-end in 35 of 62 months, gaps in 18, is exact in 9**. Worse, mean spacing drifts
monotonically (2021: 21.2 → 2026: 18.7 sessions), so the chain phase-shifts ~+1.3
sessions/month into the following month. Mechanism, visible in the year tables: the
terminal 2026 crash is smeared backward into 2025 (staged 2026 universe −31.6% vs exact
−10.9%; staged 2025 book +62.7% vs exact +84.3%).

**Re-chain, exact month-end → next month-end closes, same selection/cost logic:**

| | NET %/yr | Sharpe | maxDD | t | ex-2025 |
|---|---|---|---|---|---|
| staged (committed) | +13.67 | 0.69 | −34.5% | 1.44 | +2.08 |
| exact, 51 links (2022-04-28→2026-07-31) | **+20.76** | 1.10 | **−20.7%** | 2.26 | **+6.03** |
| exact, 52 links (→2026-08-31) | +21.81 | 1.15 | −20.7% | 2.39 | +7.58 |
| brief's "corrected headline" | +14.32 | 0.85 | −20.8% | — | +2.03 |

The brief's maxDD correction reproduces (−20.7 ≈ −20.8) and its direction is confirmed,
but **its CAGR does not reproduce**: the only principled exact method yields +20.76/+21.81,
6–8pp *above* the claimed correction. Neither +13.67 nor +14.32 should be quoted. Every
level number in FINDINGS §4 is unreliable pending a committed re-chain.

**Cost convention:** verified correct in arithmetic — `turn` is the one-way new-name
fraction; `cost = turn × 0.60` equals per-side 0.30% on both the sell and buy legs of the
replaced notional (zoo_era's `2*tu*(0.60/2)` is the same formula). Two caveats: (i) the
turnover measure ignores weight drift and name exits; (ii) the 0.60% round-trip level is
~15–25% optimistic against the program's own Roll evidence (Rp1–10bn bands imply
0.68–0.84% round trip; at 0.85% the net falls ~1.2pp/yr — immaterial to any verdict here).

## A-2 — The 2025 problem

Reproduced year tables (net, top-20% + volex):

| method | 2022 | 2023 | 2024 | 2025 | 2026 | ALL | ex-2025 |
|---|---|---|---|---|---|---|---|
| staged | +6.26 | +9.11 | +13.35 | +62.66 | −18.50 | +13.67 | +2.08 |
| exact (mine) | +6.39 | +7.98 | +16.36 | +84.28 | −4.55 | +21.81 | +7.58 |
| brief's quoted | +5.27 | +7.89 | +7.07 | +62.30 | −10.42 | +14.32 | +2.03 |

The brief's quoted years match **neither** method — part of the unresolved +14.32 cluster.
On framing: the committed doc's "its absolute performance is a 2025 artefact / ex-2025
below deposit" is **refuted** — the ex-2025 collapse is manufactured by the mis-tiled
chain, and under exact chaining ex-2025 is +6.03%/yr (51 links), i.e. at the deposit line,
not below it. What survives honestly: 2025 is still the largest single *excess* year
(+23pp over the equal-weight universe vs +15–19pp in 2022–24), and no t-statistic survives
multiplicity (below). The framing I would defend is the exact-chain table plus the A-5
tradeability cut — under which the year-framing question is moot, because the book's edge
is dead at gross level (A-5) before any year is counted.

## A-3 — Multiplicity

The claimed 92 = 23 zoo + 10 era + 8 robustness + 51 vol-sweep.

*Recount.* Each zoo factor produced **two** examined t-statistics (LS and LO) — 46, not
23. Era adds 10. `port52.py` printed 7 book variants (4 fractions + 3 volex). Bounce
re-tested 8 existing hypotheses (0 new). Vol sweep 51 as stored. **Wide honest count:
122.** Conversely the 23 zoo factors are far from independent: the participation ratio of
the 23 LO-excess correlation matrices is **9.4 effective factors** (median pairwise |corr|
0.19), so a correlation-adjusted floor is ~70 tests (zoo ≈ 19 effective + vol 51).

*Bars* (two-sided 5% Bonferroni; df≈50 so the t-quantile, not the normal, is the correct
one — the doc's normal choice is itself the lenient bound):

| n | normal | t(df=50) |
|---|---|---|
| 92 (claimed) | 3.46 | 3.70 |
| 122 (wide) | 3.53 | 3.79 |
| 70 (effective floor) | 3.38 | 3.61 |

*Against them:* portfolio net t 1.44 fails everything. vs-IHSG t 3.43 fails 92-normal and
everything stricter. Beta-adjusted alpha t 3.27 fails **every** bar including the most
generous. hi52 mean-based LO t **3.48** — a number FINDINGS never reports — clears
92-normal by 0.02 and nothing else. hi52 median t 3.69 clears 92- and 122-normal, is
razor-edge against 92-t (3.696). park60 LO −3.59 clears 92-normal but belongs to the vol
family already inside the 51.

**Verdict: UPHELD and strengthened.** 92 is defensible as a floor; under append-only
governance the wide count is more honest; nothing found clears a robust bar.

## A-4 — The median test

The load-bearing columns reproduce **exactly** (median excess, t(median), top-1% shares:
hi52 +1.63/3.69/75%, px +1.23/2.79/79%, ma50 −0.43/−0.61/87%, mom1 −0.55/−0.78/96%,
skew60 −0.34/−0.87/232%). The mean-excess column does **not** reproduce (mine: +2.16,
+2.40, +2.28, +2.12, +0.93 vs doc +1.98, +2.22, +1.85, +1.68, +0.67 — see Deferred).

**The case against the median screen, made concrete:** an equal-weight book earns the
mean. Net-of-cost mean-based decile books: hi52 **+21.97%/yr**, ma50 **+22.44**, mom1
**+19.50**, px **+26.69**, skew60 +7.54. The median test killed books whose in-sample
mean-net equalled or beat the survivor's, and FINDINGS reports none of those numbers. The
screen, not the data, chose the winner.

**The case for it, made concrete:** with 59 months, mom1's entire profit sits in the top
1% of rows (~46 of ~4,600 name-months); the monthly t already prices the variance but not
the small-sample skew. And A-5 shows the concentrated tail is not an abstraction: the
survivor's own mean is carried by frozen rows (book row-mean +1.41%/mo → **+0.14%/mo**
excluding suspension-flagged rows).

**Ruling:** the median test is the wrong *primary* screen for equal-weight profitability
but the right *robustness diagnostic*; the defensible protocol is a **tradeability-conditioned
mean** — drop untradeable/frozen rows first, then test the mean the book actually earns.
FINDINGS is internally inconsistent: it selected hi52 *for* median-robustness, then quoted
a *mean-based* headline that fails its own selection philosophy. Under the corrected
protocol nothing survives (gross +0.57%/mo, t 0.70 — A-5). This single choice did determine
the survivor, and the honest answer is that under any consistent choice, **none** of the
five survives.

## A-5 — The artefact neither test covers: frozen names

Their two tests were: attrition (scoring *missing* forward rows as −100%) and bid-ask
bounce (open-to-open on **volume>0 prints only**). Both miss the third state: rows that
are **present but untradeable** — suspended names carrying frozen prices.

**Findings (all reproducible):**

1. **15.82% of bottom-price-decile rows have forward return exactly 0.00%** (panel-wide
   3.62%); 14.8% of that decile sits with close in [50, 51) — the Rp 50 floor cluster.
   Frozen-flagged rows (fwd==0 or ≥1 zero-volume session in the forward window): **18.1%
   of the bottom price decile vs 3.4% of the top decile**.
2. The cheap-decile excess **+2.40%/mo (t 3.49) → +1.80 (t 2.94)** ex-frozen →
   **+0.92 (t 1.70)** also dropping windows containing any |daily|>34.5% move.
3. **The survivor dies the same way.** hi52 top-20%+volex gross: **+1.51%/mo (t 1.69) →
   +0.57%/mo (t 0.70)** ex-frozen → +0.45 (t 0.56) ex-dirty. Of the book's 3,009
   name-months (mean +1.41%/mo), the 92.7% non-frozen rows alone average **+0.14%/mo** —
   the 7.3% frozen rows (implied mean ≈ +17%/mo: suspension → resumption gap, measured
   print-to-print) carry essentially the whole edge.
4. Market-structure corroboration: in the Rp50–200 bucket, P(daily ≥ +34.5%) = 0.1163%
   vs P(daily ≤ −34.5%) = 0.0143% — **an 8.2:1 limit-up:limit-down asymmetry**. Downside
   routes through suspension, not traded limit-down days; the frozen rows are its shadow.

*Capturability caveat:* part of a frozen row's return is theoretically capturable (hold
through suspension, sell the resumption). But that is precisely the lottery tail the
document's own median philosophy rejects, and the 8:1 ARA asymmetry is the prize
distribution of the marketplace, not an information edge.

**Verdict: REFUTED.** The claim that no artefact explains the results is false; the artefact
neither of their tests could see removes both the cheap-decile effect and the survivor's
edge at gross level.

## A-6 — The benchmark correction

**Verified exactly.** IHSG over the book window (2022-04-28 → 2026-07-31):
21-session-sampled chaining = **−9.97%/yr** (the erroneous draft figure) vs exact
month-end chaining = **−3.43%/yr** (51 links; brief said −3.42). Full-window IHSG:
CAGR **+1.50%/yr** (doc: +1.42 — annualization-convention difference, immaterial),
Sharpe 0.17 ✓, maxDD −41.5% ✓.

**Contamination scan:** every chained *level* in FINDINGS §4 inherits the artefact (net
+13.67, Sharpe 0.69, maxDD −34.5, ex-2025 +2.08, 2025-only +62.66, "+7.42pp vs deposit").
Spreads vs universe/IHSG are computed on identically mis-tiled series (partial
cancellation) but remain phase-shifted. The strategy re-chain reproduces the maxDD
correction (−20.7 ≈ −20.8) but **not** the corrected CAGR: +20.76 (51 links) / +21.81
(52 links), not +14.32. The corrected headline is directionally right and numerically
unproven; it must not be quoted until someone reproduces it.

## A-7 — Data gaps

**UPHELD in full.** Verified against `research.db` (read-only): `stockbit_keystats`
2026-04-10 → 2026-09-18, **market_cap 0/8,833 populated**, obs/ticker **median 1** (mean
9.09; bimodal — 885 tickers ≤2 obs, 79 tickers ~90+); `ownership_composition` **0 rows**;
`candidate_watchlist_snapshot.sector` **0/1,816 populated**; `engine/sector_rotation.py`
covers exactly **82** tickers; `broker_flow`/`stockbit_flow_bars` 2025-01-02 → 2026-09-17;
`ticks` 2026-04-18 → 2026-09-18, 101 sessions; `corporate_actions` 501 tickers, full span;
`idx80_membership_history` 640 rows / 101 tickers; `suspension_events` 956 tickers;
`ohlcv` 958 tickers ex-IHSG (+IHSG = 959 as documented), 1,251 sessions, 2021-07-05 →
2026-09-17. No factor family was written off without cause.

## A-8 — Fundamentals fetch (in flight)

Not reviewed — no numbers exist yet (scratchpad shows the fetch landing 14:15;
`fund_fails.json` currently an empty array). Design-level only:

- **6-month lag vs IDX statutory deadline:** annual audited statements are due ~90 days
  after fiscal year-end, so FY(Y) is public by end-March Y+1; a 1-July-Y+1 usability lag
  is strictly conservative — no look-ahead risk, ~1 quarter of unnecessary staleness.
  Acceptable for monthly cross-sectional work; mildly power-reducing.
- **Restatement bias:** Yahoo serves restated (current) financials, so the backtest sees
  final numbers that were not knowable at the time. The bias systematically *flatters*
  value/quality constructions. Any value factor from this fetch is an **upper bound** and
  should not be registered without an external point-in-time check or a defensible
  holdout discipline. A 6-month lag does not mitigate restatement (it is an as-of
  *availability* rule, not an as-known *content* rule).

---

## What actually survives this review

1. The FINDINGS' headline answer ("no 6-7%/yr result survives") — **upheld**, on stronger
   grounds: multiplicity (nothing clears a robust bar) **and** the A-5 tradeability kill.
2. The data-gaps table (A-7) — every row verified.
3. The relative-vs-absolute distinction — direction survives, but "durable relative alpha
   (t 2.4–2.8 ex-2025)" is **refuted** by the frozen-row cut (gross t 0.70 ex-frozen).
4. Nothing else. Both corrected CAGRs (+14.32 brief, +20.76/+21.81 mine) are moot as
   performance claims because the edge they would measure does not survive A-5.

---

## Deferred observations

- FINDINGS §3 "mean excess" column does not reproduce (+0.2–0.4pp higher on my re-run);
  medians, t(median) and top-1% shares reproduce exactly — likely a stale draft variant
  of the mean definition; should be reconciled.
- `zoo_run.py`/`zoo_era.py` read/write `zoo.pkl`/`zoo_results.pkl` next to themselves
  while `zoo_build.py` writes to a `/tmp` scratchpad — pipeline paths inconsistent;
  running the sweep in-place would create untracked files in the repo.
- `zoo_build.py` computes 24 features; one silently fails the ≥24-month/≥8-decile filter,
  leaving the documented 23 — which one is undocumented.
- `ohlcv` contains |daily| prints beyond any ARA band (max +560.5%/day in the Rp200–5000
  bucket, min −98.1%) — corporate-action adjustment status of `ohlcv` should be confirmed
  before any per-name return work.
- Book trades 52 month-ends (2022-04→2026-07); "51 periods" counts links, not month-ends
  — both defensible, but the FINDINGS should state which.
- The `shift(-21)` row-based convention also underlies every `fwd` in the zoo panel and
  the vol_exclusion increments — common-mode within each month, but the V2 vol review
  should check the same phase-shift effect there.
- Scratchpad contains an in-flight fundamentals fetch (`fetch_fund.py`, `fund_shares.pkl`,
  `fund_annual.pkl`, 14:15) — unreviewed per A-8.
- Working tree carries pre-existing modifications (`.vscode/settings.json`) and many
  unstaged `Audit/` deletions — untouched per scope lock.
- **The artifact moved mid-review**: commits `46a86b2` (14:16, fundamentals pipeline) and
  `b9a3886` (14:28, IDX80 test) landed after this review began; this review covers
  `26f1048` only. The A-5 frozen-row and A-1 `shift(-21)` findings apply directly to the
  new commits' numbers and should be checked there before any of them is relied on.
- Mimosa L2 flagged the newly-landed scripts (not this review's diff): `read_pickle` in
  `combo.py:7` / `fetch_fund.py:12` is the directory's standard local-artifact pattern
  (same as committed `zoo_run.py:9`), not an untrusted-data path; `fetch_fund.py:47`
  writes to a fully script-dir-static path with no `../` and no external input — false
  positive. Recorded, not actioned, per scope lock.
- Full-suite status (3245/3/0) taken on trust per the brief; not re-run.
