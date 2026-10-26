# {FQ} point-in-time rule — DRAFT v3 (2026-10-26)

**Status: DRAFT v3 — for owner approval (D9).** Propose-only. **Not frozen. No `DECISION_LOG` entry. No {FQ}
mechanism entry.** If the owner approves it (D9), this text becomes the frozen {FQ} PIT rule and precedes any {FQ}
mechanism D-entry. v1 (`11_FQ_PIT_RULE_DRAFT_2026-10-21.md`) and v2 (`11_FQ_PIT_RULE_DRAFT_V2_2026-10-25.md`) are
untouched. v3 incorporates the owner's 2026-10-26 approval of D1–D8 as recommended (v2 §10).

**No outcome read.** Nothing here computes a return, spread, IC or factor score, and nothing joins fundamentals to
prices. The new facts in v3 come from `fin.db` metadata (`period_end`, `quarter`, counts) and from the late-filer CSV.

Provenance tags as in v2: **[P]** primary read · **[P\*]** primary names it, own text not read · **[S]** secondary ·
**[U]** unverified.

---

## 0. What changed from v2

| # | Change | Where |
|---|---|---|
| 1 | D1–D8 folded in as approved: H1 uniform 31 Oct; Q1/Q3 kept with disclosure; +1 month buffer; availability flag; COVID override table; "as first reported, narrow evidence"; Regime A backward, flagged | §1, §2, §5 |
| 2 | **New, D10.** Issuers with a fiscal year ending **March or September** are under-lagged by ~61 days on their annual and semi-annual statements. The vendor maps every issuer onto calendar quarters, so nothing in the data marks them | §3 |
| 3 | **New, D11.** v2's "deadline in force" did not say what happens when a deadline falls on a non-trading day. It does: FY2024 moved to 8 Apr 2025 [S], and the Q3-2026 deadline (31 Oct 2026) is a Saturday | §1 R3 |
| 4 | **New, D4a.** How the availability flag is applied: withhold the issuer-period, keep the issuer in the universe. v2 left this open, and dropping issuers would condition the universe on a later-known event | §2 |
| 5 | Late-filer list built (`12_FQ_LATE_FILERS_2026-10-26.csv`): 6 periods, all [S]; coverage measured | §2 |
| 6 | Regime A: the data starts at period end **2006-12-31**, not 2008. 30 issuer-periods (≤ 24 names per date) predate 2008; they take the Regime A treatment | §1 R6 |
| 7 | v2 §6 said texts (i) and (ii) "block the freeze". With D2 and D7 approved, both gaps are covered by stated conservative assumptions, so **they no longer block a freeze**; they can only tighten the rule later (R8). D8 retries 2026-10-26: still unreachable | §4 |

---

## 1. The rule (candidate frozen text)

<!--CANDIDATE-FROZEN-START-->
**R1 — Scope.** Vendor fundamentals in `~/idx_external/stockbit_fin/fin.db` (Stockbit; pinned by
`SHA256SUMS_2026-10-25.txt`), discrete quarters keyed by `period_end`. Every `period_end` in the store is a
Mar/Jun/Sep/Dec month end and `quarter` equals the calendar quarter (verified 2026-10-26: 43,987 issuer-period rows
over 957 tickers, 2006-12-31 … 2026-09-30).

**R2 — Availability.** The values of issuer-period (i, P) may enter a cross-section dated D only if
**D ≥ usable_from(P)** and (i, P) is **not flagged** under R5.

**R3 — Lag.** usable_from(P) = **deadline\*(P) + 1 calendar month** (month-end convention: a month-end deadline maps
to the next month end), where deadline(P) by the month of `period_end` is:

| period_end | Statement role (calendar-year issuer) | deadline(P) | usable_from (no shift) | Lag | Basis |
|---|---|---|---|---|---|
| 31 Mar | Q1 interim, unattested path | 30 Apr | **31 May** | 61 d | D2 (exposure disclosed) |
| 30 Jun | H1, **audited path for every issuer** | 30 Sep | **31 Oct** | 123 d | D1 |
| 30 Sep | Q3 interim, unattested path | 31 Oct | **30 Nov** | 61 d | D2 (exposure disclosed) |
| 31 Dec | FY, audited | 31 Mar | **30 Apr** | 120 d | — |

deadline\*(P) is deadline(P) after the shift chosen in **D11** (recommended: moved to the next IDX trading day when it
falls on a non-trading day, including exchange-announced holiday shifts).

**R4 — COVID overrides (D5).** For FY2019 through FY2022, deadline(P) is the relaxed deadline in the v2 §4 table
(FY2019 31 May 2020 · Q1-2020 30 Jun 2020 · H1-2020 31 Oct 2020 · Q3-2020 30 Nov 2020 · FY2020 31 May 2021 · Q1-2021
30 Jun 2021 · H1-2021 31 Oct 2021 · Q3-2021 30 Nov 2021 · FY2021 30 Apr 2022 · Q1-2022 30 Jun 2022 [U] · H1-2022
31 Oct 2022 · Q3-2022 30 Nov 2022 [U] · FY2022 30 Apr 2023), and usable_from follows R3 from it. The two [U] rows
assume Kep-00089/BEI/10-2020 was still active; they stay at that conservative assumption until its end date is read.
From Q1-2023 on, the R3 table applies.

**R5 — Availability flag (D4, D4a).** (i, P) is **flagged** if an IDX late-filing sanction announcement for period P
names issuer i at any stage (written warning I onward, fine, or suspension). A flagged (i, P) is **withheld** from
every cross-section. Issuer i **stays in the universe** and carries its most recent unflagged issuer-period whose
usable_from ≤ D. The flag never removes an issuer from a return universe, and any staleness limit belongs to the
mechanism's G0, not to this rule. Source of record: `12_FQ_LATE_FILERS_2026-10-26.csv`, extended only by
appending rows with their source URL and tag.

**R6 — Labels carried by every {FQ} row.**
- `regime_a_unverified` — period_end < 2011-06-30 (Kep-36/PM/2003 era; incl. the 30 pre-2008 issuer-periods). The R3
  table is applied backward (D7).
- `values_as_first_reported_narrow` — every row (D6: 70/70 on 3 large issuers; small caps and pre-2012 untested).
- `override_unverified` — the two [U] rows of R4.
- `flag_coverage` — `covered` for the six periods in the CSV (Q3-2024 … FY2025), `uncovered` for every other period.

**R7 — Non-calendar fiscal years (D10).** As decided under D10 (§3).

**R8 — Change control.** The rule changes only by a superseding, dated version approved by the owner. A change may
**tighten** a lag on primary evidence (e.g., the I-E tiers, Kep-36/PM/2003, Kep-00089's end date, issuer attestation
notices). No version applies retroactively to a {FQ} G0 or registration frozen under an earlier version.
<!--CANDIDATE-FROZEN-END-->

---

## 2. The availability flag (D4 approved; D4a new)

**Coverage of the list as built** (`12_FQ_LATE_FILERS_2026-10-26.csv`, 417 rows = one row per sanction event):

| Period | Distinct names | Stage listed | Known unfiled at the boundary | Completeness |
|---|---|---|---|---|
| Q3-2024 | 46 | suspension (day 91) | — | names unfiled at day 90 only |
| FY2024 | 128 | written warning I (~day 17 after the 8 Apr 2025 deadline) | — | listed **before** the buffer boundary: some may have filed by day 30 → over-withheld (conservative) |
| Q1-2025 | 59 | suspension (day 91) | — | day-90 names only |
| H1-2025 | 52 | suspension (day 91) | — | day-90 names only |
| Q3-2025 | 48 | suspension (day 91) | — | day-90 names only |
| FY2025 | 77 | warning III + fine (13), suspension (71) | 88 at day 60 | 11 of the 88 unnamed (day-60 article named 10 of 85) |

The 7 repeated (ticker, period) pairs are the same issuer at two stages (FY2025 day-60 list and day-91 suspension),
not errors. 83 of 142 names appear in ≥ 2 periods and 39 in all six: the tail is chronic.

**D4a — how the flag is applied. Recommendation: withhold the issuer-period, keep the issuer (R5).**
- Withholding only makes a late filer's fundamentals **staler**. It cannot let unpublished numbers into a
  cross-section, so it is the PIT-safe direction even though the flag is learned after D.
- **Dropping the issuer** instead (v2's wording "drops an issuer-period" was ambiguous) would remove names from the
  return universe because of an event known only later — late filing is a distress marker — which is a selection on
  the future. Not recommended.
- Withholding is permanent: without filing dates the rule cannot know when a late statement became public. IDX
  suspension-lift announcements could supply that date later (tightening under R8).

**Residuals to disclose with any {FQ} result:**
1. **Uncovered periods** (everything before Q3-2024, plus the 2026 periods: 74 of the 80 period ends in the store): late filers are not flagged. The share
   unfiled at the buffer boundary is **≥ 8.8 %** of required filers on the one period measured (FY2025); unknown earlier.
2. **Covered periods are incomplete**: issuers that filed between day 30 and day 90 are absent from the day-91 lists.
3. **Asymmetry across time**: flagged rows exist only in 2024–2026. A {FQ} G0 must report whether its result depends
   on the covered window (e.g., with and without it), because the two windows are treated differently.

---

## 3. Non-calendar fiscal years (D10, new)

v1 said to "apply the same month offsets to the issuer's own period ends; the pilot's period metadata should be used
to confirm fiscal calendars." **The metadata cannot do that:** in `fin.db` every `period_end` is a calendar quarter
end and `quarter` is always the calendar quarter (Mar→1, Jun→2, Sep→3, Dec→4, 43,987 rows). 34 tickers have gaps in
their months, but gaps are missing periods (e.g., semi-annual reporters with Jun/Dec only), not shifted calendars.

**Where the calendar table is wrong.** Applying the statute (annual: audited, month 3; semi-annual: up to month 3 on
the audited path, D1's logic) to each possible fiscal-year end:

| Fiscal year ends | Its annual period_end → needed usable_from | Table gives | Its H1 period_end → needed | Table gives | Result |
|---|---|---|---|---|---|
| 31 Dec | 31 Dec → 30 Apr | 30 Apr | 30 Jun → 31 Oct | 31 Oct | correct |
| 30 Jun | 30 Jun → 31 Oct | 31 Oct | 31 Dec → 30 Apr | 30 Apr | **correct** (coincides) |
| 31 Mar | 31 Mar → 31 Jul | **31 May** | 30 Sep → 31 Jan | **30 Nov** | **~61 days too early on both** |
| 30 Sep | 30 Sep → 31 Jan | **30 Nov** | 31 Mar → 31 Jul | **31 May** | **~61 days too early on both** |

Their Q1/Q3 interims fall on Jun/Dec period ends, where the table is longer than needed (safe).

**How many issuers this affects is unknown.** Nothing reachable here lists IDX issuers' fiscal-year ends. The vendor
data cannot reveal them.

| Option | What it does | Cost |
|---|---|---|
| **(a) Exception list (recommended)** | Identify Mar/Sep fiscal-year issuers from issuer sources (IDX company profile "tahun buku", annual report covers; owner browser for IDX). Give their Mar/Sep period ends the annual/H1 lags above. Until the list exists, disclose the residual. | Needs a list; small residual meanwhile |
| (b) Universal 4-month lag | Treat every period as possibly annual: usable_from = period_end + 4 months for all | Q1/Q3 lanes lose 2 months for every issuer (≈ v2's rejected outer bound) |
| (c) Ignore | Keep the calendar table for all | Anti-conservative for an unknown set |

---

## 4. D8 primary texts — status after the 2026-10-26 retries

From `12_FQ_PIT_FOLLOWUPS_2026-10-26.md` §3: idx.co.id still **403** (I-E PDF; Wayback copy 404); Kep-36/PM/2003
still has no URL; the COVID-era IDX decisions are known only through news [S]. Kep-00089's end date is still
unverified. Owner-browser list is in that file.

**Why this no longer blocks a freeze.** Each missing text now sits behind a conservative assumption the owner approved:
I-E Q1/Q3 tiers → D2 (kept, disclosed); Kep-36/PM/2003 → D7 (R3 applied backward, labelled); Kep-00089's end → R4's
[U] rows held at the longer deadline. Reading any of them can only shorten a lag (R8), never lengthen one, **except**
if Regime A's deadlines turn out *later* than Regime B's, which every secondary source contradicts. That is a
judgment call for the owner. If you would rather keep v2's position, D9 waits on D8.

---

## 5. Test vectors (for the implementation; not an outcome read)

Calendar-year issuer; D11 = (a) trading-day shift; D10 = (a) with no issuer on the exception list.

| Period | deadline | deadline\* | usable_from | Note |
|---|---|---|---|---|
| Q1-2025 (2025-03-31) | 2025-04-30 | 2025-04-30 | **2025-05-31** | base |
| H1-2025 (2025-06-30) | 2025-09-30 | 2025-09-30 | **2025-10-31** | D1 |
| Q3-2025 (2025-09-30) | 2025-10-31 | 2025-10-31 | **2025-11-30** | base |
| FY2024 (2024-12-31) | 2025-03-31 | 2025-04-08 [S] | **2025-05-08** | Lebaran shift (D11) |
| FY2025 (2025-12-31) | 2026-03-31 | 2026-03-31 | **2026-04-30** | base |
| Q3-2026 (2026-09-30) | 2026-10-31 (Sat) | 2026-11-02 | **2026-12-02** | weekend shift (D11) |
| FY2019 (2019-12-31) | 2020-05-31 (Sun; 1 Jun Pancasila holiday [S]) | 2020-06-02 | **2020-07-02** | R4 override + shift (v2 §4 showed 30 Jun nominal) |
| Q1-2022 (2022-03-31) | 2022-06-30 | 2022-06-30 | **2022-07-31** | R4 [U] → `override_unverified` |
| H1-2010 (2010-06-30) | 2010-09-30 | per calendar | **2010-10-31** | `regime_a_unverified` |
| FY2025, issuer ALTO | — | — | **withheld** | flagged (R5); ALTO stays in the universe on its last unflagged period |

The shift needs an IDX trading-day calendar. The settled session dates in the 5001 DB give one for recent years
(dates only; no price is read). Checked 2026-10-26: no sessions 28 Mar – 7 Apr 2025 and trading resumes 8 Apr,
matching the [S] shifted FY2024 deadline. The DB has no 2020 sessions, so earlier years need an IDX holiday list.
The implementation should ship these rows as unit tests.

---

## 6. Decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| **D4a** | Flag application | **Withhold the issuer-period, keep the issuer in the universe** (§2) |
| **D10** | Mar/Sep fiscal-year issuers | **(a) exception list from issuer sources; disclose until built** (§3) |
| **D11** | Deadline on a non-trading day | **(a) shift to the next IDX trading day, then +1 month** (R3; costs 1–10 days in shift years) · (b) nominal + flat 10 days every period · (c) ignore shifts (rows can enter ~22 days after a shifted deadline) |
| **D9** | Freeze | Approve **this v3, with D4a/D10/D11 as decided**, as the frozen {FQ} PIT rule. Freezing does not wait on D8 (§4) unless you prefer v2's position |

**Proposed `DECISION_LOG` text (not filed; the owner files and numbers it):**

> **D-1xx · {FQ} point-in-time rule frozen (v3, 2026-10-26).** The owner approves
> `P-M/data_acquisition/11_FQ_PIT_RULE_DRAFT_V3_2026-10-26.md` §1 (R1–R8) as the frozen {FQ} PIT rule, with D1–D8 as
> recorded in v2 §10 and D4a = [ ], D10 = [ ], D11 = [ ]. Residuals disclosed with every {FQ} result: Q1/Q3 attested-path
> exposure (D2); uncovered and incomplete late-filer flag (§2); narrow restatement evidence (D6); Regime A unverified
> (D7); two [U] COVID rows; non-calendar fiscal years until the exception list exists (D10). No {FQ} mechanism is
> accepted by this entry, and no outcome has been read. Changes only by a superseding version (R8), never
> retroactively to a frozen {FQ} G0.

---

## 7. Owner response (2026-10-26)

The owner chose the recommended option on all four: **D4a** withhold the issuer-period, keep the issuer · **D10** (a)
exception list from issuer sources, disclosed until built · **D11** (a) shift to the next IDX trading day, then
+1 month · **D9** freeze now, without waiting on D8.

The frozen text is `13_FQ_PIT_RULE_FROZEN_V3_2026-10-26.md` (R1–R8 with these choices filled in), sha256
`a02ad16fb2670bbf7bcc1ebf1935ecdf532886ff9497f4de002a3b1b50db6ff1`. The R7 list `13b_FQ_FISCAL_YEAR_EXCEPTIONS.csv`
was created empty (header only). The `DECISION_LOG` entry is the owner's to file and number.

---

## Sources

As v2 (OJK [P] texts; news [S] list), plus: `12_FQ_LATE_FILERS_2026-10-26.csv` (source URL per row);
`12_FQ_PIT_FOLLOWUPS_2026-10-26.md` §3 (reachability, 2026-10-26); `fin.db` metadata queries (read-only, 2026-10-26:
period_end months, quarter mapping, era counts).
