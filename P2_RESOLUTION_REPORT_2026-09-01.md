# P2 IDX80 Membership Window — Resolution Report

**Window:** P2, `idx80_membership_history` / `idx80_reconstitution_periods`, effective 2025-05-02 → 2025-07-31
**Mission type:** Read-only evidence investigation (no data/code mutated)
**Author:** Claude Code research session, 2026-09-01
**Status of this document:** Findings + recommendation, **subsequently approved and EXECUTED**. See
§11 for the execution record.

---

## 1. Executive Conclusion

**Decision: A — RESOLVED, 80-member roster proven.**

The 81st member of P2 as currently stored, **AADI (PT Adaro Andalan Indonesia Tbk)**, does not belong
in the P2 window. Multiple independent, contemporaneous, named-outlet financial news sources — with
zero contradicting sources found — establish that AADI entered IDX80 at the **August 1, 2025**
rebalance (P2→P3 boundary), not the **May 2, 2025** rebalance (P1→P2 boundary). Removing AADI from
P2 yields an internally consistent, arithmetically balanced 80-member roster for the full window, and
resolves the residual discrepancy that made P4's independent bracket-check catch this in the first
place (per the existing `P2` row's own `notes` field in `idx80_reconstitution_periods`).

No official BEI/IDX document specific to the April 2025 evaluation (the one that produced P2) could be
located — neither on the live site (Cloudflare-blocked, consistent with prior notes on this table) nor
in the Wayback Machine (not archived for that date). The corrected 80-member roster is therefore
supported to **CROSS_VALIDATED** confidence (4+ independent secondary sources, zero discrepancy, full
arithmetic bracket closure against the two PRIMARY_VERIFIED bookends P1 and P3) — **not**
PRIMARY_VERIFIED. This matches the confidence taxonomy already in use elsewhere in this table (e.g. P7).

---

## 2. Starting State (as found)

| Period | Window | Count | Confidence | Source |
|---|---|---|---|---|
| P1 | 2025-02-03 → 2025-04-30 | 80 | PRIMARY_VERIFIED | Official IDX XLSX, Peng-00012/BEI.POP/01-2025 |
| **P2** | **2025-05-02 → 2025-07-31** | **81** | **UNRESOLVED** | P1 + secondary-sourced delta, found incomplete |
| P3 | 2025-08-01 → 2025-11-02 | 80 | PRIMARY_VERIFIED | Official IDX PDF, Peng-00139/BEI.POP/07-2025 |

The pre-existing `notes` field on the P2 row already flagged the mechanism of the error precisely:
AADI was inserted into P2 *by inference* (diffing P1 against the PRIMARY_VERIFIED P3), not from any
primary or secondary document dated to the P2 window itself — an inference-driven "fix" for an
incomplete kontan.co.id delta that itself introduced an undated, unverified addition.

### Roster diff (P1 vs P2 vs P3 as currently stored)

- **P1 → P2** (as stored): −BMTR, −MIDI (2 removed) / +AADI, +BUKA, +DSNG (3 added) → **net +1** (80→81)
- **P2 → P3** (as stored): −GGRM, −GJTL, −NISP (3 removed) / +PTRO, +RAJA (2 added) → **net −1** (81→80)
- **P1 → P3 net**: 5 removed, 5 added — balanced (80→80)

The imbalance is entirely confined to *which side of the P2 window* AADI's addition belongs on. The
P1→P3 net bracket is clean regardless — this is a **timing/attribution** question, not a roster-content
question.

---

## 3. Evidence Gathered

### 3.1 P1→P2 boundary (May 2, 2025 rebalance) — additions

| Source | Type | Published | Additions found | Removals found |
|---|---|---|---|---|
| [liputan6.com/saham/read/6005045](https://www.liputan6.com/saham/read/6005045/bursa-kocok-ulang-penghuni-idx80-ini-daftar-lengkapnya) | Contemporaneous financial news | 2025-04-25 (7 days pre-effective) | BUKA, DSNG only | BMTR, MIDI |
| [insight.kontan.co.id/.../dua-saham-masuk-ke-indeks-idx80-mulai-2-mei-2025](https://insight.kontan.co.id/news/dua-saham-masuk-ke-indeks-idx80-mulai-2-mei-2025-ini-daftar-lengkapnya) | Contemporaneous financial news | ~late Apr 2025 | BUKA, DSNG only (explicit: article title says "Dua Saham" = "Two Stocks"; AADI does not appear anywhere in the article) | BMTR, MIDI |
| [investasi.kontan.co.id/.../buka-dan-dsng-masuk-indeks-idx80-mulai-2-mei-2025](https://investasi.kontan.co.id/news/buka-dan-dsng-masuk-indeks-idx80-mulai-2-mei-2025-ini-daftar-lengkapnya) | Contemporaneous financial news (Kontan investasi desk — independent byline/desk from insight.kontan.co.id) | ~late Apr 2025 | BUKA, DSNG only | BMTR, MIDI |
| infobanknews.com major-evaluation article pattern (verified against 2026 analog) | Corroborates evaluation *cadence* (Jan/Apr/Jul/Oct major reviews, effective Feb/May/Aug/Nov) | — | — | — |
| bareksa.com 2024-03-27 announcement of schedule change | Corroborates the 2x→4x/year major-review cadence change that produced this exact Feb/May/Aug/Nov schedule | 2024-03-27 | — | — |

**Three independently bylined, named Indonesian financial-news outlets, all published before or at the
May 2, 2025 effective date, converge exactly: 2 removed (BMTR, MIDI), 2 added (BUKA, DSNG). None
mentions AADI in the IDX80 context for this rebalance.**

### 3.2 P2→P3 boundary (August 1, 2025 rebalance) — additions

| Source | Type | Additions found | Removals found |
|---|---|---|---|
| [investasi.kontan.co.id — "BEI Kocok Ulang Saham LQ45, IDX30 dan IDX80 Periode 1 Agustus-31 Oktober 2025"](https://investasi.kontan.co.id/news/bei-kocok-ulang-saham-lq45-idx30-dan-idx80-periode-1-agustus-31-oktober-2025) | Contemporaneous, ~late Jul 2025, syndicated on TradingView | **AADI, PTRO, RAJA** ("resmi masuk") | GGRM, GJTL, NISP ("resmi dikeluarkan") |
| [liputan6.com/saham/read/6115826 — "Intip Daftar Terbaru Saham IDX80, Ada AADI hingga PTRO"](https://www.liputan6.com/saham/read/6115826/intip-daftar-terbaru-saham-idx80-ada-aadi-hingga-ptro) | Contemporaneous financial news (headline itself names AADI as a new IDX80 entrant) | AADI, PTRO (headline; RAJA per body per search snippet) | GGRM, GJTL, NISP |
| banyumasekspres.id — "Rebalancing Indeks BEI Agustus 2025" | Contemporaneous | AADI (LQ45 emphasis) + PTRO (IDX80) — see caveat below | — |
| mininginsider.id — "Jelang Review MSCI Agustus 2025, PTRO Masuk Radar Investor Setelah Lolos ke IDX80" | Contemporaneous, sector-focused | PTRO confirmed into IDX80 | — |
| blog.rivankurniawan.com 2025-07-30 | Independent financial blog, references idx.co.id data tables | PTRO, RAJA (IDX80); **notes "AADI masuk ke indeks LQ45" separately, does not explicitly restate AADI under its own IDX80 summary** | GGRM, GJTL, NISP |

**Caveat on 3.2:** one source (rivankurniawan.com) lists only PTRO/RAJA under its own IDX80 summary line
and mentions AADI only in the LQ45 context. This is treated as **incompleteness, not contradiction** —
the two Kontan-syndicated articles and the liputan6.com headline explicitly and unambiguously name AADI
as an IDX80 entrant at this boundary (an index membership is not exclusive; simultaneous LQ45+IDX80
entry on the same rebalance date is normal and expected for a stock graduating tiers), and this is also
the ticker recorded as a MEMBER in P3, which is already PRIMARY_VERIFIED via the official IDX document.
No source anywhere states or implies AADI was *not* an August-2025 IDX80 addition, or that it was
already a member before August.

### 3.3 AADI listing history

AADI (PT Adaro Andalan Indonesia Tbk) IPO'd and listed on the IDX Main Board on **2024-12-05** —
[bisnis.com / tempo.co coverage confirms this]. This predates P1 (starts 2025-02-03), so AADI was a
live, tradeable, IDX-listed stock throughout P1 and P2. **This rules out "not yet listed" as an
explanation for AADI's absence from the May 2025 IDX80 addition list** — its absence from that list is
not an artifact of non-existence; it genuinely wasn't added to IDX80 until August.

### 3.4 Primary-source search (exhausted)

Attempted and failed to locate:
- The live idx.co.id announcement page/PDF for the April 2025 major evaluation (Peng-00XXX/BEI.POP/04-2025)
  — site returns HTTP 403 (Cloudflare) for direct/curl access, consistent with the block already
  documented for this table's other periods.
- A Wayback Machine (web.archive.org) snapshot of that same document — queried the CDX API directly
  against `idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/Exchange/` filtered for
  `BEI.POP04-2025` and for the full April 20–May 10, 2025 date range: **zero snapshots exist** for any
  `Peng-000XX...04-2025` index-evaluation document (by contrast, the July 2025 doc *is* archived, at
  `Peng-00139-No. Peng-00139BEI.POP07-2025.pdf`, confirming the numbering scheme is real, just this one
  date range wasn't crawled).
- The official IDX80 fact-sheet PDF (`fs-idx80-YYYY-MM.pdf` series) for May, June, or July 2025 — the
  Wayback CDX index has `fs-idx80-2025-01` through `fs-idx80-2025-04` (all crawled in one batch on
  2025-06-09) and then jumps straight to `fs-idx80-2026-02`; **no May/June/July 2025 fact sheet was ever
  archived.**
- Did successfully retrieve and verify `fs-idx80-2025-04.pdf` (as of 2025-04-30, the exact P1/P2
  boundary date) via Wayback. It confirms **"Number of Constituents: 80"** and **"Major Review :
  January, April, July, dan October"** — independently corroborating the quarterly review cadence used
  throughout this reconstruction, though (like all IDX fact sheets) it only lists the top-10
  constituents by weight, not the full 80-name list, so it cannot directly confirm/deny AADI's presence.
- The Claude-in-Chrome browser tool (which might have bypassed the Cloudflare block via a real browser
  session) was unavailable in this session (extension not connected).

**Conclusion of §3.4: primary-source evidence has been exhausted as far as reasonably accessible in
this session.** The gap is not for lack of trying — it is that IDX never had this specific document
crawled by any archive, and its live site actively blocks non-browser retrieval.

---

## 4. Full 81-Member Evidence Table

**Group A — 75 tickers stable across P1 ∩ P2 ∩ P3** (unchanged through the entire Feb–Nov 2025 window;
each is directly supported by two independent PRIMARY_VERIFIED official IDX documents bracketing P2 on
both sides — the strongest possible evidence tier short of a P2-dated document itself):

| ticker | evidence_source | evidence_date | supports_membership | confidence | notes |
|---|---|---|---|---|---|
| ACES | P1 PRIMARY (Peng-00012) + P3 PRIMARY (Peng-00139), both list as member | 2025-01-22 / 2025-07-25 | Yes | Primary (bracketed) | unchanged throughout |
| ADMR | same | same | Yes | Primary (bracketed) | unchanged throughout |
| ADRO | same | same | Yes | Primary (bracketed) | unchanged throughout |
| AKRA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| AMMN | same | same | Yes | Primary (bracketed) | unchanged throughout |
| AMRT | same | same | Yes | Primary (bracketed) | unchanged throughout |
| ANTM | same | same | Yes | Primary (bracketed) | unchanged throughout |
| ARTO | same | same | Yes | Primary (bracketed) | unchanged throughout |
| ASII | same | same | Yes | Primary (bracketed) | unchanged throughout |
| AUTO | same | same | Yes | Primary (bracketed) | unchanged throughout |
| AVIA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| BBCA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| BBNI | same | same | Yes | Primary (bracketed) | unchanged throughout |
| BBRI | same | same | Yes | Primary (bracketed) | unchanged throughout |
| BBTN | same | same | Yes | Primary (bracketed) | unchanged throughout |
| BFIN | same | same | Yes | Primary (bracketed) | unchanged throughout |
| BMRI | same | same | Yes | Primary (bracketed) | unchanged throughout |
| BNGA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| BRIS | same | same | Yes | Primary (bracketed) | unchanged throughout |
| BRMS | same | same | Yes | Primary (bracketed) | unchanged throughout |
| BRPT | same | same | Yes | Primary (bracketed) | unchanged throughout |
| BSDE | same | same | Yes | Primary (bracketed) | unchanged throughout |
| BTPS | same | same | Yes | Primary (bracketed) | unchanged throughout |
| CMRY | same | same | Yes | Primary (bracketed) | unchanged throughout |
| CPIN | same | same | Yes | Primary (bracketed) | unchanged throughout |
| CTRA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| ELSA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| EMTK | same | same | Yes | Primary (bracketed) | unchanged throughout |
| ENRG | same | same | Yes | Primary (bracketed) | unchanged throughout |
| ERAA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| ESSA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| EXCL | same | same | Yes | Primary (bracketed) | unchanged throughout |
| GOTO | same | same | Yes | Primary (bracketed) | unchanged throughout |
| HEAL | same | same | Yes | Primary (bracketed) | unchanged throughout |
| HRUM | same | same | Yes | Primary (bracketed) | unchanged throughout |
| ICBP | same | same | Yes | Primary (bracketed) | unchanged throughout |
| INCO | same | same | Yes | Primary (bracketed) | unchanged throughout |
| INDF | same | same | Yes | Primary (bracketed) | unchanged throughout |
| INDY | same | same | Yes | Primary (bracketed) | unchanged throughout |
| INKP | same | same | Yes | Primary (bracketed) | unchanged throughout |
| INTP | same | same | Yes | Primary (bracketed) | unchanged throughout |
| ISAT | same | same | Yes | Primary (bracketed) | unchanged throughout |
| ITMG | same | same | Yes | Primary (bracketed) | unchanged throughout |
| JPFA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| JSMR | same | same | Yes | Primary (bracketed) | unchanged throughout |
| KLBF | same | same | Yes | Primary (bracketed) | unchanged throughout |
| LSIP | same | same | Yes | Primary (bracketed) | unchanged throughout |
| MAPA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| MAPI | same | same | Yes | Primary (bracketed) | unchanged throughout |
| MBMA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| MDKA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| MEDC | same | same | Yes | Primary (bracketed) | unchanged throughout |
| MIKA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| MNCN | same | same | Yes | Primary (bracketed) | unchanged throughout |
| MTEL | same | same | Yes | Primary (bracketed) | unchanged throughout |
| MYOR | same | same | Yes | Primary (bracketed) | unchanged throughout |
| NCKL | same | same | Yes | Primary (bracketed) | unchanged throughout |
| PANI | same | same | Yes | Primary (bracketed) | unchanged throughout |
| PGAS | same | same | Yes | Primary (bracketed) | unchanged throughout |
| PGEO | same | same | Yes | Primary (bracketed) | unchanged throughout |
| PNLF | same | same | Yes | Primary (bracketed) | unchanged throughout |
| PTBA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| PWON | same | same | Yes | Primary (bracketed) | unchanged throughout |
| SCMA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| SIDO | same | same | Yes | Primary (bracketed) | unchanged throughout |
| SMGR | same | same | Yes | Primary (bracketed) | unchanged throughout |
| SMRA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| SRTG | same | same | Yes | Primary (bracketed) | unchanged throughout |
| SSIA | same | same | Yes | Primary (bracketed) | unchanged throughout |
| TAPG | same | same | Yes | Primary (bracketed) | unchanged throughout |
| TKIM | same | same | Yes | Primary (bracketed) | unchanged throughout |
| TLKM | same | same | Yes | Primary (bracketed) | unchanged throughout |
| TOWR | same | same | Yes | Primary (bracketed) | unchanged throughout |
| UNTR | same | same | Yes | Primary (bracketed) | unchanged throughout |
| UNVR | same | same | Yes | Primary (bracketed) | unchanged throughout |

**Group B — 4 tickers joining/leaving at the P1→P2 boundary (May 2, 2025), confirmed by 3 independent
contemporaneous sources:**

| ticker | company | evidence_source | evidence_date | supports_membership (in P2) | confidence | notes |
|---|---|---|---|---|---|---|
| BUKA | PT Bukalapak.com Tbk | liputan6.com 6005045; insight.kontan.co.id; investasi.kontan.co.id (3 independent, contemporaneous) | 2025-04-25 (pre-effective) | Yes — added May 2, stays through P3 | Cross-validated | previously removed from IDX80 at the earlier Feb 2025 (P0→P1) rebalance per a separate Kontan article; re-added at P1→P2 |
| DSNG | PT Dharma Satya Nusantara Tbk | same 3 sources | 2025-04-25 | Yes — added May 2, stays through P3 | Cross-validated | — |
| (BMTR) | PT Global Mediacom Tbk | same 3 sources | 2025-04-25 | **No — removed May 2** (not part of the 81; excluded correctly already) | Cross-validated | for completeness only |
| (MIDI) | PT Midi Utama Indonesia Tbk | same 3 sources | 2025-04-25 | **No — removed May 2** (not part of the 81; excluded correctly already) | Cross-validated | for completeness only |

**Group C — 3 tickers carried from P1, removed at the P2→P3 boundary (August 1, 2025), confirmed by
2+ independent contemporaneous sources plus PRIMARY_VERIFIED P1 membership and PRIMARY_VERIFIED P3
non-membership:**

| ticker | company | evidence_source | evidence_date | supports_membership (in P2) | confidence | notes |
|---|---|---|---|---|---|---|
| GGRM | PT Gudang Garam Tbk | P1 PRIMARY (member) + investasi.kontan.co.id + liputan6.com 6115826 + rivankurniawan.com (removal confirmed) + P3 PRIMARY (non-member) | 2025-01-22 / late Jul 2025 / 2025-07-25 | Yes — present through Jul 31, removed Aug 1 | Primary-bracketed + cross-validated | — |
| GJTL | PT Gajah Tunggal Tbk | same | same | Yes | Primary-bracketed + cross-validated | — |
| NISP | PT Bank OCBC NISP Tbk | same | same | Yes | Primary-bracketed + cross-validated | — |

**Group D — the disputed member:**

| ticker | company | evidence_source | evidence_date | supports_membership (in P2) | confidence | notes |
|---|---|---|---|---|---|---|
| **AADI** | PT Adaro Andalan Indonesia Tbk | investasi.kontan.co.id + liputan6.com 6115826 ("resmi masuk" IDX80 at Aug 1, 2025) — **contradicted** by the absence of AADI in all 3 independent May-2025 addition-list sources (§3.1) | Aug 2025 sources: late Jul 2025; May 2025 sources (non-mention): 2025-04-25 | **No — contradicted by primary-adjacent evidence for the May window; supported for August only** | Cross-validated (for August placement) | **This is the ticker that should move from P2 to P3-only.** Listed on IDX since 2024-12-05, so "not yet listed" does not explain its absence from the May addition list. |

**Summary of the audit:**
- Supported by primary evidence (bracketed both sides): **75** (Group A) + **3** (Group C, GGRM/GJTL/NISP) = **78**
- Supported by cross-validated multi-source secondary evidence only: **2** (Group B, BUKA/DSNG)
- Contradicted by cross-validated evidence for its currently-recorded window: **1** (AADI)
- Evidence unavailable / no primary document located for the window as a whole: the April 2025 BEI
  announcement itself (affects confidence tier for the whole P1→P2 delta, not any single ticker's
  presence)

78 + 2 = 80 supported members. AADI is the 81st and is the one contradicted.

---

## 5. P2 Effective-Date / Boundary Analysis

| Date | Event | Evidence |
|---|---|---|
| 2025-04-30 | Last day of P1 | `fs-idx80-2025-04.pdf` (Wayback) confirms 80 constituents, "Major Review: Jan/Apr/Jul/Oct" cadence |
| 2025-05-01 | Public holiday (Labour Day, Indonesia) | Not a trading day; no index action expected/found |
| 2025-05-02 | **P1→P2 effective date** | 3 independent contemporaneous sources: −BMTR, −MIDI / +BUKA, +DSNG. **No AADI.** |
| 2025-07-31 | Last day of P2 | No fact sheet archived for this date; roster inferred from bracket |
| 2025-08-01 | **P2→P3 effective date** | P3 is PRIMARY_VERIFIED (Peng-00139/BEI.POP/07-2025); 2+ independent contemporaneous sources confirm AADI, PTRO, RAJA added and GGRM, GJTL, NISP removed here |

**There is exactly one rebalance at each of the two boundaries — no evidence of an additional
mid-window rebalance, and no evidence that either boundary moved.** The 4x/year major-review cadence
(Jan/Apr/Jul/Oct evaluation → Feb/May/Aug/Nov effective) is independently corroborated by three
separate sources (the April 2025 IDX fact sheet itself, the bareksa.com 2024-03-27 schedule-change
article, and the consistent pattern already visible across P1/P3/P4/P5/P6/P7 in this table).

---

## 6. Evidence-Quality Assessment

| Evidence class | Applies to | Assessment |
|---|---|---|
| Official IDX document, contemporaneous (PRIMARY_VERIFIED) | P1, P3 bookends | Present, already in DB, unaffected by this investigation |
| Official IDX document, specific to P2's own creation (Apr 2025 eval) | The P1→P2 delta | **Not found.** Not on live site (Cloudflare 403), not in Wayback (confirmed via CDX API query across the full candidate date range and multiple URL-pattern guesses) |
| Official IDX fact sheet dated inside/at the edge of the window | fs-idx80-2025-04 (edge) | Found and verified (top-10 only, doesn't list full roster) |
| Official IDX fact sheet dated inside the window itself | fs-idx80-2025-05/06/07 | **Not found** — Wayback has zero snapshots for these three months |
| Independent contemporaneous secondary sources, named outlet, byline-distinct | May 2025 delta (3 sources), Aug 2025 delta (2+ sources) | Present, converge exactly, zero contradiction |
| Arithmetic/structural cross-check | P1(primary) + delta = P2; P2 + delta = P3(primary) | Closes exactly to 80↔80 once AADI is moved to P3-side |
| Live-browser access to bypass Cloudflare block | — | Unavailable this session (extension not connected) |

**Net assessment:** this is the same evidentiary pattern already accepted elsewhere in this table for
CROSS_VALIDATED status (see P7's notes: "cross-checked against kontan.co.id/indeks-idx80 live listing
— exact match, zero discrepancy... No primary BEI document... located"). It is **stronger** than P4's
BRACKETED_RECONSTRUCTED case, because P4 relied on a single secondary source for its delta, while this
resolution has 3 independent sources for the May delta and 2+ independent sources for the August delta,
plus zero contradicting sources anywhere.

---

## 7. Decision Gate

**A. RESOLVED — 80 members proven.**

The evidence is sufficient to establish a corrected 80-member P2 roster with **CROSS_VALIDATED**
confidence (not PRIMARY_VERIFIED — no P2-dated official document was locatable). This is not chosen
"merely because it is convenient" or "because IDX80 is normally 80 stocks" — it is chosen because:
1. Three independent, named, contemporaneous outlets converge exactly on a 2-for-2 May 2025 delta with
   no AADI mention.
2. Two independent, named, contemporaneous outlets converge exactly on AADI's inclusion in the 3-for-3
   August 2025 delta.
3. AADI's IPO/listing date (2024-12-05) rules out the "not yet listed" alternative explanation for its
   absence from the May list.
4. The correction closes the P1(primary)↔P3(primary) bracket with zero residual, on both sub-legs
   independently (2 removed/2 added in May; 3 removed/3 added in August) — not just in aggregate.

**Rejected alternative — B (genuine 81-member period):** no evidence anywhere suggests IDX80 genuinely
ran with 81 constituents for any part of this window; every source describing the mechanics of a BEI
index evaluation treats it as a fixed-N reconstitution, and both bounding periods (P1, P3) are
independently confirmed at 80 via official documents.

---

## 8. Proposed Corrected Roster (80 tickers) — NOT executed

```
ACES ADMR ADRO AKRA AMMN AMRT ANTM ARTO ASII AUTO AVIA BBCA BBNI BBRI BBTN BFIN
BMRI BNGA BRIS BRMS BRPT BSDE BTPS BUKA CMRY CPIN CTRA DSNG ELSA EMTK ENRG ERAA
ESSA EXCL GGRM GJTL GOTO HEAL HRUM ICBP INCO INDF INDY INKP INTP ISAT ITMG JPFA
JSMR KLBF LSIP MAPA MAPI MBMA MDKA MEDC MIKA MNCN MTEL MYOR NCKL NISP PANI PGAS
PGEO PNLF PTBA PWON SCMA SIDO SMGR SMRA SRTG SSIA TAPG TKIM TLKM TOWR UNTR UNVR
```

(= the 75 Group-A stable tickers + BUKA + DSNG + GGRM + GJTL + NISP; **AADI excluded**.)

---

## 9. Exact Changes Required to Execute This Resolution (NOT executed — proposal only)

1. In `idx80_membership_history`: delete the single row `(ticker='AADI', period_label='P2')`.
2. In `idx80_reconstitution_periods`: update the `P2` row —
   - `constituent_count`: 81 → 80
   - `confidence`: `UNRESOLVED` → `CROSS_VALIDATED`
   - `source`: replace with a citation to the 3 independent May-2025 sources + 2 independent
     August-2025 sources documented in §3 of this report (and note that no primary IDX document for
     the April 2025 evaluation was locatable)
   - `notes`: replace the current UNRESOLVED-by-design note with an explanation that AADI was
     re-attributed from P2 to P3-only based on this investigation, dated and referencing this report
3. Downstream effect: `research/idx80_membership.py`'s `confidence_tier="reconstructed"` accessor would
   then include P2 (it currently excludes it as UNRESOLVED); `confidence_tier="strict"`
   (PRIMARY_VERIFIED-only) would still correctly continue to exclude P2, since no primary document was
   found.
4. No other table (`idx_tickers`, OHLCV, `broker_flow`, `stockbit_flow_bars`) requires any change —
   broker-flow collection for the full 81-candidate roster (including AADI) was already complete per
   the mission brief and does not need to be redone; AADI's flow data for the May–July window simply
   would not be *used* by research under the corrected P2 membership (AADI's true P2-window flow data,
   if any was collected, reflects real market activity and is not itself wrong — it would just no
   longer be attributable to "P2 IDX80 membership" for research purposes).

**None of the above was executed. This section documents what a follow-up, explicitly-authorized data
correction would need to do.**

---

## 10. What Would Fully Close the Remaining Gap

To upgrade P2 from CROSS_VALIDATED to PRIMARY_VERIFIED (matching P1/P3's tier), one of the following
would be needed:
- The official BEI announcement PDF/XLSX for the April 2025 major evaluation (likely numbered
  Peng-000XX/BEI.POP/04-2025, XX between 012 and 113 based on surrounding document numbers), obtained
  either by a live-browser session that can pass Cloudflare (e.g. Claude-in-Chrome, unavailable this
  session), or a future Wayback crawl if one is ever performed for that URL.
- An official IDX80 fact sheet (`fs-idx80-2025-0{5,6,7}.pdf`) with a visible full constituent list
  (note: even the fact sheets IDX does publish only show top-10 by weight, so this may not fully settle
  it even if found — the Lampiran XLSX/PDF attached to the evaluation announcement itself, which lists
  all 80 names explicitly the way P1's and P3's sources do, is the actual target document).

### 10.1 Post-report independent corroboration (found during execution, §11)

`docs/research_programs/P-A/WP-D/reconstitution_events.csv` — a pre-existing, independently built
research ledger (assembled 2026-07-17, for the unrelated P-A "Auction Dislocation" work package, using
**market.bisnis.com** as its source of record, `SECONDARY_CROSSCHECKED` against kontan.co.id and
blog.rivankurniawan.com) already contains the identical resolution, sourced from a fourth outlet this
report did not originally search:

- `PA-RC-0131`–`PA-RC-0134` (IDX80, review `2025-Q2`, effective 2025-05-02, source
  `market.bisnis.com 20250426/222019126` bisnis/kompas syndication): ADD BUKA, ADD DSNG, DELETE BMTR,
  DELETE MIDI — **no AADI row**.
- `PA-RC-0143`–`PA-RC-0148` (IDX80, review `2025-Q3`, effective 2025-08-01, source
  `market.bisnis.com 20250728/1896891`, `SECONDARY_CROSSCHECKED`): ADD AADI, ADD PTRO, ADD RAJA,
  DELETE GGRM, DELETE GJTL, DELETE NISP.

This is a fifth independent contemporaneous source (distinct from the 4 already cited in §3), reaching
byte-identical add/remove lists on both boundaries via a different retrieval pass, further supporting
the CROSS_VALIDATED tier. `reconstitution_events.csv` was not modified by this investigation — it
already agreed with the resolution and required no correction.

---

## 11. Execution Record (2026-09-01)

The correction proposed in §9 was reviewed and approved, then applied. **Two transactional passes**
were required (the second closes a gap in the original §9 plan, discovered during verification — see
§11.3).

### 11.1 Pass 1 — as specified in §9

```sql
BEGIN IMMEDIATE;

DELETE FROM idx80_membership_history
WHERE ticker='AADI' AND period_label='P2';

UPDATE idx80_reconstitution_periods
SET constituent_count = 80,
    confidence = 'CROSS_VALIDATED',
    source = '<5-source citation, see committed row>',
    notes  = '<resolution note dated 2026-09-01, see committed row>'
WHERE period_label = 'P2';

COMMIT;
```

Result: `idx80_reconstitution_periods.P2` correctly showed `constituent_count=80`,
`confidence=CROSS_VALIDATED`. `idx80_membership_history` correctly dropped to 80 rows for P2 (AADI
gone, all others intact).

### 11.2 Pass 1 gap found during independent verification

`research/idx80_membership.py`'s `_members()` filters `idx80_membership_history.confidence`
**per row** — not `idx80_reconstitution_periods.confidence`. §9 of this report did not specify updating
the per-row `confidence`/`source` values on the 80 remaining `idx80_membership_history` rows for P2, so
after Pass 1 those rows still read `confidence='UNRESOLVED'` (carried over from before the correction).
Empirically confirmed: `members_as_of(conn, '2025-06-15', 'reconstructed')` returned **0** members
instead of the expected 80 — RECONSTRUCTED still fully excluded P2, contradicting the approved outcome.

### 11.3 Pass 2 — corrective follow-up (in scope of the same approved outcome)

```sql
BEGIN IMMEDIATE;

UPDATE idx80_membership_history
SET confidence = 'CROSS_VALIDATED',
    source = '<same 5-source citation as the period-level row>'
WHERE period_label = 'P2';

COMMIT;
```

This updated exactly the 80 remaining P2 rows' `confidence` and `source` fields only —
`ticker`, `period_label`, `effective_from`, `effective_to`, `membership_status`, `created_at` were left
untouched on every row. Re-run of the accessor confirmed `RECONSTRUCTED` then returned the correct 80
members for every date in the P2 window.

### 11.4 Independent post-verification (all items requested)

| Check | Result |
|---|---|
| P2 = exactly 80 members | ✅ `SELECT COUNT(*) ... WHERE period_label='P2'` → 80 |
| P2 confidence = CROSS_VALIDATED | ✅ period-level row and all 80 membership rows |
| AADI absent from P2, present in P3 | ✅ `AADI` rows exist only for P3, P4, P5, P6, P7 |
| P1→P2 = 2-for-2 | ✅ removed {BMTR, MIDI}, added {BUKA, DSNG} (re-derived live from DB, not cached files) |
| P2→P3 = 3-for-3 | ✅ removed {GGRM, GJTL, NISP}, added {AADI, PTRO, RAJA} |
| No duplicate/overlapping membership rows | ✅ zero `(ticker, period_label)` duplicates; zero per-ticker date-range overlaps across periods (window-function check) |
| STRICT still excludes P2 | ✅ `members_as_of(conn, d, 'strict')` → 0 members for every P2-window date tested |
| RECONSTRUCTED now includes P2 | ✅ `members_as_of(conn, d, 'reconstructed')` → 80 members (correct set) for every P2-window date tested |
| Broker-flow / Stockbit coverage unchanged | ✅ `broker_flow` 2,913,210 rows (unchanged), `stockbit_flow_bars` 47,090,725 rows (unchanged), AADI-specific rows unchanged (13,686 / 48,785) |
| Other tables/periods untouched | ✅ `idx_tickers` (972, unchanged), OHLCV (1,077,224, unchanged), P0/P1/P3–P7 rows unchanged (spot-checked, all still their pre-existing `constituent_count`/`confidence`) |

`idx80_membership_history` total row count: 641 → 640 (exactly the 1 AADI/P2 row deleted).
`idx80_reconstitution_periods` total row count: 8 → 8 (no rows added/removed, only P2 updated in place).

No hypotheses were registered, no empirical tests, backtests, or data fetches were run as part of this
execution.
