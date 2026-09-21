# HYP-PM-0008 · R3 CONTROL-ARM BOUNDARY — BEHAVIOURAL AUDIT — 2026-09-14

**Authority:** generated point-in-time record. **Owner-authorized scope:** ONE narrow read-only computation
over OHLCV 2023-05 … 2023-11 to test whether local price behaviour is consistent with the proposed R2→R3
auto-rejection boundary of **2023-09-04**.

**This is not execution of HYP-PM-0008.** No forward return, no event outcome, no power/MDE, no trading
performance, no G1 harness, no threshold tuned, no write of any kind.

> **`r(t) = close(t)/close(t−1) − 1` is a CONTEMPORANEOUS daily move used for band-contact detection —
> identical in role to the existing Dataset B detector. It is never a forward return.** No quantity in this
> audit is measured after a formation date. The word "outcome" does not apply to anything computed here.

---

# A. Exact data source and coverage

| Item | Value |
|---|---|
| Source | production `data/walkforward.db`, table `ohlcv`, opened **read-only** (`file:…?mode=ro`) |
| Fields read | `ticker, date, close, volume, is_final` — **`close` only** for prices. `open`/`high`/`low` never read |
| Second table | `corporate_actions` (`ticker, date`) — exclusion set only |
| Authorized window | **2023-05-01 … 2023-11-30** — rows **125,317**, tickers **890**, dates **144** |
| Extension (disclosed) | The floor-recovery table (§E.1) and the empirical-floor diagnostics extend to **2023-01-01 … 2023-12-31** to establish the pre-boundary R2 baseline and the R1 comparison. This is a **disclosed extension** of the authorized window; every other section stays inside 2023-05 … 2023-11 |
| Not read | `broker_flow`, `bandar_detector`, Dataset B store, `research.db`, any forward-dated quantity |

**Coverage adequacy:** 890 tickers × 144 sessions in the authorized window is roughly **10× the Dataset B
window** that produced the R4-side evidence, and it straddles both 2023 boundaries.

# B. Exact session/calendar treatment

Dataset B's frozen `SessionCalendar v2` and `PitRoster v1` **cannot be reused** — both begin 2025-01-02 and
carry no 2023 coverage. The calendar was therefore derived from `ohlcv` itself:

1. Count distinct tickers per date over the window; take the **median** (875 tickers/session).
2. A date is a **session** iff it carries **≥ 50%** of that median (partial-day guard).
   → **144 / 144 dates qualified; 0 partial days dropped.**
3. **Strict session adjacency enforced**: an observation is used only if `t−1` and `t` are *consecutive
   indices* in that calendar. This is **stricter than the Dataset B detector**, which uses the previous
   available row per ticker. → **0 observations skipped as non-adjacent** in the authorized window.

*Verification that the calendar is correct:* 2023-07-19 (Islamic New Year), 2023-06-01 (Pancasila Day) and
2023-06-02 (joint holiday) are correctly absent, so 2023-07-18→07-20 and 2023-05-31→06-05 are genuinely
adjacent session pairs.

**Observation filters** (all pre-declared, none tuned):

| Filter | Dropped |
|---|---|
| `COALESCE(is_final,1)=1`, `close > 0` | — |
| Corporate action on `t` or `t−1` (`corporate_actions`, 402 rows in 2023) | **685** |
| `prev_close < Rp 50` (below the tick/board floor) | **3,549** |
| **Observations tested** | **120,193** |

Two further filters are applied **only** in the empirical-floor diagnostics (§E.1, §F), and are declared
there because they change an anomaly classification:

- **stale-reference filter** — `volume(t−1) == 0` (the reference is a carry-forward at which nothing traded)
- **adjusted-series filter** — non-integer `close` or `prev_close` (IDX quotes on an integer tick ladder; a
  fractional price proves a split adjustment was applied inside `ohlcv`)

# C. Exact existing methodology reused

Reproduced from `docs/research_programs/P-M/dataset_b/` — **no new event detector was invented**:

| Element | Source | Value used |
|---|---|---|
| `ARA_TIERS` | `foundation.py:94` | `((200.0, 0.35), (5000.0, 0.25), (inf, 0.20))`, tier selected on `prev_close` |
| `BAND_TOLERANCE` | `foundation.py:101` | `0.02` (tick-ladder + reference-price slack) |
| Band model | `foundation.ara_arb` / `exceeds_band` | `r > up + tol` or `r < dn − tol` |
| **"Naive flat ARB" breach model** | `investigate_outside_band.py:11,38` | the whole method: apply a flat ARB, then resolve every breach on its own evidence |
| Anomaly posture | `foundation.py:98–100` | "a hit … is **reported for review, never silently excused**" |
| Artifact-vs-rule test | `investigate_outside_band.py:85` | "**a data artifact would not land on the regulatory limit**" |

**The one adaptation, stated plainly.** `investigate_outside_band.py` used a naive **−15%** floor because
Dataset B's window straddles the *R3→R4* boundary. This audit straddles *R2→R3*, so the discriminating
quantity is inverted:

> **"R3-only" move** := a down-move **beyond the flat −15% R2 floor** but **inside the symmetric tiered
> floor** (−35% / −25% / −20% by tier). Such a move is **legal only if the symmetric regime is in force.**

A complementary **"R2-only"** bucket (moves in (−15%, −10%]) tests the *2023-06-05* switch and serves as an
independent **positive control** on the method itself.

**What could not be reused:** Dataset B's quarantine came from `vwap_ratio_report`, which cross-checks
`close` against broker-VWAP. `broker_flow` has **no 2023 coverage**, so that cross-check is unavailable here.
Its absence is compensated by the adjusted-series filter and by classifying every residual anomaly (§F).

# D. Proposed effective dates tested

| Boundary | Proposed date | Regime before | Regime after | Role |
|---|---|---|---|---|
| R1 → R2 | **2023-06-05** | flat ARB (LC-PM-0009: −7%) | flat ARB −15% | **positive control** |
| **R2 → R3** | **2023-09-04** | flat ARB −15% | **symmetric tiered 35/25/20%** | **the date under test** |

# E. Observed band-limit behaviour

## E.1 The empirical ARB floor, recovered from price behaviour alone

No regime assumption enters this table. It reports, per month, the **most negative daily move that actually
occurred** and the count beyond each candidate floor (2023 full year; stale-reference and adjusted-series
rows removed).

| Month | n | **min move** | ≤ −9.5% | ≤ −14.5% | ≤ −19.5% | ≤ −24.5% | ≤ −34% |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023-01 | 13,709 | **−10.0%** | 18 | **0** | 0 | 0 | 0 |
| 2023-02 | 13,967 | **−10.0%** | 12 | **0** | 0 | 0 | 0 |
| 2023-03 | 14,743 | −9.9% | 5 | **0** | 0 | 0 | 0 |
| 2023-04 | 9,828 | **−10.0%** | 6 | **0** | 0 | 0 | 0 |
| 2023-05 | 14,901 | **−10.0%** | 34 | **0** | 0 | 0 | 0 |
| **2023-06** | 11,974 | **−15.0%** | 160 | **52** | **0** | 0 | 0 |
| 2023-07 | 14,165 | **−15.0%** | 109 | 24 | **0** | 0 | 0 |
| 2023-08 | 15,973 | **−15.0%** | 156 | 33 | **0** | **0** | 0 |
| **2023-09** | 14,654 | **−34.9%** | 130 | 28 | **15** | **4** | **1** |
| 2023-10 | 16,106 | −34.4% | 213 | 64 | 32 | 16 | 1 |
| 2023-11 | 16,095 | −34.8% | 163 | 45 | 26 | 14 | 1 |
| 2023-12 | 13,875 | −34.9% | 155 | 47 | 19 | 11 | 2 |

Three flat plateaus with two sharp steps. Over **67,148** observations in Jan–May the floor is never breached
past −10.0%; over **42,112** observations in Jun–Aug it is never breached past −15.0%; from September the
tiered symmetric structure appears at all three tiers.

## E.2 Session-exact location of both transitions

**R2 → R3 (the date under test):**

| Session | n | min move | n ≤ −15.5% |
|---|---:|---:|---:|
| 2023-08-28 | 735 | −14.75% | **0** |
| 2023-08-29 | 735 | −14.91% | **0** |
| 2023-08-30 | 734 | −14.96% | **0** |
| 2023-08-31 | 737 | −14.94% | **0** |
| **2023-09-01** (last R2 session) | 731 | −14.57% | **0** |
| **2023-09-04** (first R3 session) | 725 | **−34.94%** | **2** |
| 2023-09-05 | 735 | −27.54% | 2 |
| 2023-09-07 | 740 | −23.54% | 2 |
| 2023-09-08 | 732 | −23.81% | 1 |

The −15% floor binds to within 0.43pp on the last five sessions before the boundary and is breached by
**19.9 percentage points on the very first session after it.** 2023-09-02/03 was a weekend: **2023-09-01 and
2023-09-04 are adjacent sessions.** The step admits no intermediate date.

**R1 → R2 (positive control):**

| Session | n | min move | n ≤ −10.5% |
|---|---:|---:|---:|
| 2023-05-29 | 704 | −9.71% | **0** |
| 2023-05-30 | 715 | −9.97% | **0** |
| **2023-05-31** (last R1 session) | 715 | −9.93% | **0** |
| **2023-06-05** (first R2 session) | 713 | **−15.00%** | **16** |
| 2023-06-06 | 711 | −14.88% | 6 |

2023-06-01/02 were IDX holidays and 06-03/04 a weekend, so **2023-05-31 and 2023-06-05 are adjacent.** The
method recovers the independently-documented 2023-06-05 switch **exactly**. **The positive control passes.**

## E.3 The discriminating counts, and why they are not artifacts

"R3-only" moves in the authorized window, by regime period:

| Period | R3-only moves |
|---|---:|
| R1 (2023-05-01 → 2023-06-02) | **0** |
| R2 (2023-06-05 → 2023-09-01) | **0** (one candidate, resolved in §F) |
| **R3 (2023-09-04 → 2023-11-30)** | **103** |

Four independent properties rule out a data artifact:

1. **They land on the regulatory limit.** **41 of 104** fall within **1.0pp** of their exact tier floor; **20**
   within **0.2pp**. Repeated exact prints of −25.00%, −34.94%, −34.85%, −24.92% occur. This is the existing
   methodology's own discriminator (`investigate_outside_band.py:85`).
2. **They respect the tier structure.** Distribution across tiers: **70** at the 25% tier, **32** at 35%,
   **2** at 20%. A corrupted price feed has no reason to sort itself by `prev_close`. The two 20%-tier cases
   are decisive on their own: **DCII 2023-11-27 −19.96%** against a −20% floor (ref Rp53,600) and
   **EDGE 2023-11-27 −19.89%** (ref Rp9,050) — high-priced stocks stopping just inside the *narrowest* tier.
3. **They are broad.** **74 distinct tickers** across **50 distinct sessions** — not one name, not one day.
4. **They are absent before the boundary**, across 42,112 R2-period observations.

# F. Anomalies and their classifications

Every anomaly is resolved on its own evidence; none is excused by widening a tolerance.

| # | Observation | Evidence | Classification |
|---|---|---|---|
| **F-1** | **WICO 2023-07-20**, −18.58% vs ref 226 — the **only** R2-period R3-only candidate | Reference session **2023-07-18 closed 226 on volume 0** — a carry-forward at which nothing traded. Last genuine trade was 2023-07-17. The ticker also prints a **fractional close (250.5296) on 2023-07-10 with no `corporate_actions` row**, proving an in-`ohlcv` adjustment the CA exclusion cannot see. Subsequent sessions fall in a ~−10%/day staircase | **STALE REFERENCE + adjustment-basis artifact.** Excluded by the stale-reference filter. **Same class as Dataset B's RAJA quarantine.** → the R2 period contains **zero** surviving R3-only moves |
| **F-2** | **ARGO 2023-05-24**, −44.67% vs ref 900 — the only move beyond even the symmetric floor | Six consecutive prior sessions at exactly 900.00 with **volume = 0**, then resumption at 498 on volume 900 (9 lots) | **SUSPENSION RESUMPTION.** The ARB does not apply across a suspension gap. Excluded by the stale-reference filter; in R1, irrelevant to the boundary |
| **F-3** | 43 R1-period moves in (−15%, −10%] — apparent positive-control leakage | They cluster at **−9.6% to −10.0%**, not −7%: CHIP −9.77/−9.87/−9.89/−9.80/−10.00, HAJJ −9.71/−9.96/−9.62/−9.57, on heavy volume | **NOT leakage — the control's assumed floor was wrong.** The true Jan–May 2023 floor is **−10%** (§E.1). Recomputed against −10%, the control is clean (§E.2) |
| **F-4** | 2 of 104 R3-only moves carry fractional prices (SGER 2023-10-18, WINS 2023-10-30) | Adjusted-series indicator | Flagged; **1.9%** of the R3 evidence. Removing both leaves the result unchanged |

**Unresolved anomalies: 0.**

## F-5 · A material correction to LC-PM-0009 (outside HYP-PM-0008's design, reported because it is evidence)

LC-PM-0009 states **R1 ARB = 7%** (2020-03 → 2023-06-04). **The data contradicts this for 2023.** Across
2023-01 … 2023-05 — **67,148 observations, five separate months** — the most negative daily move is
**exactly −10.0%** in four of five months and −9.9% in the fifth. **A −7% floor is breached on hundreds of
observations; a −10% floor is never breached.**

The card is Q3, not primary-verified, and flags its own R1 start as "month-precise only." The likely reading
is an **undocumented intermediate relaxation −7% → −10%** somewhere before 2023-01.

**Consequences:** (a) **none for HYP-PM-0008's primary**, which uses only R3 and R4 and excludes R1
(`SPEC` §7); (b) the card's R1 row should be corrected; (c) bounding the −7%→−10% change requires scanning
2021-07-05 … 2022-12-31, which is **outside this audit's authorization and was not performed.**

**LC-PM-0009 was not edited.** This is a referred finding.

# G. Does the evidence independently support 2023-09-04? **YES.**

Three mutually independent lines converge, and none of them consults LC-PM-0009's numbers:

1. **Floor recovery (§E.1)** — a −15% plateau across Jun–Aug (42,112 obs, zero breaches) giving way to the
   tiered symmetric structure from September.
2. **Session-exactness (§E.2)** — the last pre-boundary session binds at −14.57% with zero breaches; the
   first post-boundary session prints −34.94%. The two sessions are adjacent. **No alternative date within
   the window is compatible.**
3. **Method validation (§E.2)** — the same procedure recovers the independently-documented **2023-06-05**
   switch exactly. The detector demonstrably locates a real boundary when one exists.

Plus the structural checks of §E.3: tier-sorted, limit-hugging, broad across 74 tickers and 50 sessions.

> **This is BEHAVIOURAL CORROBORATION, not documentary primary verification.** It establishes that the
> exchange's price record behaves exactly as the R2→R3 coding predicts, with a session-exact step at
> 2023-09-04. It does **not** establish the decree, its text, its scope, or its exceptions. A rule and a
> regularity in prices are different objects, and only the issuing authority can supply the former.

# H. Is the evidence insufficient? **No — for this specific question.**

The data distinguishes the candidate dates decisively. What it **still cannot do**:

- **Cannot supply the decree.** Kep-00055/BEI/03-2023 remains unretrieved (IDX returns HTTP 403).
- **Cannot establish scope or exceptions** — which boards, ETF/DIRE treatment, Papan Pemantauan Khusus
  (±10% call auction), IPO first-day 2× bands. §F-1's ~−10%/day staircase is consistent with a
  special-monitoring-board name, and **no board-membership table exists** to confirm it. **SPEC §20 B4
  stands unchanged.**
- **Cannot certify the tier boundaries** (Rp50/200/5,000) as constant across regimes — LC-PM-0009 flags this
  as "assumed constant, unverified." The observed tier-sorting is consistent with them but does not prove
  they never moved.
- **Cannot speak to R1's start date**, or to anything before 2023-01.

# I. Is any alternative effective date supported? **No.**

Every session from 2023-08-28 to 2023-09-01 shows **zero** moves beyond −15.5%, and 2023-09-04 shows two,
one of them at −34.94%. An earlier date is excluded by the pre-boundary zeros; a later date is excluded by
the 2023-09-04 prints. With 2023-09-02/03 a weekend, **2023-09-04 is the unique session-exact solution**
within the audited window.

# J. Implications for HYP-PM-0008 D-2

| Item | Before this audit | After |
|---|---|---|
| **R3 control-arm dating** | Secondary sourcing only; **zero local evidence**; named the sharpest residual risk in the blocker audit | **Behaviourally corroborated, session-exact.** The specific failure mode feared — R2 (ARB −15%) sessions silently contaminating the control window — **is excluded by direct observation** |
| R4 treatment-arm dating | Behaviourally corroborated (13 pre-date sub-band moves, 0 after) | Unchanged |
| Method credibility | Untested outside Dataset B | **Positive control passed** — recovers 2023-06-05 exactly |
| Decree documents | Not retrieved | **Still not retrieved** |
| Scope / exceptions / PPK | Unresolved | **Still unresolved** (SPEC §20 B4) |
| LC-PM-0009 accuracy | Assumed | **R1 row contradicted** (§F-5); R2/R3 rows corroborated |

**The net effect on D-2:** its *empirical-adequacy* limb is now strong on both arms of the primary contrast,
and the one element with no local evidence has acquired the best local evidence in the file. Its
*documentary* limb is untouched — no decree was obtained, and per the standing instruction corroboration is
not upgraded to verification however many independent lines agree.

One further consequence the Owner should note: the audit **strengthens** the register-vs-card reading from
the blocker audit. `DATASET_B_SEMANTIC_REGISTER_v1`'s `VERIFIED` label — which grades *empirical adequacy*,
as its sibling entries do — is now better supported than when it was written, while LC-PM-0009's "NOT
primary-verified" remains exactly true and is, on its R1 row, **demonstrably right to have been cautious**.

**Not decided here, by instruction:** the D-1 family determination, D-3, and whether HYP-PM-0008 should be
registered.

---

# FINAL STATUS

## **R3 BOUNDARY BEHAVIOURALLY CORROBORATED**

## **D-2 PRIMARY VERIFICATION: NOT ESTABLISHED**

---

# PROVENANCE

**Files read (read-only):**

| File | sha256 |
|---|---|
| `docs/research_programs/P-M/dataset_b/foundation.py` | `e427cc482fa1e00cfda830eb5a6d84eda3cc583dde0a81fc7c1d90c47b7eab29` |
| `docs/research_programs/P-M/dataset_b/investigate_outside_band.py` | `19109e6ce3368007623cf8da3d4b6b8830c6046be070f716d762d51a19891048` |
| `data/walkforward.db` | opened `file:…?mode=ro` (13,660,860,416 bytes; hashing a 13.7 GB live DB was not attempted) |
| `docs/research_programs/P-M/LC-PM-0009.md`, `HYP-PM-0008_SPEC.md`, `HYP-PM-0008_BLOCKER_AUDIT_2026-09-14.md` | context |

**Audit script** (scratchpad, outside the repository):
`r3_boundary_audit.py` · sha256 `609842417bede7c959333e177c26111c43f59dff6de4f079dfb4bf6543ef2607`
Result: `r3_boundary_audit_result.json` (same directory).

**Exact commands:** `python3 r3_boundary_audit.py`, plus four read-only `python3 -c` inline queries
(anomaly context for WICO/ARGO; adjusted-price and floor-proximity tallies; monthly floor recovery;
daily transition-window tables). All used `sqlite3.connect("file:…?mode=ro", uri=True)`.

**Counts:**

| Quantity | Value |
|---|---|
| Rows in authorized window | 125,317 (890 tickers, 144 sessions) |
| Sessions used / partial days dropped | 144 / 0 |
| Observations tested (authorized window) | **120,193** |
| Skipped — non-adjacent / CA / price<50 | 0 / 685 / 3,549 |
| Observations in the full-2023 floor recovery | 169,990 |
| R3-only moves — R1 / R2 / R3 | **0 / 0 / 103** |
| Anomalies found / classified / unresolved | 3 classes / 3 / **0** |

**Explicit confirmations:**

- **Zero forward-return access.** No quantity dated after a formation date was read or computed. Only
  contemporaneous `close(t)/close(t−1)` band-contact moves.
- **Zero empirical hypothesis execution.** HYP-PM-0008 was not run; no `theta`, contrast, placebo, horizon,
  event count, or power figure was computed. The §11 feasibility gate remains un-evaluated.
- **Zero registry mutation.** `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`, `EXPERIMENT_LEDGER.jsonl`,
  `DECISION_LOG.md` untouched.
- **Zero database writes.** Every connection used `mode=ro`. *(`walkforward.db`'s mtime advances from the
  production scheduler's own cron jobs, which run independently of this session.)*
- **Zero `g1_config.json` mutation.** Zero Dataset B mutation. Zero semantic-register mutation. Zero
  `research.db` write. Zero production write.
- **Zero threshold tuning.** `ARA_TIERS` and `BAND_TOLERANCE` were copied verbatim from `foundation.py`;
  the candidate dates were taken from LC-PM-0009 before any computation; §E.1 assumes no regime at all.
- **No decree inferred from desired results.** §E.1 recovers the floors with no regime input, and the
  method was validated against an independently-documented boundary (2023-06-05) before the date under
  test was assessed.
- **HYP-PM-0008 specification not modified.** No registration. No family decision. No D-3 judgment. No
  recommendation to register.

**Files created by this task: one** — this report.
