# G0 FREEZE — PEAD (post-earnings announcement drift, long top-SUE quintile) · 2026-10-23

**Status of this file.** It is a DRAFT D-entry plus the G0 freeze. It supersedes
`DECISION_DRAFT_PEAD_MECHANISM_2026-10-15.md` (kept unchanged as the 10-15 record). It was frozen **before any power
number was computed**, and `g0_pead_power.py` pins its sha256 and refuses to run if the file changes.
- Nothing has been appended to `DECISION_LOG.md` and nothing is registered.
- **No post-event return has been read.** The work so far read EPS, announcement dates, KSEI month-end market caps
  and counts only. The G0 adds the E−2 close (to scale the surprise), trailing characteristics, and return
  **dispersion** in a pre-event placebo window. Means are never printed or stored.
- Census stays at **613**.

**Approval.** The owner said "Go PEAD" on 2026-10-15. On 2026-10-23 they asked to "close and fix the gap" after the
completeness review found seven gaps in the 10-15 draft (stale census, survivorship in the holdout, unfrozen data,
unfrozen stop-rule numbers, no G0 protocol or script, no data checks, no distinctness measures). Mechanism acceptance
and the D-number are still the owner's, at filing.

---

### D-0xx · Mechanism accepted: post-earnings announcement drift; family Earnings-Information {EI} proposed; G0 frozen under the D-086 stop rule

- **Mechanism (unchanged from the 10-15 draft).** Under-reaction to a quantified surprise against a salient anchor,
  the analyst consensus (M5.2), with limited attention (I10) as the declared rival origination.
  - **Pre-declared sign:** positive surprise → positive excess return after the announcement. A flat or opposite
    result is not rescued.
  - **Rival separation:** I10 predicts the effect decays over the sample. The yearly-effect slope is a mandatory
    secondary, reported with its sign.
  - **Participant class and why unarbitraged:** domestic retail and local funds; IDX has no practical single-stock
    shorting, so only the long leg is tradeable, and it competes with the 0.60% round trip (D-082).
- **Family.** New **Earnings-Information {EI}**, opened only at first registration (D-028, PG-3).
- **Census.** HYP-PM-0022 went to D-105, so this arm would be **HYP-PM-0023 at N = 614, bar 3.3001** (the same N and
  bar the {LC} freeze computed for its unregistered arm). The bar is recomputed with the census tool at registration.

#### Frozen inputs (pinned by sha256 in `g0_pead_power.py`)

| Input | Pin | Note |
|---|---|---|
| Earnings file `data/earnings_dates_pit.json` | `d07f855ca529facd…` | Yahoo `get_earnings_dates(limit=60)`, 628 tickers: the 274 from 10-15 copied unchanged (source `~/scratch/pead_g0/earnings_dates.json`, sha `568a3e1704bd9ae1…`) + 354 fetched 2026-10-23 by `fetch_earnings_pit.py` |
| KSEI market caps `data/ksei_mcap_2009_2026.csv` | `e2c297dc18e7d43f…` | date, ticker, listed shares, price for every listed equity, 2009-03-31 → 2026-09-30, later-delisted names included. Derived from `~/idx_external/ksei/ksei_equity_holdings.csv` (sha `38c8a90b10546f06…`) |
| Price snapshot `walkforward-20260928-213012.db` (2 TB archive copy) | `db48e8d885189680…` (rehashed 2026-10-23) | See "Snapshot bytes" below |
| Pre-2021 backfill `hist_pre2021.pkl` | content fingerprint `fd9f54e34f1d7d61…` | Verified 2026-10-23 |

**Snapshot bytes.** `bs_common.SNAP_SHA256` (`10f9c97f…`) is the file's hash on 2026-09-29, when S1/S2 ran. The
archive's `SHA256SUMS`, written at the 10-13 move, says `db48e8d8…`. The bytes changed in between, probably through a
read-write open that checkpointed the WAL; no script ever verified the 09-29 hash. PEAD has never read this file, so
the G0 pins **today's bytes**, records a content fingerprint of the loaded panel, and refuses to report if the file's
size or mtime changes during the read.

#### Data checks (`pead_data_checks.py` → `DATA_CHECKS_20261023T093923.json`; EPS and dates only)

| Check | Result | Decision |
|---|---|---|
| Fetch status | 628 tickers: **87 with rows**, 513 empty, 28 errors; 3,037 rows, 2,788 with both EPS fields | Yahoo has consensus history for the 87 analyst-covered names only, all currently listed. The 354 added names returned nothing |
| C1 EPS basis | Median reported / consensus: Q1 0.98, H1 1.00, 9M 1.00, FY 1.00. Median \|EPS\| vs same-year Q1: H1 1.02, 9M 1.01, FY 1.09 | Both fields are single-quarter on the same basis. **Not** the year-to-date mix IDX statements use. No adjustment |
| C2 split units | 29 splits with factor ≥ 2: **0 look unrestated**; 25 are closer to 1 than to the factor, and 4 show higher EPS after the split (growth) | EPS history is on the current share basis, the same as the split-adjusted price panel. `EPS_SPLIT_ADJUST = False` |
| C3 duplicates | 41 rows within 20 days of the same ticker's previous row | Keep the first row of each run |
| C4 consensus | est missing 182, rep missing 233, est = rep exactly 72 of 2,788 (2.6%) | No sign of a consensus revised to the actual. Missing-field rows excluded and counted |
| KSEI sanity | BCIC 2010–2017 carries 676 trillion listed shares (89% of the market) | Month-rows worth > 25% of the month total are dropped (BCIC only); the fetched universe still covers the filtered ranking (0 missing) |

#### Survivorship (measured; the gap the 10-15 draft did not see)

| Year-end | Covered names, share of KSEI top-200 (count / mcap) | Price panel, share of top-200 traded that year (count / mcap) |
|---|---|---|
| 2009 | 0.17 / 0.68 | 0.71 / 0.95 |
| 2012 | 0.26 / 0.68 | 0.78 / 0.94 |
| 2015 | 0.23 / 0.64 | 0.77 / 0.94 |
| 2018 | 0.18 / 0.64 | 0.81 / 0.95 |
| 2020 | 0.19 / 0.57 | 0.85 / 0.95 |
| 2023 | 0.21 / 0.47 | 0.98 / 0.99 |
| 2025 | 0.22 / 0.35 | 1.00 / 1.00 |

- The events come only from the 87 covered, still-listed names. Before 2021 the price panel (and so the liquid book)
  lacks 15–30% of each year's top-200 names (5–6% of market cap), mostly later-delisted ones.
- Re-fetching cannot close this: Yahoo returns no consensus for delisted or uncovered names.
- **The design neutralises it instead** (pass condition (c) below): the top quintile must also beat the middle
  quintiles of the **same covered names in the same quarter**. That contrast shares the survivor selection on both
  sides. The liquid-book excess remains the tradeable primary.

#### Frozen design

| Item | Frozen value |
|---|---|
| Events | Rows with both EPS fields, deduplicated (first of any same-ticker run < 20 days apart) |
| Event day E | Announcement converted to WIB. Before 16:00 on a session → that session; otherwise the next session |
| Eras | **Holdout** E in [2009-04-01, 2021-07-04]; **recent** E in [2021-07-05, 2026-09-16]. Before 2009-04 has no point-in-time universe and is excluded (counted). This replaces the draft's 2005 start |
| Eligibility at E−2 | KSEI rank ≤ 200 at the last month-end strictly before session E−2, **and** `liquid_idx_v1` true at E−2 (ADV20, price, traded-days, no split-band move) |
| Surprise | SUE = (reported − consensus) / close(E−2), on the split-adjusted, wealth-corrected panel |
| Top quintile | SUE ≥ the 80th percentile of eligible events in the same calendar quarter of E. Quarters with < 10 eligible events are dropped (counted) |
| Outcome (G1 only) | Compounded return on sessions **[E+2, E+60]** (59 returns: close of E+1 to close of E+60) minus the compounded equal-weight liquid book (`events._book`) on the same sessions, **minus 0.60%**. ≥ 80% session coverage. Fixed horizon: a ticker's next announcement inside the window does not truncate it (share reported) |
| Inference | One value per announcement calendar month (mean of that month's top-quintile events). t = mean / (sd / √M) |
| Pass (G1) | (a) pooled t ≥ bar (3.3001 at N = 614, recomputed at registration); **and** (b) both eras' means > 0; **and** (c) survivor-neutral contrast: top quintile minus the Q2–Q4 events of the same quarter, gross, monthly-clustered mean > 0 pooled |
| Secondaries (reported with sign, never rescue) | Bottom quintile vs book; top minus bottom; the I10 decay slope of the yearly effect; 20- and 120-session horizons only if the primary passes |
| Effect floor | **2.0%** net over the 59-session window. From external literature (long-leg 60-day PEAD about 1–3% in developed markets, larger in emerging markets); no IDX outcome informed it |
| Minimum power | **20%** at the floor (D-086 stop rule) |

#### Distinctness (computed at G0 from pre-event characteristics only; no outcome)

At E−2, for the eligible events, the G0 reports the Spearman correlation of SUE with:
- 52-week-high proximity (close / 252-session max high; the factor-zoo survivor);
- Parkinson-60 range volatility (the VOLEX-001 measure);
- log KSEI market cap (size);
- the HYP-PM-0010 {T1} trend state (EMA20 slope over 10 > 2%, ER20 ≥ 0.30, ≥ 70% of 20 closes above EMA20).

It also reports the share of top-quintile events vs all eligible events in the hi52 top 20%, the Parkinson top
decile and the T1 state. **If any |Spearman| > 0.50, G1 must report the top-quintile effect controlling for that
characteristic** (same-quarter regression of the outcome on the top-quintile flag plus the characteristic), and the
controlled coefficient must keep the sign.

#### Power method (G0; frozen)

1. For every top-quintile event, take a **placebo window** of 59 returns on sessions **[E−70, E−12]**. It ends
   before the announcement, so the event reaction and any run-up in the last two weeks are outside it.
2. Compute the placebo excess as in the outcome definition (no cost; cost does not change dispersion), assign it to
   E's calendar month, and take the cross-month sd of monthly means: **SE = sd / √M**.
3. Power = Φ(floor / SE − bar), one-sided because the sign is pre-declared. MDE at 80% = (bar + 0.8416) × SE.
   Per-era SE and power are reported but are **not** the stop metric.
4. Only dispersion, SE, MDE, power and counts are printed or stored. **No mean of any window is output.**
5. **If pooled power < 20%, the stop rule FIRES.** The arm is **WITHDRAWN before registration and not counted**
   (precedents D-087, D-094, D-097, D-102, D-110). {EI} is not opened.
6. **If power ≥ 20%:** the owner's mechanism D-entry, then registration as HYP-PM-0023, then one G1 run.

#### Disclosed pre-run arithmetic (assumption, not a measurement)

- 2,788 usable rows, minus pre-2009 and the eligibility gates, leave perhaps 1,800–2,200 eligible events, so
  360–440 top-quintile events over about 190 announcement months.
- With a 59-session excess sd of 15–20% for large caps, SE ≈ 1.2–1.6% and MDE ≈ 5–7%. **Power at the 2% floor is
  roughly 2–8%. The stop rule is expected to fire.** This G0 exists to confirm that before any G1 effort is spent.

#### Disclosures

- Yahoo's EPS and consensus are not guaranteed point-in-time. A consensus revised after the fact would make
  surprises look cleaner than they were tradeable. C4 found no sign of it, but it cannot be ruled out.
- Yahoo timestamps carry about ±1 session of error (10-15 volume check). The outcome window starts at E+2 for that
  reason.
- Events maturing after 2026-09-16 (E+60 beyond the snapshot cut) are counted but cannot enter G1 on this snapshot.
- The 10-15 draft's volume check is the only look at the event sessions so far, and it read volume, not returns.

**Amendment.** Only by a superseding D-entry.
