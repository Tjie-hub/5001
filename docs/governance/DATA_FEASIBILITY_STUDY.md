# Data Feasibility Study

**Layer:** L0 — Governance & Scope · **Status:** Canonical scope constraint · **Version:** 1.0
**Date:** 2026-07-15 · **Owner:** Chief Research Architect
**Partial re-run, 2026-09-09:** `broker_flow` / `bandar_detector` rows in §3 and the corresponding §4.1/§5.3
caveats were re-measured against live `data/walkforward.db` (read-only) per this document's own footer rule,
after the figures were found contradicted by evidence gathered during the P-M broker-flow Dataset A governance
work ([[DECISION_LOG]] D-032…D-035). **No other row in §3 was re-verified in this pass** — this is a scoped
correction, not a full re-inventory. `capability_class` is unchanged by this correction (CRO decision,
[[RESEARCH_OBJECT_SCHEMA]] §3.4) — only the underlying measured facts are corrected.
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
| Broker summary | `broker_flow` (3.00M rows, re-measured 2026-09-09 [DB-VERIFIED]; was reported 872k/~3.5 mo) | Daily, **broker-level** by investor type (Asing/Lokal/Pemerintah) | **2025-01-02 → 2026-09-08 (~20 mo)** — corrected; the ~3.5 mo figure was stale. **Density is tiered/uneven across the full 958-ticker active universe** (D-032: 291 dates at ~96–108 tickers/day, 102 dates at up to ~829 tickers/day, pre-backfill baseline) — this row states calendar span, not uniform per-ticker depth. A fully-reconciled subset (IDX80, 79-ticker fixed roster, NON-PIT, excl. 2026-08-25) exists as Dataset A `DS-broker_flow-idx80-nonpit-2025_2026v1` (D-034/D-035) | 872 tickers | Stockbit broker summary |
| Broker accumulation | `bandar_detector` (102.9k rows, re-measured 2026-09-09 [DB-VERIFIED]; was reported 36k) | Daily accdist (top1/3/5/10) | **2025-01-02 → 2026-09-08** — corrected from 2026-04-01 | broad | Derived from broker_flow |
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
| **Informed-flow / adverse-selection proxy** | `broker_flow` (foreign vs local vs govt), `bandar_detector` | **Corrected 2026-09-09:** calendar span is ~20 mo (2025-01-02 → 2026-09-08), not ~3.5 mo — the prior figure was stale. Density is **tiered/uneven** across the full active universe (see §3); regime-coverage adequacy for the *full universe* has not been reassessed in this pass. A fully-reconciled, IDX80-scoped, NON-PIT, 79-ticker subset (Dataset A, D-034/D-035) exists with zero genuinely missing cells over its declared window. |
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
3. **Short-history datasets (ticks, VPIN, fundamentals: 3 wk–3.5 mo) cannot yet support regime-stratified or walk-forward validation.** Any hypothesis depending on them must declare a *history-maturity gate*: validation deferred until ≥N months accumulate. This is a first-class scope rule, not a footnote.
   **`broker_flow`'s calendar span is corrected to ~20 mo as of 2026-09-09 (§3) — no longer ~3.5 mo.** This
   correction is a measured-fact fix only; it does **not** itself rule the history-maturity gate cleared for
   `broker_flow`, because density remains tiered/uneven across the full active universe (§3) and a *full-universe*
   regime-coverage reassessment has not been performed in this pass. Whether the gate is now cleared — in whole,
   or only for the fully-reconciled Dataset A IDX80 subset — is a Research-Architect/CRO determination, not
   resolved by this correction.

## 6. Open procurement questions (for the owner)
- Is a paid L1 quote/BBO feed within budget? (Unlocks true spread/quote microstructure — the single biggest capability jump short of institutional L3.)
- Retention policy for the 12.2M-row 1-min flow bars and 10.4M-row ticks as history grows — storage/compaction plan (feeds [[RESEARCH_DATABASE_CONCEPT]] outline).

---
*This study is a living document. Re-run the inventory query and re-classify whenever a provider or table changes. Any scope decision that contradicts §4 must cite an updated version of this file.*
