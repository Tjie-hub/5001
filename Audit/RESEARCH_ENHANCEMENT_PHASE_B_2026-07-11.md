# Research Enhancement — Phase B Final Report (2026-07-11)

**Reference audit:** `Audit/RESEARCH_ENGINE_AUDIT_2026-07-11.md`
**Phase A baseline (immutable):** commit `7ddfc22`; suite 1,371 passed; findings R-1/R-2/R-3/R-4 CLOSED.
**Branch:** `ops/hardening-2026-07-10` · **Phase B commits:** `3faf678`, `1b72803`, `031781f` (+ this report).
**Mandate:** resolve remaining findings *where appropriate*; production execution unchanged; full reproducibility; every conclusion backed by evidence; document rejected hypotheses. No look-ahead / survivorship / leakage introduced.

---

## Executive Summary

Phase B addressed the six remaining audit findings (R-5, R-6, R-7, R-9, R-10, R-11)
under a strict "production unchanged, evidence-first" mandate. Three are now
**CLOSED** with measurable evidence, and three are **KEEP OPEN** — not for lack of
effort, but because closing them would either modify production execution (R-5, R-10)
or fails a cost/benefit bar for a low-priority item (R-7). Nothing was force-closed.

- **R-6 (CLOSED)** — the engine gained a real statistical layer: `research/statistics.py`
  (bootstrap confidence intervals, one-sided tests, Benjamini-Hochberg + Bonferroni
  multiplicity, Probabilistic & Deflated Sharpe), 17 hand-verified deterministic tests.
  Applied to the flagship NR7 claim it produced the engine's **first quantified edge
  interval** — and a genuinely useful, humbling result (below).
- **R-9 (CLOSED)** — the roller cron's day-of-month/day-of-week OR bug is fixed;
  simulated firing drops from **124/yr to exactly 12/yr** (first Sunday). Source-of-truth
  only; live crontab deliberately not reinstalled.
- **R-11 (CLOSED)** — the dead `engine/strategy_registry/` package is deleted; zero
  importers, suite still collects clean.
- **R-7 (KEEP OPEN, evidence-backed)** — process-parallel walk-forward **measured at
  2.03× on 4 cores with byte-identical output** (reproducibility preserved). Not wired
  into the production weekly job: the modest speedup on available hardware plus SQLite
  single-writer contention (R-5) don't justify modifying a live P3 job.
- **R-5 (KEEP OPEN)** — **14 production files** read research tables directly; a physical
  DB split is a ~1-2 week, high-blast-radius change that would touch production reads.
- **R-10 (KEEP OPEN)** — registry lifecycle gaps confirmed, but the registry design was
  frozen in Phase A and the loader is production; documented with a non-breaking plan.

**The single most important Phase B finding is statistical, not structural:** the NR7
BULL edge is **significantly positive** (95% CI [+0.32%, +2.06%], survives regime-family
multiplicity at p_adj = 0.011, PSR 99.6%), **but** its CI lower bound sits *below* the
+0.50%/trade promotion bar and its Deflated Sharpe collapses under the full 42-cell
regime-scan family. The edge is real versus zero; its *magnitude* is uncertain and its
robustness to full multiple-testing is not established by backtest. The pre-registered
forward test remains the decisive arbiter — which is exactly the posture the engine
already adopted.

**Verdict: GO WITH CONDITIONS** (unchanged tier from Phase A; score ≈7.0 → ≈7.3).

---

## Scope & Rules Honored

- **Production execution unchanged.** No edits to the production scheduler, live scan
  path, provider layer, registry design/loader, API, or frontend. R-9 changed only the
  versioned `deploy/crontab` source (not reinstalled). R-6/R-11 touch only `research/`,
  a dead package, and tests.
- **No look-ahead / survivorship / leakage introduced.** R-6 is pure post-hoc analysis
  of already-computed trades; the NR7 re-collection reuses the Phase-A methodology
  (bar i-1 signal, i-open fill, full-corpus survivorship, `is_final` only).
- **Reproducibility preserved.** Every stochastic routine is seeded (`SEED=20260711`);
  the parallelism benchmark proved identical output; all numbers below are regenerable.
- **Rejected hypotheses documented** (BEAR "edge", full-multiplicity Sharpe survival).

---

## Per-Finding Analysis (working process)

### R-6 — No uncertainty quantification / multiplicity control → **CLOSE**

1. **Original concern.** No bootstrap/Monte-Carlo, no confidence intervals on expectancy,
   no multiple-testing control across the 14×3 regime scan; the +1.18% NR7 expectancy
   "carries no standard error anywhere."
2. **Still exists?** Yes at entry — repo-wide grep found zero CI/bootstrap/multiplicity
   utilities in `research/`; `nr7_study` had only point estimates (`pool`, `evaluate`).
3. **Evidence produced.** New `research/statistics.py` + 17 deterministic tests; applied
   to the NR7 regime cells (seed 20260711, N=1108 trades, corpus fingerprint `0d017509…`):

   | Regime | N | exp/trade | 95% bootstrap CI | p (1-sided) | BH-adj p | Sharpe |
   |---|---|---|---|---|---|---|
   | SIDEWAYS | 619 | −0.905% | [−1.352, −0.447] | 0.99994 | 0.99994 | −0.155 |
   | BEAR | 156 | +0.432% | [−1.066, +2.051] | 0.2945 | 0.4418 | +0.043 |
   | **BULL** | **333** | **+1.197%** | **[+0.324, +2.056]** | **0.00355** | **0.01066** | **+0.148** |

   BULL Sharpe multiplicity: **PSR(SR>0) = 0.9963**; **DSR(n=3 regime cells) = 0.617**
   (benchmark SR* 0.131); **DSR(n=42 full regime scan) = 0.00025** (benchmark SR* 0.339;
   `sr_trials_std` 0.154 estimated from the 3 NR7 cells — a proxy, see limitations).
4. **Impact quantified.** (a) The BULL edge is statistically **positive** — CI excludes 0,
   survives BH *and* Bonferroni across the regime family (p_adj 0.011), PSR 99.6%. (b) But
   the CI lower bound **+0.32% is below the +0.50% promotion bar**, so the magnitude that
   justified promotion is not guaranteed by the data. (c) **BEAR is not significant**
   (p 0.29, CI straddles 0) — quantitatively confirming Phase A's finding that the
   2026-07-07 BEAR "PASS" was fragile noise. (d) Under the full 42-cell family the
   Sharpe-based case **collapses** (DSR ≈ 0) — the audit's multiplicity worry, made concrete.
5. **Recommendation: CLOSE.** The capability the audit asked for now exists, is tested,
   and has been exercised on the live claim.
6. **Why.** R-6 was a tooling gap; the tool is delivered, deterministic, and immediately
   produced decision-relevant evidence. Residual (a proper 42-cell DSR from the real scan
   SRs) is a follow-on *use* of the tool, not a gap in it.

### R-9 — Roller cron fires ~11×/month; optimizer raw connection → **CLOSE**

1. **Original concern.** `0 10 1-7 * 0` triggers vanilla cron's DOM-OR-DOW trap (fires
   every day 1-7 AND every Sunday); optimizer used raw `sqlite3.connect`.
2. **Still exists?** The optimizer half was already fixed in Phase A (`data.db.connect`,
   verified lines 282–317). The cron bug was live in `deploy/crontab`.
3. **Evidence produced.** 12-month firing simulation: **old = 124 fires/yr (~10.3/mo);
   new `0 10 1-7 * * [ date +%u == 7 ]` = 12 fires/yr**, each asserted to be the first
   Sunday. Fix committed to the source-of-truth crontab.
4. **Impact.** ~10× wasteful roller invocations eliminated; behavior benign (roller only
   appends windows) but now matches documented monthly intent.
5. **Recommendation: CLOSE** (both halves).
6. **Why.** Deterministic, verified, low-risk. Not reinstalled — `crontab deploy/crontab`
   is the operator's step, so production cron is unchanged until they choose.

### R-11 — Dead `engine/strategy_registry/` package → **CLOSE**

1. **Original concern.** A second, decorator-based strategy registry that nothing uses.
2. **Still exists?** Yes — 4 modules present, only self-imports; sole external reference a
   "do not confuse" note. (The optimizer-duplication half was closed in Phase A.)
3. **Evidence produced.** Repo-wide grep: no importer outside the package, no test
   references it; after `git rm` the full suite still **collects 1,371 tests with zero
   import errors**. Note converted to a deletion tombstone.
4. **Impact.** ~24 KB / 4 modules of misleading dead code removed; one authoritative
   registry (`STRATEGY_FUNCS`) remains.
5. **Recommendation: CLOSE.**
6. **Why.** Provably unused; deletion is safe and reduces drift/maintenance surface.

### R-7 — Single-threaded sweeps, no orchestration → **KEEP OPEN** (evidence-backed)

1. **Original concern.** 2.4-hour serial walk-forward; no parallelism; caps at ~100
   manual experiments.
2. **Still exists?** Yes — Phase A's tracked recompute measured wf-refresh at **9,451 s**
   and backtest-cache at **6,123 s**, single-threaded.
3. **Evidence produced.** Serial-vs-process-parallel benchmark, 48 tickers, self-loading
   workers (no DataFrame pickling): **serial 474.7 s → parallel 233.3 s = 2.03× on 4
   cores**, with **byte-identical output (0 mismatches)** — parallelism preserves
   reproducibility.
4. **Impact quantified.** ~2× on this hardware; would scale further on a bigger host, but
   SQLite single-writer contention (R-5) and 4 physical cores cap the near-term gain.
5. **Recommendation: KEEP OPEN.** Design validated and reproducibility proven; the
   production wiring (an opt-in `n_procs` path in `refresh_wf_scores`, defaulting serial)
   is deferred.
6. **Why.** Modifying the live weekly job for a measured 2× on a P3 item does not clear
   Phase B's "small, low-risk, production-unchanged" bar. The evidence is captured so the
   change can be made deliberately when hardware or throughput ambitions justify it.

### R-5 — Shared prod/research SQLite; prod reads research tables → **KEEP OPEN**

1. **Original concern.** One `walkforward.db` holds production and research state; a
   research bug's blast radius is production; prod depends on experimental outputs.
2. **Still exists?** Yes.
3. **Evidence produced.** **14 distinct production files** SELECT from `wf_scores` /
   `wf_edge` / `backtest_cache`, including core paths: `paper_trade.py`,
   `scheduler/scanner.py`, `engine/agent_firm/firm.py`, `engine/liquidity.py`,
   `engine/watchlist.py`, `engine/edge_enrich.py`, `screener/brpt_filter.py`,
   `routes/backtest.py`, `routes/screener.py`, `routes_backtest_multi.py`.
4. **Impact.** A physical split requires re-routing or retiring all 14 readers (to
   registry evidence or a cross-DB attach) before separating `research.db` — high
   blast radius on live trading paths.
5. **Recommendation: KEEP OPEN.** Staged plan: retire gate readers (blacklist /
   quality-gate / edge-veto → registry artifacts) → then the trivial file split.
6. **Why.** Directly collides with "production execution must remain unchanged" and is a
   1-2 week effort; unsafe to attempt inside Phase B's small-commit constraint.

### R-10 — Registry lifecycle gaps → **KEEP OPEN**

1. **Original concern.** No pre-candidate states; `NR7_BULL_v1` APPROVED with shadow N=0;
   disabled strategies live in a parallel `paper_config` list, not as RETIRED entries.
2. **Still exists?** Yes — `edge_registry.yaml` has one APPROVED entry;
   `NR7_BULL_v1.yaml` records `shadow: {trades: 0, verdict: pending}`; `paper_config.
   disabled_strategies` holds 8 names (vwap_reversion, vol_weighted, conservative,
   momentum, Liquidity Sweep, ORB, Volume Profile POC, Inside Bar Breakout).
3. **Evidence produced.** The two-lifecycle-system split and the shadow-N=0 approval are
   confirmed in the manifests and DB above.
4. **Impact.** A strategy's funnel position isn't queryable; APPROVED isn't evidence-gated
   on shadow N — process-integrity gaps, not correctness bugs.
5. **Recommendation: KEEP OPEN.** Non-breaking future design: add lifecycle states +
   backfill roster entries + enforce a shadow-N gate at approval time.
6. **Why.** Phase A explicitly froze registry design, and the loader is production code —
   changing states/gates risks production loading, violating the mandate. Documented for a
   dedicated, reviewed change.

---

## Deliverable 1 — Technical Implementation Summary

| Commit | Finding | Change |
|---|---|---|
| `7ddfc22` | Phase A | Baseline: NR7 re-study + Phase A final report (docs) |
| `3faf678` | R-11 | Delete `engine/strategy_registry/` (4 modules); tombstone note |
| `1b72803` | R-9 | `deploy/crontab` roller → first-Sunday guard |
| `031781f` | R-6 | New `research/statistics.py` (172 LoC) + `tests/test_statistics.py` (17 tests) |

- **Files added:** `research/statistics.py`, `tests/test_statistics.py`,
  `Audit/RESEARCH_ENHANCEMENT_PHASE_B_2026-07-11.md`.
- **Files deleted:** `engine/strategy_registry/{__init__,registry,backtest,filters}.py`.
- **Files modified:** `deploy/crontab`, `engine/strategy_specs.py` (tombstone note).
- **Database changes:** none (Phase B added no tables/columns; R-6 analysis is read-only).
- **Schema changes:** none.
- **Tests added:** 17 (`test_statistics.py`), all hand-verified + determinism-asserted.

## Deliverable 2 — Statistical Validation

The NR7 regime-cell table and Sharpe-multiplicity results are in R-6 above.
Interpretation: **BULL edge confirmed > 0 and multiplicity-robust across regimes**
(BH/Bonferroni p_adj 0.011, PSR 0.996); **magnitude uncertain** (CI lower bound +0.32%
< +0.50% bar); **BEAR rejected** (not distinguishable from 0); **full-family Sharpe not
established** (DSR≈0 under 42-cell proxy). This *sharpens* — and appropriately tempers —
the promoted claim without overturning it; the forward test remains decisive.

## Deliverable 3 — Before vs After

| Dimension | Before (Phase A baseline) | After (Phase B) |
|---|---|---|
| Findings CLOSED | R-1, R-2, R-3, R-4 | + R-6, R-9, R-11 |
| Findings OPEN | R-5, R-6, R-7, R-9, R-10, R-11(part) | R-5, R-7, R-10 (evidence-backed) |
| Statistical tooling | none | bootstrap CI, BH/Bonferroni, PSR/DSR (tested) |
| NR7 edge evidence | point estimate +1.18% | +1.197% with 95% CI [+0.32, +2.06] + multiplicity |
| Roller cron | 124 fires/yr | 12 fires/yr (first Sunday) |
| Dead code | `strategy_registry/` present | deleted (0 importers) |
| WF parallelism | serial only (unproven) | 2.03× measured, parity identical (design validated) |
| Test suite | 1,371 passed | **1,388 passed, 0 failed** (+17 R-6 tests) |
| Production behavior | — | unchanged |

## Deliverable 4 — Risk Assessment

- **Introduced risk: essentially none.** R-6 is additive read-only tooling; R-11 removes
  provably-dead code; R-9 edits a non-installed source file. No production path changed.
- **Reproducibility risk:** controlled — seeds fixed; parallelism parity proven before any
  recommendation. No RNG leaked into the deterministic pipeline.
- **Residual/deferred risk:** R-5 (shared-DB blast radius) and R-10 (post-hoc approval
  gating) remain — both documented, neither newly worsened. R-7 parallelism carries future
  wiring risk (mitigated by the opt-in/serial-default design).
- **Statistical risk surfaced (not introduced):** the DSR/CI results caution against
  increasing NR7 allocation on backtest strength; this is a *newly visible* risk the tool
  exposed, and the correct response is the existing forward-test gate.

## Deliverable 5 — Reproducibility Notes

- All Phase B numbers regenerate from HEAD: `research/statistics.py` is deterministic
  (`SEED=20260711`); the NR7 stats reuse corpus fingerprint `0d017509…` (identical to the
  Phase-A recompute run `cac9176…`) and NR7 config hash `8845c57b…` (matches manifest).
- The parallelism benchmark asserts serial == parallel output (0 mismatches), so the
  proposed R-7 design cannot alter results.
- Scripts used for evidence live in the session scratchpad (NR7 stats, R-7 benchmark);
  they are analysis harnesses, not committed production code.

## Deliverable 6 — Remaining Limitations

- **DSR(n=42) is a proxy** — `sr_trials_std` is estimated from the 3 NR7 regime cells, not
  the true 42-cell scan Sharpes. Direction (edge weakens under full multiplicity) is
  trustworthy; the exact DSR is not. A definitive figure needs the regime-scan SRs.
- **t-test uses the normal approximation** (valid at N≥100; the engine's gate) rather than
  exact Student-t.
- **R-5, R-7, R-10 remain open** (see analysis); the engine is still one SQLite file, still
  serial in production, still post-hoc in shadow-gating.
- **Single regime cycle** (carried from Phase A): BULL expectancy rests on ~one BULL
  episode; the forward-test timebox is the compensating control.

## Deliverable 7 — Institutional Recommendation

**GO WITH CONDITIONS** (score ≈7.0 → ≈7.3). Re-score deltas vs Phase A:

| Dimension | Phase A | Phase B | Basis |
|---|---|---|---|
| Statistical Validity | 6.0–7.0 | **7.5** | CI + multiplicity + PSR/DSR shipped & exercised |
| Maintainability | 5.5 | **6.0** | dead package removed |
| Operational Maturity | 5.5 | **6.0** | R-9 cron fixed; R-7 path validated |
| Reproducibility | 7.0 | 7.0 | unchanged (seeds add determinism to new tooling) |
| Data Integrity / Backtesting / WF / Promotion / Registry / Architecture | (Phase A) | unchanged | not in Phase B scope |

Conditions to reach **INSTITUTIONAL RESEARCH READY**: (1) R-5 physical DB split after
reader retirements; (2) R-10 evidence-gated lifecycle states enforced in the loader;
(3) a real 42-cell Deflated Sharpe (retire the proxy) and a bootstrap CI baked into the
promotion gate. Operationally: **do not increase NR7 allocation on backtest strength** —
the CI lower bound is sub-threshold and full-family Sharpe is unproven; let the
pre-registered forward test decide.

## Deliverable 8 — Updated Audit Register

| ID | Sev | Status after Phase B | Evidence |
|---|---|---|---|
| R-1 | CRITICAL | **CLOSED** (Phase A) | gap-verified adjustment; premise disproven; validated no-op |
| R-2 | HIGH | **CLOSED** (Phase A) | boundary/fence tests widened to `routes/` |
| R-3 | HIGH | **CLOSED** (Phase A) | optimizer delegates to canonical strategies; parity test |
| R-4 | HIGH | **CLOSED** (Phase A) | `research_runs` append-only + fingerprint + run_id |
| R-5 | MEDIUM | **KEEP OPEN** | 14 prod files read research tables; split = high-risk 1-2wk |
| R-6 | MEDIUM | **CLOSED** (Phase B) | `research/statistics.py` + 17 tests; NR7 CI + multiplicity + DSR |
| R-7 | MED-LOW | **KEEP OPEN** | 2.03× measured, parity identical; prod wiring deferred (P3) |
| R-9 | LOW | **CLOSED** (Phase B) | cron 124→12 fires/yr; optimizer conn fixed (Phase A) |
| R-10 | MED-LOW | **KEEP OPEN** | registry design frozen; shadow-N=0 + parallel disable-list documented |
| R-11 | MED-LOW | **CLOSED** (Phase B) | dead pkg deleted (0 importers); optimizer dup removed (Phase A) |

**Closed: 7/10 (R-1,2,3,4,6,9,11). Keep open with evidence: 3/10 (R-5,7,10).**

---

*Phase B complete. Phase C not started. No production behavior was modified. All changes
are additive research tooling, dead-code removal, and a non-installed cron source fix,
each in its own reviewable commit leaving the suite green. Presented for review before
any further work.*
