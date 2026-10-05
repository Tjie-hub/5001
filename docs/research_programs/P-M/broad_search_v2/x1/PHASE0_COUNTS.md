# PHASE0_COUNTS — X1 overnight screen · 2026-10-05 (rev 2: REVIEW_R1 applied)

Companion to `PHASE0_COUNTS.json` (machine record, written by `phase0_counts_x1.py` through
`research/tracking.py` — run_id, git sha, dataset fingerprint, `issuance=True` in params).
**Counts + unconditional statistics only; no signal value was computed and nothing was
conditioned on the signal.**

**Rev 2 changes per REVIEW_R1:** the valid-open restriction is **withdrawn** (rejected by the
reviewer — tick discreteness, not corruption; see `../A_OPEN_AUDIT_2026-10-05.md`). PRIMARY
outcome = LW book over **tick-eligible** members (ex-ante PIT rule: tick(close_d)/close_d ≤ 0.5%,
IDX tick schedule), all-rows estimate reported as a co-equal lens (§2.3). Bars updated for the
W0 additions: census 515 → **555** (+20 double-top from notes, +20 gap-battery placeholder).

## 1 · Data basis (disclosed every time)

- Corpus = **local `walkforward.db`** (the snapshot `walkforward-20261004-213000.db.zst`, sha
  `8408e91a…`, never reached this host). Panel `2000-03-30 → 2026-07-29` (T=6,548, N=958);
  **confirmation window frozen at 2026-07-29** per REVIEW_R1 §3; **2026-07-30 → latest is a
  pre-declared untouched holdout**, read once at R3 from the XPS snapshot.
- Signal legs from the committed CSVs (`x1/data/`, sha256 in `MANIFEST.json`): EIDO, TLK, SPY,
  USDIDR=X, ^JKSE, JISDOR (BI official, no-auth export).
- Outcome prices through `research.rulecard.data.load_extended_ohlcv(issuance=True)`.
- FX-leg holes: 485 IDX sessions lack the USD-converted JKSE leg (USDIDR=X gaps, incl. the
  located 214-day hole **2003-05-01 → 2003-12-01** — a Yahoo history hole, market open
  throughout; 10-day hole 2002-09; 26-day hole 2008-07). Those sessions cannot form β̂ pairs.

## 2 · Outcome construction (per REVIEW_R1 §2)

- **PRIMARY: tick-eligible book** — members with adv20 ≥ Rp 5bn as of close(d), `volume > 0` at
  D (D-065 §2 tradeability rule, no carry-forward), and `tick(close_d)/close_d ≤ 0.5%`
  (IDX tick schedule: <200:1; 200–500:2; 500–2000:5; 2000–5000:10; ≥5000:25). Ex-ante and PIT:
  computed from close(d) only, never from day-D prints.
- **Co-equal lens: all-rows book** — same universe without the tick rule (both series print in
  the same run; the pass rule reads the primary, and any material disagreement is disclosed).
- TLKM arm: TLKM's own tick fraction (≈0.13–0.25% at its price range) keeps it eligible on
  essentially all days.

## 3 · Usable (signal-calendar × outcome) days per arm

Exclusion buckets counted per arm: US-holiday/no-signal, FX-missing, β warm-up (<120 pairs),
k≥4 gap (excluded), signal-leg missing, outcome missing.

| arm | split | usable days (tick-eligible primary) | all-rows lens |
|---|---|---|---|
| X1-A EIDO→book | 2021-07-05 → **2026-07-29** (frozen end) | **1,168** | 1,168 |
| X1-B EIDO→book | 2010-05-01 → 2021-06-30 | **2,612** | 2,615 |
| X1-C TLK→TLKM | 2021-07-05 → 2026-07-29 | **1,165** | 1,165 |
| X1-D TLK→TLKM | 2010-05-01 → 2021-06-30 (brief split) | **2,604** | 3,887 full-history from 2001 (not tested) |
| X1-E SPY→book | 2021-07-05 → 2026-07-29 | **1,168** | 1,168 |
| X1-F SPY→book | 2010-05-01 → 2021-06-30 (brief split) | **2,618** | 4,388 full-history from 2001 (not tested) |

## 4 · Unconditional σ (open→close, per day) and MDE per arm

Bar: **|t| ≥ 3.2745** (exact two-sided E[max|Z|] at census N = 555 + 6 arms = 561; census 555
alone = 3.2714; the reviewer's "N ≈ 565 ⇒ ≈ 3.28" example includes C3's 2 arms, which
predeclare no earlier than 2026-10-20). MDE = bar × σ / √N, in bp per day per 1σ of signal.

| series | confirmation σ | discovery σ |
|---|---|---|
| LW book, tick-eligible (PRIMARY) | 1.182% (n=1,216) | 1.366% (n=5,332) |
| TLKM tick-eligible | 1.784% (n=1,213) | 1.459% (brief-split subset used) |
| all-rows book (co-equal lens) | 1.292% | 1.351% |
| IHSG (corpus; confirmation only) | 0.894% | — (discovery benchmark = ^JKSE, Yahoo, disclosed) |

| arm | MDE (bp/day per 1σ) |
|---|---|
| X1-A / X1-E | 11.3 |
| X1-B | 8.8 |
| X1-C | 17.1 |
| X1-D | 9.4 |
| X1-F | 8.7 |

Reading: the valid-open distortion is gone (the pre-2021 discovery σ returns from a spurious
2.58% to 1.37%, in line with the unrestricted book — the eligibility rule selects on
discreteness, not on day-D outcomes). The priors' predicted effect (Levy–Lieberman-style
overnight overreaction) lives at tens of bp per σ — the primary arm detects ≥11bp/1σ. The most
likely honest outcome remains "real but mostly absorbed at the open" (absorption share), which
the predeclared kill rule handles; the reviewer independently expects high absorption
(Hamao–Masulis–Ng's t 7.7–13.9 is a *next-open* result — exactly the uncapturable part).

## 5 · Survivorship (brief-standard line)

`history_long.db` is **absent on this host**, so the recorded memo-07 line stands as the
standard citation: **54 of 929 `ohlcv_long` names end before 2026; delisted names are purged
from Yahoo and enter no free panel**. Panel-derived confirmation: **0 of 541** pre-2021 names in
the merged (backfill+DB) panel die before 2026 — the discovery half is survivorship-biased by
construction (missing names are the worst performers; this biases an avoidance-side result
*against* the effect, the same sign note as S2).

## 6 · Validity gates

- **TLK ADS-ratio gate: PASS.** SEC-verified ratio history (20→40 Jul-2004 split, →200 Sep-2013
  split, →100 on 2016-10-26 pure ratio change; current 1 ADS = 100 Series B). yfinance series
  (raw AND adjusted) are split-adjusted at source: **no ratio event appears as a return**
  (2016-10-26 raw return +0.85%; only >25% adjusted-return days are 1998-crisis prints, pre-
  window). The brief's "1 ADS = 20 shares" belief was stale (1995–2004 only).
- JISDOR added after a no-auth public-download probe (BI page's own XLSX export; 3,236 rows,
  2013-05-20 → 2026-10-02). Auxiliary series — the screen's FX leg stays USDIDR=X per the brief.
