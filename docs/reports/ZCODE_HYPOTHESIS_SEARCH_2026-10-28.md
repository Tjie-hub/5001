# ZCODE — Open-ended hypothesis search 2026-10-28 (propose-only)

Brief: `ZCODE_BRIEF_HYPOTHESIS_SEARCH_2026-10-28.md` (issued 2026-10-27, executed same day after the Wednesday
brief's same-day items K2/K3/K4.1; K1 waits for tonight's 17:41 {FQ} G0 run). **No return, P/L, Sharpe or t-stat
of any candidate was computed, read or glanced at.** All numbers below are coverage counts, pre-existing
published results (cited), or prior-only power arithmetic. Nothing registered, no D-entry, no registry touched.

## Counts

- **Exclusion index:** 64 rows across 6 families (price-pattern 13, flow/microstructure 18, event studies 11,
  factor zoo 11, learning/process 3, open records 8) — `P-M/search/00_EXCLUSION_INDEX_2026-10-28.md`.
- **Search space:** 41 cells across 5 axes (channels 8, sources 13, horizons 5, structures 6, frictions 9):
  ~12 OPEN · ~10 PARTIAL · ~15 COVERED · ~6 INFEASIBLE (order-book history, commodity/SBN series, ADR/peers,
  news-text corpus, margin series, pairs/spread) — `01_SEARCH_SPACE_MAP_2026-10-28.md`.
- **Candidates:** 8 written (`cand/C-001…C-008`); 5 skeletons (`cand/SKEL-*.md`).

## Exhaustion statement (per axis)

Exhausted at **pass 3**. Pass 1 filled from the exclusion index; pass 2 added the KSEI non-individual fields,
cap proximity, sanction boards, rights mechanics, tick/T+2/notation, call auction, USDIDR, HSC event,
dividend-yield lead; pass 3 produced only re-parameterisations of closed cells or cells needing absent data —
no new OPEN cell. Per axis: channels (8/8 swept), sources (13/13), horizons (5/5), structures (6/6), frictions
(9/9).

## Ranked shortlist (details + scores in `02_RANKED_SHORTLIST_2026-10-28.md`)

1. **C-003 dividend-yield level** — the only candidate with real prior power (~80–95% at a 0.80%/mo floor on
   209 formations; in-repo prior mean t 2.46 / median t 4.11, alpha_search_v2, debt declared). Sequence after
   tonight's {FQ} E/P G0; the FM-over-E/P separator and the family question (widen {FQ} vs new Payout family)
   are the owner's.
2. **C-001 KSEI foreign share level/Δ** — panel 100% ready (verified today: 211 months, 1,055 names); power
   marginal (18% at the 0.5%/mo convention → registrable only with an owner-accepted floor ≥ 0.80%/mo).
3. **C-006 KSEI MF/PF share + Δ** — same build/G0 as C-001, two arms, {OC} A1/A2 precedent.
4. **C-002 foreign-cap-proximity exclusion overlay** — paired-overlay design clears the 20% G0 minimum at a
   0.30%/mo floor; cheapest cost class (VOLEX precedent); 43,285 name-months ≥45% verified.
5. **C-005 USDIDR × currency exposure (FM form)** — conditional on a classification acquisition (public
   filings, one evening of Stockbit calls inside the existing rules); parked unless the owner wants it.
   Not recommended this cycle.
- C-004 (sanction deadlines), C-007 (HSC one-shot), C-008 (auction/ARB records): **records/monitors, not
  registrations** — their files state the power/blocking reasons. {FQ} family-widening arms are K5's scope
  (Wednesday memo), cited here as input, not duplicated.

## Rules compliance

- No outcome read anywhere in this search (the "stop if you need an outcome" rule was never triggered; the one
  judgement call — C-005's exporter-classification quality — is written as an owner question, not a shortlist
  assumption).
- Registries, DECISION_LOG, RESEARCH_MASTER_PLAN untouched. Frozen records untouched. All web sources for the
  rebalance check tagged [S] (Kontan; idx.co.id still blocked — owner-browser item).
- Stockbit: no calls made. Production DB: read-only. Timers: none armed by this search.

## Files and commits (local; push HOLD)

- `66fae56` — step 0 exclusion index (+ the brief file itself)
- `c0ed3e2` — step 1 search space map
- `c1e0446` — step 2 candidates C-001…C-008
- `160f652` — step 3 ranked shortlist + 5 skeletons
- this commit — deliverable report + TODO.md line

## Same-day Wednesday-brief items also completed (details in the Tuesday report's successors)

- **K2 rebalance verification:** Kontan [S] (26 Oct) agrees exactly with both branch lists (IDX30 +ISAT +PTBA
  −PGEO −UNVR; LQ45 +SMGR −SCMA; IDX80 +AALI +TINS +TKIM −HEAL −MIKA −SMRA, SCMA stays in IDX80). No
  amendments; branches stay unmerged until 2026-11-02.
- **K3 scan rerun:** Mimosa (focused, normal depth) completed on both repos — 5001 `e14a7f8..76dd6b3`: **0
  findings in the 7 changed files** (seal `sha256:ad5f3d4f…`); jurnal26 `01b0bbb`: 1 finding at
  `tape_backfill.py:91` (SSRF rule on the constant Stockbit GET) blamed to pre-existing commit `bf50036`, not
  the change (seal `sha256:1f2e8d0d…`). `pytest tests/security/test_secret_hygiene.py`: 5 passed. The 269
  repo-wide static hits (deserialization/path-traversal/SQLi rules, mostly frozen research scripts) are
  pre-existing and outside the range — flagged for a separate owner pass, no claim made either way.
- **K4.1 classification:** all 51 unresolved KSEI codes are absent from `idx_tickers` entirely (never tracked;
  long-delisted KSEI-history names), zero transient failures in the 10-26 log (no 401/403/429), so **no retry**
  — fin.db unchanged (sha `caefb1a2…` still valid), no new sums file, tonight's G0 pin intact. K4.2/K4.3
  therefore have nothing to do; K1 (G0 close-out) remains the only Wednesday item, after 17:41.
