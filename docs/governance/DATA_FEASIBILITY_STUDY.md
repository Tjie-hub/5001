# Data Feasibility Study

**Layer:** L0 — Governance & Scope · **Status:** Canonical scope constraint · **Version:** 1.0
**Date:** 2026-07-15 · **Owner:** Chief Research Architect
**Authority:** This document's **Data Capability Matrix (§4)** is the official scope constraint for the Research OS. No Research Program may register a hypothesis whose `required_data` is not classified **Available Today** or **Obtainable Later** here. Programs requiring **Institutional-Only** or **Unrealistic** data may be documented as *Future Capability* only (see [[RESEARCH_OS_MASTER_ROADMAP]] §Current-vs-Future).

---

## 1. Purpose

Determine what market data is *actually* obtainable for the Research OS, grounded in the current repository (`data/walkforward.db`, 61 tables) and its live provider stack — not in aspiration. Every downstream decision (scope, domains, programs, object model) is downstream of this study.

## 2. Method

Inventory taken 2026-07-15 directly from the production database and provider layer. For every candidate dataset we record: availability, vendor/source, historical depth, update frequency, resolution, licensing, estimated cost, implementation complexity, and a capability class.

## 3. Dataset Inventory (measured, not assumed)

| Dataset | In-repo table | Resolution | History (measured) | Universe | Vendor/source |
|---|---|---|---|---|---|
| Daily OHLCV | `ohlcv` (1.05M rows) | **Daily bars** | 2021-07-05 → present (~5 yr) | 959 tickers | Stockbit / yfinance |
| Corporate actions | `corporate_actions` (2.2k) | Event | 2021 → present | 501 tickers | Stockbit |
| Intraday signed flow | `stockbit_flow_bars` (12.2M) | **1-minute** buy/sell lot+freq+delta | 2025-07-07 → present (~1 yr) | broad | Stockbit |
| Daily net flow + scores | `stockbit_flow` (47k) | Daily | → present | broad | Stockbit (smart-money/foreign) |
| Broker summary | `broker_flow` (872k) | Daily, **broker-level** by investor type (Asing/Lokal/Pemerintah) | 2026-04-01 → present (~3.5 mo) | 871 tickers | Stockbit broker summary |
| Broker accumulation | `bandar_detector` (36k) | Daily accdist (top1/3/5/10) | 2026-04-01 → present | broad | Derived from broker_flow |
| Trade-tick prints | `ticks` (10.4M) | **Tick**, price+vol+direction (up/down/unch) — **trades only, no quotes** | 2026-04-18 → present (~3 mo) | 867 tickers | Stockbit |
| VPIN (toxicity) | `vpin_scores` (20k) | Daily | 2026-06-05 → present (~5 wk) | 972 tickers | **Computed in-repo** |
| Fundamentals | `stockbit_keystats` (5.2k) | Snapshot (PE/PBV/EV/EPS…) | 2026-04-10 → present | broad | Stockbit |
| Sector/index perf | `sectors_*` | Daily/periodic | → present | indices+sectors | Stockbit |
| Dividend calendar | `sectors_dividend_calendar` (92) | Event | → present | broad | Stockbit |
| News mentions | `news_mentions` (46k) | Daily count + headlines | 2026-04-26 → present | 972 | Aggregator |
| Suspension/halt events | `suspension_events` (3.1k) | Event | → present | broad | Derived |
| Index membership | `idx_tickers` (972) | Flags (IDX30/LQ45/IDX80) | current | 972 | Stockbit/IDX |

## 4. Data Capability Matrix — **OFFICIAL SCOPE CONSTRAINT**

### 4.1 Available Today (executable scope)
| Capability | Backing data | Notes / caveat |
|---|---|---|
| **Cross-sectional daily equity research** | `ohlcv` 5 yr, split-adjusted via `corporate_actions` | Deepest, most reliable asset. Anchor of all Programs. |
| **Illiquidity / price-impact proxies** | `ohlcv` (Amihud = \|ret\|/value), `vpin_scores` | Amihud computable over full 5 yr; VPIN only ~5 wk. |
| **Order-flow-imbalance PROXY (intraday)** | `stockbit_flow_bars` 1-min signed lot/freq/delta | ~1 yr history. **Proxy, not true OFI** (no LOB). |
| **Informed-flow / adverse-selection proxy** | `broker_flow` (foreign vs local vs govt), `bandar_detector` | Only ~3.5 mo — short for regime coverage. |
| **Trade-sign / tick-direction microstructure** | `ticks` (up/down/unchanged) | ~3 mo, **trades only — no bid/ask**. |
| **Close/near-auction dislocation (proxy)** | `ohlcv` open/close, `sectors_*` | Via OHLC only; no true auction imbalance messages. |
| **Fundamental / factor overlays** | `stockbit_keystats` | Snapshot depth ~3 mo. |
| **Event studies** | `corporate_actions`, `sectors_dividend_calendar`, `suspension_events`, `news_mentions` | Corp actions deep; others short. |

### 4.2 Obtainable Later (accumulate-forward or modest procurement)
| Capability | Path | Complexity |
|---|---|---|
| Multi-year intraday flow / broker / tick / VPIN history | **Time** — keep ingesting daily; short windows lengthen naturally | Low (already wired) |
| Level-1 quotes / BBO / bid-ask spread series | Vendor upgrade (Stockbit Pro / RTI / data reseller) | Medium (cost + adapter) |
| Deeper broker-summary backfill | Vendor historical request | Medium |
| Options / derivatives microstructure | New vendor | Medium-High |

### 4.3 Institutional Only (not attainable at current tier)
| Capability | Why | Would require |
|---|---|---|
| L3 limit order book / full depth-of-book updates | Not in any current feed | IDX direct feed / premium vendor, co-location, high cost |
| Full order-event stream (adds/cancels/modifies) | Same | Same |
| Auction imbalance messages / indicative match prices | Not published to retail feeds | Exchange-grade feed |
| Queue-position / cancel-to-trade dynamics | Requires L3 | Exchange-grade feed |

### 4.4 Unrealistic (out of scope for this institution)
| Capability | Why |
|---|---|
| Nanosecond/microsecond HFT-grade timestamps | IDX retail data tier is ≥1-minute; latency-arbitrage research is not the mission |
| Co-located tick-to-trade latency measurement | No infrastructure, not aligned with charter (mechanism discovery, not execution) |

## 5. Consequences for the Research Roadmap

1. **The three original Microstructure Programs are re-classed by data reality:**
   - *Order-Flow / Imbalance* → **Current Capability (PROXY tier)** using 1-min signed flow + broker summary; the *L3/OFI-proper* form is **Future (Institutional)**.
   - *Auction Dislocation* → **Current (proxy)** via OHLC close behaviour; *auction-message* form is **Future (Institutional)**.
   - *Liquidity Vacuum / toxicity* → **Current** via VPIN + Amihud + spread-proxy from tick direction (history-limited).
2. **The inaugural executable program should anchor on the deepest data** — daily OHLCV — hence the worked example uses **Amihud illiquidity** ([[WORKED_EXAMPLE_END_TO_END]]).
3. **Short-history datasets (broker flow, ticks, VPIN, fundamentals: 3 wk–3.5 mo) cannot yet support regime-stratified or walk-forward validation.** Any hypothesis depending on them must declare a *history-maturity gate*: validation deferred until ≥N months accumulate. This is a first-class scope rule, not a footnote.

## 6. Open procurement questions (for the owner)
- Is a paid L1 quote/BBO feed within budget? (Unlocks true spread/quote microstructure — the single biggest capability jump short of institutional L3.)
- Retention policy for the 12.2M-row 1-min flow bars and 10.4M-row ticks as history grows — storage/compaction plan (feeds [[RESEARCH_DATABASE_CONCEPT]] outline).

---
*This study is a living document. Re-run the inventory query and re-classify whenever a provider or table changes. Any scope decision that contradicts §4 must cite an updated version of this file.*
