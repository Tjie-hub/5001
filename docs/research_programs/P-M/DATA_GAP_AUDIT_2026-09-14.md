# P-M DATA GAP AUDIT — 2026-09-14

**Task type:** infrastructure / data engineering. **Empirical hypothesis tests
run: ZERO · predictive/backtest runs: ZERO · registry changes: ZERO · terminal
verdict changes: ZERO · Dataset B frozen-store modifications: ZERO · production
DB writes: ZERO.**

**Companion artifacts:**
`data_inventory_v1.json` (machine-readable field-level inventory) ·
`research_data/` (isolated research-view store v1 + builder + validator) ·
`flow_capture_prospective/` (prospective raw-response capture service, built,
not activated).

---

## 1. Executive answer

**"Are we currently limited by lack of data, or mainly by throwing away
structure that the existing data already contains?"**

**Mainly by throwing away structure — with one material historical data gap
that is now precisely quantified and largely recoverable.** The frozen data
already contains broker identity, concentration, pair/co-activity structure,
persistence, and 77.6M rows of 1-minute intraday flow — none of which survives
the daily aggregation used by the registered cells. None of this was
researchable before this audit because no broker-level or intraday view layer
existed. Conversely, the genuinely missing data is now bounded exactly:
4,311 true-gap 1-minute ticker-days on 7 post-freeze dates, 6 full
capture-outage sessions (~5,274 missing daily summaries), and one 30-session
stretch (2025-08-05..2025-09-17) whose "confirmed empty" classification is
untrustworthy — all in the minute-bar layer, not in the frozen broker-flow
store, which remains exactly as frozen (30,880/30,880 cells terminal, sha
`21661f03…`).

---

## 2. COMPLETE DATA GAP MATRIX

Grain of truth per dimension; classes per `data_inventory_v1.json`
(A = PIT-complete historical, B = available-but-incomplete, C = prospective
only, D = unavailable).

| # | Dimension | What exists (source, window) | Class | Gap | Verdict |
|---|---|---|---|---|---|
| 1a | Broker identity | Dataset B `broker_flow_b`: 95 brokers × 101 tickers × 386 sessions, frozen `21661f03…` | **A** | broker_code stability across window unaudited (vendor pseudonyms) | **CAN FIX NOW** (identity-persistence audit) |
| 1b | Broker participation | `bandar_detector_b` uncensored buyer/seller counts (30,877) + derived per-broker activity | **A** | none for IDX100/window | CLOSED |
| 1c | Broker concentration | derivable top1/3/5, HHI from frozen rows; vendor accdist cross-check | **A** | was never materialized → built (`v_b_concentration`) | CLOSED (was a view gap, not a data gap) |
| 1d | Broker pairs | daily buy-side × sell-side broker vectors | **B at daily grain** | daily data cannot identify actual counterparty matching — potential pairs only (17.27M in `v_c_pair_structure`) | PARTIAL: CANNOT FIX historically; intraday co-movement is the only path |
| 1e | Broker persistence | frozen rows + session calendar | **A** | never materialized → built (`v_d_*`) | CLOSED (view gap) |
| 1f | Accumulation/distribution | per-broker signed daily nets, streaks derivable | **A** | never materialized → `v_a_broker_day` | CLOSED (view gap) |
| 2a | 1-minute flow (history) | frozen v002: 77,559,605 bars, 900 tickers, 2025-01-02..2026-04-27, 99.70% complete incl. confirmed empties | **B** | suspect-empty stretch 2025-08-05..2025-09-17 (30 sessions, ~24,810 non-IDX80 ticker-days untrusted) + fixture 2025-04-14 | PARTIALLY SOLVABLE (clean refetch attempt; vendor-retention risk) |
| 2b | 1-minute flow (post-freeze) | production table to 2026-09-11 | **B** | 4,311 true-gap ticker-days (7 dates) + 6 full-outage sessions (~5,274 missing daily summaries) | **CAN FIX NOW** via existing `tools/backfill_flow_bars.py` (owner-run) |
| 2c | PIT integrity of intraday | raw responses were discarded by the production pipeline (parsed rows only) | **C** | vendor history is not stable across fetch cohorts (proven: 2026-09 cohort vs 2026-08 cohort disagree) | **CAN FIX PROSPECTIVELY** → `flow_capture_prospective/` built |
| 3a | Flow × price alignment (daily) | broker VWAP, daily OHLCV, broker gross | **A** | never joined → `v_f_flow_price` | CLOSED (view gap) |
| 3b | Flow × price (intraday) | v002 bars carry minute price + signed lots | **B** | co-registration only within frozen window | same verdict as 2a/2b |
| 3c | Impact vs ADV | traded value + ADV20 conventions exist | **A** | derivable; nothing computed | CLOSED (data sufficient) |
| 4 | Event conditioning | suspensions, corporate actions (+applied-basis), bandar, regime-aware IDX band contacts | **A** | never joined → `v_g_event_flow` | CLOSED (view gap). Breakouts/retests/sweeps: derivable from A/B data on request — **no event objects created (per prohibition)** |
| 5 | Attribution semantics | `investor_type` ∈ {Asing, Lokal, Pemerintah} = brokerage ownership | **A** (as ownership) | end-investor identity | **CANNOT FIX** — D; ownership must never be labeled investor identity |
| 6 | Historical coverage classes | per-field in `data_inventory_v1.json` | — | broker feed IDX80-only before 2026-04 (production); full-market pre-2026-04 broker data exists only for IDX100 via Dataset B | documented |
| 7 | Outcome data | ohlcv 2021-07-05..2026-09-14 (is_final), strict-contiguity forward returns, band contacts | **A** | none for the registered machinery | CLOSED (untouched) |

## 3. SOLVABLE NOW

1. **Post-freeze minute-bar gaps** — 4,311 true-gap ticker-days
   (2026-05-29: 706 · 06-04: 704 · 07-13: 707 · 07-22: 1 · 07-23: 709 ·
   07-27: 707 · 09-08: 777; "true gap" = nonzero daily flow, zero bars).
   Existing production tooling (`tools/backfill_flow_bars.py`,
   `tools/flow_bars_gap.py`) already implements the gap predicate and
   vendor retention is proven back to 2025-01. Exact command sequence
   handed to owner below. **Not executed in this task** (vendor-facing
   production write; see §7).
2. **Capture-outage sessions** 2026-05-18..21, 06-17..19 (real sessions,
   ~959 final OHLCV bars each, zero stockbit rows beyond IDX80 leftovers):
   same tooling covers both daily summaries and bars.
3. **Broker identity persistence audit** — compare broker_code activity
   fingerprints across the window in `v_a_broker_day` to detect renames/
   merges (pure data work, no hypothesis).

## 4. SOLVABLE PROSPECTIVELY

1. **PIT-safe raw capture** — `flow_capture_prospective/prospective_capture.py`
   is built and self-tested (immutable content-addressed raw responses,
   per-attempt manifest, checkpoint/resume, completeness markers,
   deterministic reconstruction, WIB session calendar, audit manifests).
   NOT scheduled; activation is an owner action (DESIGN.md §7). This closes
   the class of loss that produced the suspect-empty stretch: what the vendor
   returns for a past date decays — only capture-time raw bytes are durable.
2. **Intraday event objects** (sweeps, minute-level absorption): supported by
   v002 + prospective capture; deliberately not built as event definitions.

## 5. PARTIALLY SOLVABLE

1. **The 2025-08-05..2025-09-17 stretch (30 sessions).** The v002 completeness
   figure (99.70%) counts ~24,810 non-IDX80 ticker-days there as
   "confirmed empty" — but those rows were written by the 2026-09 fetch cohort
   with 5–26% nonzero rates, versus an 86% healthy baseline elsewhere
   (control: 2025-02-10, fetched 2026-08: 835/958 nonzero), while IHSG volume
   was flat across the stretch. A clean refetch with probe validation may
   recover some of it; vendor retention may equally have aged it out.
   Status: attempt-able, outcome uncertain, frozen store untouched.
2. **Broker pair identification** — daily grain can never identify actual
   counterparties (the feed reports each broker netted to one side;
   measured: 0 broker-days with both sides in the frozen store). Intraday
   co-movement from v002/prospective capture is an approximation, not matching.

## 6. FUNDAMENTALLY UNAVAILABLE (D) — documented, not fabricated

1. End-investor identity (retail/institutional per order) — no source exists.
   `stockbit_flow` is platform-aggregate market flow (a control, per D-049),
   not attribution. Broker `investor_type` is brokerage ownership.
2. `freq` semantics — values exist (no NULLs, 1..202,764) but the vendor does
   not document the unit; forbidden as a transaction-count denominator
   (standing exception; C1a/C1b withdrawn over exactly this). Passthrough only.
3. Actual trade-matching counterparty per executed trade (historical).
4. Broker-level history before 2025-01-02 (program window starts there;
   nothing older exists in any store).
5. `bar_time` sub-minute granularity / seconds / exchange timestamps — vendor
   serves HH:MM only.

## 7. DATA FIXES IMPLEMENTED (this task)

| Fix | Location | Validation |
|---|---|---|
| Research view layer v1 (views A–G): broker × ticker × date (`v_a_side` 1,518,727 rows; `v_a_broker_day` 1,518,727), concentration (`v_b_concentration` 30,877), pair structure (`v_c_pair_structure` 17,266,207), persistence (`v_d_broker_persistence` 1,518,727; `v_d_broker_activity` 34,738), intraday coverage (`v_e_intraday_summary` 296,022), minute-sequence accessor, flow×price (`v_f_flow_price` 30,720), event joins (`v_g_event_flow` 30,880) | `research_data/views_v1.sqlite` (328.5 MB, new isolated store) | 24/24 checks (§9) |
| Prospective raw-response capture service (immutable, checkpointed, manifest-audited, deterministic reconstruction; self-test green) | `flow_capture_prospective/` | built-in selftest: run accounting, checkpoint SKIPs, immutability refusal, EMPTY classification, rebuild determinism |
| Machine-readable field-level inventory with A/B/C/D classes | `data_inventory_v1.json` | JSON parses; 13 stores inventoried |
| Gap quantification methodology (true-gap vs confirmed-empty vs outage) | this document + inventory | reproduced from raw tables (queries in audit trail) |

## 8. DATA FIXES NOT IMPLEMENTED + WHY

| Fix | Why not |
|---|---|
| Backfill of the 7 true-gap dates + 6 outage sessions | Requires vendor API campaign and writes to the production `stockbit_flow_bars`/`stockbit_flow` tables while the live service runs. This task's mandate isolates research data; production writes and vendor campaigns are owner actions. Exact recipe: `python3 tools/flow_bars_gap.py --report` → `python3 tools/backfill_flow_bars.py --start 2026-05-18 --end 2026-05-21` (repeat per gap window) under the supervised runner, then re-run the coverage checker. Zero rows written by this task. |
| Refetch attempt for the suspect 2025-08/09 stretch | Outcome uncertain (vendor retention); would write production rows of ambiguous truth onto already-stored "empty" classifications. Needs an owner decision on whether to overwrite/branch those cells (a v003 freeze question), plus probe validation. Quantified and preserved instead. |
| Activating the prospective capture scheduler | Owner action by design (credentials, vendor cadence). Service built + self-tested, deliberately unscheduled. |
| IDX100 extension of frozen minute coverage beyond 2026-04-27 | A new freeze version (v003) is the correct mechanism per the v002 immutability policy ("wider window ⇒ new version"); not a patch. |

## 9. VALIDATION RESULTS (Phase 6)

`validate_research_views.py` — **25/25 PASS** (incl. `--rebuild` determinism):

- Source identity: Dataset B sha == freeze pin `21661f03…`; v002 sha == MANIFEST
  pin `fa7f07b3…`; views meta-records match recomputed pins.
- Row-count reconciliation: v_a_side == broker_flow_b (1,518,727);
  v_a_broker_day == distinct broker-days; v_b_concentration == 30,877 bandar
  cells; v_e_intraday_summary == 296,022 expected v002 ticker-days; BARS state
  == 239,695 distinct v002 bar cells; v_g_event_flow == 30,880 roster grid.
- Accounting reconciliation: Σvalue_pos = +Rp 1,585,427,502,195,600, Σvalue_neg
  = −Rp 1,585,427,502,195,600 → **all-broker net over the frozen store is
  integer-exactly 0** (exchange accounting identity; D-049 gate re-confirmed
  empirically). Σ|value| gross = Rp 3,170,855,004,391,200 reconciles.
- Duplicates: none (explicit GROUP BY checks on both keyed views).
- PIT: prev_session strictly < session in persistence view; 100% of view dates
  are admitted calendar sessions; no view carries any forward-dated column
  (structural: builder touches only ≤ t data).
- Membership: all view tickers ⊆ PIT universe (101).
- Domains: coverage_state / band_contact vocabularies clean; zero MIXED
  investor_type broker-days (vendor never reports one broker both sides of the
  same ticker-day).
- Isolation: every connection `mode=ro` + `query_only`; no WAL/SHM residue;
  the suite and builder write only `views_v1.sqlite` / temp dirs.
  During the work window walkforward.db grew ~11.4 MB (mtime 11:35:00 WIB) —
  attributed to the production scheduler's documented 11:30 flow-fetch slot
  (`idx-walkforward.service` active; transient writer, no holder remaining);
  every connection opened by this task was structurally incapable of writing
  (mode=ro + query_only). research.db: same size, mtime touched externally.
  Dataset B and v002 frozen stores: byte-identical all day (shas re-verified
  at close: `21661f03…`, `fa7f07b3…`).
- Determinism: full second build into a temp path produced a **byte-identical
  store** (sha256 `9737a58a559c844e…` both builds).

Capture service selftest: PASS (counts {SUCCESS 2, EMPTY 1, FAILED 1} →
rerun {SKIP 3, FAILED 1}; manifest accounting 13 rows; rebuild determinism;
immutability refusal).

## 10. EXACT COVERAGE / PIT NUMBERS (consolidated)

| Quantity | Number |
|---|---|
| Dataset B cells (frozen) | 30,880 = 30,877 SUCCESS + 3 EMPTY (TICKER_LEVEL_ZERO_VOLUME_SESSION), 0 failed/truncated |
| Frozen broker rows / brokers / investor split | 1,518,727 · 95 brokers · Lokal 886,679 / Asing 511,520 / Pemerintah 120,528 |
| Frozen all-broker Σvalue | +1,585,427,502,195,600 / −1,585,427,502,195,600 (**net ≡ 0**) |
| v002 minute bars | 77,559,605 rows · 900 tickers · 09:00–16:14 WIB · window 2025-01-02..2026-04-27 |
| v002 completeness | 239,695 bar cells (80.97%) + 55,448 confirmed-empty = 99.7031% complete; 879-cell fixture 2025-04-14 |
| Suspect-empty stretch | 30 sessions (2025-08-05..2025-09-17), 879 non-IDX80 rows/session refetched 2026-09 at 5.2–26.3% nonzero |
| Production bars (post-freeze era) | 98,454,570 rows to 2026-09-11; median 277,045 bars/session |
| True-gap ticker-days (post-freeze) | 4,311 across 7 dates (list §3) |
| Outage sessions (no stockbit rows at all) | 6 dates × ~879 tickers ≈ 5,274 summary-days |
| Production broker_flow scope boundary | 96–99 tickers (IDX80) 2025-01..2026-03 → ~830–870 from 2026-04 |
| ticks tape | 20.2M rows, 2026-04-18..2026-09-14 (prospective only) |
| OHLCV | 1,084,738 rows, 2021-07-05..2026-09-14, is_final machinery |

## 11. REMAINING DATA RISKS

1. **Vendor-history mutability** (the core lesson): past dates refetched later
   can return different data. Mitigation: prospective raw capture (built, not
   activated); never trust a refetch without the probe cross-checks used here
   (daily-summary nonzero rate, IHSG volume, cross-feed agreement).
2. **Suspect 2025-08/09 stretch** may silently contaminate any future intraday
   study that pools the full v002 window — exclude or re-validate those 30
   sessions first (flagged per-cell in `v_e_intraday_summary` via
   `coverage_state` + the audit note).
3. **broker_code stability** unverified across the window (renames/merges would
   distort persistence/pair analyses) — audit recommended before broker-level
   hypothesis work.
4. **IDX80-era production broker feed** (pre-2026-04) must never be pooled with
   the full-market era without scope conditioning (hard boundary documented).
5. **freq semantics** remain UNKNOWN; any use as a count denominator is
   forbidden (registry standing exception).
6. Non-IDX80 minute data before ~2026-04 rests on single-cohort vendor truth;
   the 99.70% completeness figure is conditional on it.
7. `stockbit_flow` outage rows (6 dates) will look like "no flow" rather than
   "missing" unless the outage list is consulted (recorded here and in the
   inventory).

## 12. PER-GAP VERDICT ROLL-UP

| Gap | Verdict |
|---|---|
| Broker-level view layer (identity/participation/concentration/persistence/accumulation) | **CAN FIX NOW — FIXED** (views built + validated) |
| Broker pair identification (true counterparties) | **CANNOT FIX** (historical); intraday approximation possible |
| 1-minute historical gaps (post-freeze, 7 dates + 6 outages) | **CAN FIX NOW** (owner-run backfill; recipe in §8) |
| 1-minute suspect stretch (2025-08-05..09-17) | **PARTIALLY SOLVABLE** (refetch attempt; retention risk) |
| PIT-raw intraday capture | **CAN FIX PROSPECTIVELY — BUILT** (activation = owner action) |
| End-investor identity; freq semantics; trade matching; pre-2025 broker history | **CANNOT FIX** |
| Flow × price, event conditioning, outcome-data support | **CLOSED** (data sufficient; views built; no hypotheses touched) |

## FINAL STATUS: **PARTIALLY CLOSED** — the research program is no longer
limited by unmaterialized structure (the dominant limitation, now fixed);
remaining gaps are quantified, classified, and carry explicit recovery paths
or documented impossibility.

**Zero-counters (restated):** empirical hypothesis tests run: 0 ·
predictive/backtest runs: 0 · registry changes: 0 · terminal verdict changes: 0 ·
Dataset B frozen-store modifications: 0 · production DB writes: 0.
