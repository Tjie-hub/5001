# 01 · Search Space Map — axes, cells, and what is COVERED / OPEN / INFEASIBLE (2026-10-28)

Input: `00_EXCLUSION_INDEX_2026-10-28.md` (row refs in [brackets]). Data inventory: walkforward.db (ohlcv 959
tickers 2021→ + pre-2021 backfill 2007→, stockbit_flow_bars 106M rows 2026-04→, broker_flow 3.6M rows 2025→ with
investor_type, insider_transactions, corporate_action_events, idx80_membership_history, ft_* tables), fin.db (998
tickers × {balance, cashflow, income}, PIT rule v3 frozen), KSEI monthly 2009-03→ (L_*/F_* by investor type + price
+ sec_num), fx (USDIDR month-end), jurnal26 (auction reports 10-16→, tape/bigplayer/broker summaries 10-08→),
idx_external/margin (one 2025-04 PDF only). **No** local series: CPO/coal/nickel prices, SBN yields, options,
order-book history (prospective tape only), MSCI/FTSE membership files, ADR/peer prices, news text corpus.

**Legend:** ✅ OPEN · 🟡 PARTIAL (open with named caveats) · 🔴 COVERED (closed — exclusion row) · ⛔ INFEASIBLE today (missing data named) · ⬜ not applicable.

## Axis 1 — Economic channel × (status, evidence)

| Channel | Status | Cell note |
|---|---|---|
| Risk premium (level: value, low-vol, quality) | 🟡 | E/P open [D6]; VOLEX overlay open [D7]; quality/profitability/B/M/ROE/CFP closed [D1,D3,D4]; dividend-yield level open lead [F5] |
| Behavioural bias (attention, anchoring, disposition, extrapolation) | 🔴/🟡 | price-shape patterns closed [A2-A8]; salience via MAX closed [D8]; anchoring at 52w-high closed at bar [A7]; disposition/extrapolation as pure-price signals prohibited (D-070) unless a new mechanism is named — e.g. **disposal via ownership data** open [KSEI axis] |
| Institutional friction / forced flow | 🔴/✅ | reconstitution dislocation+drift closed [C1,C2]; forced-seller reversal withdrawn [B13]; tender floor dormant [C5]; lock-up withdrawn [C8]; PEAD withdrawn on power [C9]; **NEW forced-flow events not yet enumerated: HSC index exclusion [C10/F8], rights-issue subscription deadlines, margin-call cascades (⛔ no margin series)** |
| Information asymmetry | 🔴 | M2 family comprehensively closed [B1-B10]; insider events closed [C3]; PEAD closed on power [C9] |
| Liquidity provision | 🟡 | bank 2-ATR open [A11]; market-stress reversal closed [A10]; **liquidity provision around INDEX-ADD buying or scheduled auction imbalances** — add-side untradeable pre-event [C1/C2] |
| Market-design rule | ✅ | **largest open axis**: ARB/ARA band mechanics (incl. 2026-10-19→12-31 7% window, D-107) only prospectively recorded [B16]; tick/lot size, T+2 settlement, call auction, suspension/UMA boards, special notation — none ever tested (needs mechanisms, not just rules); HSC exclusion pending [C10] |
| Macro / FX / commodity transmission | ✅/⛔ | USDIDR month-end series exists (unused ✅); CPO/coal/nickel/SBN ⛔ (no series — acquisition question); IHSG-level macro timing closed via C3/C7 nulls + A10 continuation |
| Corporate-action mechanics | 🔴/🟡 | dividends-as-event [C4], issuance [C6], young listings [C7], lock-up [C8], tender [C5] closed/dormant; splits/bonus/reverse mechanics live only as **adjustments** (D-064 §D); rights-offer arbitrage ⛔→🟡 (corp-action dates exist; offer-price/TERP terms not in DB — needs acquisition) |

## Axis 2 — Signal source / data class × (status)

| Source | Status | Cell note |
|---|---|---|
| Daily price/volume (OHLCV shape) | 🔴 | prohibited by D-070 except as controls/filters |
| Intraday tape (flow bars) | 🔴 | continuation dead [B9,B10]; overnight gap real but 3× cost [B10]; tape records frozen [B17] |
| Order book | ⛔ | no history; prospective jurnal26 reads only (band/depth in alert text) |
| Broker summary (top-25, investor_type) | 🔴/✅ | continuation/disagreement/intensity closed [B2,B6-B8]; retail-broker imbalance closed [B11]; crossing closed [B12]; **investor_type × broker concentration UNTESTED on non-continuation designs (e.g. foreign-broker share of a name)** 🟡 |
| Ownership (KSEI) | ✅ | **local-individual share closed [D10]; F_* foreign fields, MF mutual funds, CP companies, PF pension, per-type CHANGES — all untested 2009→**; KSEI price+sec_num also gives a survivorship-complete mcap series |
| Fundamentals (fin.db, PIT v3) | ✅ | the {FQ} machinery just built (998 tickers, 3 statements, USD fix, fiscal-year exceptions); E/P live [D6]; every other ratio is an open cell but family-widening rules apply (K5 memo) |
| Corporate actions (dates) | 🔴/🟡 | as events largely closed [C4-C8]; as MECHANICS (ex-date microstructure, rights timeline) untested |
| Filings / news text | ⛔ | no corpus; late-filer list just built (12_FQ CSV) — **sanction/watchlist (UMA/PK) boards are recorded in prod flags but never tested as a mechanism** 🟡 |
| Macro/FX/commodity | ✅/⛔ | USDIDR ✅ (monthly, unused); commodities/SBN ⛔ |
| Regulatory calendar | ✅ | {FQ} late-filer/sanction deadlines (D-111) — the PIT rule v3 machinery makes deadline-crossing designs testable; never used beyond E/P |
| Index-provider rules (IDX/MSCI/FTSE) | 🔴/✅ | IDX reconstitution closed [C1,C2]; **MSCI HSC-driven IHSG exclusion [C10] open one-shot**; quarterly IDX review calendar (announcements ~2wk before effect) as PREDICTABLE flow: drift closed, but pre-announcement positioning designs untested 🟡 |
| Cross-listing / ADR / peers | ⛔ | no ADR/peer price series |

## Axis 3 — Horizon × (status)

| Horizon | Status | Note |
|---|---|---|
| Intraday | 🔴 | B-family closed; prospective records only |
| Overnight | 🔴 | the one real gap factor found (B9/B10) costs 3× its size |
| 1–5d | 🔴 | every continuation/reversal at daily horizon refuted (A10, B9-B13, C3) |
| 1–3m | 🟡 | T1 forward open [A9]; event designs die on power here [C5,C8,C9]; pooled cross-sectional feasible (D-070 §5) |
| 6–12m | ✅ | value/yield/quality horizon — E/P live, dividend yield open [F5], KSEI foreign open; pre-2021 backfill + KSEI 2009→ give the depth |

## Axis 4 — Structure × (status)

| Structure | Status | Note |
|---|---|---|
| Single-name event | 🔴 | power-killer (tenders 12, lock-ups 226 but 0.49% power, PEAD 506/13.9%) |
| Cross-sectional rank (monthly panel) | ✅ | the surviving design class ({FQ} machinery, D-070 §5 preference) |
| Pairs/spread | ⛔/🔴 | needs shorting or ADR/peer data |
| Sector/industry | 🔴 | {S} withdrawn at G0 [B14]; sector map covers 82/959 |
| Market-timing (IHSG level) | 🔴 | C3/C7 nulls; A10 says stress CONTINUES |
| Volatility-regime | 🟡 | VOLEX overlay open [D7]; as standalone family never registered |

## Axis 5 — IDX frictions × (status: has any mechanism used this rule as SIGNAL?)

| Friction | Status | Note |
|---|---|---|
| ARA/ARB bands (+2026 7% window) | 🟡 | I1 band-pinning closed underpowered [B15]; halt-arb recorded [B16]; **the 7% window itself (2026-10-19→12-31) as a regime on band-hit behaviour** — untested, prospective only |
| Tick size | ✅ | untested (tick-rounded bands exist in bands.py); design would need intraday history ⛔ for backtest, prospective after |
| Lot size (100) | ⬜ | no mechanism identified |
| T+2 settlement | 🟡 | untested; pairs with corporate-action ex-date mechanics |
| Foreign-ownership limits (max 49% etc.) | ✅ | **untested; KSEI F_* gives the binding measure 2009→** — names near the cap as a constrained-flow mechanism |
| Short-sale restrictions | 🔴 | kills short legs (a structural fact, used as design constraint [C1,D2]) |
| Suspensions / UMA / watchlist boards | ✅ | recorded in flags; never a mechanism; suspension-contaminated bars documented (HYP-PM-0010 supersession) |
| Special notation | ✅ | untested |
| Call auction (IEP/match) | 🟡 | jurnal26 auction reports exist since 10-16 (frozen, recorded-not-read) — prospective G0 possible after the 60-session gate [B17] |

## Exhaustion statement (per the brief's requirement)

- **Pass 1** filled every cell from the exclusion index + data inventory.
- **Pass 2** re-swept each axis for missed cells and added: KSEI non-individual fields (foreign, MF, CP, PF),
  foreign-ownership-limit proximity, sanction/UMA board mechanism, rights-offer mechanics, tick-size, T+2,
  special notation, call-auction record, USDIDR transmission, HSC exclusion one-shot, dividend-yield level lead.
- **Pass 3** re-swept asking "what would a new pass yield?": remaining candidates were re-parameterisations of
  closed cells (e.g. OIB variants, pattern variants, insider variants, reconstitution windows) or needed absent
  data (order book history, commodity/SBN series, ADR/peers, news text, margin series). No new OPEN cell emerged.
- **Exhausted at pass 3.** The OPEN set is: KSEI foreign/institutional fields (level & change), foreign-ownership
  cap proximity, dividend-yield level (lead w/ debt), {FQ} family widening (K5 input), sanction/board deadline
  mechanisms, HSC-exclusion one-shot, USDIDR transmission, call-auction prospective record, ARB-7% regime window,
  and liquidity-provision-around-scheduled-flow designs that do not require shorting.
