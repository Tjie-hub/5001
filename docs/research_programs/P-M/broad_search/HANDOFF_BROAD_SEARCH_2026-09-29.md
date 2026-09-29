# HANDOFF — broad edge search (screens only) · 2026-09-29

**Executed under:** `ZCODE_BRIEF_BROAD_EDGE_SEARCH_2026-09-29.md`. Phase 0 (map + rights audit),
Phase 1 (2 pre-declared screens, 14 arms, one run each), Phase 2 (verdicts) — all committed in
this directory with every driver script next to its result (D-063 F-1 rule). Reads went through
snapshot `walkforward-20260928-213012.db` (sha256 `10f9c97f…46c13`, integrity ok); production DB
untouched; no registration, no family slot, no registry/DECISION_LOG/ledger edits.

**Headline: one screen PASSED its pre-declared rule — `{LC}` young-listing avoidance (−2.45 %/mo,
t −3.66 at the recomputed 2.857 bar, both halves, both benchmarks, null placebo, flat across vol
bands). The stop rule fired: nothing was refined. One screen FAILED (null) — `{CF}` issuance
avoidance. The rights-adjustment audit found the forward-test ledgers currently clean (0 ex-dates
inside any recorded window). Everything else in the six-family space is data-blocked, PIT-broken,
prior-less or correlated — see `FAMILY_MAP_v2.md`.**

## 1 · Decisions queued for the Owner (this search proposes; only the Owner disposes)

**D-a · `{LC}` — open the family and draft RC-0003, or shelve.** Proposed DECISION_LOG text:

> ### D-064 · Broad edge search (2026-09-29): SCREEN-PM-LC-001 ({LC} young-listing avoidance)
> PASSES its pre-declared rule; SCREEN-PM-CF-001 ({CF} issuance) FAILS (null); 14 arms join the
> census (N = 266, bar 2.8575)
> **Status:** RECORDED · **Date:** 2026-09-29 · **Type:** Screen verdicts + census update ·
> **Approval authority:** Owner ruling on `P-M/broad_search/HANDOFF_BROAD_SEARCH_2026-09-29.md`.
> 1. `FAMILY_MAP_v2.md` adopted as the v2 search map; `{TS}`/`{X}` recorded data-blocked, `{S}`
>    parked ({T1}-correlated), `{N}` a recorder proposal only.
> 2. SCREEN-PM-CF-001 = **FAIL (null)** (primary RI·h252·post2021 −0.635 %/mo, t −0.56; best grid
>    cell |t| 1.10; discovery half wrong sign). The `{CF}` issuance lead closes at screen level;
>    re-open = new screen id. Proposed FAILURE_REGISTRY note in §2 below.
> 3. SCREEN-PM-LC-001 = **PASS (screen level)** under the frozen rule (predeclaration
>    `e282f313…`, one run): primary −2.448 %/mo (t −3.66, 62 valid months, sign negative),
>    discovery half same sign (−1.256, t −1.29), vs-IHSG −2.435 (t −3.21), placebo t −0.41,
>    FILL-1/ID-1 pass, survivorship direction conservative. Stop rule honored: no variants, no
>    re-runs. One disclosed execution deviation: the two vol-conditioned descriptive cells ran on
>    the pooled window (flags not entry-split); they gate nothing and were not re-run.
> 4. Census: 252 → **266** disclosed trials; bar 2.8402 → **2.8575**. The screen survivor is not a
>    registered statistic and claims nothing beyond a recommendation.
> 5. Owner call requested: open family `{LC}` and authorize drafting **RC-0003** (young-listing
>    avoidance Rule Card, Tier-N: D-056 noise-floor power check first; the R9 haircut effect is
>    below the card-level MDE, so the card would need the IDX-cohort magnitude argument written
>    and its power statement honest), or shelve the lead. Any card remains subject to the D-062
>    standing directive assessment — recorded staff view: **not correlated** with FADE-001
>    (breakdown events), REGIME-002 (trend onset) or VOLEX-001 (the effect is flat across
>    realized-vol bands; conditioning cells exist to make that checkable).

**D-b · Rights-adjustment standing guard for the three recorders** (`RIGHTS_ADJUSTMENT_AUDIT.md`
§4): currently 0 recorded windows contain an issuance-type ex-date, so nothing is contaminated
today — but the corpus provably carries unadjusted mechanical drops (12 gap-verified corrections
applied in S2's run; 23 >35%-band jumps in phase 0), and FADE-001's daily h20 windows across the
liquid book will eventually span one. Proposed: recorders censor/flag any window spanning a
same-ticker `corporate_action_events` rightissue/bonus/stock_reverse ex-date. Frozen-protocol
amendment — Owner decision, zero urgency.

**D-c · Data acquisition items (from the map, priority order):** private placements (PMTHMETD —
the missing half of `{CF}`); suspension/UMA announcements with PIT dates (`{TS}` history is
detector-derived and 2022+-only); lock-up expiry calendar (`{LC}`'s supply-shock event); TLK ADR /
USD-IDR / coal-CPO series (`{X}`); rups agenda content (empty on 6,708/6,708); news_mentions
history extension with a forward attention recorder (`{N}` proposal: daily per-ticker count vs
own trailing median, accruing from now so a screen becomes possible ~2027-04).

## 2 · Proposed FAILURE_REGISTRY-style notes (nulls)

- **SCREEN-PM-CF-001 (`{CF}` issuance avoidance) — FAIL · null.** Primary RI·h252·post2021·corr
  −0.635 %/mo, t −0.56 (62 mo); all 8 grid cells |t| ≤ 1.10 both lenses; discovery half +1.11
  (t 1.01, wrong sign); vs-IHSG null; corrections verified (10 gap-verified wealth corrections;
  corrected ≈ raw within 0.03 %/mo ⇒ the null is not an adjustment artifact). Outside F1–F9;
  closes the announcement-stamp issuance lead.
- **Map-level closures (no arms spent):** A2 tender anchoring (median premium −1.3% — MTOs price
  at market; 28 pre-2021 events); A3 split/reverse drift (`stocksplit_created` batch-stamped
  pre-2022); A4 dividend events (`dividend_created` after ex-date on 27.7% of rows); A5 agenda
  (empty on all rows); warrants (no announcement field); `{TS}` resumption (no historical table);
  `{X}` (no in-house series).

## 3 · Execution record (reproducibility)

- Phase 0: `phase0_counts.py` → `phase0_counts.json` (commit `9131d56`). No outcome data read.
- Freeze: predeclarations + `bs_common.py` + both screen scripts committed **before** any run
  (`0029123`), with `PREDECLARATION_*.sha256` = `b26d7d0b…` (S1) / `e282f313…` (S2).
- Runs: one each (`RESULT_S1_20260929T043417Z.json`, `RESULT_S2_*.json`); run ids + dataset
  fingerprints in `research.db::research_runs` (kinds `broad_search_screen_s1_cf_issuance`,
  `broad_search_screen_s2_lc_listings`). Every number regenerates from the committed scripts.
- Pre-run amendment (disclosed in the S2 predeclaration): vol-conditioning switched from ret63
  (NaN at the flag row by construction) to listing-to-date realized vol — made before the run.
- Wealth corrections (brief rule 4): gap-verified per event, applied only to raw-drop prints,
  min 5% materiality; audits inside both RESULTs (S1: 10 applied; S2: 12 applied). FORU excluded
  from 2026-09-14 (8 panel rows) per D-063.

## 4 · What was NOT done (boundaries honored)

No forward test opened; no hypothesis registered; no family slot consumed; no registry,
DECISION_LOG, EXPERIMENT_LEDGER or protocol file touched; `run_formation.py` never executed; the
production walkforward.db never opened for research reads (snapshot only; `research.db` written
only by `research/tracking.py` as mandated by brief rule 9).
