# TIMING — calendar and signal timing contract (cross_asset / X1) · 2026-10-05

Companion to the X1 brief (`ZCODE_BRIEF_X1_OVERNIGHT_2026-10-05.md` §P0-C). Every rule here is
part of the predeclaration: nothing below may be revised after outcome data is read.

## 1 · Clock facts (verified)

- **WIB = UTC+7, no DST** (Indonesia does not observe DST).
- **US Eastern**: UTC−4 (EDT) / UTC−5 (EST). DST begins the 2nd Sunday of March, ends the 1st
  Sunday of November; both transitions fall on Sundays, when no US session runs, so **every US
  session has a uniform offset: WIB = ET + 11 (EDT) or ET + 12 (EST)**.
- US regular session 09:30–16:00 ET ⇒ **20:30–03:00 WIB next calendar day (EDT) or 21:30–04:00
  WIB (EST)**.
- IDX regular session 09:00–16:00 WIB (two sessions + the end-of-day pre-closing / closing call
  auction; the official close prints ≈ 16:00 — the walkforward finalization job waits until
  ≥ 16:05 WIB before reading final bars).
- Yahoo daily bars carry exchange-local **date** stamps; the close of date *t* is observable only
  after that market's close of date *t*. Yahoo FX (`USDIDR=X`) daily bar stamped *t* carries the
  aggregate close of UTC day *t* ≈ **07:00 WIB on t+1**.

## 2 · Session diagram (normal day, EDT shown)

```
WIB day d   09:00          16:00   20:30                         03:00 | 09:00
            |— IDX session d —|     |——— US session d ————————————|     |— IDX session D —
                                          US close(d) = 03:00 WIB on calendar day d+1 = day D
```

- **D = the next IDX session after d** (usually d+1 calendar day; d+3 across a weekend).
- Signal inputs: EIDO/TLK/SPY close of US session d (03:00/04:00 WIB on day D); ^JKSE close(d)
  (16:00 WIB day d); USDIDR=X bars stamped d−1 and d (≈07:00 WIB d and ≈07:00 WIB D).
- **CONTRACT: every signal input carries a timestamp ≤ 08:45 WIB on day D.** The latest input is
  the FX bar (≈07:00 WIB D). The outcome leg (open(D) → close(D), from the corpus) begins
  09:00 WIB D — strictly after every signal input.

## 3 · Construction with daily bars (the stagger, declared)

- `r_JKSE,USD[close(d−1)→close(d)] = (JKSE_d / JKSE_{d−1}) · (FX_d / FX_{d−1}) − 1`, with FX bars
  stamped d−1 and d. The FX leg's effective timestamp lags the equity legs by up to ~15 h — this
  is the daily-FX convention; **both legs are known ≤ 08:45 WIB day D**, and the identical stagger
  applies to every historical pair inside β̂, so the estimator is internally consistent.
- `r_EIDO[US close(d−1) → US close(d)]`: consecutive adjusted US closes (EIDO/TLK/SPY CSVs).
- **β̂_d**: rolling 250-pair OLS of the EIDO (or TLK) leg on the JKSE-USD leg, pairs ending ≤ d;
  expanding window until 250 pairs exist (minimum 120 pairs to produce a β̂), then rolling 250.
- **Standardization**: R standardized by the trailing-250-pair σ of R (same expanding/minimum
  rule). SPY arm: raw r_SPY standardized identically (no hedge).

## 4 · Holiday and gap rules (predeclared)

1. **US holiday** (no US close inside (close(d), 08:45 WIB day D]) ⇒ day D has **no signal** and
   is excluded from the screen (counted in PHASE0_COUNTS.md).
2. **IDX holiday** (k ≥ 2 US sessions between close(d) and 08:45 WIB day D) ⇒ the signal spans
   every US session in the gap. Aggregation: `R_D = [compounded r_EIDO over the k US sessions] −
   β̂_d · r_JKSE,USD[close(d−1)→close(d)]`, standardized by the trailing-250 **daily** σ (no √k
   scaling — declared, conservative: it treats a k-day compounded residual as one daily-scale
   observation). **k ≥ 4 gaps are excluded** (Idul Fitri weeks). A k=1-only regression is printed
   in the same run as a disclosed sensitivity line (not an arm, not gating).
3. **US half-days** (13:00 ET close: the day after Thanksgiving, Christmas Eve, occasional July 3)
   ⇒ normal handling (close still ≤ 08:45 WIB day D); count disclosed in PHASE0_COUNTS.md.
4. **Session-hour variants** — outcome side only; the screen uses each session's own open/close
   prints, so no timing adjustment is ever needed. Listed per the brief:
   - **Ramadan** (IDX shortens sessions; exact hours **not verified from this host** —
     idx.co.id is Cloudflare-blocked to both WebFetch and the web reader): 2010-08-11–09-09,
     2011-08-01–08-29, 2012-07-20–08-18, 2013-07-09–08-07, 2014-06-28–07-27, 2015-06-18–07-17,
     2016-06-06–07-05, 2017-05-27–06-24, 2018-05-16–06-14, 2019-05-06–06-04, 2020-04-24–05-23,
     2021-04-13–05-12, 2022-04-03–05-01, 2023-03-23–04-20, 2024-03-11–04-09, 2025-03-01–03-30,
     2026-02-18–03-19 (Islamic calendar, ±1 day).
   - **COVID**: 2020-03-23 trading halt; shortened sessions from 2020-03-30 until restoration in
     2021 (exact hours/restoration date not verified from this host).
5. **Data-edge rules** — day D enters an arm only if (i) a signal exists per rules 1–2, (ii) the
   outcome open/close exist and pass the D-065 §2 tradeability rule (`volume > 0`, no
   carry-forward rows), (iii) the book is non-empty that day.

## 5 · Verified vs not verified

- **Verified**: DST arithmetic; close stamps in the acquired CSVs (`cross_asset/MANIFEST.json`);
  the 08:45 WIB cutoff against those stamps; the corpus session calendar 2021-07-05 → 2026-07-29
  (`trading_calendar`, 1,216 sessions, local walkforward.db).
- **Not verifiable from this host** (idx.co.id Cloudflare-blocked to WebFetch and the web reader —
  reported per the standing rule, not worked around): exact pre-closing/closing-auction minutes,
  exact COVID-hours and Ramadan-hours schedules. The screen reads no intraday timestamps, so these
  affect documentation only. The close-fill mechanism for the economics section is the IDX
  pre-closing / closing call auction; the realistic fill assumption is a market-on-close order
  filled at the official close with fees + ½-tick floor (no spread cost inside the auction), with
  slippage risk acknowledged for imbalanced auctions.
