# ZCODE ALPHA DISCOVERY — FAMILY MAP (P-M)

**Date:** 2026-09-10 · **Status:** DISCOVERY ARTIFACT — descriptive only. Not a hypothesis registry entry; no forward-return tests run; no Dataset B changes; governance registries untouched.
**Cycles executed:** 3 (C1/species memo pass; structure passes A/B; cross-stock pass C + states pass D).
**Evidence:** `pm_data_audit/{discovery_structures,discovery_structures_B,species_design,species_design_B,family_passC_broker_stock,family_passD_states}.json`, BFI-001 frozen results (prior evidence only).

---

## 1. Mission check

Searched beyond the C1/species family across the required 16-family map (A–P). Every family received either a descriptive measurement pass, a structural rejection with evidence, or an explicit data-blocked marking. New instrument-level discovery: **broker_flow per-ticker net flow is structurally ~zero** (see §5) — a fact that reshapes several families and the BFI-002 control design.

## 2. Family map and classification (distinct-family test applied)

| Family | Status | Descriptive evidence (measured) | Strongest candidate | Classification |
|---|---|---|---|---|
| **A. Flow composition** | SEARCHED | Species axis: 60 desks (28 names/day, \|tilt\| 0.44, cross-name HHI 0.20) vs 35 aggregators (93 names/day, \|tilt\| 0.28, HHI 0.08); ticket profiles persistent (0.843); class≠species (Asing 65/35, Lokal 54/46, Pemerintah 11/**89** desk/agg by value) | **C1a** frozen-species conditional contrast (+C1b rank variant, C1c execution filter) | NEW FAMILY (leading) |
| **B. Participation/breadth** | SEARCHED | Breadth imbalance p10/p90 ±0.28/+0.39; autocorr 0.24/0.21/0.19 (lags 1–3); sign runs p50/p90/p99 = 1/4/9 days; surprise >0.3 on 23% of name-days; next-day volume 0.92 (extreme sell-breadth) vs 1.005 (extreme buy) | **C3** breadth-surprise (+ execution leg) | NEW FAMILY (independent: corr w/ species −0.147) |
| **C. Concentration/dominance** | SEARCHED | CONC event-like (within-var ≈ total; lag-1 0.15; own-p90 re-hit 10.5%); top-1 side share p50 53%; BFI-001 prior t=−2.65; **independent of species (R² 1.6%)** | **C6** CONC events (non-cap-cells) | NEW FAMILY (independent) |
| **D. Flow dynamics/sequence** | SEARCHED | Broker directional persistence 0.526 pooled (n=2.97M); **high-intensity persistence: P(next-day high intensity \| state) = 45.7%/48.1% vs 11.3% base**; breadth runs multi-day; gross autocorr 0.73/0.67/0.66 | **C5** desk program persistence; **C7** intensity-state (execution) | NEW FAMILY (execution-type) |
| **E. Broker specialization** | SEARCHED, WEAK | Broker×stock affinity top-1 share p50 0.001 (both species); rare exceptions (SC/BBNI 27%, SC/TLKM 18%, IP/ENRG 20%) | none | LOW PRIORITY (no generalizable structure) |
| **F. Cross-stock broker information** | SEARCHED, DEGENERATE | Aggregators active in 93/~850 names daily → cross-name "spreading" indistinguishable from universal breadth (p(other-name next day)=0.9999 vs breadth-implied base ~0.10 aggregated); broker market-tilt non-persistent (lag-1 0.09) | none beyond C5 | VARIANT of breadth/persistence |
| **G. Flow/price disagreement** | **BLOCKED in broker_flow** | broker_flow per-ticker net is structurally ~0 (P(\|nf\|≥0.2)=0.0000; p95 \|nf\|=0.001) — see §5 | vendor-net version **blocked pending [DEP-B: vendor net semantics]** | BLOCKED BY DATA (semantics) |
| **H. Flow/volume disagreement** | SEARCHED | gross/ADV20: p50 0.82, p90 3.12; intensity ≥2× on 18.1% of name-days; flat baselines across liquidity terciles | **C7** intensity-state (execution/liquidity alpha) | NEW FAMILY (execution-type; freq-free) |
| **I. Liquidity/execution structure** | SEARCHED | Structure baselines flat across liquidity terciles (CONC p50 −0.011/−0.018/−0.018); absorption prevalence 5.2% (gross ≥2×ADV & \|ret\|≤1%); absorption clusters: 23.4% next-day absorption after absorption day vs 4.3% base | **C8** absorption-state conditioning (descriptive; directional value unproven) | NEW FAMILY (contingent: needs forward-return leg later) |
| **J. Volatility/risk state** | SEARCHED | Low-vol regime: intensity 1.00 vs high-vol 0.65; \|breadth\| 0.20 vs 0.16; CONC flat (−0.011/−0.010/−0.017) | interaction cell only (intensity × vol) | VARIANT/interaction (low standalone value) |
| **K. Information shock/event states** | SEARCHED | Shocks (gross ≥3× trailing-60d median): 9.1% of name-days; next-day high-intensity 43.5%; next-day breadth same-sign 62.7% | feeds **C5** program detection | SUBSUMED (feeds D/A candidates) |
| **L. Absorption/resilience** | SEARCHED | Same measurement as I (absorption states, contemporaneous price response only) | **C8** | NEW FAMILY (contingent) |
| **M. Relative/peer structure** | SEARCHED | Within-stock normalization already embedded (CONC within-var ≈ total; surprise rates measured); liquidity-tercile baselines flat → peer-relative norms add little beyond own-history | — | VARIANT (normalizations inside C1a/C3 specs) |
| **N. Broker network/coordination** | SEARCHED, WEAK | Broker daily market-tilt synchronization: avg pairwise corr **−0.065** (66 pairs, top-12 brokers), p90 0.154; no stable per-stock dealer (dominant-broker identity churn 80%/day) | none | REJECTED (no measurable coordination at daily level) |
| **O. Multi-horizon/decay** | SEARCHED | Decay ladder: gross 0.73/0.67/0.66; breadth 0.24/0.21/0.19; CONC 0.15/0.12/0.11 (lags 1–3) | horizon-setting input to C1a/C3/C5 | SUBSUMED (design input) |
| **P. Negative/contrarian** | SEARCHED | Mapped onto measured states: CONC→fade (BFI prior); crowd-chase→fade (C1 mirror); extreme breadth→crowding; strong-flow-no-price-response→absorption (C8) | embedded in C1/C6/C8 | SUBSUMED |

## 3. Instrument-level discovery (changes prior designs)

**broker_flow net flow is structurally ~zero.** Per ticker-day, disclosed top-25 buy value ≈ sell value to ~0.1% (P(|nf|≥0.2) = 0.0000 across 103,389 ticker-days). Consistent with the exchange identity (every trade is simultaneously a buy and a sell; per-stock side totals equal) plus top-25 truncation: the day's directional imbalance is carried almost entirely by the undisclosed tail (also visible in net25/net_full ≈ 0.1–2% at median vs the vendor's full-market net). Consequences:

1. **No candidate may use broker_flow net as a signal or control** — it is mechanically ~0. HYP-PM-0003-style net-flow formulations are not only falsified but largely *unmeasurable* on this table.
2. **BFI-002 design amendment (recorded, not registered):** the net-flow control in the C1a estimand must come from the vendor full-market aggregate (stockbit_flow), whose buy ≠ sell asymmetry (e.g., BBCA 44.4M vs 63.9M shares on equal-ish value) suggests **aggressor-side** data rather than exchange-side identity — potentially the only true signed-net observable in the estate. **[DEP-B: vendor net/lot semantics validation]** Until validated, C1a's control set falls back to gross/ADV and breadth (both non-degenerate).
3. The species/concentration/breadth candidates are *unaffected* (they never used net): the degeneracy strengthens the case that composition/structure is the only live information in broker_flow.

## 4. Candidate scorecard (descriptive; no significance)

| Candidate | Family | Uniqueness | Credibility | Independence | Construct validity | Data avail. | Semantic robustness | Stability | Actionability | Falsifiability | Simplicity |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C1a species conditional | A | High | High | High (vs B/C/G) | High (0.843; freq row-level probe) | Yes | Medium (freq **[DEP-B]**) | High | High (dir + execution) | Max | High |
| C3 breadth surprise | B | Medium | Med-high | High | High | Yes | **Highest** (freq-free, cap-robust) | High (runs 4d) | Med-high | High | **Highest** |
| C6 CONC events | C | Medium | Medium (prior −2.65) | High (R²1.6% vs species) | Medium (cap cells **[DEP-B]**) | Yes | Medium | Medium (event) | Medium | High | High |
| C7 intensity state | H/D | Medium | High (persistence 48/46 vs 11) | Medium (needs vs C3 check) | High | Yes (gross+ADV only) | **High** (freq-free) | High | High (execution) | High | **Highest** |
| C8 absorption state | L/I | Medium | Medium | Medium (vs C7 overlap) | Medium (needs return leg) | Yes | Medium | Medium | Medium (execution) | Medium | Medium |
| C5 desk programs | D/A | Medium | Medium | Medium | Medium | Yes | Medium (freq) | Medium | Medium | High | Medium |
| C2 ownership disagreement | A(ownership) | Medium-high | Medium (weakened semantics) | Medium | Medium-high | Yes | High | High | Medium | High | Medium |

## 5. Cross-family independence summary

Measured pairwise structure correlations: species↔net 0.092; species↔CONC 0.125 (R² 1.6%); species↔breadth −0.147; CONC/breadth/species mutually < 0.15. Intensity (gross/ADV) vs breadth/species: not yet fully crossed — flagged as the one remaining orthogonality check (single correlation, no search) before BFI-002 freezing. Families A/B/C/H are mutually near-orthogonal; G is blocked; E/F/N measured weak/degenerate; J/K/M/O/P are conditioning or design inputs, not standalone families.

## 6. Blocked / unavailable dimensions (explicit)

- Intraday broker timing (not disclosed at broker level) — blocked.
- Flow/price disagreement on true net — blocked in broker_flow; vendor version **[DEP-B: net semantics]**.
- Sector/group-relative structure — `sectors_*` is a two-day snapshot; no sector membership history — blocked.
- Fundamentals/news/event conditioning — unadmitted datasets — blocked pending declaration.
- Options/short/borrow, order book, client identity — unavailable in market — blocked permanently.

## 7. SEARCH STATUS

- Families searched: **16/16**
- Families newly discovered this loop: **2** (H/D execution-intensity C7; L/I absorption C8 — both freq-free)
- Families rejected as variants/duplicates: **5** (F, J, K, M, O — evidence above)
- Families rejected as weak/no structure: **3** (E specialization, N network, P-as-standalone)
- Families blocked by data: **1** (G true-net disagreement; vendor version pending **[DEP-B]**)
- Strongest unexplored dimension: **none at ticker-day level with admitted data.** One pending check: intensity-vs-species/breadth orthogonality correlation (single measurement, no search), plus Claude's freq/net-semantics/CAP validations.
- Remaining search space: intraday, sector-relative, event-news, true-net — all blocked by data availability/admission (§6).
- **Is another discovery cycle required? NO — DISCOVERY SUFFICIENTLY EXHAUSTED** at the descriptive level permitted by current data. Next state changes require either Claude's Dataset B foundation (to run the frozen C1a/C3/C7 family) or new data admission (vendor net semantics; intraday; events).

---

## 8. ADDENDUM (2026-09-10, later) — TOWR breakout→pullback→continuation deep-dive

Triggered by the TOWR anchor case; full artifact: `ZCODE_TOWR_BREAKOUT_PULLBACK_DEEP_DIVE_2026-09-10.md`; evidence `pm_data_audit/towr_deepdive.json`. Descriptive only.

- TOWR is objectively breakout (Aug 18–26, intensity climax 10.1×ADV20) → pullback (Aug 27–Sep 3, −5.5%, intensity collapsing to 0.44) → base (Sep 4: 0.0% price on 37.6B, new desk-classified buyer HP 12.8B = 68% of buy side) → re-acceleration (Sep 8–9, +8.6%; Sep 8 broker data missing).
- **No new family.** The pattern decomposes into existing mechanisms: the discriminating analogue contrast (1,625 events; 677 CONT / 948 FAIL) is the **C7 intensity profile** (FAIL churns: breakout 4.20 / pullback 2.05 vs CONT 2.97 / 1.24) plus a **C8-type absorption base day** (TOWR Sep 4). The "same-agent persistence through retracement" hypothesis tested NEGATIVE (breakout buyers rotated; CC flipped to distribute; identity overlap/flip features show zero discrimination).
- Weak C1-flavored overlay at pullback (st: CONT +0.02 vs FAIL −0.01) — freq-dependent, indicative only.
- Family map status unchanged: exhaustion verdict stands; the TOWR pattern is classified as an existing-mechanism (C7/C8) state application, flagged INTERESTING BUT UNPROVEN, with one open descriptive item for Dataset B (event-level test of flat-price desk-concentrated base days).
