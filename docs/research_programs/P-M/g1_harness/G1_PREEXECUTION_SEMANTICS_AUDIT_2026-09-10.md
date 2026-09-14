# G1 PRE-EXECUTION DATA SEMANTICS AUDIT — 2026-09-10

**Task:** resolve/document the two remaining G1 mechanical-definition blockers — (1) `broker_flow.freq` semantics, (2) the registered net-flow (NF) control source — by determining whether the authoritative research corpus already resolves them.

**Mode:** READ-ONLY evidence gathering. No live G1, no real return calculation, no feature re-cut, no methodology change, no substitute variable, no commit. This report records what sources say; it does **not** decide anything (Part 4 rule).

**Corpora searched:** `/home/tjiesar/ZCodeProject/**` (incl. `pm_data_audit/`, `bfi001_broker_flow/`, `h1_foreign_flow/`, `h6_foreign_flow/`, `lit001/002`, `hliq_liquidity_shock/`) and `/home/tjiesar/10 Projects/idx-walkforward-5001/docs/research_programs/P-M/**` (incl. `dataset_b/artifacts/`, `experiments/`), plus production/store SQLite schemas (read-only). Search terms: freq, frequency, ticket, trade/transaction/order count, orders-vs-fills, net flow, NF, control, residualization, stockbit_flow, OFI, C1a/C1b/C2/C3, species, H0/H1/H2/H3, P0, PREREGISTRATION, FROZEN, SEMANTIC_REGISTER, BFI-001, BFI-002.

---

## 1. FREQ STATUS: **B — EXPLICITLY FORBIDDEN / UNKNOWN**

No authoritative source defines `broker_flow.freq`. The authoritative semantic register affirmatively forbids its use as a ticket denominator, and the program's dependency matrix records the item as UNRESOLVED with no resolution artifact in existence.

## 2. FREQ EVIDENCE

| Source | Path (sha256-16…) | Relevant content |
|---|---|---|
| **Dataset B semantic register** (authoritative for field semantics) | `docs/research_programs/P-M/dataset_b/artifacts/DATASET_B_SEMANTIC_REGISTER_v1.json` (`bed27a39cbd80016…`) | Entry `broker_flow.freq` — status **UNKNOWN**; meaning: **UNKNOWN**; research_use: "**FORBIDDEN** as a transaction count or ticket-size denominator until a vendor probe establishes its unit." Evidence recorded there: the fetcher maps ONE vendor field onto both buy and sell rows (`stockbit_fetcher.py:719,731`); against the independent `stockbit_flow` daily summary over 34,017 ticker-days, `SUM(freq)/(buy_freq+sell_freq)` has median **0.0080** (~100× shortfall, beyond what truncation explains); no variant reaches 2% agreement on any day. |
| Custody handoff, DEP-B matrix row 1 | `ZCodeProject/pm_data_audit/PM_CUSTODY_RECONCILIATION_HANDOFF_2026-09-10.md` | "Frequency semantics — **UNRESOLVED** — No resolution artifact anywhere in `docs/research_programs/P-M/` (grep: zero hits)… ZCode probe (`species_design.json`: freq row-level, 490/821 distinct) is descriptive, not ratified." Minimum-to-clear (§5.3): "a ratified freq-semantics note (orders vs fills; side-specific; lot=0 treatment) — **or an explicit owner decision** to lead with the freq-free candidates C3/C7." |
| BFI-001 frozen preregistration | `ZCodeProject/bfi001_broker_flow/00_PREREGISTRATION_FROZEN.md` (sha256 `91c0eb9a4a42630f…`, recorded in `11_prereg_hash_2026-09-03.txt`, frozen 2026-09-03 **before execution**) | §C lists `freq` merely as a carried field ("after close t; used only ≤ t") — **no definition given**. §E: none of the 14 registered cells consumes freq (signals use signed `value`, `lot`, and broker *counts* only). BFI-001 therefore neither defines nor ratifies freq semantics. |
| BFI-002 candidate design memo (**DESIGN ONLY — NOT REGISTERED**) | `ZCodeProject/pm_data_audit/PM_SPECIES_MECHANISM_BFI002_DESIGN_2026-09-10.md` (`9c87888f61bfdb51…`; exists ONLY in the ZCode corpus, not in the Dell tree) | §1 defines ticket = value/freq and the Rp 10M F-classifier **conditionally**: every freq usage is marked "[DEP-B: orders-vs-fills semantics still open]". §9: "C1a and C1b depend critically on freq… **If Dataset B resolves freq against us… C1a/C1b are declared untestable as specified and the design is withdrawn, not re-cut.** In that world the program falls back to C3 (freq-free, cap-robust) as the lead candidate and C2 as secondary." |
| Discovery memo (pre-design, descriptive) | `ZCodeProject/pm_data_audit/PM_ALPHA_DISCOVERY_ZCODE_2026-09-10.md` | Ticket = Σ\|value\|/Σfreq used descriptively; §robustness: "Robustness of the species split to freq semantics (**orders vs fills — unverified**)"; kill-condition: "vendor freq semantics change — flag for monitoring." |

**Finding:** every source that touches freq either forbids its use (register), records it unresolved (handoff), or uses it descriptively under an explicit unverified/DEP-B caveat (design memo, discovery docs). There is no conflicting pair of definitions to reconcile — there is **no definition at all**, and the register names the missing instrument explicitly: *a vendor probe establishing the unit*. (Note: raw vendor responses that contain `freq` are preserved in `pm_data_audit/stockbit_limit150_trial/raw/` and in the Dataset B store `raw_responses` — recorded here as the available evidence path for such a probe; no analysis was performed in this audit.)

## 3. NF STATUS: **C — CONFLICTING (across scopes/stages); NOT FOUND at G1 scope**

There is no ratified, G1-scoped NF-control definition. The corpus contains multiple authoritative-looking NF constructions that disagree on **data source** and were written at different program stages — including one registered construction that is now structurally dead at limit=150, and one amendment pointing to `stockbit_flow` that is explicitly marked "recorded, not registered". Per the task rules these are catalogued, not reconciled.

## 4. NF EVIDENCE

| # | Source | Path (sha256-16…) | Exact construction / wording | Scope & status |
|---|---|---|---|---|
| N1 | **HYP-PM-0003_REGISTERED.md** | `docs/research_programs/P-M/HYP-PM-0003_REGISTERED.md` (`4f35cfbdf9b42fa8…`, 2026-09-09) | `signed_lot_convention: net_flow(ticker,date) = SUM(lot) FROM broker_flow, treated as already-signed`; data section: broker_flow (Dataset A per D-043), "**NOT stockbit_flow_bars**". Units: signed lots. Availability: after close t (§C inherited prose). | **REGISTERED** hypothesis (BROKER flow-NF). Subsequently tested → FAILED F2 (null); and at limit=150 the construction is *identically zero* (exchange identity; 2026-09-10 limit=150 trial + family map §3). |
| N2 | **BFI-001 frozen preregistration** | `ZCodeProject/bfi001_broker_flow/00_PREREGISTRATION_FROZEN.md` (`91c0eb9a…`, hash-file frozen 2026-09-03) | §C: "vendor daily flow lots (buy_lot, sell_lot) \| `stockbit_flow` \| after close t; **OFI control only**". §I M2: "`OFI_vendor(t) = (buy_lot−sell_lot)/(buy_lot+sell_lot)` from `stockbit_flow`". Units: lot ratio ∈ [−1,+1]. | **FROZEN/REGISTERED, but scoped to BFI-001's model ladder** (M2 generic order-flow control), not to G1/C1a. |
| N3 | **BFI-002 design memo** (DESIGN ONLY) | `ZCodeProject/pm_data_audit/PM_SPECIES_MECHANISM_BFI002_DESIGN_2026-09-10.md` (`9c87888f…`) | §3: "Net-flow condition: `NF(i,t) = (buyV − sellV)/gross ∈ [−1,+1]`" computed **from broker_flow rows of (ticker, t)**; controls "inherited from BFI-001 §D conventions". | The **G1-scoped** construction — but DESIGN ONLY, and structurally ≡0 at limit=150 (predates the limit=150 capture). |
| N4 | **Family map §3** (discovery artifact) | `docs/research_programs/P-M/ZCODE_ALPHA_DISCOVERY_FAMILY_MAP_2026-09-10.md` (`e07dc07fe957c280…`) | "1. **No candidate may use broker_flow net as a signal or control** — it is mechanically ~0." "2. **BFI-002 design amendment (recorded, not registered):** the net-flow control in the C1a estimand must come from the vendor full-market aggregate (**stockbit_flow**), whose buy ≠ sell asymmetry … suggests **aggressor-side** data … **[DEP-B: vendor net/lot semantics validation]** **Until validated, C1a's control set falls back to gross/ADV and breadth (both non-degenerate).**" | Amendment toward stockbit_flow is explicitly **NOT registered** and carries its own unresolved DEP-B validation requirement. |
| N5 | **Dataset B semantic register** | `…/DATASET_B_SEMANTIC_REGISTER_v1.json` (`bed27a39…`) | Contains ratified entries for `broker_flow.value`/`lot` ("NET … SIGNED"), `bandar_detector.value/volume` ("NET CROSSED … NEVER a denominator"), **but no entry for `stockbit_flow` at all**. | The vendor full-market aggregate's net/lot semantics have **no ratified meaning**; DEP-B row 2: "Vendor net/lot semantics — UNRESOLVED (partially characterized)". |

**Direct answers to the Part 2 questions:**
1. *Was an NF control explicitly preregistered (for G1/C1a)?* **No.** The only preregistered NF-type constructions are N1 (HYP-PM-0003, broker_flow lots — dead at 150, hypothesis already failed) and N2 (BFI-001 M2 OFI — scoped to BFI-001).
2. *What data source is specified?* Conflicting across sources: broker_flow (N1, N3) vs stockbit_flow (N2 within BFI-001; N4 amendment, unregistered) vs stockbit_flow_bars (HYP-PM-0001, different instrument/horizon).
3. *What exact construction?* Three different formulas: SUM(signed lot) (N1); lot ratio (buy−sell)/(buy+sell) (N2); value ratio (buyV−sellV)/gross (N3).
4. *What units?* Signed lots (N1); lot-share ratio (N2); IDR-value-share ratio (N3). Not harmonized anywhere.
5. *What timing/availability rule?* Only prose exists: BFI-001 §C "after close t; used only ≤ t" — and DEP-B row 8 records the execution-timestamp convention as **NOT FOUND** ("asserted in prose only … no codified convention artifact").
6. *Is Stockbit flow explicitly authorized?* **For BFI-001's M2 control only** (N2, frozen). For G1/C1a: only in an explicitly unregistered amendment (N4), conditional on a validation that has not been done.
7. *Is any broker-flow-derived NF explicitly authorized?* It was (N1, N3-era) — but N1's hypothesis failed and the construction is identically zero at limit=150; N4 now forbids broker_flow net as signal or control (unregistered).
8. *Multiple conflicting definitions?* **Yes** — catalogued above without reconciliation.

## 5. H0-H3/P0 PROVENANCE: **NOT FOUND**

- No file named `BROKER_FLOW_PREREGISTRATION.md` (or sibling/numbered variant) exists in either corpus (find across `ZCodeProject/**` and `idx-walkforward-5001/docs/**`, case-insensitive, incl. archive/worktrees).
- No artifact numbered H0/H1/H2/H3/P0 for the broker-flow program exists. The only "P0" hits are unrelated table-column headers (S1-PM-0007 liquidity signflip tables) and the G1 harness's own gate references. Frozen preregistrations that DO exist belong to other programs: BFI-001 (`91c0eb9a…`), LIT-001/LIT-002, HLIQ, H6, NR7, and the retired S2-PM-0003 G-1 open-integrity census.
- Consequently the harness's CONFIRM-AT-PREREG parameters (ST tercile cuts, ADV20 binding, inference binding, NF-bucket definition, after-close availability codification) have **no authoritative anchor** in the accessible corpus. Nothing was reconstructed from implementation code.

## 6. CONFLICTS (catalogued, NOT reconciled)

1. **NF source:** registered broker_flow-NF (N1 HYP-PM-0003; N3 design memo §3) vs unregistered amendment to stockbit_flow (N4) vs frozen BFI-001-scoped stockbit_flow-OFI (N2). These disagree on source, construction, and units simultaneously.
2. **broker_flow net usability:** HYP-PM-0003 and the BFI-002 memo build on it; the family map forbids it outright ("No candidate may use broker_flow net as a signal or control"); the limit=150 trial proves it identically zero. All three statements stand in the record unreconciled.
3. **stockbit_flow authorization breadth:** BFI-001 §C authorizes it as "OFI control only" (BFI-001 scope); HYP-PM-0003's data section explicitly excludes stockbit_flow_bars; the family map proposes it as C1a's control source pending validation. No document authorizes it for G1's NF control.
4. **freq usage:** the discovery/design line uses value/freq tickets descriptively; the semantic register forbids freq as a ticket denominator. (Not a definitional conflict — the design line itself defers — but recorded as a tension in the record.)

## 7. G1 IMPACT (gates remaining closed as a consequence)

| Harness gate | State after this audit |
|---|---|
| `freq_semantics_ratified` | **STAYS CLOSED.** No definition exists to ratify; register forbids ticket-denominator use; the named instrument (vendor probe) has not been run. C1a/C1b remain BLOCKED_FREQ_SEMANTICS; freq-free C2/C3 unaffected. |
| `net_flow_source_ratified` | **STAYS CLOSED.** No G1-scoped NF definition exists; the corpus contains conflicting source/construction statements (N1-N5) requiring owner adjudication; the stockbit_flow candidate carries its own unresolved DEP-B (vendor net/lot semantics) and has no semantic-register entry. |
| `prereg_confirmed` | **STAYS CLOSED.** H0-H3/P0 artifact NOT FOUND in any accessible corpus. |
| `dataset_b_frozen` | **STAYS CLOSED** (unchanged: backfill in progress; freeze gates not yet taken — outside this audit's scope). |

## 8. RECOMMENDATION (evidence only)

- **FREQ: NOT FOUND** — no ratifiable definition exists anywhere in the corpus; the semantic register prescribes the missing instrument (a vendor probe establishing the unit) and the handoff prescribes the alternative path (explicit owner decision to lead freq-free with C3/C7). Choosing between those paths, or running the probe, is an owner decision — not made here.
- **NF: REQUIRES OWNER DECISION** — the evidence base is sufficient to *inform* a decision (four catalogued definitions with exact wording, one frozen precedent construction at N2, one explicit prohibition at N4, one dead registered construction at N1) but insufficient to self-execute: the G1-scoped source is unregistered, the stockbit_flow candidate's own DEP-B validation is open, and selecting a substitute merely because broker_flow is zero-net is prohibited by this task's rules.
- **H0-H3/P0: NOT FOUND** — the authoritative artifact is not in the accessible corpus; retrieval remains with its separate owner as stated in the task brief.

No harness changes were required: the existing `g1_config.json` gates and their `_notes` already encode precisely the state this audit documents; the PROVISIONAL loader wiring stays hard-gated off.

---

*Audit performed read-only. Files opened: those cited in §2/§4 above plus corpus-wide greps. Zero writes outside this report; zero commits; zero live queries against real G1 features.*
