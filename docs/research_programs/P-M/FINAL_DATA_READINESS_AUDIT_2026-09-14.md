# FINAL DATA READINESS AUDIT — 2026-09-14

**Task type:** infrastructure verification. **Empirical hypothesis tests run:
ZERO · backtests: ZERO · return analysis: ZERO · IC: ZERO · p-values: ZERO ·
parameter tuning: ZERO · registrations/registry changes: ZERO · Dataset B
modifications: ZERO · production DB writes: ZERO · v002 frozen store
modifications: ZERO.**

Inputs: frozen Dataset B store (`21661f03…`, re-verified), frozen flow-bars
v002 (`fa7f07b3…`, re-verified), `research_data/views_v1.sqlite` (validated
25/25), production tables read-only.

---

## 1. BROKER IDENTITY STABILITY (2025-01-02 → 2026-08-27, frozen Dataset B)

**Method (pre-declared before results):** per broker, from
`v_a_broker_day`/`v_a_side`: session span, session count, max gap in admitted
sessions, investor_type set, ticker set, row count, ticket-size profile.
Declared rules: (R1) investor_type flip ⇒ POSSIBLE CHANGE; (R2) internal gap
≥ 20 sessions AND pre/post ticker overlap < 34% ⇒ POSSIBLE CHANGE — NEEDS
EXTERNAL VERIFICATION; (R3) < 30 rows total ⇒ UNRESOLVED (insufficient
evidence); otherwise STABLE. Activity changes (exits, quiet periods, ticket
sizes) are recorded as events, never as rename evidence.

**Result: 92 STABLE · 0 POSSIBLE CHANGE · 1 UNRESOLVED (of 95).**

| Class | Brokers | Notes |
|---|---|---|
| STABLE | 92 | 78 present 2025-01-02→2026-08-27 near-daily (max gap ≤ 13 sessions; 25 of them max gap = 1); zero investor_type flips anywhere in the population |
| POSSIBLE CHANGE — NEEDS EXTERNAL VERIFICATION | none | R1 never triggered; R2's only candidate (IP, 55-session gap 2025-05-27→2025-08-20) shows 64% pre/post ticker overlap and constant `investor_type='Lokal'` ⇒ dormancy, not handover. Caveat recorded: its median ticket rose Rp 2.1M → 6.5M across the gap (activity-level fact, explicitly NOT used as rename evidence) |
| UNRESOLVED | DM | 2 rows total (2025-01-02 GOTO sell, 2025-01-03 BNGA sell), never seen again. Cannot distinguish dormant code / retired code / one-off. No merge or deletion performed |

Documented entry/exit events (activity, not identity): SC exits after
2025-07-02 · PS after 2025-11-25 · GW after 2026-01-14 · AN after 2026-02-20 ·
IP last seen 2025-11-20 · IC enters 2025-04-28 (then continuous) · AP sparse
but spans the full window.

**Metadata:** no authoritative broker names exist anywhere in the repository
(`broker_period_summary.raw_json` carries no name field; no broker lookup
table). Nothing could be externally cross-checked from repo data; historical
codes were not altered and no identities merged.

**Verdict: broker_code identity is STABLE for research use.** The single
UNRESOLVED code (DM, 2 rows) is negligible in any panel but must not be
treated as a persistent actor.

## 2. HISTORICAL 1-MINUTE INTEGRITY (frozen v002)

**Method:** for every v002 session: traded set from production `ohlcv`
(`is_final=1`, `volume>0`, ∩ v002's 958 active tickers) vs v002 bar presence;
daily-summary nonzero rate from frozen `stockbit_flow`; healthy controls
(2025-02-10, 2025-07-08, 2025-10-08, 2026-03-10).

**Controls:** 100% of traded tickers have full bars (median 335 bars Mon–Thu /
275 Fri — session-length, not a defect); 100% traded-with-flow agreement;
0 discrepancies.

**Exact affected ticker-days (full-window sweep):**

| Region | Sessions | Traded-without-bars cells | Nature |
|---|---|---|---|
| 2025-04-14 (fixture) | 1 | **768** | intentional reserved fixture; never fetched by design (backfill refuses `EXIT_FROZEN_FIXTURE`) |
| **2025-08-04 → 2025-09-17** | **31** | **20,981** | integrity contradiction: OHLCV says traded (volume>0), Stockbit daily summary says zero flow, zero bars — the two Stockbit endpoints agree with each other and contradict the OHLCV vendor; nonzero-flow rate among traded tickers 14.8–19.4% vs **100.0%** on all four controls; 0 counterexample cells (nonzero flow + missing bars) inside the stretch |
| all other dates | 278 | **0** | complete: every traded ticker has bars |
| Total | 310 | 21,749 | |

Additional facts: within the stretch, 125–163 tickers per session DO have full
bars (IDX80-era subset + partial extras; 2025-09-17 partially healed at 310).
The stretch boundary refined this audit: the bars-level break starts
**2025-08-04**, one session earlier than the summary-cohort signal
(2025-08-05) found in the previous audit.

**Lawful refetch / vendor retention:** a refetch is mechanically possible and
lawful through the owner's own tooling (no frozen store touched), but (a) the
existing gap predicate (`tools/flow_bars_gap.py`) **trusts zero-activity
summaries as proof of legitimate emptiness**, so a standard run would SKIP the
entire stretch as "complete" — recovery requires an explicit force-refetch
decision; and (b) retention evidence is split: the 2026-09 cohort refetched
232 dates of the window successfully overall (152,913/198,828 rows nonzero)
yet returned self-consistent empties for exactly this segment — so the vendor
segment itself appears damaged/aged, and a refetch outcome is uncertain.

**Verdict: SAFE WITH EXCLUSIONS.** The v002 minute asset is research-grade
everywhere except the fixture date and the 31-session zone; both are exactly
enumerated (per-cell in `v_e_intraday_summary.coverage_state`, per-region
here) and must be excluded from intraday research. NOT RESEARCH-GRADE applies
only to the 31-session zone's non-covered tickers; REQUIRES REFETCH is the
recovery path if the owner wants that zone, via a force-refetch with probe
validation (OHLCV-volume cross-check), never by trusting zero-summaries.

## 3. POST-FREEZE GAPS — recipe verified, recovery quantified (not executed)

Recipe verification (code read, no execution): `tools/backfill_flow_bars.py`
— budget clamp `HARD_CAP_S=5h` with 300s cell margin, per-cell durable
commits, DB-state resume, exit codes 0/2/3/4/5 incl. `EXIT_FROZEN_FIXTURE=5`
(refuses fixture windows), `FLOW_TICKERS` default ALL;
`tools/flow_bars_gap.py::bars_cell_complete` — bars exist OR summary row is
genuinely zero (`COALESCE` on all four columns); the IDX80 orchestrator
(`tools/agent_backfill_idx80.py`) adds fcntl + /proc concurrency guards.

Would-be recovery, exactly:

| Defect | Cells | Predicate sees it? | Recoverable by standard recipe |
|---|---|---|---|
| True gaps (nonzero flow, no bars), 7 dates: 05-29:706 · 06-04:704 · 07-13:707 · 07-22:1 · 07-23:709 · 07-27:707 · 09-08:777 | **4,311** | YES (nonzero + no bars ⇒ incomplete) | YES |
| Outage sessions 2026-05-18..21, 06-17..19 (no summary rows at all, ~879 tickers each; bars only for 79 IDX80 leftovers) | ~5,274 summary-days + bars for traded tickers | YES (no bars, no summary ⇒ incomplete) | YES |
| 2025-08-04..09-17 stretch | 20,981 | **NO — zero-summaries are trusted as "complete"** | NO — needs owner force-refetch decision (§2) |

## 4. PROSPECTIVE CAPTURE — operational readiness review

| Requirement | Status | Evidence |
|---|---|---|
| immutable raw response | PASS | content-addressed objects (`sha256(body).json.gz`), `O_EXCL` write-once + `0o444`, differing-content overwrite raises |
| timestamp provenance | PASS | `captured_at_utc` + `tz_session='Asia/Jakarta'` per manifest row |
| request metadata | PASS | `url_host`/`url_path`/requested+returned windows/attempt/`code_sha256`/`config_digest`/host run log; no credentials stored |
| response hash | PASS | sha256 of exact body bytes, stored AND used as object name |
| checkpoint / resume | PASS | terminal-state skip + per-cell attempt continuation across runs (PK collision bug found by selftest and fixed: attempts now continue from `MAX(attempt)+1`) |
| completeness | PASS | `date_echo_match`, `truncation_suspected`, SUCCESS/EMPTY/FAILED classification |
| deterministic reconstruction | PASS | `parse_body`/`rebuild_rows` pure functions; selftest asserts rebuild identity; parser matches the real vendor shape (verified against retained Dataset B raw bodies) |
| isolation | PASS | writes only under `flow_capture_prospective/store/`; offline selftest never imports the vendor adapter |

**Fixed during this review:** the vendor adapter previously wrapped
`stockbit_fetcher.fetch_flow` — wrong signature AND that function returns a
parsed summary and discards the raw body (the exact loss this service exists
to prevent). It now mirrors the validated Dataset B request verbatim
(`GET https://exodus.stockbit.com/marketdetectors/{ticker}`, NET/REGULER/ALL,
`limit=150`, bearer from repo-root `.stockbit_token` — present, refreshed
08:40 today) and keeps exact bytes. Security hardening added: https-only,
exact host pin, DNS resolution refused for private/loopback/reserved/non-global
addresses (anti DNS-rebinding), redirects disabled, ticker charset validated.
Selftest re-run after the fix: ALL CHECKS PASS.

**Operationally ready: YES** (pending Owner activation: decide cadence —
recommended EOD ~18:40 WIB shadow after the production cron — and run with
`--use-vendor`; no scheduler is wired).

## 5. FINAL RESEARCH READINESS MATRIX

| Data dimension | Historical | PIT | Integrity | Future capture | Research status |
|---|---|---|---|---|---|
| Broker identity / structure (95 codes, IDX100, frozen) | A: 2025-01-02..2026-08-27 | yes (formation-t facts) | **92 STABLE / 0 POSSIBLE / 1 UNRESOLVED**; no metadata source for external check | n/a (daily broker feed live) | **GREEN** (exclude DM from persistence claims) |
| Broker concentration / pairs (potential) / persistence / accumulation | A (views over frozen store) | yes | reconciles to source exactly (net ≡ 0 identity) | yes (live feed + views) | **GREEN** |
| 1-minute flow bars (v002) | B+: 2025-01-02..2026-04-27, 99.30% of traded ticker-days clean | at-capture-time only | exact defect set: fixture + 31-session zone (21,749 cells); controls perfect | v002 successor freeze (v003) when window extends | **YELLOW** — usable with the two enumerated exclusions |
| 1-minute flow bars (production post-freeze) | B: gaps 4,311 true-gap + 6 outage sessions | no (parsed rows only, no raw) | quantified; predicate sees all of it | prospective service (ready, not active) | **YELLOW** until owner backfill + capture activation |
| Daily flow `stockbit_flow` (NF control source) | B: outage rows missing; stretch zeros untrusted | T+1 by definition | D-049 ratified construction; suspect inside stretch only | production cron + prospective service | **GREEN** outside stretch; **YELLOW** inside |
| OHLCV outcomes | A: 2021-07-05..2026-09-14, is_final | yes (registered machinery) | basis detection + quarantine validated | live | **GREEN** |
| Event conditioning data (suspensions, CAs, band contacts, bandar) | A (views over validated sources) | yes | join grid = full 30,880 roster cells | yes | **GREEN** |
| Attribution semantics | ownership labels only | yes | standing rules (no investor-identity promotion) | n/a | **GREEN** as ownership; **RED** for any investor-identity claim (impossible) |
| freq field | values A, semantics D | n/a | forbidden as count denominator | n/a | **RED** for denominator use only |
| ticks tape | C: 2026-04-18.. | prospective | short | live | **YELLOW** (prospective microstructure only) |

## 6. FINAL QUESTION

**"After this audit, is the data infrastructure strong enough to allow
research of a genuinely new hypothesis without the result being dominated by
known data defects?"**

**Yes — for the broker-structure family outright, and for intraday research
with two mechanical exclusions.** The broker-level layer is now fully
materialized, source-reconciled, PIT-clean, identity-stable (92/95 verified
stable, 1 immaterial unresolved), and its known defect set is empty for the
frozen window. The intraday layer is near-complete with an exact, machine-
checkable defect census (2 exclusion regions out of 310 sessions) and a
ready-to-activate raw-capture service that prevents recurrence. Nothing about
the remaining defects is hidden inside aggregates — every exclusion is a
named date range and a countable cell set that any future registration can
declare ex ante.

## FINAL STATUS: **DATA-READY WITH EXCLUSIONS**

**Exact remaining exclusions:**

1. **v002 minute bars — 2025-04-14** (fixture): 768 traded ticker-days — exclude by design.
2. **v002 minute bars + daily-summary zeros — 2025-08-04 → 2025-09-17** (31 sessions): 20,981 traded-without-bars cells; exclude the zone (or restrict to the 125–163 tickers with verified full bars per session) for any intraday use; treat the zone's daily `stockbit_flow` zeros as untrusted.
3. **Production minute layer, 7 dates** (2026-05-29, 06-04, 07-13, 07-22, 07-23, 07-27, 09-08): 4,311 true-gap ticker-days — exclude until the owner-run backfill lands.
4. **Production daily flow, 6 outage dates** (2026-05-18..21, 06-17..19): ~5,274 missing summary-days — absence ≠ empty; exclude or treat as missing until backfill.
5. **Broker DM**: 2 rows — insufficient identity evidence; exclude from persistence/pair claims.
6. **freq**: forbidden as a transaction-count denominator (standing registry exception).
7. **investor_type**: brokerage ownership only — never investor identity (standing semantic rule).

Zero-counters restated: hypothesis tests 0 · backtests 0 · return analysis 0 ·
IC 0 · p-values 0 · tuning 0 · registrations 0 · registry changes 0 · Dataset B
modifications 0 · v002 modifications 0 · production DB writes 0.
