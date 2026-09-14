# CLAUDE INDEPENDENT REVIEW — G1 RESULTS & C7 TRIAGE — 2026-09-11

**Authority:** point-in-time independent review record. Not canonical, not an amendment, not a
registration. Supersedes nothing.
**Mode:** READ-ONLY. No code modified, no data modified, no G1 rerun, no C7 tuning, no rescue
specification, no new empirical strategy. All database access `mode=ro` + `PRAGMA query_only`.
**Reviewer:** Claude (Opus 5), independent of the ZCode work under review.
**Branch:** `ops/hardening-2026-07-10` · **Task category:** Research / Governance (Opus per the
escalation rule: repository-wide reasoning + statistical interpretation).

**Scope note on my own computation.** I computed *formation-side state incidence only* — how often
each registered state fires, and how many names sit in each leg on each date. I computed **no
forward returns, no θ, no t-statistic, and no p-value**, and I deliberately did **not** recompute
the withdrawn arm's inference even though the preserved artifact makes it trivial (see F-2). Those
diagnostics test whether the executed test *was what was registered*; they are not an alternative
test. Everything labelled **[measured]** below is my own read-only computation against the frozen
store and is reproducible; everything else is cited to a repository artifact.

---

## 0. Executive summary

**G1 FAIL should stand.** Every methodological divergence I found runs in the *permissive*
direction — the executed tests were easier to pass than the designed ones, and still failed. No
rescue exists on the statistical axis; nothing moves p = 0.584 / 0.747 toward 0.05.

**But the FAIL must be recorded as two different outcomes, not one.** C3 is a genuine, clean
prediction failure. **C2 is a specification failure: its registered state condition is an arithmetic
tautology on Dataset B and the conduit-disagreement mechanism was never actually tested.** Filing C2
as a refuted prediction would corrupt the institution's failure-mode diagnostic in precisely the way
`HYPOTHESIS_LIFECYCLE.md` §3.1 prohibits.

**Three governance defects are more serious than the G1 result itself:** the withdrawn arm was
computed and its full results are preserved in the "immutable" artifact (F-2); the run's pinned code
and config hashes are *already broken* and nothing is under version control (F-3); and G1 consumed
**zero** multiplicity slots because it is not a registered hypothesis in any lawful family (F-4).
F-4 blocks C7, C6 and C8 equally.

**C7 is a legitimate candidate but is not mature enough to register, and its proposed outcome
variable is wrong.** Four of the six parameters marked "NOT SET — OWNER DECISION REQUIRED" are
**already hard-coded in the shipped harness**, written *after* the readiness document that says no
such code exists.

**Recommendation: B — pause C7 and improve the hypothesis first.** Details in §6.

---

## TASK 1 — Audit of the G1 execution

### 1.1 What is clean (verified, not assumed)

An audit that lists only faults is not an audit. The following all check out:

| Check | Result |
|---|---|
| Store identity | `21661f033145ef90…` **matches** `DATASET_B_FREEZE_MANIFEST_v1.json` |
| Raw output identity | `G1_REAL_OUTPUT_RUN1_2026-09-11.json` = `74883c04cf80a867…` **matches** manifest; byte-identical to `g1_real_output.json` |
| `foundation.py` | `e427cc482fa1e00c…` **matches** manifest pin |
| Specification sources exist and are unaltered | BFI-002 memo `9c87888f61bfdb51…` and BFI-001 frozen prereg `91c0eb9a4a42630f…` found at `/home/tjiesar/ZCodeProject/`; **both sha256 match registration §11 exactly** |
| PIT roster v1 ≡ v2 "content-identical" claim | **TRUE** — `period_members` byte-identical (101 tickers, 8 periods); only `built_at_utc`/`sha256`/`version` differ. Run used v2, registration pins v1: harmless |
| Newey–West | Bartlett kernel, weights `1 − L/(lag+1)`, `L = 1…k`, lag = k. Correct. Variance divided by `n` with no df correction — negligibly **anti**-conservative, i.e. biased toward rejection, so not a source of false FAIL |
| Holm | Step-down with running max, capped at 1.0. Correct implementation |
| Multiplicity scope | Family restricted to retained {C2, C3} at k=5 — *more permissive* than the memo's 3-cell family. Cannot cause a FAIL |
| Forward returns | Exactly k admitted sessions apart; PIT membership at formation; no substitution; strict contiguity enforced on (t, t+k] via `spans_excluded`; parity-tested against `foundation.forward_returns` |
| Look-ahead | None found. Flow rows `trade_date == t`; ADV20 window `vals[i-20:i]` = true shift(1); `ret1` vs prior admitted close; breadth history appended strictly *after* use in `compute_breadth_surprise` |
| Sign handling | Store SELL values are **all** negative, BUY **all** positive **[measured]** — so `gross = buy_v + abs(sell_v)`, `desk_sell`, `for_sell`/`loc_sell` are all correct. (I initially suspected an ST sell-leg bug at `g1_harness.py:336`; the data disproves it.) |
| Duplicate rows | 0 duplicate `(ticker, trade_date, broker_code, side)` keys in the store **[measured]** — no `investor_type` double-counting |
| Write safety | All connections `mode=ro` + `query_only`; output path confined to the harness dir by `commonpath` guard |
| C1a/C1b withdrawal *decision* | Correct, and correctly followed the memo's own pre-declared §9 fallback ("the design is withdrawn, not re-cut") |

### 1.2 Findings

---

#### **F-1 · METHODOLOGY ERROR — CRITICAL · C2's registered state is an arithmetic tautology on Dataset B**

**Evidence [measured], frozen store `broker_flow_b`, RAJA excluded, 30,624 ticker-days:**

```
|Σbuy − Σ|sell|| / gross :  p50 = 0.00e+00   p90 = 0.00e+00   p99 = 0.00e+00   max = 0.00e+00
exactly-zero net         :  100.00% of ticker-days
sign(for_net) ≠ sign(loc_net) :  30,624 / 30,624  =  100.00%
```

At full population (limit=150) total buy value ≡ total sell value for **every single ticker-day** —
the exchange identity, no longer masked by top-25 truncation. Therefore
`for_net + loc_net ≡ 0`, and the C2 disagreement condition `sign(for_net) ≠ sign(loc_net)`
(`g1_harness.py:482-485`) is **satisfied identically**. It has zero variation. The only thing the
C2 filter actually does is apply the two ≥15%-of-gross participation gates; 30,176 name-days pass
them, ≈98.5% of the panel **[measured]**.

The memo measured this state at **30.2% of name-days** (§5) — on capped Dataset A, where `net25 ≠ 0`.

**What was actually executed** is therefore:

> θ_C2(k) = E[r | foreign-broker net value > 0] − E[r | foreign-broker net value < 0],
> restricted to names where each ownership group is ≥15% of gross.

That is a **foreign-broker net-flow sign contrast** — a different mechanism, on a surface already
owned by the closed foreign-flow H1/H6 line. The registered mechanism ("which client pool is driving
price *when the two conduits disagree*") has no variation to test and was never tested.

**This was knowable from ZCode's own artifacts, one day earlier:**

- `ZCODE_ALPHA_DISCOVERY_FAMILY_MAP_2026-09-10.md` §3, verbatim: *"**broker_flow net flow is
  structurally ~zero** … Consequences: 1. **No candidate may use broker_flow net as a signal or
  control** — it is mechanically ~0."* Family **G** was marked **BLOCKED BY DATA** for exactly this.
  C2 stands on the same quantity and was not blocked.
- `g1_harness.py` module docstring, line 26: *"At limit=150 broker_flow net is identically zero
  (2026-09-10 trial)."* The fact was used to justify sourcing NF externally; the implication for
  C2's state definition was missed.

**Classification:** C2 = **specification failure**. Not a prediction failure. See §2.

---

#### **F-2 · GOVERNANCE ERROR — HIGH · The C1a withdrawal was not enforced; the withdrawn arm's full results are preserved in the artifact**

`run_g1` calls `cell_c1a()` unconditionally (`g1_harness.py:821`) and only *afterwards* nulls three
of eight fields (`:832-842`). The preserved output retains, for each of k ∈ {3,5,10}:

- `theta_net_cost_floor` — from which θ recovers by adding 0.006;
- `n_days`;
- the **complete daily `theta_t` series** (152 / 148 / 142 dates);
- a per-date, per-bucket **`detail` block** (190 / 185 / 179 entries with `n_top`, `n_bot`, `contrast`).

Recovered by arithmetic from the published field **[measured]**: **k=3 +36.6 bp · k=5 +120.1 bp ·
k=10 +193.1 bp** — monotone increasing, and by an order of magnitude the largest effect anywhere in
the family. The t-statistics are trivially recomputable from the preserved `theta_t`; **I did not
compute them**, and neither should anyone else.

`G1_FINAL_EXECUTION_REPORT` §D is wrong twice: *"All six C1a/C1b cells (3 horizons × 2 arms) emitted
WITHDRAWN_FREQ_DEPENDENT with theta_mean = nw_t = p = null. No substitute results were computed."*
There are **three** C1a cells, not six — **C1b is not implemented at all** (`run_g1` appends only
C1a, C2, C3), so the report asserts verification of three cells that do not exist. And the numbers
*were* computed and *are* retained.

`test_withdrawn_arms_represented_and_holm_shrinks` (`test_g1_harness.py:197`) has the docstring
*"…emit WITHDRAWN_FREQ_DEPENDENT with **no numbers** regardless of gates"* but asserts only
`theta_mean is None and p is None`. The test certifies the leak.

**Why this matters:** withdrawal exists to prevent exactly the post-hoc selection hazard this
creates, and the leak is sitting in the record while the next hypothesis is being chosen.

**Mitigation I am recording deliberately, so the number cannot mislead later.** The preserved
`detail` block shows C1a's daily contrasts are built on a **median of 1 name per leg** — 97% of
bucket-cells have a singleton on at least one side, across only 148 of 375 dates **[measured from
the artifact]**:

```
C1a k=5 :  185 bucket-cells ; n_top min/med/max = 1/1/7 ; n_bot = 1/1/9 ; 97% have a singleton leg
```

The leaked +120 bp is the difference between two individual stocks' returns on ~148 days. It is
noise. It is not a finding, and it must never be treated as one.

---

#### **F-3 · GOVERNANCE / REPRODUCIBILITY ERROR — HIGH · The run's pinned code and config hashes are already broken; nothing is under version control**

| Artifact | Pinned in report/manifest | On disk now (10:42 WIB) | |
|---|---|---|---|
| `g1_harness.py` | `9471c740175b3135…` | `91ecf6d060e064b0…` | **BROKEN** |
| `g1_config.json` | `7211ad94c44614f2…` | `89ff2b463b382018…` | **BROKEN** |
| `foundation.py` | `e427cc482fa1e00c…` | `e427cc482fa1e00c…` | ok |
| raw output | `74883c04cf80a867…` | matches | ok |

`g1_harness.py` was modified at **10:35**, an hour after the 09:34 run output, when the C7 execution
path was added to the *same file*. `g1_config.json` gained `c7_registered`.
`G1_FINAL_EXECUTION_REPORT` §B claims *"the file itself is the preserved snapshot; unchanged
post-run"* — false on both clauses.

**A third, independent inconsistency:** the run's **own** self-recorded `config_sha256` inside the
output is `25114b9c7493f1be…`, which equals neither the manifest pin nor the current file. The
manifest hashed raw file bytes; `load_config` hashes canonical JSON. Two methods, one field name,
never reconciled — so the manifest's `config_sha256` was never the value the run stamped.

`docs/research_programs/P-M/g1_harness/` is **untracked in git** (`git status` → `??`). There is no
recoverable copy of the executed code. This violates Research Master Plan invariant #6
(reproducible = seed + dataset fingerprint + **git commit** + run_id).

The manifest's `known_label_caveat` justifies leaving a known-false provenance string in the output
*"to preserve the executed-code hash"* — a hash broken 61 minutes later. The cost was paid; the
benefit was discarded.

**The directory is still live.** `test_c7_registration.py` was written at 10:38 and again at 10:42,
during this review. Another session is actively modifying the artifact directory. The hashes above
are a snapshot.

---

#### **F-4 · GOVERNANCE ERROR — HIGH · G1 consumed no multiplicity slot and is not a registered hypothesis**

`HYPOTHESIS_REGISTRY.md` ends at HYP-PM-0003. The P-M declared family is `{I5, I6, I7, I12}` with
two consumed slots (HYP-PM-0001, HYP-PM-0003, both FAILED F2). G1/BFI-002 has **no HYP id, no family
slot, no registry row** — it was "registered" only by an ad-hoc markdown file in an untracked
directory.

Worse: C2, C3 and C7 are *new indicators* (ownership-net, breadth-surprise, intensity), outside
`{I5, I6, I7, I12}`. Per PG-3 / PG-6 / R7.5 and `DECISION_LOG` D-028, a declared multiplicity family
is append-only and monotonic and may only be **widened by a formal governance amendment**. No such
amendment exists. **There is currently no lawful family for C2, C3 or C7 to be counted in.**

`G1_POSTMORTEM_FAMILY_TRIAGE` §C calls this *"Governance records owed … registry bookkeeping"*. It
is not bookkeeping. An uncounted trial is precisely the data-snooping failure mode invariant #12
protects against, and running C7 next would make it the second uncounted trial on the same corpus.
**This blocks C7, C6 and C8 equally and is the single most important owner decision.**

---

#### **F-5 · METHODOLOGY / GOVERNANCE ERROR — MEDIUM-HIGH · Four undeclared divergences from the named specification source**

The BFI-002 memo is hash-verified as the registration's specification source (§5, §11). Registration
§7 asserts *"Every parameter below was inventoried against the harness implementation and the design
record"* and *"none was silently resolved."* Four parameters were resolved in the code's favour
without declaration:

**(a) Outcome variable.** Memo §8: *"forward return **Open(t+1) → Close(t+k)**, raw **and**
equal-weight-market-adjusted."* Executed: **Close(t) → Close(t+k)**, raw only. Registration §5
restates the code; §9's NOT-SET list omits it.
*Direction:* Close(t) entry is **not implementable** — the signal consumes after-close broker flow
of session t and then assumes execution at that same close — and it captures the overnight gap. It
is strictly the *more favourable* convention. It cannot manufacture a false FAIL, but it does mean
that even a positive G1 result would not have been tradeable. The dropped market-adjustment is
immaterial here: a same-date long-leg-minus-short-leg spread already differences out the market
factor.

**(b) C3's trailing window.** Memo §7 C3 specifies a **60-observation trailing median**; the harness
even declares `BREADTH_SURPRISE_WINDOW = 60` (`:54`) — and then never uses it.
`compute_breadth_surprise` (`:428`) takes an **expanding median over all prior rows** (min history
30). Registration §4 restates the *code*; `G1_FINAL_GOVERNANCE_STATUS` §4 restates the *memo*
("60-obs/30-min-history trailing median"). Three documents, two incompatible statistics, one dead
constant. The ±0.30 threshold was *"frozen from measured 23% incidence"* under the 60-obs statistic;
under the expanding statistic the incidence is 18.9% broad / 20.5% narrow **[measured]**, so the
threshold's calibration basis no longer matches the operative statistic.

**(c) C2's conditioning.** Memo §5 and §7: C2 is *"conditional (disagreement state **× liquidity
tercile** × species mix as control)"*, falsified if *"no **cell** separates sides"*. Executed:
pooled and unconditional. Registration §9.3 declares the *species* control dropped but is **silent
on the liquidity conditioning**. The harness computes `liq_bucket` (`:377`) and never reads it.

**(d) C3's falsification clause, half-honoured.** Memo §7 C3: *"Falsified if it adds nothing **after
NF and ST controls**."* Registration §9.2 correctly declares the ST half inapplicable (ST withdrawn
with C1a) — but the **NF half was executable** (NF is ratified, computed, and carried in the panel
as `nf`) and was still not run.

---

#### **F-6 · DATA / SPECIFICATION ERROR — MEDIUM · `Pemerintah` silently folded into "local"**

The store carries **three** `investor_type` values **[measured]**: `Asing` 511,520 · `Lokal` 886,679
· **`Pemerintah` 120,528 (7.9% of rows)**. The code (`:275`, `:284`) buckets
`startswith("asing") → foreign, else → local`.

Memo §5 treats government-related brokerages as an explicitly **distinct third class** ("the four
government brokerages are tiny-ticket institutions", 11% desk / **89% aggregator**, *"mostly a
retail-distribution channel"*) and defines C2 as foreign-owned vs **locally-owned**. Registration §4
says only *"loc_net symmetric"*, which never resolves the third class.

Measured impact of the undeclared choice **[measured, formation-side only]**: adopting the memo's
Lokal-only definition changes gated disagreement name-days by **−26.5%** (30,176 → 22,179) and flips
a net sign on **6,808** name-days. Subsumed in practice by F-1 (the state is vacuous either way),
but it is an independent undeclared specification decision on 7.9% of the data.

---

#### **F-7 · ACCURACY ERROR — MEDIUM · "freq is never read" is false**

Registration §6 exclusion 9: *"freq is never read."* `G1_FINAL_GOVERNANCE_STATUS` §5: freq is *"not
read by any retained arm."*

`run_g1` unconditionally calls `build_species_classifier` (`:781`), which reads `r.get("freq")`
(`:206`); `build_panel` then **drops every flow row whose broker is unclassified** (`:254-257`), and
that panel is the shared input to both C2 and C3. Freq is read, and it gates row inclusion.

Empirically immaterial in Run 1 — all 95 brokers have `freq > 0` prefix rows and
`flow_rows_unclassified_broker = 0` **[verified in the output]** — but the guarantee as written is
false, and it would bite for any broker first appearing after the 2025-09-30 prefix.

---

#### **F-8 · GOVERNANCE ERROR — MEDIUM · A power claim was made after registering that none is authorized**

Registration §9.1: *"MDE/power: **NOT SET** … **No power claim may be attached to any G1 output**."*

`G1_FINAL_EXECUTION_REPORT` §M: *"the verdict is **not power-limited** at the registered
inference."* `G1_POSTMORTEM_FAMILY_TRIAGE` §A: *"**Determinate, not power-limited** … a real null,
not an underpowered ambiguity"* — in the same paragraph as *"no power claim is made in either
direction."* Self-contradictory, and the first clause is prohibited by §9.1.

The justification offered — *"329–365 daily observations per cell"* — conflates the *number* of
daily θ_t observations with their *precision*. On this estimator that conflation is demonstrably
unsafe: the same machinery produced C1a's θ_t from a median of one name per leg (F-2).

**In fairness to ZCode, the substantive intuition is correct — I checked.** C2 and C3 legs are
healthy **[measured]**:

```
C3 : 356 dates with both legs ; broad leg min/med/max 2/14/35 ; narrow 2/16/46 ; 0% singleton dates
C2 : 386 dates with both legs ; long-F  15/35/52            ; short-F 26/43/64 ; 0% singleton dates
```

So C3's daily spread is a genuine ~14-vs-16-name cross-sectional contrast, and determinacy is
defensible. What is not defensible is asserting it *without the diagnostic*, *after* registering
that no such claim may be made — and the run emits no per-leg counts at all, so the claim was
unsupported by the artifact at the moment it was made.

---

#### **F-9 · ACCOUNTING GAP — LOW/MEDIUM · Registration §7's "every exclusion is counted" is not met**

- `excluded_no_net_flow` is incremented at two distinct sites (`:317` gross ≤ 0; `:330` missing NF) —
  two registered exclusions collapsed into one counter. Disclosed in report §L, but the split is
  unrecoverable from the artifact.
- `excluded_ca_at_t` is initialised and never incremented — dead counter.
- Not counted anywhere: C3's min-history drop (**2,978 ticker-days, ~10%** [measured]), C3's
  mid-state drop, C2's failures of the 15% gates, and per-date leg sizes for either arm (F-8).

---

#### **F-10 · GOVERNANCE / TAXONOMY — LOW/MEDIUM · "G1" collides with the controlled vocabulary**

`TAXONOMY_AND_NAMING_STANDARD.md` — the vocabulary authority under Decision-Making Hierarchy rule 3
— reserves **G1–G4 for institutional Gates**. Here "G1" names a BFI-002 experiment; separately,
`S2-PM-0004_G1_RESULT.md` uses "G-1" for an I3 preregistration gate. Three meanings. The postmortem
itself flags the collision. This will corrupt the ledger the moment G1 is appended to it.

---

#### **F-11 · COSMETIC (already disclosed) · stale `net_flow_source` label**

`provenance.net_flow_source` reads `"stockbit_flow (PROVISIONAL, unratified)"` (`:620`) while the
executed construction is the ratified share-ratio NF. Disclosed in report §M and the manifest. Given
F-3, the stated justification for leaving it ("to preserve the executed-code hash") no longer holds.

---

#### Note on the NF timing convention (not scored as an error)

NF is materialized T+1 morning (registration §9.6) yet is consumed at formation t. For C2/C3 it
enters **only as an exclusion filter** (516 rows dropped), so it is a mild sample-selection
look-ahead, not a signal look-ahead. It is registered, disclosed, and — like F-5(a) — runs in the
permissive direction. Recording it for completeness, not as a defect.

---

## TASK 2 — Is the FAIL verdict justified?

**Yes, G1 FAIL stands.** Under the registered rule (`G1_REGISTRATION_v1` §8), a retained arm is
confirmed iff Holm-adjusted p < 0.05 at primary k **and** sign consistency across k. Holm p = 1.0
for both arms. Neither is confirmed.

Decomposed as requested:

| Failure axis | C2 | C3 | Assessment |
|---|---|---|---|
| **Statistical** | p = 0.584, t = +0.55 | p = 0.747, t = +0.32 | **Real.** Largest effect anywhere in the family is C3 k=3, t = 1.11 — still non-significant and not a registered primary |
| **Sign consistency** | +/+/− | +/+/− | **Real.** Both flip at k=10 |
| **Economic** | −55 bp net | −54 bp net | **Real and independent.** All six cells net −44…−67 bp against the 0.60% floor; the largest gross effect (+16 bp) is a quarter of the friction |
| **Insufficient power** | not established | not established | **Cannot be claimed in either direction** (F-8). My diagnostic supports determinacy for both arms, but that diagnostic did not exist when the claim was made, and §9.1 barred making it |
| **Specification** | **FAILED — decisive** (F-1) | Partial (F-5b, F-5d) | See below |

**Per-arm classification for the ledger:**

- **C3 — genuine prediction failure (F2-type).** The construct is sound: count-based, cap-robust,
  not identity-constrained, real cross-sectional variation (18.9% broad / 20.5% narrow), healthy
  legs (median 14 v 16 names over 329 dates). θ = +5.8 bp at k=5 with a sign flip at k=10 is a real
  null. **Caveat for the ledger wording:** the tested statistic is not exactly the designed one
  (expanding vs 60-obs median, F-5b) and the executable half of its falsification clause was skipped
  (F-5d). Record as *"C3 as executed did not confirm"*, **not** *"the breadth-surprise mechanism is
  refuted."*

- **C2 — specification failure, NOT a prediction failure.** Per F-1, the registered state has zero
  variation on Dataset B. What failed is a foreign-net-flow sign contrast nobody registered. Filing
  this as F2 would record a refutation of a mechanism that was never tested, corrupting the
  failure-mode distribution — the exact error `HYPOTHESIS_LIFECYCLE.md` §3.1 names as corrupting the
  institution's own self-diagnostic.

**One drafting defect to fix before the next registration:** §8's literal text is *"Holm-adjusted
p < 0.05 … AND sign consistency across k ∈ {3,5,10} **is reported**"* — which requires the
consistency to be *reported*, not to *hold*. The reports treat it as a requirement that must hold.
Immaterial here (the Holm conjunct fails alone), but it is an ambiguity that would matter in a
borderline case.

---

## TASK 3 — Hidden rescue opportunities

I checked each named category against the executed code and the frozen data:

| Candidate issue | Finding |
|---|---|
| Wrong denominator | **No.** `gross = buy_v + \|sell_v\|` verified correct against the store's sign convention |
| Wrong timing | **Permissive, not restrictive** (F-5a). Close(t) entry + overnight gap favours finding an effect |
| Wrong PIT universe | **No.** Roster v1 ≡ v2 verified byte-identical; PIT membership enforced at formation |
| Incorrect NF control | **Yes, but permissive** — NF was dropped as a control entirely (F-5c/d); running C3 unconditionally is the *easier* test |
| Accidental lookahead | **None found** in feature construction. One disclosed sample-selection T+1 filter, permissive |
| Wrong exclusion | **No.** No exclusion found that removes signal; the one accounting conflation (F-9) does not change membership |
| Incorrect multiplicity | **No** — Holm correct, and the 2-cell family is *weaker* correction than the memo's 3-cell |
| Registration ↔ implementation mismatch | **Yes — F-1 is decisive; F-5, F-6, F-7 are real but secondary** |

**One genuine invalidating issue exists: F-1.** It invalidates **C2's construct, not C2's number**.
It does **not** imply an effect exists, and it is **not a rescue** — it is a reclassification. It
explicitly does not license rerunning C2. A future C2 would need a new dated registration, a lawful
family slot (F-4), and a state definition that survives the net ≡ 0 identity — for example, shares
of each group's **own-side** gross rather than of total gross. Designing that is out of scope here
and I have not done it.

Everything else runs in the permissive direction. **The registered tests, as executed, were easier
to pass than the designed ones, and still failed.** The FAIL is not an artifact of a mistake.

---

## TASK 4 — Audit of the C7 proposal

**Genuinely distinct from failed G1? Partly — with one unclosed prerequisite.**
Intensity (gross/ADV20) is not C2's or C3's statistic. But `ZCODE_ALPHA_DISCOVERY_FAMILY_MAP` §5
records an explicit open item: *"Intensity (gross/ADV) vs breadth/species: **not yet fully crossed
— flagged as the one remaining orthogonality check** (single correlation, no search) **before
BFI-002 freezing**."* C3 (breadth) has just failed. Until that one correlation is measured, "C7 is
not a partial re-test of failed C3" is an assumption, not a finding. The C7 registration cites map
rows D/H/K/I/L but **not §5**, and does not carry the check.

**Mature enough to register? No — and the reason is serious.**
Six parameters are marked "NOT SET — OWNER DECISION REQUIRED". **Four of them are already hard-coded
in the shipped harness.** `g1_harness.py:625-770` contains `C7_HIGH_THRESHOLD = 2.0`,
`c7_build_panel`, `cell_c7`, `run_c7`, `main_c7` — implementing a **return-based** outcome
(close→close, item 1), a **high-vs-non-high** contrast (item 2), **k ∈ {3,5,10} with primary k=5**
(item 3), and a **single-cell Holm** family (item 4). That code was written at **10:35**, *after*
`C7_REGISTRATION_READINESS` (10:08), whose §H states *"**No such code was written in this task**"*
and describes a future `c7_harness.py`. The owner is being asked to decide parameters the
implementation has already chosen. **This is pre-committed implementation presented as an open
registration, and it is the single strongest reason to pause.**

Two further defects in the same code path: `run_c7` calls
`load_real_bundle(cfg, required_gates={"dataset_b_frozen"})` — **one** gate, bypassing
`prereg_confirmed`, whereas G1 required four. And the only registration check is a plain boolean
`c7_registered` in a mutable config file, bound to no registration document hash. The readiness
doc's claim of *"the identical pre-run battery"* does not hold.

**Intensity definition correctly sourced?** Formula yes (map row H + generator `17_family_passD.py`).
**Calibration no.** The registration cites `high_intensity_prevalence = 0.18109` as the basis for the
2.0 cut. Measured on frozen Dataset B under the *registered* ADV20 convention **[measured, 28,866
name-days]**:

```
intensity = gross/ADV20 :  p10 0.36  p25 0.54  p50 0.86  p75 1.38  p90 2.20  p99 6.06
P(intensity ≥ 2.0)      =  12.29%       [registration claims 18.11%; map claims p50 0.82 / p90 3.12]
```

The registration's disclosed caveat says prevalence *"may shift **marginally**"* because the
descriptive pass used a 21-value rather than 20-value median. A 21→20 change cannot move 18.1% →
12.3%. The drift comes from the Dataset A → Dataset B population change, and it is unacknowledged.

**Is `gross / ADV20` economically meaningful? Yes.** I checked this specifically, because buy value
≡ sell value in the store raised the possibility that `gross` double-counts. It does not:
`gross / (close × volume)` has p50 = **0.93** **[measured]** (broker_flow `value` runs ≈ half OHLCV
traded value per side, and the two sides recombine to ≈ 1×). So intensity is a clean turnover-surge
ratio and `intensity ≥ 2.0` ≈ "today's turnover ≈ 2× its own 20-day median", on ~12% of name-days.
Sensible state.

**Threshold sufficiently pre-specified? Borderline-yes on provenance, no on hygiene.** Real credit
where due: it is **not return-derived**, it predates the G1 result, and it is cited to a dated
artifact — so this is *not* a data-mined threshold in the sense that matters most. But it was
calibrated on a different dataset and the cited incidence does not reproduce on the execution
dataset. Cheap to fix, and it must be fixed *before* execution, not after.

**Proposed return outcome appropriate? No — this is my main substantive objection.**
The family map classifies D/H as **execution-type**. C7's entire descriptive footprint is
state→state persistence and next-day volume; **zero return evidence exists for C7**. Meanwhile
`FAILURE_REGISTRY.md` records the program-level pattern in its own words: *"all three mechanisms
died at short-to-swing horizons against the same 0.60% round-trip friction — a program-level pattern
(horizon/friction mismatch) that no single F-code expresses."* G1 is now the fourth instance (every
cell −44 to −67 bp net). A return-based C7 at k ∈ {3,5,10} under a friction-anchored MDE needs
θ > 60 bp per k-period; the largest gross effect ever observed across this program's structure
families is 16 bp. **A return-based C7 would be the fifth iteration of a design that has failed four
times for a structural reason, not an idiosyncratic one.**

**Contrast construction precise enough?** Not in the document (item 2 open) — though the code has
already fixed it as high-vs-non-high, where "non-high" is ~88% of the panel: one narrow state
against a heterogeneous everything-else. High-vs-low-tercile would be sharper. This belongs in the
registration, not in the code.

**k = {3,5,10}, primary 5 — post hoc? Not post hoc, but inappropriately inherited.** It is the
pre-existing BFI-001/memo §8 convention, adopted rather than selected — that is legitimate. But
those horizons were set to bracket a *pressure half-life* for a directional-flow mechanism. C7's own
measured dynamic is t→t+1 persistence, with gross autocorrelation 0.73/0.67/0.66 at lags 1–3 (map
row O). Adopting {3,5,10} here is convention-following, not design.

**Truly freq-free? Yes — genuinely.** Verified in code: `c7_build_panel` and `cell_c7` never touch
`freq`, and `run_c7`/`main_c7` never build the species classifier. C7 is the one place where the
freq-free claim is actually true (contrast F-7, where the same claim is false for C2/C3).

**Does the 45.7–48.1% vs 11.3% descriptive result create selection/tuning bias?**
**Not tuning bias on returns** — no return was ever computed for C7, so the threshold is clean on the
outcome axis. But it creates a **relevance illusion**. P(high tomorrow | high today) ≈ 46–48% vs an
~11–12% base is **volume clustering** — a textbook property of turnover, not evidence of an
exploitable edge. It is evidence about the *predictor*, not the *outcome*. Under `EVIDENCE_MODEL`
rule U10 and ADR-L1-003 (mechanism-first is a gate), it supports no claim about forward returns. Yet
it is the sole stated basis for ranking C7 first ("strongest measured descriptive footprint").

**Legitimate new hypothesis, or a disguised G1 rescue? Legitimate.** Different measurement surface,
genuinely freq-free, and — importantly — **pre-designated as a primary survivor on 2026-09-10,
before the G1 result existed**. That pre-designation is the strongest thing C7 has, and I credit it
fully. The only caveat is the unclosed orthogonality check above.

---

## TASK 5 — C6 / C7 / C8 compared

Qualitative ranking on repository evidence, using the Program's own binding tie-breaker: **evidence
over documentation**.

| | **C6 — concentration** | **C7 — intensity-state** | **C8 — absorption** |
|---|---|---|---|
| **Outcome-axis prior** | **Yes — BFI-001 frozen footprint t = −2.65** (map row C) | **None.** Persistence + next-day volume only | **None.** Map row I: *"directional value unproven"* |
| **Predictor-axis evidence** | CONC event-like, lag-1 0.15, own-p90 re-hit 10.5% | Strong — 45.7–48.1% vs 11.3% base (= volume clustering) | Clusters 23.4% vs 4.3% base; prevalence 5.2% |
| **Independence from failed G1 arms** | **High** — R² 1.6% vs species, <0.15 vs breadth (both measured) | **Unverified** — map §5 orthogonality check open | Low — **nested inside C7** |
| **Freq-free** | Yes | Yes (verified in code) | Yes |
| **Data-ready** | Yes (side-value HHIs from frozen store) | Yes (already wired) | Yes |
| **Known weaknesses** | t = −2.65 unconfirmed-Holm; from a *consumed* prereg ⇒ needs T12 supersession; cap-cell composition DEP-B; negative sign ⇒ same friction problem | Threshold drift 18.1%→12.3%; horizons inherited from a different mechanism; pre-implemented ahead of registration | Definition **contains** C7's state (`gross ≥ 2×ADV & \|ret\| ≤ 1%`); thin cells at 5.2% |

**The recommended order C7 → C6 → C8 is not justified by the repository evidence as stated.** The
stated justification — "strongest measured descriptive footprint" — ranks a *predictor*
autocorrelation statistic above an actual *forward-return* prior. On outcome-relevant evidence the
order is **C6 → C7 → C8**; on freq-independence and data-readiness C6 and C7 tie.

And **C8 should not be a separate family at all while it is nested inside C7.** Map row L already
records independence *"Medium (**vs C7 overlap**)"*, and C8's definition literally contains C7's
state. Running C7 then C8 as two separately-counted registrations would double-count one measurement
surface — an F3-style multiplicity error waiting to happen.

*(Caveat, stated plainly: this is a ranking of which candidate has the better prior. Per §6, I do
not recommend running **any** of the three as a return test next.)*

---

## TASK 6 — Recommendation

### **B — Pause C7 and improve the hypothesis first.**

Why not the alternatives:

- **Not C (kill the family).** C3 was a clean, well-constructed null and C6 still carries an
  unexhausted forward-return prior. The family is **mis-sequenced, not exhausted**.
- **Not A (proceed with C7).** C7 cannot lawfully execute — there is no family slot (F-4) — and it
  is pre-implemented ahead of its own open decisions, with the wrong outcome variable.
- **Not D / E immediately.** C6 requires a T12 supersession registration; C8 is nested inside C7.

### Smallest useful next actions, in order

The first three cost governance hours, not research cycles. **None of them consumes a trial.**

1. **Close the G1 ledger correctly** *(owner + registry)*. Append G1 to `HYPOTHESIS_REGISTRY.md`
   with a HYP-PM id and a lawful family slot. Record **C3 as a prediction failure (F2)** and **C2 as
   a specification failure, explicitly NOT F2** (F-1). Two arms, two different outcomes, two
   different ledger entries.

2. **Resolve the family question** *(owner — blocking for everything)*. Either formally widen
   `{I5, I6, I7, I12}` by dated amendment to admit structure indicators, or open a new declared
   family for the broker-flow structure program. Until this exists, **every** C-candidate run is an
   uncounted trial (F-4).

3. **Repair provenance** (F-3). Put `g1_harness/` under git and commit. Reconstruct the executed
   `g1_harness.py` / `g1_config.json` or explicitly declare them lost with a recorded
   reproducibility (X-axis) downgrade. Adopt **one** hashing method. Going forward, copy each run's
   code + config into an immutable per-run subdirectory rather than hashing mutable files in place.
   Note that another session is writing to this directory *right now*.

4. **Purge the withdrawn-arm leak** (F-2) *(needs owner sign-off — it edits a preserved artifact)*.
   Re-emit the preserved output with `theta_t` and `detail` removed from the C1a cells, recording
   the redaction and its reason in the manifest rather than silently. Move the withdrawal check
   *before* `cell_c1a()` is called. Extend the withdrawal test to assert absence of **all** numeric
   fields. Record in the same note that the leaked θ derives from a median of one name per leg, so
   nobody is tempted by it later.

5. **Run the single measurement the family map already requires** — `corr(intensity,
   breadth-surprise)` and `corr(intensity, ST)` on Dataset B. One correlation, explicitly "no
   search", pre-declared 2026-09-10 (map §5) as required *before* freezing. This is the difference
   between C7 being independent and C7 being a partial re-test of just-failed C3.

6. **Then re-scope C7 before registering it.** What must be frozen — in the document, before any
   execution:
   - **Outcome = execution/liquidity**, not forward return (next-session volume/ADV, or a realised
     spread / impact proxy). This matches the map's own "execution-type" classification, matches the
     only evidence C7 actually has, and — decisively — is **not subject to the 0.60% friction floor
     that has now killed four consecutive P-M return tests**.
   - **Re-measure and freeze the state incidence on Dataset B** (12.29%, not 18.11%) — or switch to
     a distributional quantile threshold so the state is defined on the dataset it executes against.
   - **Horizons from C7's own measured decay** (t+1, t+2, t+3 — gross autocorr 0.73/0.67/0.66), not
     the inherited {3,5,10}.
   - **Contrast = high vs low tercile**, not high vs an 88% heterogeneous remainder.
   - **Multiplicity**: a lawful family slot (action 2), and an explicit decision on whether C8 is a
     separate slot or a sub-cell of C7 (it is currently nested).
   - **Power stance**: register "no power claim" *or* a friction-anchored MDE — and then hold to it
     (F-8).
   - **Delete the pre-written C7 code path from `g1_harness.py` until the registration is signed**,
     so the document leads the implementation rather than ratifying it. Restore the full four-gate
     fail-closed battery for any C7 runner, and bind `c7_registered` to a registration document
     hash rather than a bare boolean.

**If the owner wants a return test next despite the friction record: C6, not C7** — it is the only
candidate with prior outcome-axis evidence. It should be registered with an explicit
friction-anchored MDE stated up front, so the test can be declared underpowered *before* it runs
rather than argued about afterwards.

---

## TASK 7 — Independent bottom line

### 1. What ZCode got right

Substantially more than it got wrong, and the failures are of a kind that only careful work
produces:

- **The FAIL verdict itself is correct** and was reached without rescue, re-cut, subgroup search, or
  threshold movement. That discipline is the hardest part and it held.
- **The C1a/C1b withdrawal decision** was right and followed the memo's own pre-declared §9 fallback
  rather than re-cutting the design to survive.
- **Data integrity is real:** store hash, output hash, `foundation.py` hash, both specification-source
  hashes, roster v1≡v2 content-identity — I checked all of them independently and all hold.
- **No look-ahead in feature construction**, correct strict contiguity, correct PIT membership,
  correct Newey–West, correct Holm — I tried to break each of these and could not.
- **Read-only discipline** was genuinely enforced (`mode=ro` + `query_only`, output path guarded).
- **Honest self-disclosure of several defects** (the stale NF label, the conflated exclusion
  counter, the C2 species-control gap, the C7 threshold caveat, the H4–H9 NOT FOUND triage, the
  "no candidate family has a frozen spec" warning in the postmortem). Several of my findings are
  refinements of things ZCode already flagged.
- **C7 was pre-designated a survivor before the G1 result existed** — the proposal is not a
  retrofit, and that matters.

### 2. What ZCode got wrong

- **F-1 (critical):** C2's registered state is an arithmetic tautology on Dataset B — 100.00% of
  ticker-days — so the conduit-disagreement mechanism was never tested. ZCode's own family map §3
  had already ruled "no candidate may use broker_flow net", and the harness docstring already
  recorded "net is identically zero at limit=150". The fact was in hand; the implication was missed.
- **F-2:** the withdrawal was not enforced — the withdrawn arm was computed in full and its complete
  daily series and per-bucket detail are preserved in the artifact; θ is recoverable by arithmetic;
  and the report claims six verified cells when three exist and C1b was never implemented.
- **F-3:** the executed code and config hashes are already broken, the directory is untracked, and
  the run is not reproducible. A known-false label was retained to protect a hash that was then
  discarded.
- **F-4:** G1 consumed zero multiplicity slots and is not a registered hypothesis in any lawful
  family — described as "bookkeeping owed" when it is the difference between a counted and an
  uncounted trial.
- **F-5, F-6, F-7:** four undeclared divergences from the named specification source (outcome
  variable, C3's window, C2's liquidity conditioning, C3's executable NF-control clause), plus the
  undeclared `Pemerintah` folding and a false "freq is never read" guarantee.
- **F-8:** a power claim was made after registering that none is authorized — and, separately, the
  run emits no per-leg counts, so nothing in the artifact supported the claim at the time.
- **C7 triage:** ranks C7 above C6 by comparing a predictor-autocorrelation statistic to a
  forward-return prior; skips the map's own pre-declared orthogonality prerequisite; proposes a
  return outcome for a family the map classifies as execution-type, against a four-for-four record
  of return tests dying on the same friction floor; and presents as open owner decisions four
  parameters already hard-coded in the harness.

### 3. Should G1 FAIL stand?

**Yes — with a split classification.** Statistically and economically the verdict is unambiguous and
robust: every divergence I found made the test *easier*, and it still failed. But **C3 is a
prediction failure and C2 is a specification failure**, and they must be recorded differently. A
single undifferentiated "G1 FAIL — C2/C3 not confirmed" line in the ledger would be wrong.

### 4. Is C7 genuinely worth testing?

**Yes — but not as a return test, and not next.** The mechanism is real, the state is well-formed
and economically meaningful (I verified the units), it is genuinely freq-free, and it was
pre-designated before the result it is now following. As an **execution/liquidity** hypothesis it is
worth a slot. As a fifth swing-horizon return test against the same 0.60% friction floor that has
killed four in a row, it is predictably futile.

### 5. Is C7 mature enough?

**No.** Three independent reasons, any one of which is sufficient: no lawful family slot (F-4); an
unclosed prerequisite the family map itself declared mandatory before freezing (map §5); and four of
six "owner decision required" parameters already committed in code written after the readiness
document that denied the code existed.

### 6. Recommended next action

**Option B.** Close the G1 ledger with the split classification, resolve the multiplicity family,
repair provenance, redact the withdrawn-arm leak, run the one pre-declared orthogonality
correlation — then re-scope C7 around an execution/liquidity outcome with a Dataset-B-calibrated
threshold and horizons drawn from its own decay profile. Full detail in §6.

### 7. Issues requiring owner intervention

| # | Issue | Decision required |
|---|---|---|
| **1** | **Multiplicity family** (F-4) — no lawful family exists for C2/C3/C7 | Widen `{I5,I6,I7,I12}` by dated amendment, or open a new declared family. **Blocking for C7, C6 and C8 alike** |
| **2** | **C2's classification** (F-1) | Rule whether C2 is filed as a specification failure (my recommendation) or a prediction failure. This is a permanent, append-only ledger entry |
| **3** | **Provenance breach** (F-3) | Accept Run 1 as valid-but-non-reproducible with a recorded X-axis downgrade (my recommendation — the *output* artifact is intact and re-running changes nothing scientifically), or require re-execution under version control |
| **4** | **Withdrawn-arm redaction** (F-2) | Authorize editing a preserved artifact. Needs explicit sign-off given the preservation rule; leaving the leak in place is the worse option |
| **5** | **C7 registration independence** | Rule whether "NOT SET — owner decision required" parameters that are already hard-coded in the harness invalidate the C7 draft's status as an open registration |
| **6** | **Concurrent writes** (F-3) | Another session modified `g1_harness/` during this review (10:35, 10:38, 10:42). Establish who owns this directory before any further governance act |

---

*No code modified. No data modified. No G1 rerun. No C7 execution or tuning. No rescue
specification. No registry or decision-log entry created or edited. No commits. All measurements
labelled **[measured]** are read-only formation-side diagnostics against the frozen store and
production `ohlcv` (`mode=ro` + `PRAGMA query_only`); no forward return, θ, t-statistic or p-value
was computed by this review.*
