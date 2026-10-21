# {FQ} point-in-time rule — DRAFT (2026-10-21)

**Status: DRAFT — owner review.** Not frozen, no D-entry, no mechanism entry. Written under the 2026-10-21
brief (Z3); the Stockbit probe found no filing dates (`10_STOCKBIT_FIN_HISTORY_PROBE_2026-10-20.md`,
limit 1), so PIT must use the statutory-lag design of `06_PIT_FUNDAMENTALS_FEASIBILITY`.

**Rule in one line.** A quarter's fundamental values are usable in a cross-section dated D only if
D ≥ period_end + statutory_deadline + 1 month buffer, with the deadline taken from the OJK/exchange
rules in force for that period (table below).

---

## 1. The deadlines, from the regulations

The OJK-level obligation has always covered **annual and semi-annual** statements only; **quarterly
(Q1, Q3) statements are an exchange-level obligation** for IDX-listed issuers. Our universe is
entirely IDX-listed, so both layers apply. Three regimes fall inside 2007–2026:

### Regime A — 1 Jan 2008 … 29 Jun 2011: Kep-36/PM/2003

Keputusan Ketua Bapepam No. Kep-36/PM/2003 (30 Sep 2003), Peraturan X.K.2 as amended by
Kep-40/BL/2007 (dual-listed issuers). Annual audited FS: **end of the 3rd month** after the FS date;
unaudited interim: **~30 days** after the period end.
*Caveat:* this regulation's text was **not retrieved from a primary source** for this draft (only
academic secondary citations, consistent among themselves). Confirm the article text before freeze —
see open question OQ-3.

### Regime B — 30 Jun 2011 … 21 Aug 2022: Kep-346/BL/2011 (Peraturan X.K.2)

Keputusan Ketua Bapepam-LK No. Kep-346/BL/2011 (5 Jul 2011). Verified against the official text
(`X.K.2.pdf` on ojk.go.id; local copy `/tmp/xk2.pdf` at drafting time):

| Statement | Deadline | Article |
|---|---|---|
| Annual, audited | **end of 3rd month** after FS date, submitted to Bapepam-LK **and publicly announced** | Lampiran angka 2 huruf c |
| Semi-annual, no accountant | end of 1st month | angka 3 huruf b 1) |
| Semi-annual, limited review | end of 2nd month | angka 3 huruf b 2) |
| Semi-annual, audited | end of 3rd month | angka 3 huruf b 3) |
| Announcement proof to regulator | ≤ 2 business days after the newspaper announcement | angka 2 huruf e 3) |
| Deadline on a holiday | next business day | angka 5 huruf b |

Applies to reporting periods ending on or after **30 Jun 2011** (Pasal 2); revoked Kep-36/PM/2003
and Kep-40/BL/2007 (Pasal 3). No OJK-level quarterly obligation — quarterly is exchange-level.

### Regime C — 22 Aug 2022 … today: POJK 14/POJK.04/2022

Peraturan OJK No. 14/POJK.04/2022 (set 18 Aug 2022, promulgated 22 Aug 2022, effective on
promulgation; Pasal 7 from 22 Feb 2023). Same deadlines as Regime B (verified from the consolidated
text on pasal.id): annual audited **end of 3rd month** (Pasal 4); semi-annual **end of month 1
unattested / month 2 reviewed / month 3 audited** (Pasal 6); early-authorized FS filed ≤ 2 business
days after authorization (Pasal 7); holiday shift (Pasal 8); "deemed not submitted" if >6 months
(annual) / >3 months (semi-annual) late (Pasal 10). Revokes Kep-346/BL/2011 (Pasal 29).
Scope (Pasal 2 ayat 3): annual + semi-annual only — quarterly remains exchange-level.

### Exchange layer (IDX), all regimes

IDX Peraturan No. I-E (Kewajiban Penyampaian Informasi) requires listed issuers to file FS with the
exchange and publicise them; the sanction ladder (Peraturan Bursa I-H: written warning → Rp 50 jt
fine → Rp 150 jt fine → **suspension** when >3 months late or fines unpaid) is enforced in visible
waves (e.g. 59 names suspended end-July 2025 over the 31-Mar-2025 interim — deadline end-April plus
the 3-month ladder). Current text: **Kep-00087/BEI/12-2025** (effective 12 Dec 2025, revoking
Kep-00066/BEI/09-2022): interim and annual FS filed by **end of month 3 if audited / month 2 if
limited-reviewed / month 1 if unaudited** after the FS date — i.e. Q1/Q3 unaudited interims are due
**end of the following month** (30 Apr / 31 Oct), semester FS in practice **reviewed by end of the
2nd month** (31 Aug), matching the OJK tiers. *Caveat:* idx.co.id blocks document retrieval from
this box; the Kep-00087 numbers are from its analysis (veritask.ai) and the official document should
be pulled once (owner has browser access) before freeze — OQ-3.

## 2. The proposed conservative lag (calendar-year issuers)

Deadline **plus a 1-calendar-month buffer**, because (a) the public-announcement step can trail the
filing by up to 2 business days (X.K.2 angka 2.e.3) and holiday shifts exist (angka 5.b); (b) the
vendor's (Stockbit's) ingestion latency after publication is **unmeasured and unmeasurable from the
probe** (no date fields at all); (c) 1 month is deliberately crude — it can only be tightened later
with measured vendor latency, never needed as headroom.

| Period | Attestation consumed | Statutory/exchange deadline | **Usable from** | Lag (days) |
|---|---|---|---|---|
| Q1 (ends 31 Mar) | unaudited (IDX) | 30 Apr | **31 May** | 61 |
| H1 (ends 30 Jun) | reviewed | 31 Aug | **30 Sep** | 92 |
| Q3 (ends 30 Sep) | unaudited (IDX) | 31 Oct | **30 Nov** | 61 |
| FY (ends 31 Dec) | audited | 31 Mar | **30 Apr** | 120 |

For issuers with non-calendar fiscal years (a minority on IDX), apply the same month offsets to the
issuer's own period ends; the pilot's period metadata should be used to confirm fiscal calendars.

Why the H1 row uses the reviewed (month-2) deadline: unaudited H1 filings exist but the values we
consume are as finally stored (restated), and IDX practice is overwhelming reviewed-at-month-2; the
audited-H1 (month-3) case is rare. If the owner wants ultra-conservatism the H1 row can move to
30 Sep usable-from (month-3 deadline) — OQ-2.

**No outcome read.** This draft computes no return, spread, IC or factor score on the fundamentals
and joins them to no price data (brief rules; D-070 §1).

## 3. Restatement limit

The vendor stores **values as currently standing (restated), not as first reported** (probe limit 2).
Consequences and handling:

1. **Label:** every {FQ} card/manifest must carry: *"fundamental values are as currently stored
   (potentially restated), first-visibility is modelled by statutory lag only"*.
2. **Availability vs magnitude:** the lag rule above fixes *when a number may be used*; restatement
   fixes *what number it is*. A restated value is a mild look-ahead in magnitude (the cross-section
   sees a cleaner number than any trader of the day could). The lag buffer does not cure this; it is
   a separate, disclosed limitation.
3. **Cross-check plan (needs owner go-ahead, OQ-4):** sample ≈ 20 ticker-periods across eras
   (2009, 2013, 2017, 2021, 2024), half randomly drawn, half restatement-prone (going-concern
   opinions, late filers that were suspended), and compare the stored values against the original
   filings (idx.co.id disclosures). Report the share of material differences (>5% on equity or
   earnings items). If material differences are common, restrict {FQ} to ratios less sensitive to
   restatement (e.g. scale-free valuation numerators/denominators from the same statement) or accept
   the label.
4. **Vendor quarterisation:** Stockbit's per-quarter figures are vendor-derived from cumulative
   YTD statements (Indonesian interims are YTD). The cross-check sample must also verify one
   differenced quarter against the original YTD statement, and the {FQ} design may prefer YTD levels
   (4 of them a year) to vendor-differenced quarters — decision at mechanism-D-entry time.

## 4. Open questions for the owner

- **OQ-1 Buffer:** is the +1 month buffer (§2) acceptable, or tighter/looser?
- **OQ-2 H1 basis:** reviewed month-2 (proposed) or audited month-3 for H1?
- **OQ-3 Primary texts before freeze:** (a) Kep-36/PM/2003 article text (Regime A currently rests on
  consistent secondary sources); (b) official Kep-00087/BEI/12-2025 and the pre-2025 I-E quarterly
  article numbers (idx.co.id blocks this box; a one-time manual pull by the owner covers both).
- **OQ-4 Restatement cross-check:** approve the ≈20-case sample of §3.3 (manual, idx.co.id)?
- **OQ-5 COVID 2020 relaxations:** OJK granted temporary deadline extensions in 2020 (FY2019 annual
  and Q1-2020). Statutory deadlines were temporarily later; the lag table would apply the extended
  deadline for those two periods only. Confirm whether to encode them (and their exact instrument,
  which still needs sourcing) or to accept the slight conservatism of ignoring them.
- **OQ-6 Freeze path:** on owner approval this becomes the frozen {FQ} PIT rule and precedes any
  {FQ} mechanism D-entry (probe Next steps 3).
