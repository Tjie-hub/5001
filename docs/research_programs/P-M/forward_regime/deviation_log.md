# FWD-PM-REGIME-002 — deviation log

Append-only. Never rewritten. Every entry is dated and states what changed, why, and whether any
outcome was visible at the time. (Opened 2026-09-24 with DEV-001. The three 2026-09-17
observability amendments predate this file; they are recorded in `ledger.json` `_amendment_note`
and PROTOCOL.md limitations 9–10.)

---

## DEV-001 · 2026-09-24 · overlap-robust and calendar-time t reported beside the frozen statistic (observability only)

**Authority.** DECISION_LOG D-057. Owner instruction on 2026-09-24 ("approve all"), option (b) of
`docs/research_programs/AUDIT_2026-09-24_RESULT_VALIDITY.md` §4.

**What changed.**
- Nothing in PROTOCOL.md §2 or §3. The PROTOCOL.md sha256 stays `4063752e…`.
- Nothing in `ledger.json` or `run_formation.py`.
- **Added:** `P-M/forward_robust/robust_report.py`, a read-only report (tests:
  `tests/test_forward_robust_report.py`).
  - **When:** at every read (12, 24 and 36 months, and any interim), next to the frozen §3 statistic.
  - **What:** the same mean excess with three further t-statistics:
    - month-cluster t;
    - Driscoll-Kraay t with L = 60 sessions (the cap);
    - calendar-time portfolio t (gross daily excess vs IHSG, NW(5)).

**Why.**
- **The frozen §3 statistic** is a one-way t clustered on entry date. The holds (up to 60 sessions,
  mean ≈ 20) overlap across entry dates, so that t understates the standard error.
- **Audit evidence** (in-sample, same data and spec):
  - reference t 6.19 → month 3.44 / DK 2.73 / calendar 2.69;
  - ex-2025 t 2.70 → 1.84 / 1.55 / 1.71;
  - ex-2025 without the holding-window guard: +1.06%/trade, month 2.16 / DK 1.78.
- **On a simulated null** the frozen estimator rejected 39% at a nominal 5%.
- **Read through the §3 rule:**
  - P(PASS | zero effect) ≈ 13–17%, not 5%;
  - 80% power at the +0.928% planning effect needs ≈ 73–103 months, not 36.

**Was any outcome visible?** No. `ledger.json` holds **0 trades**: sha256 `c06970ac…`, unchanged since
2026-09-17 08:04 UTC. The report was written and tested on synthetic ledgers only.

**What did NOT change.**
- Specification, thresholds, exit, universe, benchmark, endpoint, cost, cadence and ledger schema.
- **The §3 PASS / FAIL / INCONCLUSIVE rule remains the only decision.** No column of the report can
  change a verdict.

**Pre-declared reading.**
- Whenever §3 yields PASS and the calendar-time t is ≤ 1.65, the read is recorded as
  **"PASS under the frozen rule; not confirmed under overlap-robust inference."**
- It is recorded the same way for FAIL and INCONCLUSIVE, with the robust columns shown.
- Any action on a disagreement is a separate Owner decision.

---

## DEV-002 · 2026-09-25 · modeled-cost excess reported beside the frozen statistic (observability only)

**Authority.** DECISION_LOG D-059, point 2. Owner instruction on 2026-09-25 ("complete all path with
your recommendation"), which adopted the recommendation to add this line.

**What changed.**
- Nothing in PROTOCOL.md, `ledger.json` or `run_formation.py`.
- **Added to `P-M/forward_robust/robust_report.py`:** `modeled_cost()`, `liquidity_panel()` and one
  extra REGIME-002 row, "excess (modeled cost D-059, vs IHSG) - observability". Tested in
  `tests/test_forward_robust_report.py`.
  - **What:** `gross_return − (0.50% fees + ½ spread at entry + ½ spread at exit + 2·σ_d·√(Rp 100m / adv20))
    − market_return`. The spread is Abdi-Ranaldo floored at one tick; spread, σ_d and adv20 are all known
    at t−1 (`P-M/cost_liquidity/cost_by_adv.py`, as run for D-059).
  - **Estimators:** the same ones as the frozen row, plus DEV-001's robust columns.

**Why.** D-059 measured realistic all-in cost for T1's names at about 1.5–3.5% per round trip, against
the frozen 0.60% (PROTOCOL §2's own "open ambiguity"). On the in-sample reference, T1 nets +0.11%/trade
under the model (FRICTION). A frozen PASS would not by itself imply a tradeable edge.

**Was any outcome visible?** Yes, one trade. `ledger.json` held **1 closed trade** when the report was
first run end to end to verify the new row (2026-09-25): frozen excess −8.61%, modeled −9.74%. The
column was designed and tested on synthetic ledgers before that run, and the model is D-059's
pre-declared model, unchanged. No parameter was chosen after seeing the trade.

**What did NOT change.** Specification, thresholds, universe, endpoint, frozen 0.60% cost and ledger
schema. **The §3 rule remains the only decision.**

**Pre-declared reading.** At every read, report the modeled-cost mean beside the frozen one. If §3 gives
PASS while the modeled-cost mean is ≤ +0.30%/trade (the §3 FAIL floor), record the read as **"PASS under
the frozen rule; not tradeable under modeled cost (D-059)."** Realised fills, once they exist, supersede
the model (PROTOCOL §2).
