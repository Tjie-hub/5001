# I3 · S2 G-1 — OPEN-INTEGRITY RESULT

**Doc:** S2-PM-0004 · **Date:** 2026-08-25 · **Owner:** Claude
**Candidate:** I3 · overnight/intraday clientele decomposition — **CANDIDATE ONLY, NOT REGISTERED**
**Governed by:** `S2-PM-0003_G1_PREREGISTRATION.md`, sha256 verified before execution
**Artifacts executed:** the frozen originals, unmodified

---

# VERDICT: **FAIL**

**Triggered by rule F2**, verbatim from the frozen pre-registration:

> **F2** — `open == prev_close` rate, liquid stratum, S2 — **>= 50%**

**Observed: 51.94%.** Threshold 50%. **Rule fires. Stop rule engaged: no G-2, no universe
restriction applied.**

---

## 1 · Artifact verification

| Artifact | Placed at | Bytes | SHA-256 |
|---|---|---|---|
| Pre-registration | `D:\IDX\S2-PM-0003_G1_PREREGISTRATION.md` | 6,163 | `de2b728834464386199dcae41800bde1759dec96622a1ac925f37882b204031a` |
| Census script | `D:\IDX\g1_open_integrity_census.py` | 8,468 | `29892009f722f3640e6de372402ce7dd00368ba8675deb616dbea0c0d896dccb` |

**Expected pre-registration hash:** `de2b728834464386199dcae41800bde1759dec96622a1ac925f37882b204031a`
**Result: EXACT MATCH.** Neither artifact was recreated, rewritten or modified. Byte-identical
copies of the originals frozen 2026-08-21 02:09 UTC.

**Database:** `D:\IDX\data\walkforward.db` (= `/mnt/d/IDX/data/walkforward.db`), 3,354,836,992 bytes,
mtime 2026-08-15 10:47. Opened `mode=ro`. **Unmodified.**

**Command:** `python3 -u g1_open_integrity_census.py` executed with cwd `D:\IDX`.
Output captured to `D:\IDX\g1_census_output.txt`.

## 2 · D1–D6 results

### D1 · Range violation — **CLEAN**
**8 violations in 1,051,742 ticker-days = 0.0008%.** `low <= open <= high` holds essentially
universally. **There is no evidence of a value being stuffed in from outside the traded range.**
This was the hard logical test and the corpus passes it. It is also the finding that makes the
verdict *interesting* rather than trivial — see §7.

### D2 · Edge-pinning — **mild excess, not decisive**
Among `open == prev_close` days, **58.89%** sit at the high or the low.
Among `open != prev_close` days, **46.68%**. An excess of ~12pp. Directionally consistent with
substitution, but a genuinely unchanged open on a day that only moved one way would also sit at an
edge. **Weak evidence.**

### D3 · Stickiness ratio — **FAILS the PASS bar, and the pattern is the real finding**

| Stratum | `open==prev_close` | `close==prev_close` | **D3** |
|---|---:|---:|---:|
| All rows | 56.55% | 32.01% | **1.77** |
| Liquid, S0 | 52.35% | 17.20% | **3.04** |
| Liquid, S1 | 53.90% | 19.47% | **2.77** |
| **Liquid, S2 (primary)** | **51.94%** | **22.57%** | **2.30** |
| Liquid, S3 | 42.42% | 14.59% | **2.91** |

P3 required **< 2.0** in the liquid stratum. **Every regime fails it.**

**By volume bucket — this is the decisive pattern:**

| Volume bucket | n | `open==prev_close` | `close==prev_close` | **D3** |
|---|---:|---:|---:|---:|
| 0 | 109,273 | 99.98% | 99.98% | 1.00 |
| 1–10k | 96,980 | 54.01% | 42.81% | 1.26 |
| 10k–100k | 133,318 | 51.85% | 30.76% | 1.69 |
| 100k–1M | 204,266 | 54.13% | 28.16% | 1.92 |
| 1M–10M | 264,268 | 53.61% | 21.43% | 2.50 |
| **>10M** | **243,637** | **45.88%** | **12.61%** | **3.64** |

> **As liquidity rises, the close's stickiness collapses from 42.8% to 12.6% — exactly as it should.
> The open's stickiness barely moves: 54.0% to 45.9%. D3 therefore RISES with liquidity, reaching
> 3.64 in the most heavily traded bucket.**
>
> **No market mechanism produces that.** For a stock trading over 10 million shares a day, an
> opening call auction clearing at exactly the previous close on 46% of sessions — while that same
> stock's closing auction does so on only 13% — is not a property of trading. **It is the signature
> of a value that is not being formed by trading.** The open's near-invariance to liquidity is the
> single strongest piece of evidence in this census.

### D4 · Bar degeneracy — **PASSES**
`O==H==L==C`: **19.03%** of all rows, but only **6.43%** in the liquid stratum in S2 — inside the
< 10% bar. The all-rows figure is driven by the 109,273 zero-volume rows, where every field equals
the previous close (99.98%) and which the liquid stratum correctly removes.

### D5 · Intraday corroboration — **FAILS the PASS bar; must be read with a caveat**
38,539 ticker-days corroborated against the `ticks` tape.

- `open` == first traded price, **exact: 56.40%**
- `open` within 1% of first traded price: **74.15%**
- **Among the 43.60% that mismatch, 40.88% have `open == prev_close`**

P4 required **>= 80%**. Observed 56.40%. **Not met.**

**The caveat, stated because it cuts against my own verdict.** The first-tick timestamp distribution
is **25,074 of 38,539 at exactly 09:00:00** — the start of the *continuous* session. The tape
therefore appears **not to contain the pre-opening auction match (08:58:00–08:59:59)**. A genuine
auction open *can* legitimately differ from the first continuous-session trade. **D5 as constructed
compares the daily open against the wrong reference for a call-auction market, so its 56.40% is a
lower bound on integrity, not a direct measurement.**

**What survives the caveat:** of the mismatches, **four in ten are exactly the previous close.** A
genuine auction print that differs from the 09:00 trade would land on an arbitrary price, not
disproportionately on yesterday's close. That residual is direct evidence of substitution on a
material minority of days, independent of the timestamp problem.

### D6 · Frozen opens
Longest run of identical `open`: **1,197 consecutive rows.** **760 tickers** with runs >= 20;
**375 tickers** with runs >= 60. Much of this is explicable by suspension and zero-volume names, but
a 1,197-day frozen open is a dead ticker being carried forward, not a market.

**Per-ticker dispersion, liquid stratum, 883 tickers with >= 100 liquid days:**
`open==prev_close` rate deciles [10/25/50/75/90] = **0.372 / 0.433 / 0.500 / 0.566 / 0.643**.
**440 of 883 tickers (49.8%) exceed a 50% rate.** The defect is **not** confined to a removable
sub-population — it is centred on the median ticker. This is why no universe restriction rescues it.

## 3 · Regime differences

`open==prev_close` in the liquid stratum: S0 52.35% · S1 53.90% · **S2 51.94%** · S3 42.42%.

**S3 is meaningfully cleaner** (42.42%, D3 2.91) than the earlier regimes, and S3 is also the only
regime with tick coverage. But S3 spans **2025-12-15 → 2026-07-29 — roughly seven months, 132,015
rows** — far too short to serve as a primary window, and the improvement is not enough to clear F2's
bar even on its own terms.

**The pre-designated primary window S2 fails.** It was named in the pre-registration before the
census, and it is the window the verdict is adjudicated on.

## 4 · Liquidity differences

Covered in D3 above. The finding worth repeating: **the liquid stratum did its job and the defect
survived it.** Filtering to `volume >= 100,000` removed the zero-volume rows almost entirely
(degeneracy 19.03% → 6.43%) and moved `open==prev_close` by less than five percentage points
(56.55% → ~51.9%). **The problem is not illiquidity. Illiquidity was controlled for and the problem
remained.**

## 5 · Back-adjustment verification of `close_t / open_t` — **INCONCLUSIVE AS SPECIFIED**

| Event | n | median \|log(close/open)\| on-event vs off | median \|log(open/prev_close)\| on vs off |
|---|---:|---|---|
| split | 101 | 0.03390 vs 0.00957 — **ratio 3.54** | 0.01342 vs **0.00000** — ratio 1.3e10 |
| dividend | 2,067 | 0.01509 vs 0.00957 — ratio 1.58 | 0.01126 vs **0.00000** — ratio 1.1e10 |

**The direct test degenerated, and it degenerated for the same reason the gate failed.** The off-event
median of `|log(open/prev_close)|` is **exactly 0.00000** — because 56.55% of opens equal the
previous close, so the median of that quantity is identically zero. The 1.3e10 "ratio" is an artefact
of dividing by zero, not a finding. **It is reported rather than suppressed, and it means nothing.**

**What can be concluded, indirectly and weakly:**
- A uniform per-row scaling preserves the ordering `low <= open <= high`. **D1's violation rate of
  0.0008% is consistent with per-row uniform scaling**, under which `close_t/open_t` **is**
  invariant by construction.
- The split-day elevation in `|log(close/open)|` (ratio 3.54, **n = 101**) is confounded with genuine
  event-day volatility and cannot separate the two at that sample size.

> **Honest verdict on this section: invariance is supported indirectly by D1 and is NOT directly
> verified. The verification requested could not be completed as specified.** It is also now moot —
> a component built on an unreliable `open` does not become usable by being adjustment-invariant.

## 6 · Sample quality ledger

| | Count |
|---|---:|
| ticker-days examined | 1,054,382 |
| with `open > 0` and `close > 0` | 1,054,382 |
| with identifiable prior close | 1,053,424 |
| **consecutive prior day (census base)** | **1,051,742** |
| non-consecutive (excluded) | 1,682 |
| with intraday corroboration | 38,539 |
| **clear range-violation signature** | **8** |
| degenerate bars (`O==H==L==C`) | 200,122 |
| **`open == prev_close` (ambiguous)** | **594,781** |
| liquid stratum rows (`volume >= 100k`) | 712,341 |
| non-integer opens (back-adjustment) | 36,842 |
| zero-volume rows | 109,436 |

## 7 · The exact rule that determined the verdict

> **F2** — `open == prev_close` rate, liquid stratum, S2 — **>= 50%** → **51.94% observed** → **FAIL**

**PASS scorecard:** P1 ✅ (0.0008% < 0.5%) · **P2 ❌** (51.94%, needed < 20%) · **P3 ❌** (2.30,
needed < 2.0) · **P4 ❌** (56.40%, needed >= 80%) · P5 ✅ (6.43% < 10%). **Three of five PASS
conditions missed.**
**FAIL scorecard:** F1 no (0.0008% < 5%) · **F2 YES** · F3 no (2.30 < 5.0) · F4 no (56.40% > 40%).

**How close the call was, stated plainly.** F2 fired by **1.94 percentage points**. Had the frozen
threshold been 55% instead of 50%, the verdict would have been **CONDITIONAL**, not FAIL. **The
threshold was frozen before the census and is not being revisited** — that is the entire purpose of
pre-registration, and softening it now would make the exercise worthless.

**But the verdict does not rest on that margin.** Three independent lines converge on the same
diagnosis, none of which depends on where the 50% line was drawn:
1. **D3 rises with liquidity to 3.64.** The open's stickiness is nearly liquidity-invariant while
   the close's collapses. Nothing about market behaviour produces that.
2. **40.88% of D5 mismatches are exactly the previous close.** A genuine auction print would not
   concentrate there.
3. **The median liquid ticker sits at a 50.0% rate**, and 440 of 883 exceed it. There is no
   sub-population to escape into.

**This is the correct outcome, arrived at cheaply.** One query, before any outcome variable was
computed, prevented a monthly-horizon cross-sectional study whose formation variable —
`overnight_t = log(open_t / close_{t-1})` — would have been **mechanically zero on roughly half of
all liquid ticker-days**. The decomposition would have measured vendor fill convention and
reported it as clientele behaviour.

## 8 · Weakest link — of the result, not the candidate

**D5 could not be run against the right reference price.** The `ticks` tape starts at the continuous
open (09:00:00) and appears not to carry the pre-opening auction match. **A clean test of whether
IDX's daily `open` equals the pre-opening auction clearing price was not possible with the data
held**, and D5's 56.40% is therefore a lower bound rather than a measurement.

This does not change the verdict — F2, D3 and the per-ticker dispersion are all independent of D5 —
but it means the *diagnosis* is not fully closed. Two possibilities remain unseparated: the vendor
substitutes the previous close for a missing auction print, **or** the vendor reports the last
available price as the open and IDX's own feed does the same. **Both are fatal for this candidate.
They differ only in whose convention is responsible.**

## 9 · Status and next step

**I3 · overnight/intraday clientele decomposition — G-1 FAILED. STOPPED.**

Per the frozen stop rule: no G-2, no universe restriction applied, no outcome test, no registration.

**The candidate is not refuted as a mechanism — it is blocked as a measurement.** Reviving it would
require an `open` sourced from IDX's pre-opening auction print, which is not in this corpus and was
not located in any accessible source. That is a data-acquisition question, not a research question,
and it is not opened here.

**Note for the programme ledger:** this is now the **second** consequence of the same underlying
condition — the corpus's price fields are vendor-processed in ways the system never documented.
B-0 (back-adjustment) invalidated M6/I1's price-level tier assignment; the open convention now
invalidates I3's formation variable. **The two failures share a root cause, and it is worth treating
as such rather than as two unlucky candidates.**

## 10 · Confirmations

No hypothesis registered · no family slot consumed · no predictive return, portfolio return, alpha,
Sharpe, t-statistic, regression, power or profitability computed · no OFI, no `cont_k` ·
**`stockbit_flow_bars` not queried** · no backfill launched or altered · `HYP-PM-0002` **untouched** ·
`HYPOTHESIS_REGISTRY.md` and `FAILURE_REGISTRY.md` **unmodified** · no production code modified ·
database opened **read-only** and **unmodified** · thresholds and methodology **unchanged from the
frozen pre-registration** · neither artifact recreated, rewritten or modified.

**Files written to `D:\IDX` this stage:** `S2-PM-0003_G1_PREREGISTRATION.md` (copy of the frozen
original), `g1_open_integrity_census.py` (copy of the frozen original), `g1_census_output.txt`
(captured output), and this result document.
