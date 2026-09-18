# ZCODE ADVERSARIAL REVIEW BRIEF — FWD-PM-REGIME-002 + 2026-09-17 PATTERN SCAN

**Date:** 2026-09-18 · **Status:** REVIEW BRIEF — the artifact under review is an OPEN forward test
plus an unregistered exploratory scan. Registries: `HYPOTHESIS_REGISTRY.md` appended (additive only);
`FAILURE_REGISTRY.md`, `EXPERIMENT_LEDGER.jsonl`, `gate_decisions`, `gate_evidence`, `registry/` all
**untouched**.
**Reviewer mandate:** refute. Upholds are worth little; only refutations survive (LIM8/R2/D-019).

---

## 1. What is under review

| Artifact | Path | State |
|---|---|---|
| Forward test spec | `P-M/forward_regime/PROTOCOL.md` | **OPEN**, sha256 `4063752ef76bae840b0ff007ec2d4b3bdf9325a2b18ece0779e2fa737ec58870` |
| Ledger | `P-M/forward_regime/ledger.json` | 0 trades; opened 2026-09-17; first eligible entry 2026-09-18 |
| Recorder | `P-M/forward_regime/run_formation.py` | live via cron 09:30 daily, verified rc=0 |
| Superseded spec | `P-M/forward_regime/PROTOCOL_001_SUPERSEDED.md` | closed, 0 trades, preserved unedited |
| Pattern scan | `P-M/pattern_scan/PATTERN_SCAN_2026-09-17.md` | ~12 unregistered arms |
| Book overlay | `BOOK_OVERLAY_POLICY.md` | volatility exclusion at allocation, outside both specs |
| Scripts + hashes | `P-M/forward_regime/scripts/`, `P-M/pattern_scan/scripts/` | `SHA256SUMS.txt` in each |

Hypothesis: **HYP-PM-0010**, family **P-M · Price-Trend {T1}** (new family, member 1).

## 2. Claims to attack, strongest first

| # | Claim | Evidence | Where it would break |
|---|---|---|---|
| **C-1** | Trend-regime onset + 3xATR exit earns **+1.26%/trade (t 3.90)** ex-2025, next-open entry vs equal-weight book | `scripts/audit2.py` | Survivorship (see LIM-1); entry-date clustering insufficient for overlapping 60-session holds; EW benchmark construction |
| **C-2** | **Top 1% of trades carry 85%** of total excess; 3.3% cap-exits average +45.93% vs +0.64% for the 96.7% | `scripts/exit3.py`, PROTOCOL limitation 9 | If true, is t-based inference valid at all on this distribution? Attack the SE, not the mean |
| **C-3** | Every mean-reversion pattern is a significant **anti-edge**: sweep -1.33%, failed breakdown -1.94%, wedge -1.89% (ex-2025, t to -12) | `pattern_scan/scripts/{sweep,patterns,wedge2}.py` | Detector fidelity (arm 1 used PRODUCTION `engine/smc.py`); definition invariance already tested (6 wedge variants, exc5 stable -1.16 to -1.22) |
| **C-4** | **Single-ticker validation is worthless**: every refuted pattern looks profitable on BRPT (+4.41% to +6.09%); BRPT sits at the **91st percentile** where only 35% of tickers are positive | `pattern_scan/scripts/{brpt_all,why}.py` | Is the ticker-demeaned -1.02% (t -3.97) itself an artifact of unbalanced per-ticker N? |
| **C-5** | The 001->002 supersession was necessary: zero-volume carry-forward bars are **0.951%** of liquid ticker-days but **4.778%** of regime-UP days | `scripts/zvguard.py` | Was the >=18/20 guard chosen on hygiene or on performance? (claimed hygiene: variants moved ex-2025 only 0.78/0.85/0.83/0.80) |
| **C-6** | Regime **conditioning is infeasible**: BULL has 9 episodes / 98 sessions; `regime_config.yaml` needs min_n=100 across 12 cells | `scripts/{regime,regime_perf}.py` | Is the episode count the right N, or is it sessions? |
| **C-7** | Three-tier alignment score is **monotonic** (-6.79 / -4.21 / -1.10 / +0.62 / +1.11 ex-2025) but score +2 **inverts** (2025 artifact) | `scripts/{tiers,table27}.py` | 27 cells searched before collapsing to a score — is the collapse pre-specified or post-hoc? |
| **C-8** | **All-three-BULL has never occurred** (0 of 1,099 sessions); LONG&MID both BULL occurred once | `scripts/tiers.py` | Is SHORT (ADX 7 / MA 10 / slope 3) a legitimate tier or a parameter fork that manufactures the result? |

## 3. Governance decisions open to challenge

1. **HYP-PM-0010 retained through the 001->002 supersession, not re-registered as HYP-PM-0011.**
   Reasoning: 001 closed with **zero** recorded trades, so the re-spec cannot be outcome-driven, and
   the mechanism/thresholds/exit/horizon/benchmark/endpoint are unchanged. The conservative reading
   advances {T1} to two members. **Flagged for owner override in PROTOCOL section 7.**
2. **New family {T1} opened rather than joining a price-feature family.** No price family existed:
   FWD-PM-VOLEX-001 is an **unregistered** prospective record holding no slot, so nothing was split.
   Widening {T1} to absorb volatility later is permitted; narrowing is not.
3. **Volatility exclusion placed at book level, not in the spec** — to avoid irreversibly widening
   {T1}. Challenge: does the overlay contaminate the 002 endpoint in practice? (Design says no: the
   endpoint is computed over every signal regardless of overlay.)
4. **Pattern scan deliberately NOT filed in FAILURE_REGISTRY** — its counts feed family denominators
   and it records only *registered* hypotheses.

## 4. Limitations ALREADY disclosed — do not spend the review here

| ID | Limitation |
|---|---|
| LIM-1 | **Survivorship unmeasured.** Corpus holds only names listed as of 2026-09; max ticker-end lag is 61 days. Bias optimistic, magnitude unknown. **Largest open threat.** |
| LIM-2 | 2025 dominance throughout. Full-sample Sharpe 1.13 vs ex-2025 0.51. Ex-2025 is the planning basis everywhere. |
| LIM-3 | Close-triggered exits; a real intraday stop fires earlier at a different price. |
| LIM-4 | Effective breadth ~10 (rho 0.089) from ~131 nominal positions. |
| LIM-5 | Sector neutrality untested and unenforceable — no ticker->sector map for 77% of the universe; `engine/sector_rotation.py` maps 82 of 959 and returns permissive "sector unknown" for the rest. |
| LIM-6 | Long-only, beta 0.95. Alpha +2.258% (t 6.43) survives beta adjustment. |
| LIM-7 | Multiplicity: ~12 scan arms + 6 wedge variants + 6 entry filters + 48 threshold cells + 27 alignment cells, all on one corpus in one session. |
| LIM-8 | `stockbit_flow.composite_score` is **unpopulated** — a >=70 filter returns zero rows. The engine's composite flow score has never been testable. |
| LIM-9 | Flow-confirmation arm covers 2025-01+ only, inside the outlier regime. |

## 5. Eleven self-corrections already made (verify they were correctly resolved)

`delist.py` checked only calendar gaps and missed zero-volume suspensions (forced 001->002);
resistance-breakout 5d was an entry-timing artifact (+0.66% -> -0.30% when fixed); the first
Episodic Pivot test entered at the close and was not Qullamaggie's rule (+3.77% at the true ORB
entry); "downtrend gating is harmful" was measured on excess and needed re-testing on absolute
(conclusion survived); UP-state vs episode-onset were conflated in BEAR (+2.58% vs **-2.42%** — the
onset figure is what 002 trades); TUGU's "4.7x volume" was 3.37x; "ER peaks at tops" is wrong (it is
steepness); "never exit on the entry indicator, it lags 20%" was wrong mechanism; "stop at 50
positions" was wrong (Sharpe improves to 131); "skip slope-Q5" was overstated (small-sample);
and a regime-map proposal was initially misread as regime gating.

## 6. What a valid refutation looks like

- A mechanism by which C-1's edge is an artifact **that survives** the next-open + equal-weight audit.
- A demonstration that C-3's negatives are detector-driven **despite** production-code replication and
  six-variant definition invariance.
- A quantification of LIM-1 (survivorship) that moves C-1 materially.
- Evidence that the C-7 score collapse is post-hoc selection rather than an aggregation.
- Any look-ahead in `run_formation.py` — particularly `weekly_at()`, which must use the last week
  **closed strictly before** the entry date (verified: entries 2026-09-14/15/16 all resolve to the
  week closing 2026-09-11).

## 7. Reproduction

Build the panels with `forward_regime/scripts/{extract,panel,t1,t2,ma}.py`, then run any arm.
`SP` must point at a scratch directory. Corpus fingerprint: `ohlcv` `is_final=1`, 1,087,436 rows,
959 tickers, 2021-07-05 to 2026-09-16; `corporate_actions` 2,171 rows (101 split). Guards: splits
excluded; single sessions beyond +/-35% excluded (305 bars).
