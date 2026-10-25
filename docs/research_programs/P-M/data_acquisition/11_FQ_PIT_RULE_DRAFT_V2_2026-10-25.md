# {FQ} point-in-time rule — DRAFT v2 (2026-10-25)

**Status: DRAFT v2 — owner review.** Propose-only (approval A3). **Not frozen. No D-entry. No {FQ} mechanism
entry.** Written under brief `ZCODE_BRIEF_FQ_FULL_PULL_AND_PIT_REVISION_2026-10-21.md` §Y3. The v1 draft
(`11_FQ_PIT_RULE_DRAFT_2026-10-21.md`) is untouched; this file revises it, one recommendation per open question.

**No outcome read.** Nothing here computes a return, spread, IC or factor score on the fundamentals, and
nothing joins them to prices. The restatement check (§5) compares the vendor's stored numbers with the
issuers' own published statements — data against data.

**Provenance tags used below**

| Tag | Meaning |
|---|---|
| **[P]** | Primary text retrieved and read in this session (ojk.go.id, issuer sites) |
| **[P\*]** | A primary text names the instrument, but the instrument's own text was not retrieved |
| **[S]** | Secondary only: news or search-engine extract, not read at the source |
| **[U]** | Not verified / not reachable from this machine |

---

## 0. What changed from v1

| # | v1 said | v2 finding | Section |
|---|---|---|---|
| 1 | H1 lag 30 Sep (reviewed deadline + 1 month) | An audited-only H1 has until 30 Sep itself, so the buffer is zero. No attestation field exists anywhere in the data → recommend a uniform **31 Oct** (123 days) | §2 |
| 2 | (not raised) | **Q1 and Q3 carry the same exposure** as H1 (exchange-level tiers keyed to the accountant's report). Owner decision; recommendation is to keep 31 May / 30 Nov with disclosure | §2 |
| 3 | +1 month buffer, "deliberately crude" | Keep +1 month. But a **late-filer tail of at least 8.8 %** of required filers is still unfiled at the buffer boundary and no buffer ≤ 3 months fixes it; it is mostly chronic repeat names. Handle with an availability flag, not a longer buffer | §3 |
| 4 | OQ-5: "accept the slight conservatism of ignoring" the COVID relaxations | **Wrong direction.** Ignoring a relaxation is *anti*-conservative (the legal deadline was later than the table assumes). And the relaxations ran **FY2019 through FY2022**, not "2020 only" | §4 |
| 5 | Vendor values "probably restated (as currently stored)" | Evidence points the other way: **70 of 70** compared fields equal the *originally published* statements (3 issuers, 16 issuer-periods), including two cases where the issuer later restated and the vendor kept the original. Narrow sample — see limits | §5 |
| 6 | Two blocked texts | Still blocked; the COVID-era IDX decisions and the IDX sanction lists join the list | §6 |
| 7 | Regime A (2008 – mid-2011) rests on secondary sources | Recommend applying the Regime B/C table backward, flagged | §7 |

---

## 1. Proposed lag table (calendar-year issuers)

Rule unchanged in form: a quarter's values are usable in a cross-section dated D only if
D ≥ period_end + deadline + buffer, with the deadline in force for that period.

| Period | Deadline used | v1 usable-from (lag) | **v2 usable-from (lag)** | Change |
|---|---|---|---|---|
| Q1 (31 Mar) | unattested, month 1 → 30 Apr | 31 May (61 d) | **31 May (61 d)** | none; exposure disclosed (D2) |
| H1 (30 Jun) | **audited, month 3 → 30 Sep** | 30 Sep (92 d) | **31 Oct (123 d)** | +31 days (D1) |
| Q3 (30 Sep) | unattested, month 1 → 31 Oct | 30 Nov (61 d) | **30 Nov (61 d)** | none; exposure disclosed (D2) |
| FY (31 Dec) | audited, month 3 → 31 Mar | 30 Apr (120 d) | **30 Apr (120 d)** | none |

Dated overrides for 2019–2023 are in §4; they replace this table for the periods listed there.

---

## 2. H1 basis — and the same question for Q1 and Q3 (Y3.1, OQ-2)

**The statute has three tiers keyed to the accountant's report.** [P] `X.K.2.pdf`, Lampiran angka 3.b
(Kep-346/BL/2011, re-read this session): semi-annual statements are due at the end of **month 1** "jika tidak
disertai laporan Akuntan", **month 2** if accompanied by an accountant's report for a limited review, **month 3**
if accompanied by an accountant's report for an audit. The same three tiers sit in POJK 14/POJK.04/2022
Pasal 6 (read for v1). The month-3 path is an ordinary, lawful choice — not an exotic one. For an issuer that
takes it, v1's usable-from of 30 Sep is the deadline day itself: buffer zero.

**Option (b) — lag by each issuer's actual attestation — is not available.** All 2,871 raw files of the
full pull (read-only scan) have exactly the keys `message` and `data`; `data` has exactly `currency`,
`default_currency`, `html_report`, `rounding_value`, `data_tables`. A text scan of every `html_report` for
`audit / unaudit / diaudit / tinjau / limited / filing / publish / announce / released / tanggal` found only
account names (`Limited Public Offering`, `Tanggal Perolehan`, `Audit Pajak` = tax audit). Nothing in the data
says which tier an issuer used, and the 2026-10-20 probe already found no filing dates.

**Sample count of audited H1s.** Not knowable at population level — neither from the data (above) nor from any
source reachable here (idx.co.id returns 403). The only count in hand is three H1 statements I read for the
restatement check: TLKM H1-2012, TLKM H1-2014 and BMRI H1-2014 are **all labelled unaudited** (0 of 3 audited).
That is a convenience sample of large caps, and "unaudited" does not separate *limited review* from *no
accountant's report*, so it is an observation, not an estimate.

**One adjacent fact [S].** IDX runs the sanction clock for interim statements from the *unattested* deadline.
For H1-2025, 52 issuers were still on IDX's non-filer / unpaid-fine list at 29 Oct 2025, which is day 90 after
31 Jul 2025 — month 1 of the period. Issuers using the attested path are expected to give IDX notice within a
month of period end [S, search extract; text of I-E not retrieved].

**Recommendation for H1: (a), a uniform 31 Oct for every issuer (123 days).**
- It is PIT-safe for every lawful path (month-3 deadline 30 Sep + 1 month); (b) cannot be built.
- Cost: the 30-Sep cross-section of each year uses Q1 numbers instead of H1 numbers, and H1 enters at the
  31-Oct cross-section. That is one month of extra staleness for one cross-section a year, and it reads no outcome.
- It can be tightened later only with evidence of each issuer's tier (see §6, IDX notices).

**Same exposure, Q1 and Q3 (new in v2).** The OJK text covers annual and semi-annual statements only; Q1 and Q3
are exchange-level (IDX I-E), where the sanction announcements themselves describe the 30 April date as the
deadline for the interim statement "yang tidak disertai laporan Akuntan Publik" [S], i.e. the same keying.
An issuer that attaches a limited review or audit to a Q1/Q3 statement has up to month 2 / month 3. The outer-bound
version of the table would be Q1 → 31 Jul (122 d) and Q3 → 31 Jan (123 d).

**Recommendation for Q1/Q3: keep 31 May / 30 Nov, disclose the exposure, and settle it with evidence (D2).**
Reason: the outer bound pushes two of the three interim updates two months later, which leaves the "quarterly"
lane almost as stale as the annual lane, to guard against a path believed to be uncommon for quarterlies — a
belief I could not verify. The size of the exposure is knowable: it is the set of issuers that gave IDX notice
of an attested interim (§6). If that set is large, move to the outer bound.

Minor, unquantified: dual-listed issuers may follow the other exchange's deadlines (X.K.2 angka 4.a) [P].

---

## 3. Buffer size (Y3.2, OQ-1)

The +1 month covers (a) the announcement step that can trail filing by ≤ 2 business days (X.K.2 angka 2.e.3),
(b) holiday shifts — observed: the FY2024 deadline moved from 31 Mar to **8 Apr 2025** for the Lebaran holidays
[S] — and (c) vendor ingestion latency, which stays unmeasurable. The evidence below is about whether a
*longer* buffer would buy anything. It uses IDX's public non-filer lists only; no returns.

| Statement (deadline) | Observation | Tag |
|---|---|---|
| FY2025 audited (31 Mar 2026) | **88 of 997** required filers had not filed at 30 May 2026 (day 60) = **8.8 %**; written warning III + Rp150 jt fine. **71** at 29 Jun 2026 (day 90) = 7.1 %, suspended from day 91 | [S] Kontan 15 Jun 2026 (fetched; IDX Peng-S-00016/BEI.PLP/06-2026); 71: Bisnis / Detik / InvestorTrust 30 Jun 2026 headlines |
| Q1-2025 interim (30 Apr 2025) | **59** on the list at 29 Jul 2025 (day 90) — **57 of them already suspended** from earlier lapses, 2 newly suspended | [S] CNBC 31 Jul 2025 (fetched) |
| H1-2025 interim (31 Jul 2025) | **52** at 29 Oct 2025 (day 90) | [S] CNBC 30 Oct 2025 (fetched) |
| Q3-2025 interim (31 Oct 2025) | **48** suspended 30 Jan 2026 (day 91) | [S] Kontan 30 Jan 2026 (fetched) |
| Q3-2024 interim (31 Oct 2024) | **46** suspended Jan 2025; ARMY, BOSS, CBMF, COWL are on this list **and** on the Jan-2026 list | [S] search extracts (Kontan / Fortune IDN) |
| Year 2025 totals | 1,223 late-financial-statement sanction cases against **196 issuers** (2024: 1,203 against 246) | [S] Kontan (fetched) |

The deadlines in the first column are the standard dates (month 1 for unattested interims, month 3 for audited
annuals). Each is consistent with the reported day-91 suspension date (30 Apr + 91 d = 30 Jul 2025; 31 Jul + 91 d =
30 Oct 2025; 31 Oct + 91 d = 30 Jan 2026; 31 Mar + 91 d = 30 Jun 2026); the articles for the Q1-2025 and H1-2025
rows do not print the deadline itself.

What follows, using only the table:
1. **The tail is not a buffer problem.** Non-filer counts can only fall with time, so the share still unfiled at the
   +1-month boundary (day ~30) is **at least the day-60 share: ≥ 8.8 %** of required filers for FY2025. From
   day 60 to day 90 only 17 of the 88 filed.
2. **A longer buffer buys little and costs a lot.** Moving from +1 to +3 months would shrink the exposed set by
   about 1.7 points of required filers (88 → 71) while delaying the other ~91 % by two more months.
3. **The tail is chronic.** 57 of 59 on the Q1-2025 list were repeat offenders; four named issuers recur a year apart.

**Recommendation: keep +1 month. Treat late filers with an availability flag, not a larger buffer (D3, D4).**
The flag drops an issuer-period when IDX's sanction announcements list the issuer as unfiled past the buffer for
that period. It conditions on availability, not on any outcome; it needs the IDX announcements (§6), which this
machine cannot reach. Not built here. A caveat for the owner: the flag uses information that arrived after the
cross-section date (that the filing was late). That only removes rows whose availability cannot be established,
so it errs toward fewer look-ahead rows, but it does shrink the universe toward punctual filers.

---

## 4. COVID-era relaxations (Y3.3, OQ-5)

**Correction to v1.** v1 proposed that ignoring the relaxations would only add "slight conservatism". The reverse
holds: during a relaxation the legal deadline was *later* than the table assumes, so using the base deadline lets
numbers into a cross-section before an issuer that used the extension was required to publish them. Ignoring them
is anti-conservative. **And the relaxations did not stop in 2020.**

**Instruments**

| Instrument | What it did for issuers | Tag |
|---|---|---|
| Joint release OJK SP 21/DHMS/OJK/III/2020 + IDX PR 033/BEI.SPR/03-2020 (March 2020) | FY2019 annual FS and annual report **+2 months**; Interim I (Q1) 2020 for listed companies **+2 months** from the deadline in IDX rules | **[P]** (infographic PDF on ojk.go.id, read) |
| OJK S-92/D.04/2020 (18 Mar 2020) | 2-month extension of annual reports / AGM; named as the earlier basis in SEOJK 29/2021 | [P\*] (cited in SEOJK 29/SEOJK.04/2021, for securities institutions; own text not retrieved) |
| IDX Kep-00027/BEI/03-2020 (20 Mar 2020) | Q1-2020 to 30 Jun 2020 | [S] |
| OJK S-205/D.04/2020 (3 Aug 2020) | semi-annual FS **+1 month** | [P\*] (cited in SEOJK 29/2021 ¶5 for securities companies; issuer coverage [S]: IDX's 6 Aug 2020 list still had 10 issuers on relaxation) |
| IDX Kep-00057/BEI/08-2020 (19 Aug 2020), revoked by Kep-00089/BEI/10-2020 (15 Oct 2020) | annual FS / annual report and Q1 **+2 months**; semi-annual and Q3 **+1 month**; "until a date to be set later" | [S] (CNN Indonesia, 16 Oct 2020) |
| POJK 7/POJK.04/2021 Pasal 4 | COVID policy period to **31 Mar 2022** | **[P]** |
| POJK 4/POJK.04/2022 (promulgated 22 Mar 2022) | policy period to **31 Mar 2023** (+6 months after the government ends the national-disaster status, if that happens first) | **[P]** |
| SEOJK 20/SEOJK.04/2021 (10 Aug 2021) ¶II.5 | annual FS and annual report **+2 months**; semi-annual FS **+1 month** | **[P]** |
| SEOJK 4/SEOJK.04/2022 (10 Mar 2022) ¶II.5 | annual **+1 month**; semi-annual **+1 month**; takes effect on signature | **[P]** |

**Resulting overrides** (deadline + relaxation + the same +1-month buffer; H1 on the outer-bound basis of §2).
Q1/Q3 are exchange-level, so those rows follow IDX decisions only.

| Period | Base deadline | Relaxation | Relaxed deadline | **Usable from** | Lag (d) | Basis |
|---|---|---|---|---|---|---|
| FY2019 | 31 Mar 2020 | +2 m | 31 May 2020 | **30 Jun 2020** | 182 | **[P]** |
| Q1-2020 | 30 Apr 2020 | +2 m | 30 Jun 2020 | **31 Jul 2020** | 122 | **[P]** |
| H1-2020 | 30 Sep 2020 | +1 m | 31 Oct 2020 | **30 Nov 2020** | 153 | [P\*] / [S] |
| Q3-2020 | 31 Oct 2020 | +1 m | 30 Nov 2020 | **31 Dec 2020** | 92 | [S] |
| FY2020 | 31 Mar 2021 | +2 m | 31 May 2021 | **30 Jun 2021** | 181 | [S]; no OJK-level instrument for this deadline found |
| Q1-2021 | 30 Apr 2021 | +2 m | 30 Jun 2021 | **31 Jul 2021** | 122 | [S] |
| H1-2021 | 30 Sep 2021 | +1 m | 31 Oct 2021 | **30 Nov 2021** | 153 | **[P]** (SEOJK 20/2021) |
| Q3-2021 | 31 Oct 2021 | +1 m | 30 Nov 2021 | **31 Dec 2021** | 92 | [S] |
| FY2021 | 31 Mar 2022 | +1 m | 30 Apr 2022 | **31 May 2022** | 151 | **[P]** (SEOJK 4/2022 replaced the +2 m on 10 Mar 2022) |
| Q1-2022 | 30 Apr 2022 | +2 m | 30 Jun 2022 | **31 Jul 2022** | 122 | [U]: assumes Kep-00089 still active |
| H1-2022 | 30 Sep 2022 | +1 m | 31 Oct 2022 | **30 Nov 2022** | 153 | **[P]** (SEOJK 4/2022) |
| Q3-2022 | 31 Oct 2022 | +1 m | 30 Nov 2022 | **31 Dec 2022** | 92 | [U]: assumes Kep-00089 still active |
| FY2022 | 31 Mar 2023 | +1 m | 30 Apr 2023 | **31 May 2023** | 151 | [P] policy ends 31 Mar 2023, the deadline day itself: applying +1 m is the conservative reading |

From Q1-2023 on, the base table in §1 applies. The [U] rows use the conservative assumption (relaxation stays
active until a superseding IDX decision is seen); when Kep-00089's end date is known they can be tightened.
**Recommendation (D5):** encode this as a dated override table keyed by `period_end`, and withdraw v1's "ignore" option.

---

## 5. Restatement check (Y3.4, OQ-4)

**Method.** Vendor values come from the raw store (`~/idx_external/stockbit_fin/raw`, read through the existing
`parse_report`; `fin.db` and the raw files were not touched). "Original" values were read off the issuers' own
statements as published — Telkom's quarterly consolidated statements on telkom.co.id, Bank Mandiri's quarterly
publications on bankmandiri.co.id, and Astra's 3Q2014 results release filed with SGX. Vendor quarters are discrete,
so YTD and full-year originals were compared with the sum of the vendor's quarters. Every comparison, with the
source URL and the sha256 of the retrieved PDF, is in `11b_FQ_RESTATEMENT_CHECK_2026-10-25.csv`.

**Result: 70 field comparisons, 16 issuer-periods, 3 issuers — 0 differences.**

| Issuer | Layout | Periods compared | Fields |
|---|---|---|---|
| TLKM | non-bank | Q1-12, H1-12, FY12, 9M-13, FY13, H1-14, 9M-14, FY14, FY15 (9) | assets, equity, revenue, net income, owners' net income (45) |
| BMRI | bank | FY13, Q1-14, H1-14, 9M-14, FY14, Q1-16 (6) | assets, equity, gross interest income, net income (+ FY13 interest expense) (23) |
| ASII | non-bank | 9M-14 (1) | revenue, owners' net income (2) — summary-level release, not the full statements |

TLKM and ASII match to Rp billion (printed precision); BMRI matches to the Rp million.

**Two cases that discriminate "as first reported" from "as currently restated":**
1. **TLKM FY2014.** Vendor: assets 140,895 / equity 86,125 / net income 21,446 / owners' 14,638. Those are the FY2014
   statement as published. The FY2015 statement re-presents 2014 as *restated*: 141,822 / 85,992 / 21,274 / 14,471.
   The vendor kept the original.
2. **BMRI FY2013 interest expense.** Vendor sum of Q1–Q4 2013: 17,432,216 = the FY2013 statement as published. The FY2014
   statement reclassified the 2013 comparative to 16,399,424 (net interest income 32,776,626 → 33,809,418). The vendor
   kept the original.

**It also answers v1 §3 item 4 (vendor quarterisation)** for these 16 periods: the sum of vendor quarters equals the
issuer's YTD figure at Q1, H1, 9M and FY every time, so the vendor's discrete quarters are arithmetically consistent
with the issuers' cumulative statements.

**Limits — this is not the stratified ~20-case sample the brief asked for.**
- 3 issuers, all large caps, chosen because their IR sites host the originals (a convenience sample, biased toward
  easy-to-reach issuers). No small cap, no period before 2012, no going-concern or late-filer name.
- Pre-2012 periods straddle the IFRS convergence, where restatement is most likely; untested.
- It tests the lines I compared, not every account. Outside this sample the vendor may still hold restated values.

**Recommendation (D6).** Relabel v1 §3.1 to *"values appear to be as first reported (70/70 on 3 large issuers;
small caps and pre-2012 untested)"* — a weaker claim than v1's — and run the stratified extension before the label is
relaxed further. Protocol, to be run after `parse` so it is reproducible from the pinned `fin.db`:
- seeded draw (record the seed) of ~20 issuer-periods, strata from fundamentals only — no prices: bank layout by
  the Interest-Income rule in the Y2 runbook; size by Total Aset tercile within the period; period end ≤ 2014 vs ≥ 2015;
  include at least 4 small names and 2 pre-2012 periods;
- originals from issuer IR sites or OJK portals; IDX (blocked here) from the owner's browser for the rest;
- report exact-match rate and the share of differences > 5 % on equity or earnings items (v1's threshold).

---

## 6. Texts and data this machine cannot reach (Y3.5, OQ-3)

idx.co.id returned 403 again this session. ojk.go.id is reachable for PDFs only with a browser-like User-Agent, an
`Accept: application/pdf` header and an ojk.go.id Referer; a bare `Mozilla/5.0` agent got a "Request Rejected" page.
Two texts block the freeze:

**(i) Kep-36/PM/2003 (30 Sep 2003) — the original Peraturan X.K.2.** Not on the OJK site: OJK's X.K.2 page carries
only Kep-346/BL/2011, which cites the 2003 text as revoked. **Settles:** the annual and interim deadlines for periods
ending 31 Dec 2007 – 29 Jun 2011 (the first ~14 of the ~74 quarters). v1 has them from secondary sources (annual: month 3;
interim: ~30 days). **Where:** Bapepam-LK archive / OJK regulation library, search `KEP-36/PM/2003`, or OJK contact 157.
I have no verified URL for it.

**(ii) IDX Peraturan No. I-E (Kewajiban Penyampaian Informasi), current text.** v1 names Kep-00087/BEI/12-2025; the latest
amendment I could confirm from issuers' filings is Kep-00066/BEI/09-2022 [S]. **Settles:** the Q1/Q3 deadline tiers (D2),
the notice rule for attested interims, the sanction ladder's day thresholds (the lists in §3 show written warning III
and the Rp150 jt fine already at day 60, and suspension from day 91). **URL (from the Y2 runbook, unverified):**
`https://www.idx.co.id/Media/gmddcpw4/signed_peraturan_nomor_ie_tentang_kewajiban_penyampaian_informasi.pdf`

**Also not retrieved — text of the instruments in §4 that are [S] or [P\*]:** IDX Kep-00027/BEI/03-2020,
Kep-00057/BEI/08-2020, Kep-00089/BEI/10-2020 (and when it ended); OJK S-92/D.04/2020 and S-205/D.04/2020.

**Data the owner can pull by hand (idx.co.id, browser):**
- IDX sanction announcements by period (e.g. Peng-S-00016/BEI.PLP/06-2026 for FY2025 audited), which give the
  late-filer lists for the availability flag (D4);
- the issuers' notices of an attested (limited-review / audited) interim statement, which give the Q1/Q3 exposure for D2.

---

## 7. Regime A, periods ending before 30 Jun 2011 (OQ-3a)

Until (i) is in hand, Regime A rests on consistent secondary sources. **Recommendation (D7):** apply the §1 table
backward to these ~14 quarters and label them "Regime A, unverified". That is conservative if Regime A's deadlines were
no later than Regime B's, which the secondary sources say (annual month 3; interim ~30 days). The alternative is to
start the panel at the first Regime-B period (period end 30 Jun 2011 or later), which gives up about 3.5 of the ~18 years.

---

## 8. Decisions for the owner

| # | Decision | Recommendation | Needs |
|---|---|---|---|
| **D1** | H1 basis | **(a) uniform 31 Oct, 123 d** (§2) | — |
| **D2** | Q1 / Q3 attested-path exposure | Keep 31 May / 30 Nov **with disclosure**; move to 31 Jul / 31 Jan only if IDX attested-interim notices show the path is common | IDX notices (§6) |
| **D3** | Buffer size | **Keep +1 month**; do not lengthen (§3) | — |
| **D4** | Late-filer tail (≥ 8.8 % at the buffer boundary) | **Availability flag** from IDX sanction lists, once obtained; until then, disclose the residual | IDX announcements (§6) |
| **D5** | COVID relaxations | **Encode the §4 override table**; the [U] rows at the conservative assumption; withdraw v1's "ignore" option | — |
| **D6** | Restatement label | **Relabel to "as first reported, narrow evidence"** now; approve the stratified ~20-case extension (§5) before relaxing it | Owner browser for small-cap originals |
| **D7** | Regime A (pre-Jul 2011) | **Apply the §1 table backward, flagged**, until Kep-36/PM/2003 is read | Text (i) |
| **D8** | Primary texts | Fetch (i), (ii) and the COVID-era IDX decisions (§6) | Owner browser |
| **D9** | Freeze path (v1 OQ-6) | After D1–D8: a v3 that you approve becomes the frozen {FQ} PIT rule and precedes any {FQ} mechanism D-entry. **Nothing is frozen by this file.** | D1–D8 |

---

## 9. What this revision did not do

- The Y2 post-steps — `parse`, the sha256 pin manifest, the coverage table and the off-SSD copy — are **not** run.
  The fetch finished at 10:24 on 2026-10-25 (`fetch rc=0`; 2,841 saved in the run + 30 from the pilot; 6 missing/empty
  = 2 tickers × 3 statements). This draft read the raw store only, and `fin.db` still holds the pilot's 10 tickers.
- Not built: the stratified restatement sample, the late-filer list, and a count of unfiled statements at day 30.
- Not verified: the Kep-00089 end date, the IDX I-E tiers for Q1/Q3, and the OJK-level instrument for the FY2020 deadline.

---

## Sources

**[P] OJK texts read in this session** (all `https://www.ojk.go.id/…`, retrieved 2026-10-25):
- Peraturan X.K.2 (Kep-346/BL/2011): `/Files/regulasi/pasar-modal/bapepam-pm/emiten-pp/pelaporan/X.K.2.pdf`
- POJK 7/POJK.04/2021: `/id/regulasi/Documents/Pages/Kebijakan-dalam-Menjaga-Kinerja-dan-Stabilitas-Pasar-Modal-Akibat-Penyebaran-Corona-Virus-Disease-2019/pojk%207-2021.pdf`
- POJK 4/POJK.04/2022: `/id/regulasi/Documents/Pages/Perubahan-Atas-Peraturan-Otoritas-Jasa-Keuangan-Nomor-7-POJK-04-2021-tentang-Kebijakan-Dalam-Menjaga-Kinerja-dan-Stabilitas/POJK%204%20-%2004%20-%202022.pdf`
- SEOJK 20/SEOJK.04/2021: `/id/regulasi/Documents/Pages/Kebijakan-Stimulus-dan-Relaksasi-Ketentuan-Terkait-Emiten-atau-Perusahaan-Publik-dalam-Menjaga-Kinerja-/seojk%2020-2021.pdf`
- SEOJK 4/SEOJK.04/2022: `/id/regulasi/Documents/Pages/Perubahan-Atas-Surat-Edaran-Otoritas-Jasa-Keuangan-Nomor-20-SEOJK-04-2021/SEOJK%204%20-%2004%20-%202022.pdf`
- SEOJK 29/SEOJK.04/2021 (cites S-92 and S-205): `/id/regulasi/Documents/Pages/Kebijakan-Relaksasi-atas-Kewajiban-Penyampaian-Laporan-Lembaga-Efek-dan-Perintah-Kepada-Bursa-Efek,-Lembaga-Kliring-dan-Pen/SEOJK%2029%20-%2004%20-%202021.pdf`
- Joint OJK/IDX release, March 2020: `/id/berita-dan-kegiatan/Documents/Pages/informasi-covid-19/OJK%20dan%20SRO%20Jaga%20Keberlangsungan%20Aktivitas%20Perdagangan%20Bursa%20Efek%20yang%20Teratur.pdf`

**[S] News, as quoted in the tables** (the 88, 59, 52, 48 and 2025-totals articles were fetched; the rest are
search-engine extracts, and the Bisnis page itself returned 403):
- FY2025 audited, 88 unfiled at day 60: https://investasi.kontan.co.id/news/telat-lapor-bei-hukum-emiten-ini-dengan-peringatan-hingga-denda-rp-150-juta
- FY2025 audited, 71 suspended: https://market.bisnis.com/read/20260630/7/1984411/bei-suspensi-71-emiten-yang-telat-setor-laporan-keuangan-2025-ini-daftarnya · https://finance.detik.com/bursa-dan-valas/d-8553608/bursa-gembok-denda-71-emiten-gegara-laporan-keuangan · https://investortrust.id/market/107977/belum-rilis-laporan-keuangan-audit-2025-bei-suspensi-71-saham-emiten
- Q1-2025, 59: https://www.cnbcindonesia.com/market/20250731095802-17-653810/belum-sampaikan-laporkan-keuangan-q1-2025-bei-sanksi-59-emiten/amp
- H1-2025, 52: https://www.cnbcindonesia.com/market/20251030165011-17-680813/belum-lapor-lapkeu-52-emiten-kena-hukum-bursa-ini-daftarnya/amp
- Q3-2025, 48: https://investasi.kontan.co.id/news/bei-suspensi-48-saham-emiten-karena-belum-menyampaikan-laporan-keuangan
- 2025 sanction totals: https://investasi.kontan.co.id/news/bei-jatuhkan-3040-sanksi-ke-453-emiten-di-2025-masalah-laporan-keuangan-dominan
- Q3-2024, 46: https://investasi.kontan.co.id/news/daftar-46-emiten-yang-kena-suspensi-gegara-belum-serahkan-laporan-keuangan
- FY2024 deadline 8 Apr 2025 and 128 first warnings: https://www.cnbcindonesia.com/market/20250425083539-17-628625/bei-beri-sanksi-ke-128-emiten-ini-daftarnya · https://bcasekuritas.co.id/en/latest-news/news/puluhan-emiten-belum-setor-laporan-keuangan-2025-bei-jatuhkan-sanksi-dan-denda
- Q1-2026 interim deadline wording and "tidak disertai laporan Akuntan Publik": https://investasi.kontan.co.id/news/bei-73-emiten-belum-sampaikan-laporan-keuangan-per-kuartal-i-2026
- IDX Kep-00089/BEI/10-2020: https://www.cnnindonesia.com/ekonomi/20201016104619-92-559109/bei-longgarkan-batas-waktu-emiten-sampaikan-lapkeu
- IDX Kep-00027/BEI/03-2020: https://investasi.kontan.co.id/news/gara-gara-corona-bei-perpanjang-tenggat-penyampaian-laporan-keuangan-kuartal-i-2020
- 10 issuers still on H1-2020 relaxation: https://market.bisnis.com/read/20200807/7/1276318/dikasih-ampun-10-saham-ini-bebas-dari-cap-notasi-khusus

**Originals for §5:** URLs and sha256 per row in `11b_FQ_RESTATEMENT_CHECK_2026-10-25.csv`.
