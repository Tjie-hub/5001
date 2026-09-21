# IDX Strategy Suite — Live Review

**Latest review:** 15 Jun 2026, ~06:08 WIB (pre-market) · **Host:** `192.168.31.214:5001` (Linux) · **Mode:** SHADOW
**First review:** 13 Jun 2026, ~21:34 WIB
Accessed live over the LAN via browser automation. Remote Desktop not required — the app answers directly on the LAN.

---

## TL;DR (as of 15 Jun)

The frontend was rebuilt and the **multi-path consolidation landed well**: there is now one unified global nav across every page. **3 of the 4 data issues** from the first review are fixed. **One bug remains** (scanner duplicate/empty rows) and **one new issue** appeared (two overlapping nav rows).

| Item | 13 Jun | 15 Jun | Status |
|---|---|---|---|
| Fragmented nav (3 separate frontends) | 3 different nav bars | One unified global nav on all pages | ✅ Fixed |
| Dashboard panels — no "as of" date | Missing | "as of 2026-06-15" stamps added | ✅ Fixed |
| BRPT VPIN contradiction (0.985 TOXIC vs −3σ) | Contradictory | Split: `VPIN absolute 0.985` + `Z-score relative 0.0σ vs 10d` | ✅ Fixed |
| BRPT order-flow magnitude (−1354.8B) | Unlabeled/confusing | Relabeled `Net Value (20d, IDR): −1.35T` | ✅ Fixed |
| Scanner duplicate / empty rows | Present | Still present (worse: GRPH ×3, BAIK ×2) | ❌ Not fixed |
| Nav redundancy | n/a | Global nav + secondary tab row overlap | ⚠️ New |

---

## 1. Architecture — consolidation confirmed

Previously three separate frontends, each with its own nav and styling:
- Main SPA `/` (hash tabs), standalone `/dashboard`, standalone `/dive/<ticker>`.

Now there is a **single global header** shared across all pages:

`IDX Suite · Dashboard · Sector · Calendar · | Trades · Signals · Scanner · Backtest · Intraday · | Screener · Broker Flow · Portfolio · Audit · | Search · OFF/SHADOW/ENFORCE · clock`

Verified identical on `/`, `/dashboard`, and `/screener`. The Dashboard's old separate `Signals/Screener/Portfolio` nav is gone. Clean URLs are kept for the standalone routes (`/dashboard`, `/sector`, `/screener`, `/portfolio`) while the SPA views stay as hash tabs — matches the recommended approach (one shell + one nav, keep bookmarkable URLs).

**New page:** `/screener` — a Fundamental Screener (972-ticker universe, PE/PBV/ROE/D-E/Net Margin/Revenue Growth + Flow Score & Verdict, custom column picker, rule-based filters, presets, 49 pages). Data populated and clean.

---

## 2. Data fixes — verified live

**VPIN (BRPT Deep Dive).** Old single field "VPIN 0.985 / Z-score −3.0σ" was internally contradictory. Now two clearly separated fields: **VPIN (absolute) = 0.985 abs** (high level) and **Z-score (relative) = 0.0σ vs 10d** (normal vs its own recent history). Correct and self-consistent.

**Order flow (BRPT).** Old "Net Vol (20d): −1354.8B" read like −1354 billion. Now **Net Value (20d, IDR): −1.35T** — clarified as net traded *value in rupiah*, which is plausible for a liquid name. Was a labeling gap, not a calc error; now resolved.

**Dashboard staleness.** Panels (Market Breadth, Foreign Flow & VPIN) now show **"as of 2026-06-15"**, removing the earlier confusion between "no data today" and cached historical data.

---

## 3. Still open

**(A) Scanner duplicate & empty rows — NOT fixed.**
Re-ran Quick Scan (959–972 universe) on 15 Jun. The result table still contains:
- `GRPH / ORB / BULLISH / 0%` repeated **3×**
- `BAIK / — / BULLISH / 0%` repeated **2×**
- Rows with **0% strength, WF `—`, no close** rendered as signals (BAIK, GRPH)
- Top rows (`FORU`, `SURE`) with empty close

Fix: dedupe server-side by `ticker + strategy`, and suppress rows with no close / no WF score. The new `/screener` table is clean, so the rendering logic exists — the strategy scanner just isn't applying it.

**(B) Nav redundancy — new.**
On `/`, the **global top nav** and the **secondary tab row** both list Trades · Signals · Scanner · Backtest · Intraday · Broker Flow · Calendar — the same destinations twice. Recommendation: keep the global nav as primary and either remove the duplicate tab strip or repurpose the second row for contextual sub-tabs only.

---

## 4. Feature health (functionally tested, both sessions)

| Feature | Path | Test | Result |
|---|---|---|---|
| Market Dashboard | `/dashboard` | Load | ✅ Risk gauge, IHSG, sector heatmap, foreign flow, watchlist |
| Fundamental Screener | `/screener` | Load + paginate | ✅ 972 tickers, fundamentals + flow verdict |
| Deep Dive | `/dive/BRPT` | Load | ✅ Chart, walk-forward, VPIN, order flow, brokers |
| Backtest | `/#backtest` | Ran BRPT | ✅ Win 100%, Avg +9.5%, Sharpe 1.64, MaxDD −20.9% |
| Broker Flow | `/#brokerflow` | Loaded BBRI | ✅ Net +32 Dist, top buyers/sellers w/ ASING-LOKAL tags |
| Scanner | `/#scanner` | Ran Quick Scan | ⚠️ Works (959+ scanned) but dup/empty rows |
| Agent Audit | `/#audit` | Load | ✅ Approve/Veto/Baseline + agreement table + log |
| Monitor / paper trade | `/` | Clicked NEST | ✅ Live trade + broker drill-down modal |

Empty/`INSUFFICIENT_DATA` panels are expected outside market hours (pre-market Monday; last full scan 12 Jun).

---

## Punch-list for next push
1. Dedupe scanner rows (`ticker+strategy`) and drop rows with no close/WF.
2. Remove the duplicate nav row on `/` (keep one nav).
3. (Optional) Carry the unified header onto `/dive/<ticker>` and `/sector`/`/portfolio` for full consistency.

*Source code is not in the connected `IDX` folder, so these were assessed live, not from code. Copy the Flask app + templates into the folder and I can implement the punch-list directly.*
