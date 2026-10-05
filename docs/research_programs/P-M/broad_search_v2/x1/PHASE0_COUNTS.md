# PHASE0_COUNTS — X1 overnight screen · 2026-10-05

Companion to `PHASE0_COUNTS.json` (machine record, written by `phase0_counts_x1.py` through
`research/tracking.py` — run_id, git sha, dataset fingerprint, `issuance=True` in params).
**Counts + unconditional statistics only; no signal value was computed and nothing was
conditioned on the signal.**

## 1 · Data basis (disclosed every time)

- Corpus = **local `walkforward.db`** (the snapshot `walkforward-20261004-213000.db.zst`, sha
  `8408e91a…`, never reached this host). Panel `2000-03-30 → 2026-07-29` (T=6,548, N=958);
  **max(date) = 2026-07-29** — the confirmation window ends there, not "latest".
- Signal legs from the committed CSVs (`cross_asset/data/`, sha256 in `MANIFEST.json`): EIDO,
  TLK, SPY (yfinance adjusted closes), USDIDR=X, ^JKSE, JISDOR (BI official, no-auth export).
- Outcome prices through `research.rulecard.data.load_extended_ohlcv(issuance=True)`.
- FX-leg holes: 485 IDX sessions lack the USD-converted JKSE leg (USDIDR=X gaps, incl. the
  located 214-day hole **2003-05-01 → 2003-12-01** — a Yahoo history hole, market open
  throughout; 10-day hole 2002-09; 26-day hole 2008-07). Those sessions cannot form β̂ pairs.

## 2 · The valid-open outcome restriction (spec deviation #1, predeclared before any signal read)

Open-quality per year (liquid name-days, share of rows): `open == close` 0.6→35% rising across
2010→2024; `open == prev_close` **12% (2010) → 21.5% (BBCA 2022+, direct DB check on
mega-caps) → 47–56% of panel liquid rows (2023–2025)**. A stale open turns open→close into a
close-to-close return — the outcome would silently include the overnight gap, which is exactly
the part the signal predicts. **PRIMARY outcome = valid-open members only** (`open > 0`,
`open != close`, `open != prev_close`, `volume > 0`, adv20 ≥ Rp 5bn as of prior session). The
unrestricted book is carried as a secondary disclosure. Full table in the JSON.

## 3 · Usable (signal-calendar × outcome) days per arm

Exclusion buckets counted per arm: US-holiday/no-signal, FX-missing, β warm-up (<120 pairs),
k≥4 gap (excluded), signal-leg missing, outcome missing (no valid-open member / TLKM stale).

| arm | split | usable days | notes |
|---|---|---|---|
| X1-A EIDO→book | 2021-07-05 → 2026-07-29 | **1,166** | 39 US-holiday days, 7 k≥4 gaps |
| X1-B EIDO→book | 2010-05-01 → 2021-06-30 | **2,169** | first signal 2010-05-11 |
| X1-C TLK→TLKM | 2021-07-05 → 2026-07-29 | **839** | TLKM valid-open on 877 of 1,213 sessions |
| X1-D TLK→TLKM | 2010-05-01 → 2021-06-30 (brief split) | **1,326** | 1,599 usable from 2001 (not tested) |
| X1-E SPY→book | 2021-07-05 → 2026-07-29 | **1,166** | |
| X1-F SPY→book | 2010-05-01 → 2021-06-30 (brief split) | **2,174** | 3,841 usable from 2001 (not tested) |

## 4 · Unconditional σ (open→close, per day) and MDE per arm

Bar: **|t| ≥ 3.2534** (exact two-sided E[max|Z|] at census N = 515 + 6 arms = 521, W0 recount;
at the pre-recount census 276 it was 3.067). MDE = bar × σ / √N, in bp per day per 1σ of signal.

| series | confirmation σ | discovery σ |
|---|---|---|
| LW book, valid-open (PRIMARY) | 1.470% (n=1,216) | **2.575%** (n=5,332) |
| TLKM valid-open | 1.952% (n=877) | 1.975% (n=1,663) |
| IHSG (corpus; confirmation only) | 0.894% | — (discovery benchmark = ^JKSE, Yahoo, disclosed) |
| unrestricted book (secondary) | 1.292% | 1.351% |

The valid-open book is *more* volatile than the unrestricted one (selection: names that traded
at the open are the movers) and the pre-2021 discovery σ (2.58%) is era-inflated. MDEs:

| arm | MDE (bp/day per 1σ) |
|---|---|
| X1-A / X1-E | 14.0 |
| X1-B | 18.0 |
| X1-C | 21.9 |
| X1-D | 17.6 |
| X1-F | 18.0 |

Reading: the effect the priors predict (Levy–Lieberman-style overnight overreaction) lives at
tens of bp per σ of signal — the primary arm can detect a ≥14bp/1σ response at the bar. The
most likely honest outcome remains "real but mostly absorbed at the open" (absorption share),
which the predeclared kill rule handles.

## 5 · Survivorship (brief-standard line)

`history_long.db` is **absent on this host**, so the recorded memo-07 line stands as the
standard citation: **54 of 929 `ohlcv_long` names end before 2026; delisted names are purged
from Yahoo and enter no free panel**. Panel-derived confirmation: **0 of 541** pre-2021 names in
the merged (backfill+DB) panel die before 2026 — the discovery half is survivorship-biased by
construction (missing names are the worst performers; this biases an avoidance-side result
*against* the effect, the same sign note as S2).

## 6 · Pre-2021 discovery verdict (predeclared)

The brief: "If pre-2021 opens are unreliable, the discovery half becomes descriptive only."
Measured: open quality is poor in BOTH halves (and worst 2022–2025). Resolution predeclared
before the screen: the valid-open restriction (§2) applies to both halves, so the discovery arms
stay inferential **but** carry two disclosed caveats — (a) 100% survivorship bias (§5), (b)
pre-2021 prices are the yfinance backfill (memo 07). No arm is silently downgraded; the
discovery arms' role stays "replication: sign must match".

## 7 · Validity gates

- **TLK ADS-ratio gate: PASS.** SEC-verified ratio history (20→40 Jul-2004 split, →200 Sep-2013
  split, →100 on 2016-10-26 pure ratio change; current 1 ADS = 100 Series B). yfinance series
  (raw AND adjusted) are split-adjusted at source: **no ratio event appears as a return**
  (2016-10-26 raw return +0.85%; only >25% adjusted-return days are 1998-crisis prints, pre-
  window). Yahoo reports the 2016 change as split 2.0; TLKM's 5:1 appears 2013-08-28. The
  brief's "1 ADS = 20 shares" belief was stale (1995–2004 only).
- JISDOR added after a no-auth public-download probe (BI page's own XLSX export; 3,236 rows,
  2013-05-20 → 2026-10-02). Auxiliary series — the screen's FX leg stays USDIDR=X per the brief.
