# IDX Strategy Suite — Live Review

**Reviewed:** 13 Jun 2026, ~21:34 WIB · **Host:** `192.168.31.214:5001` (Linux) · **Market:** CLOSED (Saturday) · **Mode:** SHADOW

Accessed live over the LAN. Chrome Remote Desktop to the Linux box was not needed — the app responds directly on `192.168.31.214:5001`.

---

## 1. Overall status

The app is **up and the compute backend works**. Every interactive feature I triggered returned real results. The many empty / `INSUFFICIENT_DATA` panels on the Dashboard are expected: it's Saturday, the scheduler last ran **2026-06-12 14:35**, so there is no intraday data for today. Historical data (through Fri 12 Jun) is intact.

---

## 2. Features tested (not just viewed)

| Feature | Path | Action taken | Result |
|---|---|---|---|
| Market Dashboard | `/dashboard` | Load | ✅ Renders: risk gauge 31/YELLOW, IHSG 6.007, sector heatmap, foreign flow, unified watchlist (40) |
| Deep Dive | `/dive/BRPT` | Load | ✅ Chart + VWMA20 + vol profile, strategy walk-forward table, VPIN, order flow, top brokers |
| Backtest | `/#backtest` | Ran walk-forward on **BRPT** | ✅ Best Win 100%, Avg +9.5%, Sharpe 1.64, Max DD −20.9% + per-strategy table |
| Broker Flow | `/#brokerflow` | Loaded **BBRI** (12 Jun) | ✅ Net +32 (Dist), 52 buyers / 20 sellers, top buyers/sellers w/ ASING-LOKAL-PEMERINTAH |
| Scanner | `/#scanner` | Ran **Quick Scan** | ✅ 959 tickers scanned → 7 signals, 6 WF≥60%; ranked table w/ Trade/BT/Dive actions |
| Agent Audit | `/#audit` | Load | ✅ Approve/Veto/Baseline stats, agent-agreement table, decision log |
| Monitor + broker modal | `/` | Clicked NEST card | ✅ Live paper trade (+5.36% HOLD) + broker acc/dist drill-down |
| Signals | `/#signals` | Load | ✅ Works; "No signals recorded today" (expected — weekend) |

**Verdict:** functionally healthy. The scanner crunching 959 names and the backtest engine both completed live.

---

## 3. Issues / data quirks worth fixing

1. **Scanner duplicate & empty rows** — `FORU / Conservative Confirm / BULLISH 100%` appears twice (one with close `3,600`, one with close `—`). Several rows show `BULLISH` with **0% strength, WF `—`, close `—`** (BAIK, GRPH). Dedupe by ticker+strategy and suppress rows with no close/WF.
2. **Deep Dive VPIN contradiction (BRPT)** — VPIN `0.9850` labelled **TOXIC** but Z-score `−3.0σ`, regime NORMAL, and "NO_SIGNAL / no informed activity". A 0.985 VPIN with a −3σ z-score is internally inconsistent — check the z-score window/normalisation.
3. **Order-flow magnitude (BRPT)** — "Net Vol (20d): **−1354.8B**" reads as −1.35 *trillion*, which is implausible for one stock. Likely a units/scaling bug (lot vs share vs rupiah). Worth auditing the aggregation.
4. **Dashboard zeros vs. populated watchlist** — breadth shows 0 advancing / 0 declining and "INSUFFICIENT_DATA", yet the Unified Watchlist below lists 40 tickers. Mixed "no data today" + "cached data" on one screen is confusing; add an explicit "as of <date>" stamp on each panel.

---

## 4. Why there are "so many paths"

There are effectively **three separate frontends**, each with its own template, styling, and navigation:

| Frontend | Path(s) | Its own nav bar |
|---|---|---|
| Main SPA "IDX Suite v2.6" | `/` + 12 hash tabs (`#signals`, `#scanner`, `#backtest`, `#brokerflow`, `#audit`, …) | Monitor · Signals · Scanner · … · Agent Audit |
| Market Dashboard | `/dashboard` | Signals · Screener · Portfolio · Dashboard |
| Deep Dive | `/dive/<ticker>` | "← Dashboard" link only |

So it's not really 15 pages — it's **one SPA plus two stand-alone server-rendered pages** that were bolted on later. The friction is that each has a *different* navigation and visual language, and the names overlap (Dashboard's "Signals/Screener" vs the SPA's "Signals/Scanner"), so it feels like many disconnected apps.

---

## 5. Can it be one frontend? — Yes

Recommended, in order of effort:

**Option A — Quick win (low effort):** Extract a **single shared header/nav** (one Jinja partial / one nav component) and include it in all three templates. Same logo, same tab set, same SHADOW/ENFORCE toggle and clock everywhere. The pages stay separate routes but stop *feeling* separate. ~1 day.

**Option B — Real consolidation (recommended):** Fold Dashboard and Deep Dive into the v2.6 SPA shell:
- Add **Dashboard** as a tab (or make it the Monitor landing).
- Render **Deep Dive** inside the SPA shell instead of a standalone template — keep the URL `/dive/BRPT` as a real route via the History API so links/bookmarks still work, but it loads the shared shell + mounts the dive view.
- Delete the Dashboard's separate `Signals/Screener/Portfolio` nav; there is now **one** nav.
- Benefits: one CSS/JS codebase, consistent styling, shared global state (mode toggle, clock, ticker search), and the Trade/BT/**Dive** buttons in the scanner navigate within the same shell. ~2–4 days.

**Keep separate routes regardless** — clean URLs like `/dashboard` and `/dive/BRPT` are good for bookmarking and for the scanner's per-row links. The goal isn't fewer URLs, it's **one shell and one nav** behind them.

I'd suggest **Option B** with real (History-API) routing so `/dashboard`, `/scanner`, `/dive/<t>` all serve the same shell. Heavy views (the Deep Dive chart) can lazy-load so the SPA stays light.

---

*To let me implement any of this, copy the project source into the connected `IDX` folder (or share the Flask app + templates) — the folder is currently empty, so I can't edit the code from here yet.*
