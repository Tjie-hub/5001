# HYP-PM-0024 — {PY} dividend-yield level, payout-commitment risk premium (REGISTERED)

> **Status: REGISTERED** 2026-10-29 per DECISION_LOG **D-119** (Owner: "Daftarkan", 2026-10-28; "complete all
> step", 2026-10-29; FM data source chosen by the owner 2026-10-29: "Pin pickle, full 2009→"). Family **{PY}**
> (P-M · Payout, opened D-116), **one arm**. Census **614 → 615**; bar **3.300529** = `e_max_abs_z(615)`
> (`deflation_audit/bar_v2.py`; E/P's frozen bar 3.300069 is not changed — non-retroactive). This record is
> frozen at registration; its sha256 is pinned in `g1_dy.py::REG_SHA256`. The G1 may run **once**. Amendment
> only by a superseding D-entry.

## 1. Hypothesis (sign fixed)
Within the frozen top-200 IDX universe, a higher trailing total-payout yield earns a **positive** premium: the
equal-weight top-quintile yield book, net of cost, beats the equal-weight universe book.
H₁ (freeze §8): net monthly spread ≥ +0.80% with one-sided t ≥ the census bar at registration, both halves
> 0, FM incremental over E/P, size, Parkinson-60, VOLEX (t ≥ 2). The +0.80%/mo floor is the hypothesised
effect size (G0 power floor); per the frozen kill rule it is **reported, not a kill condition**.

## 2. Universe, formation, signal (frozen: `G0_FREEZE_DY_DRAFT_2026-10-28.md` §1–§2, sha `2789ab21…`, D-116)
Exactly the panel `g0_dy_breadth.py` builds (sha `497f32b9…`, D-116; unchanged):
- **Formations:** KSEI month-ends from 2009-04 after 2 warm-up months (`monthly_panel()`); a formation is
  tested if month D+1 exists in the KSEI file.
- **Universe:** top-200 by `sec_num × price` at D among 4-letter codes, stale-price filter (price identical at
  D, D−1, D−2 excludes), **price ≥ Rp 50** (gate b).
- **Signal:** `yield = ex.ttm_at(series[t], D) / (sec_num × price)` — TTM cash dividends paid (IDR, D-111 v3
  PIT, extraction v1.1 `106db63`), built as in `g0_dy_breadth.main()` (`sum_paid_rows` → `dividends_with_meta`
  → `build_ttm`). **Valid-yield names** = universe names whose `ttm_at` is not None (the G0's definition,
  median 68/month).

## 3. Test (G1, computed once) — every detail fixed here, before any return is read
- **Book:** valid-yield names sorted by (yield, ticker); top quintile = the last ⌊n_valid / 5⌋ names, **equal
  weight**. A formation is formable only if n_valid ≥ 30 (G0: 209/209 formable).
- **Benchmark ("EW liquid book"):** equal weight of the whole formation universe (all ≤ 200 names).
- **Returns D → D+1:** the frozen {FQ} G1 return code, imported (`g1_fq_ep.leg_return`): KSEI price ratio with
  the whole-ratio ±25% split rule; **price-only** (KSEI carries no dividends — see §6); a name absent at D+1
  exits at its last print (0%); mechanical drops below −95% are excluded from the leg mean and listed.
- **Net spread per month:** `net_t = (r_book − r_EW) − 0.006 × TO_t`; `TO_t` = one-way turnover of the book
  against the previous formation's weights (first formation = 1.0, the initial build); 0.60% round trip =
  D-082 basis; the benchmark is a costless reference.
- **Primary statistic:** mean of `net_t`, Newey–West SE with **6 lags**, Bartlett weights (the freeze is silent
  on lags; this is the {FQ} G1's rule, `g1_fq_ep.newey_west`), **one-sided**, against **3.300529**.
- **Halves:** formations in date order; first half = the first ⌊n/2⌋ months, second half = the rest. Kill if
  either half's mean `net_t` ≤ 0.
- **FM incremental separator (re-labelled value test):** for each formation D, cross-section = valid-yield
  names that also have a positive-TTM E/P from the frozen {FQ} code (`g1_fq_ep.signal("ep", …)`, deadlines
  qualified exactly as `g1_fq_ep.run_variant` does), Parkinson-60 available, and a D→D+1 return (same return
  code; mechanical drops excluded). Regressors: cross-sectional percentile ranks in (0, 1] (average ties) of
  yield, E/P, log(mcap), Parkinson-60, plus **VOLEX** = 1 if the name's Parkinson-60 exceeds the 90th percentile
  of Parkinson-60 over the whole formation universe that month (the VOLEX-001 exclusion line), else 0. OLS with
  intercept; months with fewer than 30 names are skipped. Incremental t = NW (6 lags) t of the monthly
  yield-rank coefficient; **kill if t < 2** (one-sided, positive).
- **Parkinson-60 at D:** `sqrt(mean(ln(high/low)²) / (4·ln 2))` over the last 60 daily bars dated ≤ D (bars with
  high ≤ 0, low ≤ 0 or high < low skipped); requires 60 bars with the newest within 10 calendar days of D. Daily
  source: `forward_volex/remeasure/work/hist_pre2021.pkl` for dates < 2021-07-05; production `ohlcv`
  (`is_final = 1`, read-only) for 2021-07-05 … 2026-09-30.
- **Pass = all three:** t ≥ 3.300529 **and** both halves > 0 **and** FM t ≥ 2. Otherwise **FAILED (F2)**, one run,
  no rescue. A pass is recorded as passing G1, never VALIDATED (forward-test receipt via `set_status()`).

## 4. Pre-declared sensitivities (report-only, never substituted for the primary)
Gross spread (no cost) · −100% delisting row · era split at 2021-07 · FM on 2021-07 → only (production daily
data, no survivorship) · FM without VOLEX · value-weighted top quintile. Report-only lines: per-month n_valid and
book size, mechanical drops, split-adjusted names, mean net vs the +0.80% floor, the yield-carry gap (§6), FM
months used.

## 5. Pins
- Freeze `G0_FREEZE_DY_DRAFT_2026-10-28.md` sha256 `2789ab21dedc269d0eeaf20b264c27a0e29c82362c6790a8065318524350c208`
  (D-116); G0 result `G0_RESULT_20261028T092519.json` (formable 209/209, placebo σ 3.54%/mo, power 48.7% at the
  0.80%/mo floor against 3.300069; stop rule not fired).
- Inputs per freeze §1, verified by `g0_dy_breadth.verify_inputs()` before anything else: KSEI csv `38c8a90b…`,
  Yahoo `a0937cde…`, late-filer list `b549358b…`, FY exceptions `013af724…`, fin.db per `SHA256SUMS_2026-10-26.txt`.
- **FM daily inputs (new at registration, owner 2026-10-29):** `hist_pre2021.pkl` file sha256
  `ea827fa632d09c5b8ed85163c4e3a141ebfc853adca12678e6a549350bd221f8` (fetch-log content fingerprint `fd9f54e3…`;
  541 tickers, 2000-03-30 → 2021-07-02); production `ohlcv` fingerprint sha256
  `3978ec8f395b180c65f041cc1aa3e9a7ea934daeffdda5d0dd3cbea37817b941` = sha256 over the lines
  `"{ticker},{date},{high!r},{low!r}\n"` of `is_final = 1` rows 2021-07-05 … 2026-09-30 ordered by (ticker, date)
  — 1,098,266 rows on 2026-10-29.
- **Imported code, verified by sha256 before the run:** `g0_dy_breadth.py` `497f32b9c28eea2bd288881114d00c1919d38709b05df5bf9b8b540d0e6f6899`
  (D-116), `extract_dividends.py` `a73a2df2c60fc210b1a7c5436f9f43e9358438bb1fb55e3e907d91ae3026e366` (v1.1),
  `g1_fq_ep.py` `f5d35449caaf6e584d11d258bce7014aefefd21ccda5c50e26f4a83a8f6a437b` (D-115),
  `g0_fq_ep_breadth.py` `d741e9b50a3d6547f683f0d94e6bd237734187c9ad370752f4e2c4392e7ef1b1`.
- Census 615; bar 3.300529. G1 script `g1_dy.py`: sha256 recorded in the D-entry that pins it.

## 6. Disclosures
- **Price-only returns favour the null.** The frozen construction measures close-to-close KSEI price returns,
  so the high-yield book forgoes its dividends in this test; the spread is understated by roughly
  (book yield − universe yield) / 12 per month. Not corrected (frozen); the G1 reports this gap (universe
  non-payers counted at yield 0) so the reader can size it.
- **FM survivorship.** The pre-2021 daily file holds only names Yahoo still lists: Parkinson-60 is available for
  72–85% of the universe per year 2009–2020 and 90–100% from 2021 (coverage measured 2026-10-29, no return read).
  The FM therefore runs on a survivor-tilted cross-section before 2021; the 2021-07 → FM row is the clean check.
- **Honest power line.** MDE80 at the deflated bar ≈ 1.01%/mo net (the 0.61%/mo in the G0 JSON is the frozen
  report-only 2.487·SE formula, i.e. a plain 5% test). At the G0, t at the floor was 3.27 — just under the bar.
- **Declared multiplicity debt:** alpha_search_v2 exploratory trial #6 (2021–26 dividend-yield book), disclosed,
  used for nothing.
- **Family:** {PY} · Payout, separate from {FQ} by the owner's 2026-10-28 choice (inference-equivalent to
  widening {FQ}); dividends only; C-009 buyback not folded in (UNDERPOWERED).
