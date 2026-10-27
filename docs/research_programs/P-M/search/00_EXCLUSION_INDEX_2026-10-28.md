# 00 · Exclusion Index — every mechanism already tried, on IDX, by this program (2026-10-28)

**Purpose:** the mandatory Step-0 input to the open-ended hypothesis search (`ZCODE_BRIEF_HYPOTHESIS_SEARCH_2026-10-28.md`).
One row per mechanism variant already TESTED, FAILED, WITHDRAWN, RETIRED, DORMANT, INVALID or OPEN. States use the
record's own word (HYPOTHESIS_LIFECYCLE §3: WITHDRAWN/RETIRED/DECAYED are **not** failures). Sources read in full or
in verdict-bearing part: `HYPOTHESIS_REGISTRY.md` (19 HYP rows + family ledger + notes), `FAILURE_REGISTRY.md` (15
rows + distribution + notes), `DECISION_LOG.md` D-001..D-112 (titles all; bodies of D-064, D-070, D-092, D-103),
`EXPERIMENT_LEDGER.jsonl` (23 rows), `OBJECTIVES_2026H2.md`, `RESEARCH_PROGRAM.md` headers, `P-A/`, all of `P-M/`
(file inventory + verdict files: pattern_scan, factor_zoo, alpha_search_v2, shock_absorption, exit_study,
broad_search v1/v2, insider_screen, universe_screen, retail_broker, forced_seller, sector_momentum, lockup_lc, pead,
fq, S1-PM-000x, LC-PM-000x, vol_exclusion, ml_rank, sniper_filter, dividend_clientele, tender_offer, stress_reversal,
forward_* protocols), `docs/reports/` (all), and the auto-memory index titles.
**Census context:** 613 disclosed trials → deflation bar ≈ **3.300069** (two-sided |Z|, D-064 §C / D-112 bar 3.300069).

## A. Price-pattern / OHLCV-shape (search CLOSED by D-070, 2026-10-07)

| # | Variant | Universe/era | State | Entry | Rules out / leaves open |
|---|---|---|---|---|---|
| A1 | NR7 range-contraction breakout (NR7_BULL) | liquid IDX, prod era | **RETIRED** from SHADOW (every stratum negative; demoted D-029, retired D-066[1]) | D-029/D-066 | all NR7 re-params |
| A2 | chart/swing patterns: double top, lower highs, staircase bottom, BOS/CHoCH, trendline breaks, falling wedge, Wedge Pop, Episodic Pivot | 2001–2026 + 2021→ | **NULL/anti-edge** (~12-arm scan + TOWR/BRPT/SMIL studies, every mean-reversion pattern significantly negative) | D-070; pattern_scan 2026-09-17; memory: double-top 14 arms NULL, lower-high fails 24-test bar, BOS/CHoCH/TLB 2021-26 negative | leaves OPEN only variants naming a NEW economic mechanism (D-070 exception) |
| A3 | liquidity sweep, failed breakdown/breakout, resistance breakout | liquid IDX | **anti-edge** (sweep −1.33% t−7.16 ex-2025; failed breakdown −1.94% t−7.15) — R1 anti-edge REGISTERED as HYP-PM-0012 (open forward) | pattern_scan; HYP-PM-0012 | breakdown-family re-tests closed; the ANTI-edge itself is the open record |
| A4 | ATR exhaustion flags (both directions) | 2026-09-25 study | **NULL** (continuation, not reversal) | exhaustion study | exhaustion re-params |
| A5 | sniper support-zone entry as signal; sniper meta-label filter | owner E-SN entry | **FAILED F2** (HYP-PM-0016, t +0.23 vs 3.2931); last admitted price-feature study (D-070) | D-072 | price-only meta-labelling closed |
| A6 | price-only ML cross-sectional rank (ridge/HistGBR, 14 features) | top-150 ADV60 monthly | **FAILED F2** (best t 1.71, PBO 0.51) | HYP-PM-0015, D-068 | OHLCV-feature learning closed; learning on OTHER data classes open (new mechanism required) |
| A7 | 52-week-high proximity + vol-excl (best clean-slate construction) | 780 tickers, 2022-26 | **NULL at bar** (t 1.44 net; 2.44 rel. ex-2025 vs 3.46 bar) | factor_zoo 2026-09-18 (92 trials) | hi52 as overlay control only |
| A8 | exit/position-management arms (swing lot, parity, overlays) | owner practice | **no arm recommended** (swing-lot edge phantom + look-ahead; G1bis stopped at parity gate) | exit_study 2026-10; D-070 | exit-rule research on the owner's entries closed |
| A9 | time-series momentum / trend state (EMA slope + ER + participation, 3ATR trail) | liquid IDX 2021→ | **OPEN** — HYP-PM-0010 REGISTERED, FWD-PM-REGIME-002 in forward test (36-mo decision) | D-028/{T1} | T1-family variants (other trend features) would need family-widening; 48-cell grid multiplicity already carried |
| A10 | market-stress reversal (−2.5σ day, bottom-quintile basket) | 63 episodes 2007→ | **FAILED F2** (−2.12% t−6.18; continuation, not reversal, in both eras) | HYP-PM-0019, D-079 | market-wide forced-selling REVERSAL closed; continuation direction = anti-edge class |
| A11 | bank 2-ATR climax low (big-4, liquidity provision) | big-4 banks | **OPEN** — HYP-PM-0014 REGISTERED, FWD-PM-BANK-001 forward (N≥15 events/36 mo) | D-066[2]/{R2} | other R2-style climax variants = re-params (closed) |
| A12 | shock→absorption→continuation (top-broker accumulation after shock) | liquid IDX | **DEAD (null)** + negative direction = FADE-class (needs new dated spec + multiplicity debt) | S1/shock_absorption 2026-09-21 | formalization dead; anti direction carries 1-trial debt |
| A13 | opening-minute bar vs open (bar09 data quality) | 59 tickers 309 sessions | data check only (48.7% within 1 tick) | broad_search_v2 A-leg | not a mechanism; flags intraday-bar staleness risk |

## B. Flow / orderbook / microstructure ({I5,I6,I7,I12} family, 6 members consumed + withdrawals)

| # | Variant | State | Entry | Rules out / leaves open |
|---|---|---|---|---|
| B1 | M1.1 inventory-imbalance mean reversion (per-bar OFI) | **INVALID·data** (cumulative-counter instrument; was F2) — counted | HYP-PM-0001, D-089 | re-test = new registration (T12); instrument semantics now guarded (TRADE_BOOK_SEMANTIC_REGISTER) |
| B2 | M2.1 adverse-selection permanence (broker_flow/Dataset A) | **FAILED F2** (then data caveats) — counted | HYP-PM-0003 | net-flow continuation k∈{3,7,15} on that instrument |
| B3 | flow decomposition (stockbit_flow_bars instrument, HYP-PM-0002 draft) | **DRAFT, never executed** (no slot) | registry notes | open in principle; instrument = cumulative counters (B1 semantics) |
| B4 | broker-flow imbalance baseline BFI-001 (BROKER-001) | **INVALID·data** (NV/GV identity-attenuated) — counted | HYP-PM-0007, D-063 | BFI_broad construct unmeasurable on this instrument |
| B5 | I7 intraday execution timing (back- vs front-loaded net buying) | **INVALID·data** (segment SUMs = cumulative) — counted; NO power claim (D-050) | HYP-PM-0009, D-089 | intraday-timing re-test with corrected instrument = new entry |
| B6 | C2 conduit disagreement (foreign vs local broker net flow) | **INVALID·governance** (species-mix control unimplementable); NOT CONFIRMED | HYP-PM-0004, D-048 | C2 as designed untestable; unconditional contrast null |
| B7 | C3 breadth surprise (±0.30 vs trailing median) | **NOT CONFIRMED** (valid bounded null, Holm p=1.0) | HYP-PM-0005, D-048 | breadth-surprise state closed at that spec |
| B8 | C7 intensity state (gross/ADV20 ≥ 2) | **NOT CONFIRMED** (t 0.51) | HYP-PM-0006, D-049 | intensity-threshold re-params |
| B9 | daily OIB continuation (final cumulative aggressor lots) | **FAILED F2** — wrong sign (−0.17%/day t−3.29); reversal is overnight, next-open flat | HYP-PM-0021, D-091 | daily aggressor-imbalance continuation closed; overnight leg untradeable (cost 3× gap) |
| B10 | closing-window LATE imbalance continuation (15:19→15:49) | **FAILED F2** — reverses (−0.54%/day t−9.95); close→open −0.53%, open→close flat | HYP-PM-0022, D-106 | late-tape continuation closed; **overnight gap mechanics noted as real but untradeable** |
| B11 | online-retail broker imbalance ({RF}, liquid + breadth panels) | **WITHDRAWN at G0** (power 3–7% vs 20% min); family closed, no members; backfill stopped | D-086/D-087/D-092 | retail-broker imbalance closed unless re-specified as new mechanism; note D-091 daily reversal |
| B12 | intra-broker crossing / manufactured volume ({MI}, NeoBDM clone) | **WITHDRAWN at G0** (stop rule); page retired to jurnal26 Brokers tab | D-093/D-094 | crossing-as-signal closed; brokermon stays observational |
| B13 | single-broker forced selling → temporary concession → reversal | **WITHDRAWN at G0** (stop rule) | D-096/D-097 | forced-seller reversal closed |
| B14 | sector/industry momentum ({S}) | **WITHDRAWN at G0** (power 8.3%); production sector block observe-only | D-101/D-102 | industry-momentum family closed at that spec; sector maps cover 82/959 tickers |
| B15 | I1 auto-rejection band pinning (ARB close-contact continuation) | in EXPERIMENT_LEDGER (RC-0001-MAX era) — **closed underpowered/not tested** | D-055/D-056 | band-pinning untested at power; ARB/ARA as DATA (bands, halts) still feeds monitors |
| B16 | FWD-PM-HALTARB-001 — names at ARB on IHSG trading-halt days | **OPEN record, recorded-not-read** (frozen; G0 needed before any read) | D-100 | prospective halt-arb record only |
| B17 | jurnal26 tape/bigplayer/limit forward records | **FROZEN, recorded-not-read** (60 sessions/100 events gate) | D-098/D-099/D-103/D-108 | prospective only |
| B18 | wf_edge legacy channel / premover EOD admission | channels OFF / standing (not hypotheses) | D-030/D-031 | — |

## C. Event studies

| # | Variant | State | Entry | Rules out / leaves open |
|---|---|---|---|---|
| C1 | index reconstitution closing-auction dislocation (ADD/DELETE) | **FAILED F2** (pooled null; ADD-side +1.89% gross not capturable — no shorting for DELETE) | HYP-PA-0001 | reconstitution DISLOCATION closed; the ADD-side gross drift noted untradeable pre-2025 |
| C2 | IDX80 reconstitution drift windows (14 windows) | **marginal** (adds +3.47% t2.76 pre-add; deletes −5.19/−9.78) — nothing clears Bonferroni | alpha_search_v2 #2 | reconstitution drift closed unless new design (e.g. deletion-only long-short needs shorting) |
| C3 | insider buys/sells (E1 accumulation ≥1%, E2 confluence, E3 director/commissary) | **FAIL (null)** — "last unscanned in-house dataset read"; median 20d excess −2% | SCREEN-PM-INS-001, D-061 | insider-event family closed at that spec |
| C4 | dividend clientele D1 pre-cum run-up / D2 ex-day tax capture | **FAILED F2** (D1 falsified; D2 below bar, decays to negative) | HYP-PM-0017, D-077 | dividend EVENT mechanics closed; **dividend-yield LEVEL is a separate open lead (see F5)** |
| C5 | tender-offer price floor | **REGISTERED-dormant** (stop rule at G0: 12 eligible < 20; no G1) | HYP-PM-0018, D-080 | re-opens only if tender flow grows; spread ledger filed |
| C6 | {CF} equity issuance (post-rights/listing supply) | **FAIL (null)** at screen | SCREEN-PM-CF-001, D-064 | issuance-supply lead closed |
| C7 | {LC} young listings (IPO-cohort short/avoid) | **PASS at screen** (−2.45%/mo t−3.66) but era-concentrated 2021-23 → **NOT opened**; later {LC} slot used by lock-up | D-064; universe_screen | young-listing UNDERPERFORMANCE is a real-but-era-carried anti-edge; a prospective recorder was offered, never taken |
| C8 | {LC} lock-up expiry supply overhang | **WITHDRAWN at G0** (power 0.49% vs 20%) | D-109/D-110 | lock-up event family closed (sourcing 2-3 days not spent) |
| C9 | PEAD (earnings surprise → drift, top-SUE quintile) | **WITHDRAWN at G0** (power 13.9% vs 20%; holdout 8.2%, recent 1.5%) — uncounted, never registered | G0 2026-10-26; Tuesday report §J2 | SUE-drift closed on power; monthly-formation earnings designs with more obs could be NEW (needs own G0) |
| C10 | MSCI shock day / HSC index-exclusion event (~80 names to leave IHSG; date TBD) | **descriptive only** (bank_stress note; macro_watch alerts) — no arm | bank_stress_2026-10-16; HSC memory | OPEN as an EVENT (market-design): a future one-shot study window exists when the exclusion date lands |
| C11 | outage cohorts (2026-10-09/12) | recorded as data gaps, excluded | D-095 | — |

## D. Cross-sectional factor zoo (fundamentals/price ratios, monthly)

| # | Variant | State | Entry | Rules out / leaves open |
|---|---|---|---|---|
| D1 | book-to-market, ROE (prior sweep) | **NULL** | factor_zoo / alpha_v2 §0 | B/M + ROE closed |
| D2 | composite equity issuance | **dead** (long leg weak; untradeable without shorting; degrades vol-excl) | alpha_search_v2 #1 | issuance FACTOR closed ({CF} event also closed) |
| D3 | cash-flow-to-price (OPCF coverage 8.6%; FCF/P weak/dead) | **dead** | alpha_search_v2 #3 | OCF/P blocked by fin.db coverage **then** — coverage now 998 tickers post-{FQ} pull; FCF/P re-spec would be a NEW arm |
| D4 | RNOA / operating profitability variants | **dead** (all null) | alpha_search_v2 #4 | operating-profitability rank closed |
| D5 | calendar months (June/Dec) | **non-inferential** (data mining) | alpha_search_v2 #5 | calendar cells closed unless mechanism-backed |
| D6 | **{FQ} E/P value risk premium (top-200 KSEI mcap, monthly)** | **OPEN** — D-112 registered mechanism, G0 freeze sha e14ab4d9, G0 runs 2026-10-27 17:41; G1/registration = owner go | D-111/D-112; fq/ | THE live fundamentals arm; family-widening memo = Wednesday K5 |
| D7 | low-vol / Parkinson-60 top-decile exclusion (VOLEX) | **OPEN unregistered prospective record** (FWD-PM-VOLEX-001; survives ±20 audit; decaying; overlay-only, no slot) | D-053/D-063 | vol-exclusion as overlay live; as STANDALONE family never registered |
| D8 | lottery avoidance (MAX) | in EXPERIMENT_LEDGER; **null-class** (killed by median test) | ledger + alpha_v2 | MAX closed |
| D9 | gross profitability (EM set) | tested in alpha_v2 EM set — **null/dead** (only dividend yield passed) | alpha_search_v2 | GP rank closed |
| D10 | retail ownership share/Δ (KSEI A1/A2, {OC}) | **FAILED F2** (determinate null vs MDE 1.68%/mo) | HYP-PM-0020, D-085 | KSEI retail-share LEVEL closed; other KSEI fields (foreign, institutional) NOT tested |
| D11 | momentum 12-1 (as baseline/control) | used as control (M0); standalone tested in zoo/EM set — **null at bar** | factor_zoo/alpha_v2 | 12-1 momentum closed; weekly/daily momentum variants tied to flow (B9/B10) closed |

## E. Learning / meta / process

| E1 | learned execution/parity (exit study G1bis) | stopped at parity gate, no verdict | exit_study | — |
| E2 | gatekeeper PBO/CSCV stage 9 | framework, live | D-065 | — |
| E3 | prospective protocol (broker_summary nets) | signal = 0 (adversarial review); TFB net −0.59%/trade | 2026-09-16 review | prospective-capture design dead at v1 |

## F. OPEN records (live book — correlation concerns for any new candidate)

| # | Record | State |
|---|---|---|
| F1 | HYP-PM-0010 / FWD-PM-REGIME-002 (T1 trend) | forward test open |
| F2 | HYP-PM-0012 / FWD-PM-FADE-001 (R1 failed-breakdown anti-edge) | forward test open |
| F3 | HYP-PM-0014 / FWD-PM-BANK-001 (R2 bank 2-ATR) | forward test open |
| F4 | FWD-PM-VOLEX-001 (volatility exclusion overlay) | open, unregistered |
| F5 | **Dividend-yield level** (top-20% TTM DPS/P, median t 4.11, works in all size terciles, net +7.07%/yr with vol-excl t 1.21) | **exploratory POSITIVE, never registered, carrying multiplicity debt** (alpha_search_v2; adjacent to but distinct from dead C4) |
| F6 | {FQ} E/P (D6 above) | G0 tonight; registration = owner |
| F7 | FWD-PM-HALTARB-001 + jurnal26 frozen records (B16/B17) | recorded, not read |
| F8 | HSC/IHSG exclusion event (C10) | future one-shot window |

## What the closed space means for new candidates (Step-1 input)

1. **Daily-OHLCV-shape signals are prohibited** (D-070) unless a new economic mechanism is named and accepted first.
2. **Flow continuation at daily/intraday horizons is comprehensively refuted on correctly-measured instruments** (B9/B10),
   and the reversal legs sit in the overnight gap where costs are 3× the move.
3. **Event studies die on power** (tenders, lock-ups, PEAD, reconstitution windows): single-name IDX event counts are
   small; designs must be pooled cross-sectional or panel-based (D-070 §5).
4. **Fundamentals ranks other than E/P and dividend yield are dead at today's bar**; the {FQ} panel (998 tickers, PIT v3)
   is the one materially NEW data asset; coverage historically blocked OCF/P (8.6%) — now worth re-counting.
5. **KSEI fields not yet used:** foreign share, institutional (non-individual) composition, per-investor-type flows —
   only the retail individual share (D10) was tested. Margin data exists (`~/idx_external/margin`, unread).
6. **Short-sale constraint kills every short leg** (C1 DELETE-side, D2 issuance, C7 long-mirror); candidates must be
   long-only or anti-edge (avoidance) designs.
7. **The 6.25–7% deposit-rate hurdle** (factor_zoo §1) sets the economic floor any long-only arm must clear net.
