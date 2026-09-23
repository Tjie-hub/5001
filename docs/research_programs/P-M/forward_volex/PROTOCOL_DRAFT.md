# FWD-PM-VOLEX-SN-001 — PROTOCOL (DRAFT v2 — REFUSED AT G1, 2026-09-23)

**Status:** **REFUSED AT G1** (2026-09-23). The D-053 pre-declared re-measurement FAILED its gate:
pre-2021 t 1.39 vs bar 2.87 (`REMEASUREMENT_RESULT_2026-09-23.md`). Never registered, no family slot
consumed, never opened. HYP-PM-0013 reserved-retired. Terminal: no re-cut is permitted. The title,
this block and the struck-through status line are the only changes; every other line is unchanged from
the v2 pinned in D-053 (sha256 `1bc868c73f1cbc4925eb06678202594ea80efa50821b9b908f9d9fc532eaa6c2`,
commit `f6ebd8f`).

~~**Status:** DRAFT v2. **Not registered. No family slot consumed. Not open.**~~
**v2 approved:** D-053 (Owner, 2026-09-23, Option B of
`OWNER_DECISION_PACKAGE_V1_FAMILY_2026-09-23.md`). Registration (D-054) is conditional on the
pre-declared re-measurement in §7 clearing its bar.
**Supersedes:** draft v1 of 2026-09-19 (sha256 `f85b78f1f51b9dbb…`, commit `c5469ec`), repaired per
the package's pre-registration audit, findings F-1 to F-8. v1 was never opened, so this is a revision,
not a supersession: there is no forward record on either side.
**Family (on registration):** `P-M · Cross-Sectional Volatility {V1}`, member 1, as HYP-PM-0013.

## 0. What changed from v1, and why

| | v1 | v2 | audit finding |
|---|---|---|---|
| Tradeability filter | "0 zero-vol in trailing 60" — but measured jointly with a forward-window filter | ex-ante only; re-measured (§7) | F-1 look-ahead |
| Evidence | 5 rows, 1 with committed code | one committed, hash-pinned script (§7) | F-2 |
| Entry | "first session after month-end, not at the open" | `close` of the first session after formation | F-3 |
| Endpoint | gross vs net unstated | gross increment, iid t primary | F-4 |
| Decision | 36m t>2.5 · 60m t>3.0 (power 0.26–0.54) | 48m single decision (§4) | F-5 |
| Mechanism | absent | §1 | F-6 |
| Sector source | unspecified | frozen CSV, sha-pinned | F-7 |
| Suspension/delisting in hold | silently dropped | last traded close, flagged | F-8 |

v1's dividend-draft rationale (why this candidate replaced `forward_dividend/`) stands. See
`../data_gaps/GAP1_SECTOR_2026-09-19.md` and `EXTENDED_PANEL_RESULT_2026-09-19.md`.

## 1. The claim

**Mechanism.** Leverage-constrained and retail IDX investors take exposure through high-volatility
names instead of leverage (a lottery-type demand). Short-sale constraints — IDX has no practical
short side — prevent the resulting overpricing from being arbitraged down.
- **No M-class assignment:** `ECONOMIC_MECHANISM_TAXONOMY` has no fitting class. This is referred to
  the CRO (D-053).
- **Persistence:** two barriers.
  - **Constraint barrier:** there is no short side on IDX.
  - **Capacity barrier:** the pooled version fails in the top-ADV tercile, so the effect is too small
    for the capital that could remove it. This has not been measured for the sector-neutral variant;
    §7 reports it.

**Direction.** Within each sector, the top-decile Parkinson-60 volatility names underperform the rest
of the sector over the following month, so the overlay increment is **positive**.

**Null.** Top-decile-volatility names earn the same forward return as their sector peers, so the
increment is ≤ 0.

**Refutation (R14).** *If high-volatility overpricing were not real, IDX names in their sector's top
volatility decile would earn the same forward return as the rest of the sector, and the overlay
increment would be zero or negative.*

This is the **low-volatility anomaly**, documented globally. It is a replication, not a discovery.

## 2. Frozen specification

All windows are per ticker and count the ticker's own settled bars (`is_final=1`) through formation
date `t` inclusive.

**Formation date `t`:** one per calendar month — the last **complete** session of the month. A session
is complete only if its priced-ticker count is ≥ 95% of the trailing-20-session median (the
`FWD-PM-VOLEX-001` guard). The historical re-measurement (§7) uses the last session of each month
present in the panel.

**Universe at `t`**, all conditions required:
- ≥ 60 bars of history through `t`
- `ADV60` = mean of `close × volume` over the trailing 60 bars ≥ **Rp 1,000,000,000**
- `close(t)` ≥ **Rp 50** and `volume(t)` > 0
- **zero** zero-volume bars among the trailing 60 (ex-ante only — nothing after `t` is inspected)

**Sector:** `sector_map_frozen_v2.csv` (780 tickers, sha256
`3c2c537a81269c87e70b950514dbe7c43be968a976454d9b29e5683d06c0f15d`). This is a snapshot of
`data_gaps/data/sector_map.pkl`, which is identical to production `ticker_sector` as of 2026-09-23.
Unlabelled tickers and tickers absent from the file form one `UNLABELLED` bucket. The file is never
updated during the test.

**Signal:** Parkinson-60 volatility, `sqrt( mean_60( ln(high/low)^2 ) / (4 ln 2) )`.

**Rule:**
- Within each sector with **≥ 10** universe names, exclude names whose signal is **≥ the sector's 90th
  percentile** (linear interpolation). Equivalently, hold names strictly below it.
- Sectors with fewer than 10 names are held whole.
- Held names are equal-weighted. The benchmark is the equal-weighted full universe.

**Entry:** `E` = the first session after `t`. Entry price = the ticker's **close on `E`**. A universe
name with no bar on `E` is not entered and is removed from **both** books for that month.

**Exit:** `E'` = the entry session of the next formation. Exit price = the ticker's **last close on or
before `E'`**. A name whose last bar falls before `E'` (suspended or delisted) exits at its last traded
close and is **flagged**, never dropped. Single-day moves beyond ±35% inside the hold are flagged and
reported, never dropped.

**Month validity:** a month counts only if the universe has **≥ 50** names **and** the held book has
**≥ 20**. Skipped months are recorded with the reason.

## 3. Endpoint

**Primary:** the monthly **gross** overlay increment, `mean(held return) − mean(universe return)`, in
%. It is summarised by its mean and an **iid t** over valid months.

**Reported, non-gating:**
- the **net** increment: each book is charged 0.60% round trip on its own one-way target-weight
  turnover, `0.5 × Σ|w_m − w_{m−1}|`;
- Newey-West(3) t;
- P(increment > 0);
- the increment by ADV60 tercile of the universe;
- counts of flagged exits.

Recorded per month, never pooled across specs.

## 4. Decision rule

| month count | action |
|---|---|
| 12 | report only. **Harm stop:** if the mean is below −0.20%/mo, the rule is abandoned. |
| 24 | interim report only. No decision. |
| **48** | **the single decision** |

At 48 months:
- **PASS:** one-sided t > **1.68** **and** mean ≥ **+0.10%/mo**.
- **FAIL:** mean < +0.10%/mo. This covers both a decayed effect and a wrong one; the failure is
  attributed to a single F-mode.
- **INCONCLUSIVE:** anything else. The claim stays parked and is never read as a pass.

Months 49–60 are post-decision monitoring, not a second gate.

**Power** (normal approximation, monthly sd 0.50–0.65):

| true effect %/mo | P(PASS) |
|---|---|
| 0 | 0.05 |
| 0.10 | 0.27–0.39 |
| 0.20 | 0.68–0.86 |
| 0.25 | 0.84–0.96 |

The 1.68 bar is justified because there is one frozen endpoint and one family member, and the search
penalty was paid in-sample (§7).

## 5. Expectations, stated in advance

The modern-era estimate is **+0.20%/mo** (2021-26, sector-neutral, n=67, t 3.31 — measured with v1's
look-ahead filter, so provisional until §7 reports). The full-panel figure is +0.25. Decay is
anticipated: the pooled version fell from +0.70 (2022) to +0.22 (2026) %/mo. A forward mean below
+0.10 is a FAIL by rule, not a judgement call.

## 6. Forbidden

- Changing the universe, sector file, exclusion decile, formation/entry/exit convention, validity
  thresholds, or endpoint after opening. Any change closes this spec and opens a successor; results on
  either side are never pooled (the 001→002 precedent).
- Reading the ledger to decide anything before 48 months, except the 12-month harm stop.
- Converting the overlay into a standalone long book and judging it on absolute return.
- Citing `FWD-PM-VOLEX-001` (a non-independent sibling) as evidence for this test, or the reverse.
- Filtering any other test's ledger by this rule (`BOOK_OVERLAY_POLICY` stays bound to VOLEX-001).

## 7. Pre-declared re-measurement (the last in-sample look — D-053)

- **Script:** `remeasure/remeasure_v2.py` implements §2–§3 exactly. Its sha256 is pinned in D-053
  **before** it runs. It runs **once**. Its output (`remeasure/RESULT.json`) is committed with its
  hash.
- **Data:**
  - pre-2021 bars regenerated by `remeasure/fetch_pre2021.py` — the original backfill was never
    committed and does not survive; the source may have revised history, and any difference is
    disclosed;
  - the settled DB corpus from 2021-07-05;
  - splits from `data_gaps/data/split_hist.pkl`, applied to pre-2021 rows only (`data_gaps/README`
    trap 1).
- **Gating window:** formations 2000-07 → 2020-12.
- **Bar (frozen):** pre-2021 **t ≥ 2.87** (Bonferroni-12, two-sided α=0.05, over the ~12 overlay looks
  already taken on pre-2021 data) **and** mean **≥ +0.10%/mo**.
- **Reported, non-gating:** the full panel, 2021-26 (known data, no confirmatory weight), and all §3
  secondaries.
- **If it clears:** D-054 registers HYP-PM-0013 and opens the forward test.
- **If it fails:** no registration; the result is recorded in `EXPERIMENT_LEDGER.jsonl`, this draft is
  marked REFUSED-AT-G1, and **no re-cut** is permitted.

## 8. Limitations

1. **This is an overlay increment, not a strategy.** Absolute performance depends on the underlying
   book, which lost money over 2021-26.
2. **Not deployable under the current mandate.** It needs ~100+ names (IR 0.39 at N=10), and it is
   −0.32%/mo inside IDX80. Registration buys knowledge (D-053).
3. **Pre-2021 evidence is a thinner, more liquid subset.** Zero-volume rates were 24–43% in 2003-09,
   and the ex-ante filter excludes more of the old panel.
4. **Survivorship:** the backfill contains only tickers listed today (~1.0–1.7%/yr attrition). The
   bias is plausibly conservative, but it is unmeasured.
5. **Sector labels** are a 2026 snapshot applied back to 2000 (non point-in-time).
6. **Capacity** of the sector-neutral variant is unmeasured. §7 reports ADV terciles.
