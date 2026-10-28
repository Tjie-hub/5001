# 02 · Ranked Shortlist — hypothesis search 2026-10-28

**Propose-only.** Nothing registered, no D-entry, no registry edit. Scores are 1–5 (5 best). Power uses the
monthly-panel calibration SE ≈ 0.68%/mo at 209 formations (HYP-PM-0020 G0), bar 3.300069 at census 613, G0
minimum power 20%. Sources: `00_EXCLUSION_INDEX` rows in brackets.

| Rank | Candidate | Barrier durability | Data ready today | Prior-only power | Distinctness | Cost survives | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | **C-003 dividend-yield level** [F5] | 4 (payout commitment, tax/agency) | 4 (dividends line via {FQ} machinery; coverage count at build) | **5** (~80–95% at 0.80%/mo floor on 209 formations; in-repo prior t 2.46–4.11) | 3 (E/P correlation — FM separator mandatory; family governance open) | 5 (turnover 0.16, net +7.07%/yr prior) | **REGISTERABLE** after owner rules on debt + family |
| 2 | **C-001 KSEI foreign share level/Δ** [D10-adjacent] | 5 (public monthly custody, rule-based cap) | 5 (panel verified today: 211 mo, 1,055 names) | 2 (18% at 0.5%/mo → fails; ≥35% at 0.8%/mo) | 5 (F_* never tested) | 5 | **REGISTERABLE ONLY with a pre-registered floor ≥ 0.8%/mo** |
| 3 | **C-006 KSEI MF/PF share + Δ** | 4 (mandate-driven custody flows) | 5 (same panel) | 2 (same as C-001) | 4 (holder class never tested; complements {OC}) | 5 | Same condition as C-001; share one build/G0 with it |
| 4 | **C-002 foreign-cap-proximity exclusion overlay** | 5 (49% cap is a standing rule) | 5 (43,285 name-months ≥45% verified) | 3 (paired-overlay design ~25–35% at a 0.30%/mo floor — clears the 20% minimum, not 80%) | 4 (threshold-exclusion, not a rank) | 5 (overlay ≈ zero added cost) | **REGISTERABLE as an overlay arm** (the VOLEX precedent) |
| 5 | **C-005 USDIDR × currency-exposure (FM form)** | 4 (macro accounting transmission) | 2 (FX ready 2008-12→; exposure classification only 108 USD-reporter flags; revenue-currency needs acquisition) | 2 (FM interaction ~40% at 1.0%/mo; quintile-state form underpowered) | 5 (first macro series ever used) | 4 | **CONDITIONAL: blocked on classification acquisition** (public filings, ~2 Stockbit calls × 959, one evening, inside existing rules) |
| 6 | C-004 sanction-deadline pressure [C-004] | 4 | 3 (CSV exists; <24 formations) | 1 | 5 | 2 | NOT registrable (own G0 would fire); keep as monitored list |
| 7 | C-008 auction/ARB-7% records [C-008] | 5 | 4 (recording now) | 1 (by design, records) | 4 | 5 | Records only; G0 re-check 2027-Q2 |
| 8 | C-007 HSC IHSG-exclusion one-shot [C10/F8] | 5 | 3 (date pending, idx.co.id blocked) | 1 (N=1) | 5 | n/a | Record; also an owner note: it changes the IHSG benchmark itself |
| 9 | C-009 executed buybacks / mcap [buyback brief B1-B3, 2026-10-27] | 4 (OJK-mandated buyer, rule barrier) | 3 (139 tickers / 787 periods in fin.db; **no announcement dates** — IDX page 403) | 1 standalone (~12% at 1.0%/mo on ~100 formations) / rides C-003 as net-payout composite | 3 (net-payout collapse + stress confound — two FM separators) | 4 | **UNDERPOWERED standalone**; composite net-payout path or owner-browser announcement pull |

**{FQ} family-widening arms (B/M, gross profitability, low asset growth, low leverage on the 998-ticker panel)**
are deliberately NOT ranked here — they are the Wednesday brief's K5 memo's scope and an input to this search,
not a duplicate of it (brief header). They share C-003's panel and its power class.

## Data acquisition the shortlist implies (all inside existing rules)

1. **Dividends-paid extraction from fin.db cashflow** (C-003): pure local compute, ~an hour, no external calls;
   coverage table first (count-only).
2. **Revenue-currency / USD-debt disclosure** (C-005, only if pursued): public IDX filings via Stockbit, ~2
   requests × 959 tickers ≈ one evening ≤21:05 window; legality: public disclosures, no login scraping; disk
   trivial.
3. **BEI announcement pages** (C-007 date; D8 carry-over): remain blocked from this machine → owner-browser list.
4. Nothing else: C-001/C-002/C-006 need zero acquisition.

## Recommendation (for the owner — decide, do not have ZCode file)

1. **C-003 is the only candidate with real prior power.** Sequence it AFTER the {FQ} E/P G0 result (tonight
   17:41): if E/P passes and registers, C-003's FM-over-E/P separator is directly measurable and the family
   question (widen {FQ} vs new Payout family) is the owner's; if E/P stops out, C-003 stands alone with its
   declared alpha_v2 debt.
2. **C-001 + C-006 as one KSEI-holder build/G0** (two arms, one census entry each — the {OC} A1/A2 precedent),
   with a pre-registered floor the owner must explicitly accept at ≥ 0.8%/mo (otherwise the G0 stop rule fires
   by construction, cf. D-087/D-092/D-102).
3. **C-002 as a cheap overlay arm** piggybacking the same KSEI build (paired book-vs-book, VOLEX-style,
   floor 0.30%/mo).
4. C-005: only if the owner wants the acquisition evening; otherwise park.
5. C-004/C-007/C-008: records and monitors, no registration (their files say why).

## Draft skeletons

Written for the top 5 (marked DRAFT, propose-only): `cand/SKEL-C-003_dividend_yield.md`,
`cand/SKEL-C-001_foreign_share.md`, `cand/SKEL-C-006_mf_pf_share.md`, `cand/SKEL-C-002_cap_proximity_overlay.md`,
`cand/SKEL-C-005_usdidr_fm.md` (conditional).
