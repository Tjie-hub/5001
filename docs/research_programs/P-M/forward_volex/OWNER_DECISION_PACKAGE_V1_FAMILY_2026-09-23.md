# OWNER DECISION PACKAGE — Family determination for the sector-neutral volatility overlay (FWD-PM-VOLEX-SN-001)

**Prepared:** 2026-09-23 (Claude Code, Dell) · **Subject:** `PROTOCOL_DRAFT.md` (2026-09-19, sha256
prefix `f85b78f1f51b9dbb`, commit `c5469ec`) · **Evidence:** `../data_gaps/EXTENDED_PANEL_RESULT_2026-09-19.md`
+ `../data_gaps/scripts/{ext_panel,ext_test}.py` (SHA256SUMS verified OK 2026-09-23)
**Status:** PROPOSED. **Nothing has been applied.** No registry, decision-log, ledger, or draft file
was edited, and **no data was touched to prepare this package** (the re-measurement in §4.4 is
deliberately left un-run, because running it before its bar is frozen would spend the last clean look).

---

## 0. Bottom line

1. **Family: yes, open a new one** — `P-M · Cross-Sectional Volatility {V1}`. No existing family fits,
   and the Owner already declined widening `{T1}` for volatility features on 2026-09-17.
2. **Registration: not yet.** The draft cannot be frozen as written. A pre-registration audit (§2)
   found that the headline evidence row uses a **look-ahead filter**, that **the drafted spec was never
   actually measured**, and that the **decision rule has ~26–46% power** against the effect it expects.
3. **Recommended path (Option B): two acts.** Act 1 (now, **D-053**): fix the family determination,
   approve repaired spec v2, and authorize **one** pre-declared ex-ante re-measurement with a frozen
   bar. Act 2 (**D-054**): register HYP-PM-0013 and open the forward test **only if** that
   re-measurement clears. If it does not clear, nothing is registered and the result is recorded.

---

## 1. What is being decided, and the evidence in one paragraph

Whether, and how, to give the program's only verified positive effect — **within-sector exclusion of
the top-decile Parkinson-60 volatility names from a liquid IDX book** — a registered hypothesis and a
confirmatory forward test. Evidence: on a 26-year panel (43,136 name-months, 780 tickers,
2000-07→2026-07), the sector-neutral overlay increment is **+0.254%/mo, t 4.70** (full) and
**+0.300%/mo, t 3.48** on pre-2021 data that entered none of the ~140 in-sample trials; positive in
every 5-year block; sector neutrality *raises* t in old data (2.22→3.48). The modern-era figure is
lower: **+0.201%/mo, t 3.31** (2021-26, n=67), consistent with the decay seen in the pooled version
(2022 +0.70 → 2026 +0.22 %/mo). It is the **low-volatility anomaly**, globally documented — a
replication, not a discovery. It is an **overlay increment (~+2.4 to +3.6%/yr), not a strategy**,
and it needs ~100+ names.

---

## 2. Pre-registration audit — findings that block freezing the draft as written

Each finding cites the code or document it rests on. F-1 to F-5 are blocking; F-6 to F-8 must be
settled in the spec but are not disqualifying.

### F-1 · The headline "clean" filter looks ahead (BLOCKING)

`ext_panel.py:68` builds `z_fwd` = count of zero-volume sessions in the **21 sessions after**
formation, and `ext_panel.py:74` defines `clean = (z_form == 0) & (z_fwd == 0)`. `ext_test.py`
runs every overlay on `C = S[S.clean]`. The headline row (pre-2021 t 3.48) therefore **drops
name-months that stopped trading during the holding month** — information unavailable at formation.

The draft's §2 freezes only the ex-ante half ("zero zero-volume sessions in the trailing 60"). So
**the spec proposed for freezing is not the spec that was measured.** The draft's reasoning that the
strict filter is "the harder test" is void: its strictness partly comes from the look-ahead.

The row labelled **"forward-only" (the strongest, t 4.22)** by its name conditions on the forward
window only; it must be treated as look-ahead until its code shows otherwise.

### F-2 · Four of the five evidence rows have no committed code (BLOCKING)

`ext_test.py` computes only the `clean` row. The `≤3`, `≤6`, `forward-only`, and `no filter` rows in
`EXTENDED_PANEL_RESULT` §0 are not produced by any committed script. That includes **`no filter`
(pre-2021 t 4.14)** — the only row that looks fully ex-ante (it still requires `fwd.notna()`,
see F-8). The one number that would survive F-1 **cannot be reproduced from the repository.**
This is a reproducibility gap (Invariant 6), not only a documentation gap.

### F-3 · Entry convention mismatch (BLOCKING)

The evidence enters at the **formation-day close**: `fwd = close(t+21)/close(t)` (`ext_panel.py:69`),
with `park60` and `adv60` including day t. That close cannot be traded by a process that computes the
signal after it settles. The draft instead says "first session after month-end, **not at the open**",
which names no price. Fix: enter at `close(t+1)` — the `FWD-PM-VOLEX-001` precedent — and
re-measure under that convention (§4.4).

### F-4 · Endpoint undefined between gross and net (BLOCKING)

The evidence is a **gross** increment with an **iid t** on the monthly series (`ext_test.py::stat`).
The draft's §2 adds "0.60% round trip on realised turnover" without saying whether the endpoint is
gross or net. Fix: **primary = gross increment, iid t** (matches the evidence; the two books'
turnover largely cancels, as `FWD-PM-VOLEX-001` §2 documented). Net increment and Newey-West(3) t are
reported alongside the primary, but neither gates the decision.

### F-5 · The decision rule is roughly a coin flip against the expected effect (BLOCKING)

The draft sets PROMOTE at **t > 2.5 at 36 months** and **t > 3.0 at 60 months**, justified as
"below the in-sample 3.57". But 3.57 is a *search* bar (Bonferroni-140). A frozen, single-endpoint
forward test carries no search penalty, so it has no bearing here. What matters is power.

Monthly sd of the sector-neutral increment: **0.50** (2021-26) to **0.65** (full panel). Normal approximation:

| true effect %/mo | draft 36m t>2.5 | draft 60m t>3.0 | **v2 48m: t>1.68 AND mean ≥ +0.10** |
|---|---|---|---|
| 0.00 (no effect) | 0.01 | 0.00 | **0.05** (false-positive rate) |
| 0.10 (half-decayed) | 0.06–0.10 | 0.04–0.07 | 0.27–0.39 |
| 0.15 | 0.13–0.24 | 0.11–0.25 | 0.47–0.66 |
| **0.20 (modern-era estimate)** | **0.26–0.46** | **0.27–0.54** | **0.68–0.86** |
| 0.25 (full-panel estimate) | 0.42–0.69 | 0.49–0.81 | 0.84–0.96 |

Under the draft rule, a real effect at its modern-era size fails about half the time or more. The
test *could* fail (R2), but it could hardly pass. Also, the draft's own decay floor (§4: "materially
below ~+0.10%/mo … should be rejected") is narrative and **not in the decision rule**. Its stated
expectation (+0.24 to +0.31) uses full-panel numbers, not the lower modern-era +0.20.

### F-6 · §5.2 item 1 (MECHANISM) is not supplied, and the taxonomy has no fitting class

The draft names no M-class, participant class, or constraint. The two standard origination stories
for the low-volatility anomaly are (a) leverage-constrained investors bidding up high-volatility names
and (b) retail lottery preference. Neither matches an entry in `ECONOMIC_MECHANISM_TAXONOMY`: M5.1 is
*delayed incorporation* of information, not overpricing. Adding a class is a CRO amendment to
`01_SCIENTIFIC_FOUNDATION` §3.4 (`MARKET_INEFFICIENCY_TAXONOMY` §6 governance). **Note for the Owner:**
HYP-PM-0010 `{T1}` and HYP-PM-0012 `{R1}` were also registered without an M-class. This is the third
case, so it is worth one line in D-053 (§4.3).

### F-7 · Sector labels are a present-day snapshot applied back to 2000

`ext_panel.py:98` merges `data/sector_map.pkl` (fetched 2026-09-19, 98.6% labelled, 11 sectors). This
applies current classification to 26 years of history — mild look-ahead, likely small, since sector
reclassification is rare. The forward spec must freeze **one** hashed sector source (the pkl, or the
production `ticker_sector` table added 2026-09-19 — not both), and a rule for unlabelled and newly
listed names.

### F-8 · Name-months without a forward price are silently dropped

`S.fwd.notna()` (`ext_panel.py:73`) drops any name-month with no close 21 trading rows later —
delistings, long suspensions, and (pre-2021) gappy series. The horizon is also **row-based**
(`shift(-21)`), not calendar-based. The forward spec must say what a mid-month suspension or delisting
contributes. Proposed rule: last traded close, flagged. The reported survivorship direction
(conservative, since dead names skew high-vol) is plausible but unmeasured.

---

## 3. Options

**A · Register now, as drafted. REJECTED.** F-1 to F-5 would be frozen into a registered spec. Every
later fix would be a supersession (the 001→002 precedent), and results on either side could never be
pooled.

**B · Two acts: repair → one pre-declared ex-ante re-measurement → register if it clears.
RECOMMENDED.** The family determination is made now, so the question the draft raised is answered.
The spec is repaired *before* any forward observation exists, so the eventual read stays clean. The
single remaining in-sample look is spent under a bar frozen in advance, so it cannot become a rescue.
Cost: about one working session, plus a few days of calendar delay before the first formation. Nothing
forward is lost: the first eligible formation is the 2026-10 month-end whether registration happens
today or next week.

**C · Keep it unregistered, like FWD-PM-VOLEX-001. Acceptable fallback.** No family slot is consumed.
But the claim can never reach confirmatory status, and `VOLEX-001` already covers the pooled top-200
version. This is the right choice only if the Owner judges the claim not worth a family (see §4.7:
it is not deployable under the current mandate).

**D · Widen `P-M · Price-Trend {T1}`. REJECTED** — the Owner already declined this on 2026-09-17
(`BOOK_OVERLAY_POLICY.md` §1). Volatility level is not a trend feature, and the widening could never
be undone.

**E · Join `P-A {I2,I3,I8}`, the C-family, or `{I5,I6,I7,I12}`. REJECTED** — no auction, flow, or
inventory instrument is involved. `{R1}` is scoped to short-horizon reversal anti-edges.

---

## 4. Rulings Act 1 would make (confirm or amend each)

### 4.1 Family determination

**`P-M · Cross-Sectional Volatility {V1}`**, opened at the first registration into it (D-028/PG-3
precedent: families open at registration, so this ruling commits the determination and does not
itself consume a slot). **Scope, deliberately narrow:** cross-sectional *volatility-level*
characteristics computed from OHLCV only (range-based or close-to-close realized volatility), applied
as within-universe exclusion or tilt, measured as a book-level increment against the same unfiltered
universe, on the liquid IDX universe.

**Out of scope until a widening amendment:** beta, idiosyncratic volatility against a factor model,
skewness/MAX-type lottery measures, and any flow or fundamental input. Widening is permitted and
cheap; narrowing is impossible. That is why the scope starts narrow.

**Sibling disclosure:** `FWD-PM-VOLEX-001` (open 2026-09-16, unregistered, pooled top-200) measures
the same effect family. It stays **outside** `{V1}` as an unregistered prospective record. Its
outcomes are **not independent** of HYP-PM-0013's: neither may be cited as evidence for the other. If
VOLEX-001 is ever registered, it enters `{V1}` as a counted member.

### 4.2 IDs

Hypothesis **HYP-PM-0013** (0011 reserved-retired per D-052; 0012 taken). Spec id stays
**FWD-PM-VOLEX-SN-001**: it was never opened, so v2 of the draft is not a supersession.

### 4.3 §5.2 intake elements (supplied here, to be carried verbatim into the registration)

- **Mechanism.** Participant class: leverage-constrained and retail investors on IDX, who seek
  exposure through high-volatility names rather than leverage. Constraint: leverage and short-sale
  constraints. Short selling is effectively unavailable on IDX, so overpricing of volatile names is
  not arbitraged down. **No M-class assignment is made:** the taxonomy has no fitting class (F-6).
  Following the D-048 "no taxonomy assignment" precedent, the gap is recorded and referred to the CRO
  as a candidate class amendment. The same gap is noted for HYP-PM-0010 and HYP-PM-0012.
- **Direction.** The within-sector top-decile volatility names underperform the rest of their sector,
  so the overlay increment is **positive**.
- **Null.** Top-decile-volatility names earn the same forward return as their sector peers, and the
  increment is ≤ 0.
- **Scope.** v2 universe (§5), monthly formation, 1-month hold, 2026-10 onward.
- **Ex-ante criterion with effect size.** §4.5 — mean ≥ +0.10%/mo is required, not significance alone.
- **Family.** §4.1.
- **Refutation (one sentence, R14).** *If high-volatility overpricing were not real, IDX names in
  their sector's top volatility decile would earn the same forward return as the rest of the sector,
  and the overlay increment would be zero or negative.*
- **Power (R2).** §2 F-5 table, v2 column.
- **Persistence (R16.2), two barriers from §6.3.** **Constraint barrier:** no short side on IDX.
  **Capacity barrier:** the effect lives in the mid-ADV tercile and fails in the top-ADV tercile
  (every one of 12 specs era-fails there), so it is too small for the capital that could remove it.
  The capacity barrier is supported by the program's own data, not just asserted — but that
  tercile result was measured on the *pooled* (not sector-neutral) version, and capacity for the
  sector-neutral variant is unmeasured (draft §6.5). The §4.4 run reports it by ADV tercile.

### 4.4 The one remaining in-sample look — pre-declared (runs between Act 1 and Act 2)

- **What.** The exact v2 spec (§5), with ex-ante filters only, `close(t+1)` entry, gross increment,
  and iid t, run by a **new committed script** whose sha256 is recorded in D-053's receipt line
  **before** it is executed.
- **Where.** Primary: the pre-2021 panel (2000-07 → 2020-12). Reported but non-gating: full panel
  and 2021-26. The 2021-26 figure is known data and carries no confirmatory weight.
- **Bar (frozen now).** Pre-2021 **t ≥ 2.87** AND mean **≥ +0.10%/mo**. 2.87 is Bonferroni-12,
  two-sided α=0.05, over the ~12 overlay looks already taken on pre-2021 data: 5 filters × pooled or
  sector-neutral, plus the 2010-20 sub-window.
- **If it clears:** Act 2 proceeds with the texts in §6.2.
- **If it fails:** no registration. The result goes into `EXPERIMENT_LEDGER.jsonl` and a dated note
  in this directory. The draft is marked REFUSED-AT-G1, and **no re-cut is permitted** (R15 rescue).
  `BOOK_OVERLAY_POLICY` and `VOLEX-001` are untouched either way; they have their own evidential basis.

### 4.5 Decision rule v2 (replaces draft §3)

- **Primary endpoint:** the monthly gross overlay increment with an iid t; net increment and NW(3) t
  are reported.
- **12 months:** report only. **Early harm stop:** at n ≥ 12, if the mean is below −0.20%/mo, abandon
  the rule (VOLEX-001 precedent).
- **24 months:** interim report only. No decision.
- **48 months: the single decision.**
  - **PASS:** one-sided t > 1.68 **and** mean ≥ +0.10%/mo.
  - **FAIL:** mean < +0.10%/mo. This covers both a decayed effect and a wrong effect; the failure is
    attributed per the F-modes.
  - **INCONCLUSIVE:** anything else. The claim stays parked, and it is never read as a pass.
- **Why 48 months, not 36:** the sd is uncertain (0.50 vs 0.65), and 48 months keeps power ≥ ~0.68 at
  the modern-era effect under the pessimistic sd.
- **Why t > 1.68:** there is one frozen endpoint and one family member, and the search penalty was
  already paid in-sample (§4.4).
- **Months 49–60:** post-decision monitoring. This is not a second gate.

### 4.6 Non-wiring

`BOOK_OVERLAY_POLICY.md` stays bound to `FWD-PM-VOLEX-001` and is not rebased onto this test.
`FWD-PM-REGIME-002` and `FWD-PM-FADE-001` are untouched.

### 4.7 Mandate acknowledgement (the Owner should confirm this explicitly)

A PASS would **not be deployable under the current book mandate**. The overlay needs about 100 names
(IR 0.39 at N=10), and it is negative inside IDX80 (−0.32%/mo; draft §6.2). What registration buys is
**knowledge**: a confirmed or refuted claim, and a candidate for any future broad book. If that is not
worth a family, choose Option C.

---

## 5. Spec v2 — changes from the 2026-09-19 draft

| Element | Draft | v2 |
|---|---|---|
| Tradeability filter | "0 zero-vol in trailing 60" (measured with a look-ahead half) | 0 zero-volume sessions in trailing 60, **ex-ante only**; re-measured in §4.4 |
| Entry | "first session after month-end, not at the open" | **close of the first session after the formation date** (`close(t+1)`); hold to the next formation's entry |
| Formation date | month-end | last **complete** session of the month, using the VOLEX-001 guard (priced-ticker count ≥ 95% of trailing-20 median; `is_final=1`) |
| Sector source | unspecified (evidence: `sector_map.pkl`) | one frozen source, sha256-pinned at registration; unlabelled names form their own bucket, held whole if <10 names |
| Suspension/delisting in hold | silently dropped | last traded close, flagged per name; never dropped |
| Endpoint | "increment", gross vs net unstated | **gross** increment, iid t, primary; net and NW(3) reported |
| Decision | 36m t>2.5 · 60m t>3.0 | **48m single decision**: t>1.68 AND mean ≥ +0.10; FAIL if mean < +0.10; harm stop at n≥12 |
| Expectation | +0.24–0.31 %/mo | **+0.20 %/mo** (2021-26 sector-neutral), with decay explicitly anticipated |
| Mechanism / persistence | absent | §4.3 |

Unchanged: `ADV60 ≥ Rp 1e9`, `close ≥ Rp 50`, ≥ 60 sessions of history, `volume > 0` on the
formation date, Parkinson-60, within-sector top-decile exclusion, sectors < 10 names held whole,
equal weight, monthly rebalance, measurement as an overlay (not a standalone book), and the §5
forbidden list.

---

## 6. Exact texts

### 6.1 Act 1 — `docs/roadmap/DECISION_LOG.md`, append D-053 (apply verbatim on approval)

```markdown
### D-053 · Cross-Sectional Volatility {V1} family determined; FWD-PM-VOLEX-SN-001 spec v2 approved; one pre-declared ex-ante re-measurement authorized; registration deferred to D-054
**Status:** RECORDED · **Date:** <ACT_DATE> · **Type:** Family determination + pre-registration act (D-028/PG-3) ·
**Approval authority:** Owner instruction <ACT_DATE> (approving Option B of
`P-M/forward_volex/OWNER_DECISION_PACKAGE_V1_FAMILY_2026-09-23.md`)

**Family.** The sector-neutral volatility overlay, when registered, enters a NEW family
`P-M · Cross-Sectional Volatility {V1}` — cross-sectional volatility-level characteristics from OHLCV
only, applied as within-universe exclusion/tilt, measured as a book-level increment vs the same
unfiltered universe, liquid IDX. Beta, factor-model idiosyncratic volatility, skewness/MAX measures,
and any flow or fundamental input are out of scope until a widening amendment. The family opens at its
first registration (D-054); this act consumes no slot. FWD-PM-VOLEX-001 remains outside {V1} as an
unregistered prospective record, declared non-independent: neither test may be cited as evidence for
the other.

**Pre-registration audit.** The 2026-09-19 draft was not frozen: its headline "clean" evidence row
conditions on zero-volume sessions in the forward holding window (`ext_panel.py` `z_fwd`); four of the
five evidence rows have no committed code; the entry convention differed between evidence and spec;
and its decision rule had ~0.26–0.54 power at the modern-era effect (+0.20%/mo). Spec v2 (package §5)
repairs all of these before any forward observation exists.

**Pre-declared re-measurement (the last in-sample look).** The exact v2 spec, ex-ante filters,
close(t+1) entry, gross increment, iid t, via script `<SCRIPT_PATH>` sha256 `<SCRIPT_SHA>` (pinned
before execution). Bar: pre-2021 (2000-07..2020-12) t >= 2.87 (Bonferroni-12 over prior pre-2021
overlay looks) AND mean >= +0.10%/mo. Clears → D-054 registers HYP-PM-0013 and opens
FWD-PM-VOLEX-SN-001. Fails → no registration; the result is recorded in EXPERIMENT_LEDGER.jsonl, the
draft is marked REFUSED-AT-G1, and no re-cut is permitted.

**Decision rule v2 (to be frozen at D-054).** 48-month single decision: PASS one-sided t > 1.68 AND
mean >= +0.10%/mo; FAIL mean < +0.10%/mo; otherwise INCONCLUSIVE. Harm stop at n >= 12 if the mean is
< -0.20%/mo. 12- and 24-month reports carry no decision.

**Mechanism.** Leverage- and short-sale-constrained demand for high-volatility names (participant
class: leverage-constrained and retail IDX investors); persistence via the Constraint barrier (no IDX
short side) and the Capacity barrier (effect absent in the top-ADV tercile). No M-class assignment:
ECONOMIC_MECHANISM_TAXONOMY has no fitting class. Referred to the CRO as a candidate class amendment
(01_SCIENTIFIC_FOUNDATION §3.4). The same absence is recorded for HYP-PM-0010 and HYP-PM-0012.

**Mandate acknowledgement.** A PASS is not deployable under the current book mandate (needs ~100+
names; negative inside IDX80). The registration's purpose is knowledge.

**Non-wiring.** BOOK_OVERLAY_POLICY (still bound to FWD-PM-VOLEX-001), FWD-PM-REGIME-002, and
FWD-PM-FADE-001 are untouched.

**Receipts:** package `P-M/forward_volex/OWNER_DECISION_PACKAGE_V1_FAMILY_2026-09-23.md` ·
`P-M/forward_volex/PROTOCOL_DRAFT.md` → v2 (sha256 `<DRAFT_V2_SHA>`) · re-measurement script
`<SCRIPT_PATH>` (sha256 `<SCRIPT_SHA>`).
```

### 6.2 Act 2 — D-054 (drafted only after §4.4 clears; templated on D-052)

Same structure as the R1 package §4a–4e:
- D-054 decision-log entry;
- `P-M/HYP-PM-0013_REGISTERED.md`;
- `HYPOTHESIS_REGISTRY.md`: main row, new `{V1}` family-slot row (member 1), notes paragraph, and
  header bump;
- `forward_volex/ledger.json`, opened empty;
- `PROTOCOL_DRAFT.md` → `PROTOCOL.md` rename with a status line change, sha256 computed after the
  edit and pinned everywhere.

**First eligible formation:** the 2026-10 month-end (or the first month-end after D-054, if later).
The recorder mirrors `forward_exclusion/run_forward.py`: read-only, append-only, calendar-month guard,
and no back-fill before `opened_utc`. The D-054 texts are deliberately not pre-written: their numbers
depend on the §4.4 result.

---

## 7. What this package deliberately does NOT do

- It does not run the §4.4 re-measurement.
- It does not edit `PROTOCOL_DRAFT.md`, which remains at its 2026-09-19 state until Act 1.
- It does not touch the registry, decision log, or any ledger.
- It does not register `VOLEX-001`, rebase `BOOK_OVERLAY_POLICY`, or add a taxonomy class.
- It does not reconsider the dividend draft, whose extended-panel discrepancy remains unexplained
  (`EXTENDED_PANEL_RESULT` §4).

## 8. Execution on approval of Option B

1. Edit `PROTOCOL_DRAFT.md` to v2 (§5) and record its sha256.
2. Write and commit the re-measurement script. Record its sha256. **Do not run it yet.**
3. Append D-053 (§6.1) with the three hashes filled in. Commit:
   `docs(P-M): D-053 -- {V1} family determined, VOLEX-SN spec v2, pre-declared re-measurement`.
4. Run the script once and commit its output and output hash.
5. If the bar clears, prepare D-054 texts (§6.2) for Owner approval. If it fails, record the result
   (§4.4) and stop.
