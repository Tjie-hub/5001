# {FQ} point-in-time rule — FROZEN v3 (2026-10-26)

**Status: FROZEN on owner approval (D9, 2026-10-26).** Text of `11_FQ_PIT_RULE_DRAFT_V3_2026-10-26.md` §1 with the
owner's choices D4a = withhold/keep issuer, D10 = exception list, D11 = next trading day. Rationale, coverage, test
vectors and residuals: the v3 draft (§2–§5). Amendment only by a superseding, dated version (R8). This file is pinned
by sha256 in its `DECISION_LOG` entry; any edit breaks the pin.

<!--FROZEN-START-->
**R1 — Scope.** Vendor fundamentals in `~/idx_external/stockbit_fin/fin.db` (Stockbit; pinned by
`SHA256SUMS_2026-10-25.txt`), discrete quarters keyed by `period_end`. Every `period_end` in the store is a
Mar/Jun/Sep/Dec month end and `quarter` equals the calendar quarter (verified 2026-10-26: 43,987 issuer-periods over
957 tickers, 80 period ends, 2006-12-31 … 2026-09-30).

**R2 — Availability.** The values of issuer-period (i, P) may enter a cross-section dated D only if
D ≥ usable_from(i, P) and (i, P) is not flagged under R5.

**R3 — Lag.** usable_from(i, P) = deadline\*(i, P) + 1 calendar month. Month arithmetic: a month-end date maps to the
next month end; any other date maps to the same day of the next month (or that month's end if the day does not
exist). deadline\*(i, P) is deadline(i, P) moved to the next IDX trading day when it falls on a non-trading day
(weekend, public holiday, or exchange closure). Trading calendar: the settled session dates in the 5001 DB where they
exist (dates only); the IDX holiday calendar otherwise. For an issuer not on the R7 list, deadline(i, P) is:

| period_end | deadline(i, P) | usable_from without a shift |
|---|---|---|
| 31 Mar | 30 Apr (Q1 interim, unattested path) | 31 May |
| 30 Jun | 30 Sep (H1, audited path for every issuer) | 31 Oct |
| 30 Sep | 31 Oct (Q3 interim, unattested path) | 30 Nov |
| 31 Dec | 31 Mar (FY, audited) | 30 Apr |

**R4 — COVID overrides.** For these periods deadline(i, P) is replaced by the relaxed deadline below, and R3 applies
to it: FY2019 31 May 2020 · Q1-2020 30 Jun 2020 · H1-2020 31 Oct 2020 · Q3-2020 30 Nov 2020 · FY2020 31 May 2021 ·
Q1-2021 30 Jun 2021 · H1-2021 31 Oct 2021 · Q3-2021 30 Nov 2021 · FY2021 30 Apr 2022 · Q1-2022 30 Jun 2022 [U] ·
H1-2022 31 Oct 2022 · Q3-2022 30 Nov 2022 [U] · FY2022 30 Apr 2023. The [U] rows assume Kep-00089/BEI/10-2020 was
still active. From Q1-2023 on, R3's table applies.

**R5 — Availability flag.** (i, P) is flagged if an IDX late-filing sanction announcement for period P names issuer i
at any stage (written warning I onward, fine, or suspension). A flagged (i, P) is withheld from every cross-section.
Issuer i stays in the universe and carries its most recent unflagged issuer-period whose usable_from ≤ D. The flag
never removes an issuer from a return universe. Any staleness limit belongs to a mechanism's G0, not to this rule.
Source of record: `12_FQ_LATE_FILERS_2026-10-26.csv`, extended only by appending rows with source URL and tag.

**R6 — Labels carried by every {FQ} row.**
- `regime_a_unverified`: period_end < 2011-06-30. R3 is applied backward to these periods.
- `values_as_first_reported_narrow`: every row.
- `override_unverified`: Q1-2022 and Q3-2022.
- `flag_coverage`: `covered` for Q3-2024, FY2024, Q1-2025, H1-2025, Q3-2025, FY2025; `uncovered` otherwise.
- `fy_exception`: rows of issuers on the R7 list.

**R7 — Non-calendar fiscal years.** Issuers on `13b_FQ_FISCAL_YEAR_EXCEPTIONS.csv` with a fiscal year ending 31 Mar
or 30 Sep take deadline(i, P) = end of month 3 after period_end for their fiscal-year-end period and for their H1
period (the period ending six months after fiscal-year start); their other periods follow R3's table. The list is
extended only by appending rows with source URL and tag. Until an issuer is on it, it is treated as calendar-year,
and that residual is disclosed with every {FQ} result.

**R8 — Change control.** The rule changes only by a superseding, dated version approved by the owner, which may
tighten a lag on primary evidence. Appending to the R5 or R7 lists is not a rule change, because it can only withhold
rows or lengthen lags. Any {FQ} G0 or registration pins the rule version and the sha256 of both lists as of its
freeze. No later version or list change applies to it retroactively.
<!--FROZEN-END-->
