# FWD-PM-FADE-001 — PROTOCOL (REGISTERED 2026-09-21 · HYP-PM-0012 · D-052)

**Status:** REGISTERED → IN_TESTING. **Family:** P-M · Price-Reversal {R1} (member 1).
**Registered:** 2026-09-21T01:46:55+00:00 under DECISION_LOG **D-052** (Owner Option A,
`OWNER_DECISION_PACKAGE_R1_OPEN_2026-09-21.md`); forward test **FWD-PM-FADE-001 OPEN** —
`ledger.json` opened empty, first eligible entry 2026-09-22. Sections 1–9 unchanged from the
2026-09-20 v1 freeze. (Pre-registration history: candidate for a **new family** — P-M had no
existing family covering short-horizon reversal patterns as an anti-edge, §6 — documented as a
completed pre-registration package frozen before any forward observation.)

**Drafted:** 2026-09-20 · **Spec frozen:** 2026-09-20 v1 (section 2 + `scripts/fade_failed_breakdown.py`, SHA256SUMS)
**In-sample reference run:** 2026-09-20, local settled DB (data through 2026-07-29), output in §1

## 0. What this is, and what it is not

This tests whether the **"failed breakdown"** pattern — price sweeps intraday below the
trailing 20-session low, then closes back **above** it — is followed by **negative** forward
excess returns on the liquid IDX universe, net of cost. This setup is widely read by retail and
technical traders as a bullish reversal ("stop hunt", "spring", "shakeout": price fakes out the
weak hands below support, then reclaims it, and "should" rally). The empirical claim is the
opposite: buying this setup loses money, reliably.

**It is not a novel discovery invented from nothing.** The pattern is a documented category in
technical-trading and behavioral-finance literature — naive chart-pattern rules that traders
believe are bullish reversals, but which underperform once measured net of cost against a fair
benchmark, consistent with crowd-following/overconfidence effects arbitraging away exactly the
patterns popular enough to be widely taught. What is specific to tonight's work is the IDX
measurement.

**It is not a standalone long or short strategy.** No entry is proposed on this signal. The
tradeable form — if this test confirms — is an **allocation-level avoidance/exit overlay**
(don't buy, or exit, a name flagged by this signal) applied to some other system, most directly
`FWD-PM-REGIME-002`. That application is explicitly **out of scope for this document** and
requires its own step later, for the reason given in §6: this is exactly the two-stage structure
`BOOK_OVERLAY_POLICY.md` already established for volatility exclusion — measure the effect on
its own first (`FWD-PM-VOLEX-001`), only adopt it into an overlay after it has independent
standing. A fresh in-sample search result does not skip that step (`BOOK_OVERLAY_POLICY.md` §4
explicitly rejected five other same-session filters for exactly this reason).

**Honest lineage.** This pattern was found via `docs/research_programs/P-M/pattern_scan/
PATTERN_SCAN_2026-09-17.md` (arm P3a of `scripts/patterns.py`), one of roughly twelve
exploratory arms scanned in that session (§6). The mechanism argument above is not blind to the
result — it is a post-hoc plausibility case for an effect discovered by search, exactly the same
epistemic position `HYP-PM-0010`'s trend mechanism was in. It carries full multiplicity debt and
earns nothing until the forward test in §3 clears its bar.

## 1. Evidence being pre-registered (IN-SAMPLE, no confirmatory weight)

Three independent measurements of the same signal, quoted together because the agreement across
methodology is itself part of the evidence:

| measurement | fill convention | benchmark | h=5 | h=20 | h=20 ex-2025 |
|---|---|---|---|---|---|
| original scan, `patterns.py` §1 | signal-bar **close** | IHSG | −1.20%, t −9.90 | −1.51%, t −5.96 | −1.94%, t −7.15 |
| original scan's own self-audit, §7 | **next-open** (corrected) | EW liquid book | −1.17%, t −12.24 | −1.53%, t −7.98 | — |
| **this draft**, independent rebuild, next-open, dual benchmark | **next-open** | IHSG | −1.14%, t −8.91 | −1.46%, t −5.64 | −1.88%, t −6.80 |
| **this draft**, same rebuild | **next-open** | EW liquid book | −1.05%, t −11.94 | −1.47%, t −8.20 | — |

This draft's script was written independently from the original scan's pipeline (a fresh
SQL pull, a fresh feature build, no shared intermediate files) specifically to check whether a
from-scratch rebuild would surface a hidden defect — exactly the check that took
`FWD-PM-TREND-001` from +63% down to a corrected small-negative number over four revisions
earlier this session. It did not: three independently-built measurements agree within about
0.1–0.3 percentage points and the same order of statistical significance. This is the most
corroborated result in the P-M program to date.

v1 full output:

```
signal   : 12,131 candidate signals, 1,151 distinct dates, 757 distinct tickers
           top ticker CMNT = 72 signals (0.6% of total)
 h     N  exc_vs_IHSG%  t_IHSG  N_ewb  exc_vs_EWbook%  t_EWbook
 5 12114         -1.14   -8.91  12114           -1.05    -11.94
10 12090         -1.35   -6.91  12090           -1.26     -9.94
20 12015         -1.46   -5.64  12015           -1.47     -8.20
ex-2025 h=20 vs IHSG: N=9939  exc -1.88%  t -6.80
```

Concentration check (the lesson of `PATTERN_SCAN_2026-09-17.md` §5 — single-ticker validation
is worthless on this corpus): 757 distinct tickers contributed signals; the top ticker (CMNT)
supplied 0.6% of the total. This is not a small-N or single-name effect.

Robustness already established by the original scan and carried forward, not re-run here:
detector invariance across six wedge-adjacent strictness definitions was not applicable to this
specific arm, but the ticker-demeaned panel test was — removing each ticker's own mean moves the
failed-breakdown estimate from −1.51% to −1.02% (t −3.97), still significant (§5 of the scan).

## 2. Frozen specification

| | |
|---|---|
| universe | **per-row threshold gate**, evaluated independently each session (no ticker-level membership set — structurally immune to the sticky-universe defect found in `FWD-PM-TREND-001`): `adv20 >= Rp 1e9` (20-session mean of close×volume, shifted 1, min_periods 15), `close >= Rp 50`, `>= 25` prior sessions, `volume > 0` on the row, **>= 18 of the trailing 20 sessions traded** (`nz20`) |
| signal | `low(t) < lo20(t)` **and** `close(t) > lo20(t)`, where `lo20` is the prior-20-session rolling low, shifted 1 (known at t); evaluated on the full per-ticker calendar frame — no row is ever dropped before a rolling window is computed |
| entry fill | **next session's open** — the signal bar's close is not knowable until it is set and cannot be traded (the bias `PATTERN_SCAN_2026-09-17.md` §7 found and corrected; inherited here from the start rather than found again) |
| exit fill | close of session `entry + h − 1`, for `h ∈ {5, 10, 20}` — a fixed-horizon holding period, not a rule-based exit (this is an event study, not a position book) |
| costs | 0.60% round trip, the repo cost authority (`engine/exits/costs.py` basis, same convention as every other frozen spec in this program) |
| contamination guard | a signal is voided if any session in its holding window has `|ret| > 35%` or a recorded split — reused verbatim from `panel.py`'s `bad`/`badh` convention, already validated by three independent implementations reproducing the same numbers |
| benchmark, **dual, both required** | (a) IHSG, entered/exited on the identical next-open/h-close convention; (b) an equal-weight liquid book (mean forward return of every `liq`-eligible name under the identical convention, per calendar date) — declared dual because IHSG alone is known generous: liquid IDX stocks beat IHSG by roughly +0.35%/20d unconditionally, which would understate this signal's true magnitude if IHSG were trusted alone |
| inference | one-way entry-date-clustered t-statistic (`cluster_t`, identical formula to `forward_regime/scripts/panel.py`, reused verbatim not reimplemented) |
| direction | this is a **fade/avoidance** signal, not a long entry: the registered claim is that forward excess is **negative** |

Frozen implementation: `scripts/fade_failed_breakdown.py` (sha256 in `scripts/SHA256SUMS.txt`).
Section 2 and this file's constants are closed. Any change requires a new dated superseding
entry.

## 3. Endpoint and decision rule

**Primary endpoint:** per-signal excess return at h=20 sessions, **against both benchmarks**,
with one-way entry-date-clustered standard errors. Both benchmarks must clear their bar
independently — one significant benchmark and one null is not sufficient (the whole point of
carrying two benchmarks is that IHSG alone is known generous).

Because this signal fires far more often than a trend entry (≈200/month, ≈95% of trading days
carry at least one signal), the *number of trading days* forward, not calendar time, is what
governs power — but clustering by entry date, not by individual signal, means the effective
sample size is the count of **distinct dates**, not the much larger signal count. §3.1 derives
the cadence below from that constraint rather than assuming high signal frequency implies fast
power (it does not, once clustering is accounted for).

- **3 months (interim):** observability only, no decision. Expected clustered dates ≈ 63; even
  under the full in-sample effect size this is under-powered on the binding (IHSG) benchmark.
- **12 months:** PROMOTE-track requires **t < −2.5 on IHSG AND t < −2.5 on EW-book**, and
  cumulative excess negative against both.
- **18 months (final):** PROMOTE requires **t < −3.0 on both benchmarks**.
- **REJECT** at any checkpoint if cumulative excess turns positive against either benchmark, or
  if fewer than 100 distinct signal-dates have accumulated by month 12 (dead-signal guard).

### 3.1 Power / MDE (derived for THIS spec, not inherited)

From the frozen h=20 in-sample run, treating the observed effect as the planning basis and
solving `t(G) ≈ d·√G` for the per-cluster standardized effect `d`:

| benchmark | in-sample t (G≈1,151) | implied d | G needed for t=2.5 | ≈ months* |
|---|---|---|---|---|
| **IHSG (binding)** | −5.64 | −0.166 | 226 | **11.4** |
| EW-book | −8.20 | −0.242 | 107 | 5.4 |

*at ≈20.0 effective trading days/month (1,151 signal-bearing dates of 1,216 total sessions in
the in-sample window).

**IHSG is the binding constraint**, not EW-book — the more generous-looking benchmark is
reached with power far sooner. The 12-month checkpoint (§3) sits almost exactly at the date
count needed to reach t=2.5 on IHSG *if the true effect matches the in-sample estimate exactly*;
per R2, that means this test is genuinely capable of failing to promote at 12 months even under
a faithfully-replicating effect, and a null result there is informative, not just underpowered
noise. The 18-month final checkpoint requires the IHSG effect to hold up to t=3.0, needing
≈326 clustered dates (≈16 months) — 18 months leaves a modest margin.

## 4. Expectations, stated in advance

In-sample: h=20 excess ≈ −1.46% (IHSG) / −1.47% (EW-book), both t < −5.6. Ex-2025, the read
strengthens against IHSG (−1.88%, t −6.80), the opposite direction from most patterns in this
program's history (most in-sample effects concentrate in and shrink outside 2025 — this one
does not, which is itself worth tracking as a forward falsification trigger, §5.3).

**Decay haircut, pre-declared:** in-sample discovery, ~12-arm exploratory search (§6). If
forward h=20 excess against IHSG runs weaker than **−0.5%** by the 12-month checkpoint even
without formally rejecting on t, treat it as decayed/optimistic in-sample estimation, not a
confirmation deferred.

## 5. Falsification conditions (pre-declared)

1. Cumulative excess >= 0 against either benchmark at any checkpoint (§3).
2. Forward |t| against IHSG below 1.5 at the 12-month checkpoint (meaningfully underpowered
   relative to the §3.1 plan; continue to 18 months but do not treat 12-month silence as
   confirmation).
3. Effect concentrated in one calendar year or one sector (no year or GICS-equivalent sector
   contributing > 50% of total excess) — the direct successor to the single-ticker-trap lesson
   of `PATTERN_SCAN_2026-09-17.md` §5, applied at the year/sector level since ticker
   concentration is already ruled out in-sample (§1).
4. The 2025-inflation pattern reverses — i.e., forward excess through 2026+ turns out to be
   *weaker* than the ex-2025 in-sample read (−1.88%), the opposite of what §4 states as expected
   — a specific, checkable prediction, not just "if it gets worse."
5. Fewer than 100 distinct signal-dates by month 12 (liquidity/volume regime shift; dead-signal
   guard, mirrors the convention used across every other frozen spec in this program).
6. A membership/liquidity re-derivation against the real IDX80 history (rather than the ADV20
   threshold proxy) materially changes which names qualify — re-verify before any operational
   use, per the same limitation carried in every other spec in this program.

## 6. Multiplicity accounting and family scope — stated honestly

- **Multiplicity.** The discovery session (`PATTERN_SCAN_2026-09-17.md`) measured roughly
  twelve independent pattern arms plus six wedge-strictness variants (eighteen total) on one
  corpus. This draft is the strongest surviving arm by both magnitude and significance, and the
  **only** arm that has since been independently rebuilt from scratch and reproduced (§1). Even
  under a crude Bonferroni correction for eighteen trials (α = 0.05/18 ≈ 0.0028, two-sided
  z ≈ 2.99), the in-sample t of −5.64 to −8.91 clears the bar comfortably — unusual for this
  program, where most surviving results sit close to their threshold, not far past it.
- **Family scope — open question for the Owner act.** This does not fit any existing P-M
  family. It is not `{I5,I6,I7,I12}` (no broker/flow instrument), not the C-family (no
  conduit/breadth construct), not `Price-Trend {T1}` (this is a reversal/anti-momentum pattern,
  the structural opposite of a trend feature — widening {T1} to cover it would be the kind of
  irreversible, ill-fitting widening `RESEARCH_PROGRAM.md` §2.1 warns against). A new family —
  candidate name **Price-Reversal {R1}** — is proposed but not assumed; the Owner act that
  registers this draft must rule on it explicitly, the same way `Price-Trend {T1}` was opened at
  `HYP-PM-0010`'s registration (D-028, PG-3).
- **Relationship to `FWD-PM-REGIME-002` and `BOOK_OVERLAY_POLICY.md` — explicitly not amending
  either.** This test's ledger is entirely separate from 002's. No entry-suppression or
  exit-acceleration logic is wired into 002 by this document. Per the precedent
  `BOOK_OVERLAY_POLICY.md` §4 already set for volatility exclusion — an overlay is adopted only
  once its effect has *independent* standing, not merely a same-session search result — any
  future overlay built on this signal requires FWD-PM-FADE-001 to clear a checkpoint in §3
  first. `BOOK_OVERLAY_POLICY.md` §4 explicitly rejected five other same-session filters for
  lacking exactly that independent standing; this document does not ask for an exception.

## 7. Registration elements (program §5.2 checklist)

| element | value |
|---|---|
| mechanism | documented technical/behavioral-finance category: naive "stop-hunt reversal" chart patterns attract uninformed buying and underperform once measured net of cost against a fair benchmark; no IDX-specific microstructure channel claimed beyond that the pattern is popularly followed here too |
| directional prediction | negative forward excess return following the signal, against both IHSG and an equal-weight liquid book, at h=5/10/20 |
| null | excess return = 0 (both benchmarks) |
| scope | IDX liquid universe (`adv20 >= Rp 1e9` threshold, per-row, no membership set), next-open fill, fixed 5/10/20-session holding periods, 2021-07-05 onward |
| effect_size_floor | forward h=20 excess vs IHSG weaker than −0.5% by month 12 = decayed (§4 haircut); §3.1 power: t < −2.5 on IHSG needs ≈226 clustered dates (≈11.4 months) even under a faithfully-replicating effect — the test can fail |
| multiplicity_family | proposed **Price-Reversal {R1}** (new) — pending Owner ruling on family scope (§6); this draft consumes no slot |
| refutation condition, one sentence | if forward excess against IHSG and the equal-weight liquid book fails to stay significantly negative (t < −2.5) by month 12 and t < −3.0 by month 18, the anti-edge does not replicate out of sample and this draft dies |

## 8. Limitations, stated rather than buried

1. In-sample discovery via an 18-arm exploratory scan (§6); §3 thresholds are the only
   pre-committed inference.
2. Mechanism is post-hoc plausibility reasoning for a search-discovered pattern, not a
   blind-authored prediction (§0) — carried honestly, not concealed.
3. No dedicated split-continuity audit has been run for this specific ADV20-threshold universe
   (the kind done for `FWD-PM-TREND-001`'s top-80 hygiene list); the `|ret| > 35%` contamination
   guard is the only defense, and it is the same guard whose adequacy was already demonstrated
   by three independent implementations converging on similar numbers (§1) — but a dedicated
   audit is still owed before this is trusted at the same level as a hygiene-audited spec.
4. This is a fixed-horizon event study, not a rule-based exit system; no claim is made about
   optimal holding period, only that 5/10/20 sessions all show the same sign and rough
   magnitude.
5. No standalone trading application is proposed (§0); the eventual overlay use is unscoped
   pending both this test's own result and a separate design decision about *how* to apply it
   (suppress new entries only, or also accelerate exits of existing positions) — deliberately
   left open rather than pre-answered here.
6. Universe is the same ADV20-threshold proxy used by `FWD-PM-REGIME-002`, not real IDX80
   membership history; carries the same re-derivation-before-operational-use limitation as every
   other spec in this program (§5.6).
7. Costs are the repo authority, not broker-quoted; unchanged from every other spec here.

## 9. Provenance

- Data: local settled DB `data/walkforward.db`, `ohlcv.is_final=1`, data through 2026-07-29.
- Spec script: `scripts/fade_failed_breakdown.py` · SHA256SUMS: `scripts/SHA256SUMS.txt`
- Discovery source: `docs/research_programs/P-M/pattern_scan/PATTERN_SCAN_2026-09-17.md`
  (arm P3a, `scripts/patterns.py`), including its own self-audit (§7 there) which independently
  found and corrected the same close-fill bias this draft's script avoids from the start.
- Precedent for the overlay/hypothesis separation in §6: `BOOK_OVERLAY_POLICY.md`
  (`FWD-PM-VOLEX-001`'s relationship to it).
- Session record: reviewer-directed audit, 2026-09-20 — this draft exists because the reviewer
  who found and fixed four defects in `FWD-PM-TREND-001` the same session was asked to check
  whether the pattern-scan's negative results would survive the same treatment; they did (§1).
