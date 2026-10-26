# {FQ} PIT follow-ups (2026-10-26) — prep for approved D4 and D8

**Scope:** data and reachability only. No v3, no freeze, no D-entry (D9 stays open). No join to prices, no returns.
Companion to `11_FQ_PIT_RULE_DRAFT_V2_2026-10-25.md` §6/§8/§9/§10.

## 1. D4 late-filer list — `12_FQ_LATE_FILERS_2026-10-26.csv`

Built 09:21 by the earlier session from the news articles cited in v2 (verified here 12:xx, read-only).

| Item | Value |
|---|---|
| Rows | 417 (no malformed rows) |
| Distinct tickers | 142 |
| Tag | **all 417 are [S]** (secondary news); no [P] row exists |
| Periods | FY2024 128 · FY2025 84 · H1-2025 52 · Q1-2025 59 · Q3-2024 46 · Q3-2025 48 |
| Repeat names | appear in 1 period: 59 · 2: 27 · 3: 6 · 4: 3 · 5: 8 · **6 (all six periods): 39** |
| Duplicate (ticker, period) rows | 7 — to be de-duplicated or explained before any use |

**Reading:** 83 of 142 names (58%) appear in two or more of the six periods, and 39 appear in all six. The late-filer
tail is concentrated in a persistent set, not spread evenly. That supports an availability flag keyed to the issuer
(D4) rather than only to the period. This is a count of listed sanctions, not a statement about returns.

**Limits:** six periods only (Q3-2024 to Q3-2025); sources are news lists, so a name sanctioned but not reported by
the cited articles is missing. Issuers sanctioned in the same article appear once per period named in it.

## 2. Unfiled at day 30 (v2 §9 "not built")

**Cannot be answered from data on this machine.** `fin.db` (`~/idx_external/stockbit_fin/fin.db`: tables `fin_rows`,
`fin_values`, `fin_files`) holds `period_end` but **no filing, publication or release date**. A raw vendor file
(`raw/LMAS/income.json.gz`) has 10 keys, none date-like. Without a filing date there is no "filed by day 30" test.
**What would answer it:** the issuer submission timestamp from IDX (SPE-IDXnet / "laporan keuangan" listing, owner
browser) or a vendor field that carries a publication date.

## 3. D8 primary texts — reachability from this machine (2026-10-26, curl, browser UA + Accept + Referer)

| Text | Result | Where it stands |
|---|---|---|
| IDX I-E (current; Kep-00087/BEI/12-2025) | `idx.co.id` PDF → **403**; Wayback copy → **404** | Cited as the governing decree by an issuer filing ([S], Waskita, Apr 2026). Full text not obtained. |
| Kep-36/PM/2003 (original X.K.2) | OJK regulation page → 302/404; no URL found | Owner/OJK library, search `KEP-36/PM/2003`. |
| Kep-00027/BEI/03-2020 | Not fetched; [S] only | Per secondary reports: 20 Mar 2020 relief, +2 months for annual and Q1. |
| Kep-00057/BEI/08-2020 | Not fetched; [S] only | Per secondary reports: dated 19 Aug 2020, revoked on Kep-00089 taking effect. |
| Kep-00089/BEI/10-2020 | Not fetched; [S] only | Per secondary reports: 15 Oct 2020; +2 months annual/Q1, +1 month mid-year/quarterly. **End date still unverified.** |
| Sanction ladder (I-H, II.6.4) | [S] only | Suspension at calendar day 91; written warning III with Rp150 jt fine reported before that. |

**Owner-browser list (all blocked):**
- `https://www.idx.co.id/Media/gmddcpw4/signed_peraturan_nomor_ie_tentang_kewajiban_penyampaian_informasi.pdf` (I-E, 403)
- idx.co.id regulations page for Kep-00027/BEI/03-2020, Kep-00057/BEI/08-2020, Kep-00089/BEI/10-2020 and its end date
- OJK / Bapepam-LK archive for KEP-36/PM/2003

Secondary-source summaries above were produced by a web search tool and are **[S]**: do not cite them as the decisions' text.

## 4. Which D-items are unblocked for a v3, if the owner later asks for one

| D | Status |
|---|---|
| D1, D3, D5 | Unblocked (no external text needed). |
| D2 | **Still needs** IDX attested-interim notices and I-E tiers. |
| D4 | Partly unblocked: [S] list exists (§1); a [P] source list from IDX is still wanted. Day-30 question (§2) unanswerable. |
| D6 | Still needs owner-browser originals for the stratified restatement sample. |
| D7 | Still needs Kep-36/PM/2003. |
| D8 | **Blocked** — nothing primary obtained; list in §3. |
| D9 | Not approved; not touched. |
