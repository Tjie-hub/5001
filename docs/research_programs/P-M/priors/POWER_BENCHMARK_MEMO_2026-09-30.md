**SUPERSEDED by POWER_MEMO v2 (`priors/POWER_MEMO_2026-09-30.md`) — 2026-09-30 research
consolidation.** This memo's "LW" (trailing-volume) weight proxy is replaced by true cap weights
from `factor_zoo/data/fund_shares.pkl`; see `UNIVERSE_BENCHMARK_MEMO_2026-09-30.md`'s "2026-09-30
rebuild" section for the corrected 2a-equivalent decomposition (GOTO/ARTO 2022, BBRI 2024 findings
reproduce here; magnitudes differ under true CW). Retained below for provenance only.

# POWER + BENCHMARK memo · 2026-09-30

Panel/window identical to SCREEN-PM-XP-001 (fingerprinted panel sha256 `4fbc79db…`, VOLEX top-200
liquid universe, month-end formation on the last complete session, next-session-open fills,
entries 2021-08→2026-06) plus the standing tradeability rule (volume > 0 at entry AND exit).
Companion data: `power_benchmark_results.json` (this directory). Numbers only.

**Weighting caveat (reads on every cap-weighted row):** the corpus holds no shares-outstanding /
market-cap history (`stockbit_keystats.market_cap` is 100% NULL), so "cap-weighted" is proxied by
trailing-60-median traded value weights — labelled **LW**. A true CW decomposition needs Task 3's
PIT fundamentals.

## 2a · Decomposition (monthly books, % summed per year)

| year | months | IHSG | LW universe | EW universe | EW−IHSG | LW−EW |
|---|---|---|---|---|---|---|
| 2021 | 5 | +7.88 | +2.20 | +1.33 | **−6.55** | +0.87 |
| 2022 | 9 | +6.79 | +3.91 | −10.37 | **−17.16** | +14.28 |
| 2023 | 10 | +8.75 | −2.33 | −4.99 | **−13.74** | +2.66 |
| 2024 | 12 | −2.00 | −5.24 | −1.01 | +0.98 | −4.23 |
| 2025 | 12 | +22.79 | +31.54 | +33.37 | **+10.57** | −1.83 |
| 2026 | 6 | −41.06 | −49.16 | −40.14 | +0.92 | −9.02 |
| **full** | **54** | **+0.059/mo** | **−0.353/mo** | **−0.404/mo** | **−0.463/mo (t −1.30)** | **+0.051/mo** |

**Answer to 2a: the gap is NOT broad and NOT stable — it is a few mega-caps per era, concentrated
in 2021–2023.** 2024–2026 the EW−IHSG gap is ≈ 0 (+0.98, +10.57, +0.92pp); in 2025 the EW book
*beat* IHSG by +10.6pp. Top-10 |contribution| names within the LW book (results.json, all years):
2022's −17.2pp gap is dominated by **GOTO** (−4.21pp, avg weight 3.9%) and **ARTO** (−1.60pp) —
the fintech collapse; 2024's LW deficit is one name, **BBRI** (−2.79pp at 13.2% average weight);
2026's crash is the coal/Barito complex — **BUMI** (−6.87pp), PTRO (−2.55), CUAN (−2.47),
DEWA (−2.19). No year's gap is spread across the breadth of the book; every year has a
2–4-name story. The LW−EW spread (+14.3pp in 2022, −9.0pp in 2026) shows weighting itself swings
multi-pp per year on these few names.

## 2b · Tracking error (monthly, %, 54 months)

| tilt | TE vs LW (cap proxy) | TE vs EW | mean excess vs EW |
|---|---|---|---|
| 10% Parkinson exclusion (= XP-001 rule B) | 1.951 | **0.752** | +0.343 |
| Tercile exclusion (top third) | 2.755 | 2.004 | +0.405 |
| Lowest-vol-20% book | 3.823 | 3.555 | +0.547 |
| EW universe vs IHSG (reference) | — | 2.623 | −0.463 |

Confirms the planner's read: the broad 10%-exclusion tilt has TE ≈ 0.75%/mo against its own EW
universe — detectable in ~5 years — while concentrated books (tercile, top-20%) run TE 2–3.6%/mo
and are not.

## 2c · Effect | prior | power table (MDE in %/month over 54 months; months = months needed for a +0.50%/mo effect)

| effect | prior (Task 1 source, cited) | TE (vs EW unless noted) | MDE @1.65 | @2.00 | @2.8575 (D-064 bar) | @3.46 | months for +0.50 @bar | verdict at 54 months |
|---|---|---|---|---|---|---|---|---|
| Low-vol 10% exclusion vs EW universe | volatility effect in EM — Blitz/Pang/van Vliet 2013 EMR **(source blocked, abstract-only; no number taken)**; program in-sample +0.394%/mo (VOLEX PROTOCOL §3) | 0.752 | 0.169 | 0.205 | **0.292** | 0.354 | 30 | **CAN confirm**: in-sample-size effect (0.394) exceeds the 54-month MDE 0.292; needs n≈24 to clear its own forward-test bar (t>1.71) |
| Tercile low-vol exclusion vs EW | same prior, scaled by concentration (no separate number; blocked source) | 2.004 | 0.450 | 0.545 | 0.779 | 0.944 | 132 | **Cannot**: a 0.4–0.5%/mo effect needs 11 years at the bar |
| Lowest-vol-20% book vs EW | same prior, concentrated form | 3.555 | 0.798 | 0.968 | 1.382 | 1.674 | 413 | **Cannot** |
| Size tilt embedded in EW-vs-IHSG (small minus cap-weight) | **−0.46%/mo in IDX 1990–97 (t −0.77), Rouwenhorst (ingested)**; EM-wide SMB +0.69 (t 3.09, same source) — sign conflict across samples | 2.623 (vs IHSG) | 0.589 | 0.714 | 1.020 | 1.235 | 225 | **Cannot**: the observed −0.463%/mo (t −1.30) is inside the 54-month noise band; indistinguishable from zero at the bar |
| EM value tilt (needs PIT fundamentals; Task 3 gate) | +0.72%/mo stock-EW / +0.93 country-EW, t 3.82/4.00 (Rouwenhorst, ingested); FF(1998) VW EM value 16.91%/yr t 3.06 (via Rouwenhorst's tables) | n/a — no PIT data | — | — | — | — | — | **Cannot even test** until Task 3 finds a PIT source; then power per the low-vol row's geometry (broad tilt ≈ TE 0.75–2.0) |
| EM momentum tilt | +0.39%/mo stock-EW / +0.58 country-EW, t 2.35/3.78 (Rouwenhorst, ingested) | n/a | — | — | — | — | — | same gate as value |
| MAX/lottery & IVOL tilts | US VW only: MAX −1.03%/mo (t −2.83), IVOL alpha −1.33 (t −5.09); **EW flips IVOL sign** (+0.37, t 1.09) — Bali-Cakici-Whitelaw (ingested, NBER w14804) | n/a | — | — | — | — | — | weighting-sensitivity is the finding: an EW book can carry opposite-signed exposures to the US-documented effects |

**Cross-cutting conclusions (numbers above, no new claims):**
1. The EW-vs-IHSG gap (−0.463%/mo gross, t −1.30) that motivated this review is **an era-and-names
   artifact (2a), not a stable benchmark property** — and at TE 2.62%/mo it is statistically
   indistinguishable from zero over any 5-year window (MDE 1.02 at the bar).
2. Only **broad, low-TE tilts (≈0.75%/mo) are confirmable in 5 years** at the D-064 bar
   (MDE 0.29). Concentration destroys power faster than it raises expected excess (tercile MDE
   0.78, low-20 MDE 1.38).
3. Every published prior that survives into an EW IDX book carries a weighting caveat
   (BCW's MAX/IVOL sign flip; Rouwenhorst's EW-vs-VW premia gaps of 0.2–0.5%/mo) — priors must be
   read as *sign hypotheses*, not magnitude forecasts, for this book.
4. VOLEX §3 quote (as instructed, protocol untouched): "**PASS** — mean incremental > 0, one-sided
   t > 1.71, **and** P(>0) ≥ 60%" — the endpoint is §2's `incremental = mean(held) − mean(universe)`
   (the excluded decile's names inside the same top-200 universe), i.e. **the EW same-universe
   benchmark only; IHSG appears nowhere in the decision rule.** VOLEX-001 can therefore PASS while
   the book still loses to IHSG — and per 2a, over its backtest reference window that IHSG loss
   was driven by GOTO/ARTO-era (2021–2023) mega-cap events, not by the vol exclusion itself.
5. Trial census (per the planner's instruction, recorded here because CENSUS_UPDATE.md is outside
   this task's write boundary): XP-001 ran 4 declared arms (A∪B∪C, A, B, C) → census
   **N = 266 + 4 = 270**; two-sided bar at N=270 remains 2.857 (2.8575 applied). A one-line append
   to `broad_search/CENSUS_UPDATE.md` is owed by whoever next holds that file.
