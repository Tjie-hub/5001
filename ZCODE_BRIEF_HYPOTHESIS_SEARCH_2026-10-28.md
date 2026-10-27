# ZCODE BRIEF — Open-ended hypothesis search for IDX (propose-only, exhaust the space)

**Issued:** 2026-10-27, by Claude (planner role). Owner: "delegate task for zcode — search for new hypotheses for IDX,
don't overlap with existing ones, broaden the search until exhausted".
**Repos:** `~/10 Projects/idx-walkforward-5001` (`ops/hardening-2026-07-10`), data read-only from `~/idx_external`.
**Push: HOLD.** Commit locally. **Scheduling:** systemd one-shot timers only.
**Relationship to the Wednesday brief:** independent. Do K1–K4 of `ZCODE_BRIEF_WEDNESDAY_2026-10-28.md` first; this
brief takes the remaining time. K5 of that brief (fundamentals family widening) is one input here, not a duplicate.

## What this brief is, and is not
A **literature-and-data-feasibility search** that produces candidate hypotheses as text. It is **not** a backtest.
- **No return, P/L, Sharpe or t-stat of any candidate may be computed, read or glanced at.** Data-availability counts,
  coverage tables, event counts and prior-only power arithmetic are allowed. Looking at outcomes first would burn the
  candidate (data-snooping), and the census is already 613 (deflation bar ~3.3).
- Nothing is registered, no D-number is filed, no registry is edited, no freeze is written. The owner decides.
- Frozen things stay frozen: forward records, {FQ} G0 freeze, PEAD freeze, jurnal26 tape/bigplayer/limit watchers.

## Step 0 — build the exclusion index (mandatory, before proposing anything)
Write `docs/research_programs/P-M/search/00_EXCLUSION_INDEX_2026-10-28.md`: one row per mechanism already tried,
FAILED, WITHDRAWN, RETIRED, DORMANT, INVALID or open. Sources, read all of them, not only the registries:
`HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`, `docs/roadmap/DECISION_LOG.md` (≈4,000 lines; D-entries hold many
null studies that never got a HYP id), `EXPERIMENT_LEDGER.jsonl`, `OBJECTIVES_2026H2.md`, `P-A/`, `P-M/` (all
DISCOVERY_*, *_AUDIT_*, G0/G1 files), `docs/reports/`, and the auto-memory index titles
(`~/.claude/projects/-home-tjiesar-10-Projects-idx-walkforward-5001/memory/MEMORY.md`).
Columns: mechanism family, exact variant tested, universe/era, outcome (state per HYPOTHESIS_LIFECYCLE §3.1 — do not
file a WITHDRAWN as FAILED), entry id (HYP/D-/report), and what *adjacent* variants it rules out or leaves open.
Known closed or open to seed it (verify each, do not trust this list): price patterns (NR7, BOS/CHoCH, double top/
bottom, lower-high, ATR exhaustion, sniper support zone), flow/orderbook (flow edge study, OIB, closing tape,
crossing, broker flow, band pinning I1), event studies (insider buys/sells, dividends, tenders, market stress, PEAD),
index reconstitution (HYP-PA-0001), sector momentum, ML rank, volatility exclusion, retail/KSEI paths, bank 2-ATR
(forward test), accrual (I7), {FQ} E/P (open), {LC}/{CF} (null/artifact).

## Step 1 — enumerate the search space broadly
Write `01_SEARCH_SPACE_MAP_2026-10-28.md` organised along **independent axes**, so gaps are visible, not just ideas:
- **Economic channel:** risk premium, behavioural bias, institutional friction/forced flow, information asymmetry,
  liquidity provision, market-design rule, macro/FX/commodity transmission, corporate-action mechanics.
- **Signal source / data class:** price/volume, intraday tape, order book, broker summary, ownership (KSEI),
  fundamentals (fin.db), corporate actions, filings/news text, macro/FX/commodity series, cross-asset (USD/IDR,
  CPO, coal, nickel, SBN yield), regulatory calendar, index-provider rules (MSCI/FTSE/IDX), cross-listing/ADR/peers.
- **Horizon:** intraday, overnight, 1–5d, 1–3m, 6–12m.
- **Structure:** single-name, cross-sectional rank, pairs/spread, sector/industry, market-timing, volatility-regime.
- **IDX-specific frictions:** ARA/ARB limits and the 2026 ARB 7% window, tick size, lot size, T+2, foreign-ownership
  limits, short-sale restrictions, suspensions/UMA/FCA/watchlist boards, special notation, call auction.
For every cell: mark COVERED (cite the exclusion-index row), OPEN, or INFEASIBLE (name the missing data). **Keep
widening until each axis has had a documented pass and a new pass yields no new OPEN cell** — say so explicitly
("exhausted at pass N: …"), do not stop at a round number of ideas.

## Step 2 — turn OPEN cells into candidate hypotheses
Write one file per candidate: `P-M/search/cand/C-NNN_<slug>.md`, max ~1 page each:
1. **Mechanism** — who is forced/biased/constrained, why it should persist after costs. Prefer rule-based or
   structural mechanisms (barrier durability) over statistical patterns.
2. **Falsifiable prediction** — sign, horizon, universe, benchmark; what result would kill it.
3. **Data** — exact tables/files, coverage, point-in-time status, known look-ahead/survivorship risks.
4. **Event/obs count and prior-only power** at the repo's deflation bar (use the census 613 → ~3.3). State the
   minimum detectable effect. A candidate that cannot reach the bar at any plausible effect size is tagged
   **UNDERPOWERED** (as happened to tenders, PEAD) and not recommended.
5. **Non-overlap proof** — name the 2–3 nearest exclusion-index rows and say precisely how this differs (different
   signal, horizon or universe — not a re-parameterisation). A candidate that is a re-skin of a closed arm is dropped.
6. **Cost/capacity** — turnover, ADV requirement, ARA/ARB execution risk; the D-059 "friction" test in words.
7. **Distinctness from the live book** — correlation concern with {FQ} E/P and the bank forward test.

## Step 3 — rank and recommend
Write `02_RANKED_SHORTLIST_2026-10-28.md`: candidates scored on (a) barrier durability, (b) data readiness today,
(c) prior-only power, (d) distinctness, (e) cost survivability. Top 5 only get a draft pre-registration skeleton
(hypothesis, universe, eras, bar, stop rule, G0 power plan) in the same format as `HYP-PM-*_DRAFT.md`, marked
**DRAFT, propose-only**. Say which candidates need new data acquisition and what it would cost (Stockbit calls,
disk, scraping legality).

## Rules
- Stockbit: read `.stockbit_token` only, never log in, stop on 401/403/429. Nothing heavy 21:05–06:30.
- Web research is allowed for literature, regulations and corporate-action calendars; tag every source [P]/[S].
  Do not scrape anything behind a login or against site terms.
- Production DB: read-only via `data.db.connect()`. Research code never imports execution modules.
- Do not edit `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`, `DECISION_LOG.md`, `RESEARCH_MASTER_PLAN.md`.
- If an idea overlaps an existing one only partially, write the *difference* down; do not silently merge or drop.
- If you catch yourself needing an outcome to decide whether an idea is good, stop: that idea goes to the owner as
  a question, not into the shortlist.

## Deliverable
`docs/reports/ZCODE_HYPOTHESIS_SEARCH_2026-10-28.md`: counts (rows in the exclusion index, cells per axis, OPEN/
COVERED/INFEASIBLE), the exhaustion statement per axis, the ranked shortlist, files written, and commit hashes.
Commit the search files under `docs/research_programs/P-M/search/` in small commits
(`docs(research): hypothesis search -- <step>`); add a "Hypothesis search" line to the `TODO.md` status block.
