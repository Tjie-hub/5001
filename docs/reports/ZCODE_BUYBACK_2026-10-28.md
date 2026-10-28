# ZCODE — Buyback candidate (2026-10-28, propose-only)

Brief: `ZCODE_BRIEF_BUYBACK_2026-10-28.md`. No return, spread, t-stat, IR or P/L of any buyback sort was
computed or read. Census stays 613; nothing registered, no D-entry, no freeze.

## B1 — data availability (`P-M/buyback/00_DATA_AVAILABILITY_2026-10-28.md`)
- Local announcement series: **none.** `corporate_action_events` (7 types, 6,790 rups rows) has zero
  buyback/pembelian-kembali/repurchase matches (planner's check re-verified); `news_mentions` starts
  2026-04-26; KSEI cannot see buybacks.
- **fin.db executed-repurchase series: FEASIBLE-THIN** — treasury-purchase cashflow lines, **139 tickers,
  787 (ticker, period) values 2008–2026**, waves exactly at the OJK no-RUPS regimes (2020: 80, 2022: 81,
  2025: 130, 2026: 67). PIT-able via the C-003 machinery (D-111 v3 + USD rule). Statement dates only — no
  announcement dates.
- External: the official [IDX Aksi Korporasi buyback list](https://www.idx.co.id/id/perusahaan-tertacat/aksi-korporasi) [P]
  is the dated announcement series but 403s from this machine → **owner-browser item**. OJK press releases [P]
  date the policy regimes (Mar-2020 COVID issue; 19 Mar-2025 renewal; [extension to June 2027, 26 Oct 2026 [S]](https://snips.stockbit.com/stockbit-research/ojk-perpanjang-izin-untuk-emiten-buyback-saham-tanpa-rups-hingga-juni-2027));
  secondary spot lists exist ([ajaib, Apr 2025 [S]](https://ajaib.co.id/belajar/berita/16-emiten-siap-buyback-saham)) but no systematic archive.
- **Verdict: announcement design INFEASIBLE today; executed design feasible-thin. Not INFEASIBLE overall.**

## B2 — overlap (`P-M/buyback/01_OVERLAP_2026-10-28.md`)
Distinct **only** as an executed-flow / liquidity-provision panel arm. Two mandatory separators:
(1) FM incremental over dividend yield + E/P (net-payout collapse clause — otherwise it is C-003's family,
as a component), (2) the D-075 stress-state control (buyback waves = OJK crisis windows; if the effect lives
only there it is a re-skin of the dead D-079 stress-reversal). The MPW prior on issuance asymmetry is stated:
the dead {CF} arm does not predict its mirror. Not a re-skin at the proposed construction.

## B3 — C-009 status: **UNDERPOWERED (standalone); composite path open** (`search/cand/C-009_buyback.md`)
- Standalone rank arm: ~100 usable formations 2018→, SE ≈ 0.98%/mo → power ≈ 12% at 1.0%/mo — the
  tender/PEAD/lock-up class. **No skeleton written** (brief rule).
- The arithmetic favours the **composite net-payout arm** (dividends + buybacks − issuance) riding C-003's
  209 formations and power — a **family-widening decision inside the C-003 freeze, to be made BEFORE the
  freeze is pinned**, not a separate registration.
- The **announcement design** becomes feasible only via an owner-browser IDX pull (dated programme
  announcements) — acquisition decision.

## Open owner questions
1. Fold buybacks into the C-003 freeze as a pre-specified net-payout variant (one census entry, C-003's
   power), or keep C-003 pure (dividends only)?
2. Owner-browser pull of the IDX buyback announcement list (and the HSC exclusion date, D8 carry-over)?
3. If neither: C-009 stays filed as UNDERPOWERED; no further action.

## Files and commits
- `docs(research): buyback -- B1 data availability` (this step's commit)
- B2 overlap, C-009 + shortlist row + TODO line + this report in the same or follow-up small commits.
- Reminder carried: tonight 17:41 {FQ} G0 (Wednesday K1 + C-003 L4 line).
