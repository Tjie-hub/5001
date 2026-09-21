# SHOCK→ABSORPTION→CONTINUATION — FEASIBILITY SPEC (frozen pre-count, 2026-09-21)

**Status:** SPEC FROZEN before any counting. Exploratory feasibility — **consumes no family slot**.
Routing pre-declared by Owner 2026-09-21 (option A): **survive → prospective recorder, not
registration; dead → report only, nothing built.**

**Provenance of the lead.** Extracted 2026-09-17 from the TUGU/SMMT ad-hoc trader review (n = 2
anecdotes, unvalidated): both names showed shock → absorption (VPIN label HIGH→LOW drop,
single-broker accumulation) → continuation, and both surfaced in the EOD watchlist only AFTER the
move (publication latency). The premover had scored SMMT on 2026-09-01 and TUGU on 2026-09-09.
This spec converts that story into one pre-committed count.

## 1. Question

After a single-session up-shock, does top-broker accumulation within days predict POSITIVE
forward continuation — often enough, and strongly enough, to be worth capturing prospectively?
Tradeable form is long-only (up-shocks; the program's no-shorts rule stands).

## 2. Data (measured 2026-09-21, read-only `data/walkforward.db` mode=ro)

| table | coverage | rows | note |
|---|---|---|---|
| `bandar_detector` | 2025-01-02 → 2026-09-18 | 109,142 | 872 tickers; `top1_accdist` ∈ {Big Acc, Normal Acc, Small Acc, Neutral, Small Dist, Normal Dist, Big Dist} |
| `broker_flow` | 2025-01-02 → 2026-09-18 | 3,169,417 | per-broker; not gated on, provenance only |
| `vpin_scores` | 2026-06-05 → 2026-09-18 | 61,550 | `vpin_label` ∈ {LOW, MODERATE, HIGH, TOXIC, N/A}; Stage-2 attribute only |
| `ohlcv` (is_final=1) | full settled history | — | shock + forward returns |
| `corporate_actions` | — | — | splits for the contamination guard |

Known defect carried honestly: neither TUGU nor SMMT is in Dataset B's 101-name roster — this
spec deliberately uses the production full-universe tables instead, which cover both.

## 3. Frozen definitions (one pass, no threshold iteration; any change = new dated spec)

- **Shock** (event trigger): single-session close-to-close return ≥ **+10%** on a settled bar
  (`is_final=1`), `volume > 0`, `close ≥ Rp 50`, ≥ 25 prior sessions, ticker ≠ IHSG.
  Up-shocks only.
- **Absorption marker:** within **3 sessions strictly after** the shock session (ticker's own
  calendar), `top1_accdist` ∈ {**Normal Acc, Big Acc**} (≥ +2 on the 7-level map
  Big Acc +3 / Normal Acc +2 / Small Acc +1 / Neutral 0 / Small Dist −1 / Normal Dist −2 /
  Big Dist −3). The **first** qualifying session is the marker session; later qualifying
  sessions are ignored (one event per shock).
- **Entry:** next session's open after the marker session. **Horizons:** h ∈ {5, 10, 20},
  exit at close of entry + h − 1. **Costs:** 0.60% RT. **Contamination guard:** event voided
  if any session in [marker+1 .. marker+h] has |ret| > 35% or a recorded split (FADE/panel.py
  convention, reused verbatim; per-horizon at read time, signal-level at capture time is
  equivalent because the windows nest).
- **Benchmarks (dual, identical convention):** (a) IHSG entry-open → exit-close;
  (b) equal-weight LIQUID book — per-(date, h) mean forward return of rows passing the FADE
  per-row liquid gate (`adv20 ≥ Rp 1e9` etc.). The benchmark book stays liquid-gated; the
  EVENT universe does not (see below).
- **Universe:** all tickers in `bandar_detector` (872) — **no liquidity gate at capture**; the
  anecdotes were small caps. `adv20` (Rp bn) at the shock is recorded per event; any gate is
  an Owner decision at registration time, made with the tier breakdown in hand.
- **Window:** shocks 2025-01-02 → latest settled session. **Dedup key:** (ticker, shock_date).
  Overlaps across tickers allowed; inference clusters one-way on **entry date**
  (`cluster_t` formula reused verbatim from `fade_failed_breakdown.py` / panel.py).
- **Attributes recorded per event (never gating):** top1/top3 label scores at marker;
  `net_broker_count`; `broker_accdist`; **pre-shock accumulation flag** (top1 ≥ +2 on any of
  the 5 sessions before the shock — the TUGU Sep-10..14 configuration); adv20 tier;
  `vpin_label` at marker where coverage exists (2026-06-05 onward).

## 4. Stage 2 — VPIN split (descriptive only, never gating)

On the subset with VPIN coverage (2026-06-05 →), split events by `vpin_label` at the marker
session: LOW/MODERATE vs HIGH/TOXIC. Reported as a two-row table; no test, no threshold.

## 5. Pre-declared outcomes

| outcome | condition | routing |
|---|---|---|
| **ALIVE** | N ≥ 50 events AND ≥ 20 distinct entry dates AND cluster-t of h=20 excess vs EW-book ≥ **+2** (mean > 0) | build prospective recorder same-session (mirror `forward_fade/run_recorder.py`), ledger opened then, no back-fill; registration decision deferred ≈ 3 months |
| **DEAD (null)** | N ≥ 50 but h=20 excess vs EW-book ≤ 0 or t < 2 | report only; nothing built |
| **TOO RARE** | N < 50 | report only; Owner may still order capture after reading, but nothing is built automatically |

No re-run with relaxed thresholds under this spec. A second look = a new dated spec carrying
this one's multiplicity debt.

## 6. Sanity anchors (validation, not tuning)

The pipeline must attempt to reproduce the two anecdotes inside the window:
- **TUGU**: shock 2026-09-16 (+12.03%; 09-15 close 1455 → 09-16 close 1630, verified); observed
  `top1_accdist` = Big Acc on 09-10/11/14 (pre-shock), Big Dist on 09-16. Anchor expectation
  stated in advance: the pre-shock accumulation flag fires; whether the POST-shock marker fires
  depends on 09-17+ rows (currently absent for TUGU — reported honestly as data-limited, not
  tuned around).
- **SMMT**: shock 2026-09-16 (+15.67%; 09-15 close 2680 → 09-16 close 3100, verified); same
  treatment.
Failure of an anchor is reported as-is: it means the extracted story does not survive
formalization, which is itself the finding.

## 7. Multiplicity & governance

One mechanism, one pre-frozen definition set, one pass. Exploratory grade throughout — the
in-sample count earns nothing; if ALIVE, the recorder exists so that a future registration
decision is made on forward evidence, not on this count. This document consumes no family
slot; family taxonomy (broker-flow-adjacent vs new) is an Owner act that only happens if the
lead survives forward. Honest base rate carried from the 2026-09-15 sprint (≈120 constructions
→ 0 tradable edges) and the 2026-09-18 negative-marginal-value ruling on same-panel search:
this spec is justified ONLY by the new-surface argument (universe-wide broker-identity marker,
untouched by the sprint's families).

## 8. Limitations

1. n = 2 anecdote origin; mechanism is post-hoc narrative until the count speaks.
2. 21 months of broker history is one market regime slice (2025–2026); decade robustness
   unknown (26-year panel is OHLCV-only — no broker dimension).
3. Publication-latency confound is NOT tested here: this spec measures whether the pattern
   predicts continuation from observable markers, not whether it can be acted on at retail
   latency. Actionability is a later, separate question.
4. `bandar_detector` rows depend on the daily stockbit fetch; missing rows (e.g. TUGU after
   09-16) silently narrow the marker window — counted as data-limited, never imputed.
5. VPIN leg is 3.5 months young; Stage 2 is underpowered by construction and says so.

## 9. Deliverables

`docs/research_programs/P-M/shock_absorption/` — this spec, `scripts/feasibility_count.py`
(read-only), `results_2026-09-21.json`, and `FEASIBILITY_REPORT_2026-09-21.md` (verdict first,
anchors second, tables last). If ALIVE: additionally `forward_recorder.py` + opened ledger,
mirroring `forward_fade/`.
