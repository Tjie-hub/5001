# ADVERSARIAL DISCOVERY PASS — REPORT

**Date:** 2026-09-15 · **Program:** P-M · **Stage:** DISCOVERY ONLY (second, adversarial pass)
**Mandate:** attempt to destroy the first sprint's shortlist. No registration, no confirmatory run,
no registry change, no I7 contact.

**Headline answer to the mandate question —**

> **After trying hard to kill UP3 and the other candidates: no robust, economically tradable ENTRY
> edge survives. UP3 is dead. The single durable discovery of both sprints is a flow-toxicity
> marker — "platform outflow into a rising price" — which is stable in all four half-years and is
> usable as an AVOIDANCE / RISK FILTER, not as an entry signal.**

That is a clean "no robust edge found yet" on the entry side, with one negative-information finding
that survived every test thrown at it.

**Artifacts:** `adversarial_up3.py` → `cache/adv_up3.json`; `adversarial_flow.py` → `cache/adv_flow.json`.
All kill rules were declared in code comments **before** the runs; no cell was selected after the fact.

---

## 1. UP3 — DEATH CERTIFICATE (six independent kills)

Recall the headline: `ret1 ≥ +3%`, enter next close, hold 5–10: +1.39% gross h5, +0.79% net of 60bp.

| # | Attack | Result |
|---|---|---|
| K1 | **Tail dependence** | Mean +1.14% but **trimmed-20% mean is −0.20%**; top 1% of observations carry **65%** of the total gain (top 10% carry 269%); median ≈ 0; max single event +177.6% (UANG 2025-11). Lottery-tail phenomenon. |
| K2 | **Suspension contamination** | 1,002 events (5.7%) overlapping suspension windows average **+11.7% h5**. Clean subset: **h5 +0.50%, h10 +0.56%, h20 +0.43% — at or below the 60bp cost floor at every horizon.** |
| K3 | **Entry mechanics** | Buying at next **open**: h5 **+0.13%** (net −0.47%). Buying across day t+1 (typ-price ≈ VWAP proxy): +0.36%. The entire effect requires entering at the **close of day t+1** — i.e., the continuation lives in stocks that are strong *during* day t+1. Executable only as a close-auction entry that conditions on that session's strength; fragile to slippage. |
| K4 | **Pseudo-OOS 2021-07..2024-12** (3.5 years, ~64K events, untouched by any prior discovery; price-only signal) | **h5 ≈ 0.00% (2021-22, all thresholds 2/3/5%) and +0.06..+0.14% (2023-24). The effect does not exist before 2025.** It is a property of the 2025–2026 canvas, not a durable market regularity. |
| K5 | **Overlap with the existing production system** | 56.7% of UP3 events already fire `fastmover_patterns` (24.1% as CONTINUATION). Overlapping events: h5 +2.11%. **UP3-only (novel to the estate) events: h5 +0.32% — below cost.** Zero incremental alpha beyond what the fast-mover scanner already harvests. |
| K6 | **Survivorship bound** | Canvas has **zero dropouts** (all 959 tickers alive today; pure current-roster backfill). If just **1–2%** of historical events actually ended in a −60% delisting tail, the adj h5 falls to +0.5%..−0.1% net-negative. The magnitude of survivorship inflation needed to erase UP3 is well within plausible IDX delisting hazard. |
| — | Threshold surface (declared) | Broad plateau (all thresholds +1%..+10% positive, 3/4 halves) — the surface is smooth, but smooth around zero once K2/K4 apply. Horizon surface similarly smooth. These do not rescue the candidate. |
| — | Liquidity / lottery | Bottom-ADV tercile +1.80% vs top-ADV +1.06%; mega-cap (ADV & price top-3rd) only **+0.41%**. The effect is a small-cap/cheap-stock lottery gradient. |
| — | Time stability | 12/21 positive months; rolling-3m mean dips to **−15.5%**; the 2026-05 basket month was −9.7%. Deep drawdown episodes, not a smooth premium. Bear-state events: +0.35% only. |
| — | Corporate actions | The one clean bill: only 38 of 17,486 events carry a split inside the window (ex-split subset h5 +1.12% ≈ full). The ±25% heuristic is immaterial for UP3. |

**Bucket: DEAD** (as a new entry edge; the surviving sliver is the estate's existing fast-mover
harvest plus a suspension/lottery tail).

---

## 2. A5 (flow acceleration) — DEAD as a tradable construction

Predeclared kill rule: a branch survives only with incremental h5 ≥ +30bp vs parent AND ≥3/4 positive
halves AND net-of-cost positive h10. Result of the declared grid (all on the suspension-clean base):

| Branch | n | h5 | Verdict vs rule |
|---|---|---|---|
| A5 standalone | 7,920 | −0.16% | below cost, 2/4 halves → fail |
| UP3c & accel ≥ +1.5 | 1,941 | +0.08% (parent +0.50%) | **incremental −42bp → fail** |
| A5 & ADV top/mid/bot | 2.7K each | +0.32% / −0.41% / −0.40% | 2/4 halves → fail |
| A5 × volatility, × prior return, × volume | — | all ≤ +0.14% h5 | fail |

The FM result (β +0.36%, t=+3.11 even against raw flow) is real as a **within-strata statistical
association** but no declared conditioning extracts it economically. Notably, *accelerating* flow
arriving into an up-move makes outcomes WORSE (chase), while flow-neutral up-moves are the best cell.
**Bucket: DEAD** (the FM coefficient should be re-read as "flow level = chase = negative; flow
*change* = mildly positive," an accounting identity of crowd behavior, not a trade).

## 3. A4 (flow/ADV) — DEAD as a flow signal

Suspension-clean portfolio +0.38% h5 (≈ breakeven net). FM vs controls β = −0.09% (t=−1.68); vs
controls+accel β = −0.13% (t=−2.26). Its celebrated subperiod stability is just a smoother
normalization of the flow-level variable, which is itself non-incremental once acceleration is
controlled. **Bucket: DEAD.**

## 4. Interaction search (small declared tree) — nothing passes

UP3c × acceleration × liquidity × volatility × flow-direction: no branch met the kill rule. The most
informative cells: UP3c + accelerating flow + bottom-liquidity = **−0.81% h5** (chase into
illiquidity is the worst pocket in the dataset); UP3c + flow-neutral = +0.72%. Discipline note: the
tree was capped at the predeclared branches; no further explosion was attempted.

---

## 5. THE SURVIVOR — a risk filter, not an entry

**C. AVOIDANCE / RISK FILTERS — "platform outflow into strength"**

- **Definition:** on a day with `ret1 ≥ +3%` (suspension-clean event), the retail-platform net-flow
  z-score (trailing 60-session PIT) is ≤ −0.5 — price rising while platform flow is materially
  *selling*. Downstream returns: **h5 −0.44%, h10 −0.76%, h20 −0.50%** (n = 1,529; ≈ 3.8 events/day).
- **Stability — the only 4/4 in either sprint:** the avoid-spread vs flow-neutral up-moves by
  half-year: **−0.52% (25H1), −0.98% (25H2), −1.76% (26H1), −3.09% (26H2)** — negative in all four,
  monotonically deepening. No other candidate construction in two sprints achieved 4/4.
- **Why it might be real:** price pumped while the platform crowd is net-exiting is the classic
  signature of distribution into strength (operators unloading to slower hands, or informed exit);
  the platform flow variable cannot identify *who* is selling (program rule: never interpret
  `investor_type`/brokerage ownership as end-investor identity), but the *divergence itself* is the
  information. It is also consistent with everything else found: chase (flow-with-move) is flat,
  flow-against-move is toxic.
- **What could make it spurious:** the window is only 20 months and the marker's economic depth grew
  over time (may be a 2026-regime artifact with 2025 noise); the z-score threshold −0.5 is one point
  on a continuum (adjacent thresholds not re-tuned post hoc — that would be tuning); flow measurement
  is Stockbit-platform-specific; suspension-clean applied, but the canvas survivorship caveat applies
  to every cell equally.
- **What it is NOT:** an entry signal (the filtered entry book — UP3c ex-selling — gains only +12bp
  vs the parent: not enough to matter), and not a short strategy (out of scope, long-only program).
  Its value is **avoidance**: do not buy, and consider exiting, positions showing a ≥+3% day *with*
  heavy platform outflow. It is a veto overlay for existing long logic (e.g., the fast-mover book).
- **Minimum additional evidence before it could become a registered (filter-amendment) hypothesis:**
  1. A named parent strategy to amend (a filter has no standalone meaning);
  2. A frozen spec: z-window (60), threshold (−0.5), event definition (ret1 ≥ +3%), treatment of
     missing-flow days, universe and liquidity floor, PIT gates;
  3. **Prospective forward data as the only clean OOS** — flow exists only from 2025-01 and the
     2025-26 canvas is in-sample for discovery; there is no historical holdout. A pre-declared
     prospective window (e.g., 8-12 weeks of live capture) with the spread sign intact;
  4. Power/MDE for the spread at the achieved daily event rate;
  5. The decision rule (what filter outcome triggers what portfolio action) fixed in advance.

---

## 6. The four buckets (required output)

**A. SURVIVORS (entry edges):** **none.** No candidate from either sprint survived the adversarial
pass as a robust, executable, net-positive entry edge.

**B. CONDITIONAL EDGES:** **none pass the predeclared rule.** The nearest misses are documented
(UP3c + accel + top-liquidity at +28bp incremental vs the +30bp bar, n=746 — noted for completeness,
explicitly not promoted).

**C. AVOIDANCE / RISK FILTERS:** **platform-outflow-into-strength** (§5) — the one survivor, as a
veto overlay. Secondary, weaker filter candidates (documented, NOT promoted): down-move +
capitulation (h5/h10/h20 consistently negative: −0.77/−0.89/−0.86%) — spread unstable across halves;
down-move + accelerating sell flow (−1.25% h5, small n).

**D. DEAD:** UP3 (six kills, §1); A5 (§2); A4 (§3); raw-flow z; broker concentration/persistence/
bandar labels (first sprint, unchanged by this pass); all absorption constructions; all intraday
constructions.

---

## 7. What this pass could NOT solve (stated plainly)

1. **Survivorship is structural, not fixable retrospectively.** The store is a current-roster backfill
   (zero dropouts since 2025-01). Any historical result on this canvas — including the survivor
   filter — carries unknown upward bias. The delisting-hazard bound (§1 K6) brackets UP3; the same
   bound applies qualitatively to every candidate.
2. **No clean historical OOS exists for flow signals.** Flow data begins 2025-01; everything
   flow-based is in-sample by construction. Only prospective capture can produce a true holdout.
3. **Single-market, single-regime sample.** 2025-2026 contained one full drawdown cycle (2026H1);
   all conclusions are one-market, one-regime, twenty months.
4. **The 2026-09-15 pre-open `ohlcv` rows** (flagged in the first sprint) remain in production
   pending owner cleanup; excluded here by the canvas cap.

---

## 8. Discipline statement

Every number above is exploratory. Kill rules were declared before their respective runs; no surface
cell was promoted after inspection; no p-value was used as a selection device; the registry is
untouched; nothing is registered, executed, or authorized.

```json
{
  "pass": "ADVERSARIAL-PM-2026-09-15",
  "entry_edge_survivors": [],
  "conditional_edge_survivors": [],
  "avoidance_filter_survivors": ["platform-outflow-into-strength (up-move & nbz<=-0.5, 4/4 halves)"],
  "dead": ["UP3", "A5", "A4", "raw-flow", "broker-family", "absorption", "intraday"],
  "registration_actions": "none",
  "next_action": "owner review"
}
```
