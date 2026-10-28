# 00 · Buyback data availability (2026-10-28) — B1 of `ZCODE_BRIEF_BUYBACK_2026-10-28.md`

**Counts only; no outcome read.** Each source: what it can and cannot identify (announcement date / executed
amount / shares / period), range, PIT quality, event count, acquisition cost.

| Source | Can identify | Cannot identify | Range / count | PIT quality | Cost |
|---|---|---|---|---|---|
| `walkforward.db corporate_action_events` (7 action types, 6,790 rups rows) | nothing buyback-related | **everything**: zero rows match `buyback` / `pembelian kembali` / `repurchase` in any `raw_json` (verified 2026-10-27 planner + re-verified today incl. rups agendas) | — | — | — |
| `walkforward.db news_mentions` (113,610 rows) | recent news mentions | a historical announcement series — table starts **2026-04-26** | 6 months | n/a | — |
| **fin.db cashflow treasury-purchase lines** (`Pembelian Saham Treasuri` 52 tickers, `Perolehan Saham Treasuri` 22, `Saham Treasuri` 22, `Purchase Of Treasury Stocks` 17, `Pembayaran` 9, `Akuisisi` 7, `Pembelian Kembali Saham*` ~20, singles) | **executed repurchase amount per fiscal period** (statement value, treasury purchases), reusable with the C-003 machinery: D-111 v3 deadlines, USD rule, layout handling | **announcement dates**, programme caps, windows, whether a programme was announced but never executed | **139 tickers, 787 non-null (ticker, period) values, 2008–2026**; by year 2008-2014 ≈ 2–26/yr, 2015-2019 ≈ 26–39, **2020: 80, 2022: 81, 2025: 130, 2026: 67** | statement-date availability via D-111 v3 (same as dividends); no look-ahead by construction | zero (local) |
| fin.db balance-sheet treasury-stock lines | cross-check of holdings level | flow attribution | not yet counted (build-time check) | same | zero |
| KSEI monthly | nothing for buybacks (treasury shares remain issued; investor buckets unaffected) | — | — | — | — |
| **IDX Aksi Korporasi page** (idx.co.id, "Pembelian Kembali Saham" filter) [P] | **the official dated announcement series** (announcement date, value, cap, window) | — | unknown depth | official | **blocked from this machine (403)** → owner-browser item |
| OJK press releases [P] | the policy-regime boundaries: buyback-without-RUPS first issued **Mar 2020** (COVID), renewed **19 Mar 2025**, **extended to June 2027** (26 Oct 2026 news [S]) | per-name announcements | 3 regime dates | official | free |
| Secondary coverage (Stockbit/ajaib lists, e.g. 19 Oct 2026: ~28 names incl. BBCA, BREN, CNMA [S]) | spot lists, current wave | a systematic historical archive | ad hoc | mixed | free |

## Verdict

- **Announcement-event design: INFEASIBLE today.** No local source carries a dated announcement series; the
  official IDX page is blocked from this machine. It becomes feasible only via an owner-browser IDX pull
  (keterbukaan informasi / aksi korporasi) — an acquisition decision, not a ZCode action.
- **Executed-repurchase design: FEASIBLE-THIN locally** (139 tickers / 787 periods, PIT-able, zero cost),
  with the wave structure matching the OJK policy regimes (2020, 2025→). Statement dates only — the signal is
  "the company IS buying", not "the company announced".
- Not INFEASIBLE overall → proceed to B2 (overlap).
