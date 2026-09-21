# OWNER DECISION PACKAGE — Open P-M · Price-Reversal {R1}, register HYP-PM-0012, open FWD-PM-FADE-001

**Prepared:** 2026-09-21 (ZCode, Windows) · **Frozen spec being registered:** `PROTOCOL_DRAFT.md`
2026-09-20 v1 + `scripts/fade_failed_breakdown.py` (SHA256SUMS verified OK 2026-09-21)
**Decision required:** one Owner act, three coupled parts (family open + registration + forward-test
open). Nothing has been applied yet; every text below is exact and applies verbatim on approval.

---

## 1. What is being decided, and the evidence in one paragraph

Register the **failed-breakdown anti-edge** (price sweeps intraday below the trailing 20-session low,
then closes back above it — the retail "spring/shakeout" bullish reversal) as the measured claim that
buying it **loses money**: forward excess is negative against BOTH benchmarks, net of 0.60% RT. It is
the strongest in-sample result this program has produced: three independent builds agree within
0.1–0.3pp (h=20: −1.46%/t −5.64 vs IHSG, −1.47%/t −8.20 vs EW-book; ex-2025 −1.88%/t −6.80), breadth
is clean (757 tickers, top name 0.6%), and it clears a Bonferroni correction for the full 18-arm
discovery scan (bar z≈2.99; observed |t| 5.6–12). Unlike every trend result, it does **not** weaken
ex-2025 — it strengthens. The tradeable form, if it replicates forward, is an **avoidance/exit overlay**
on the book (per `BOOK_OVERLAY_POLICY.md`'s two-stage rule), not a strategy and never a short.

## 2. Options

**A (RECOMMENDED): Open the new family {R1}, register HYP-PM-0012, open FWD-PM-FADE-001 now.**
Zero capital risk (the test proposes no entries), near-zero maintenance (docs ledger, one script),
and opening now — before any forward observation exists — is what keeps the eventual read clean.
The program registered {T1}/HYP-PM-0010 on weaker, less-corroborated evidence (ex-2025 t=3.35, no
independent rebuild). Deferral has a real cost: forward observations would accumulate against an
unfrozen endpoint, and any later registration would then have to prove it was not outcome-driven —
exactly the burden the FWD-PM-REGIME-001→002 supersession had to discharge.

**B: Register into an existing family. Rejected.** Not {I5,I6,I7,I12} or the C-family (no flow
instrument). Not {T1}: this is a reversal/anti-momentum pattern — the structural opposite of the
family's enumerated mechanism — and widening {T1} to cover it would be the irreversible, ill-fitting
widening `RESEARCH_PROGRAM.md` §2.1 warns against (the Owner already declined exactly such a widening
for volatility features on 2026-09-17).

**C: Keep as an unregistered prospective record (FWD-PM-VOLEX-001 style). Rejected for this case.**
That status fits overlay-evidence records that support a *registered* test. This is a standalone
falsifiable claim needing its own endpoint; hiding it in a draft would waste the strongest dataset
the program has and leave the multiplicity accounting informal.

## 3. Rulings this act makes (confirm or amend)

1. **Family open: P-M · Price-Reversal {R1}, member 1 = HYP-PM-0012**, per D-028/PG-3. Scope:
   short-horizon reversal / failed-breakout-below-support patterns derived from OHLCV only — no flow
   instrument, no trend features — measured as **negative** forward excess (anti-edges) on the liquid
   IDX universe. Separately denominated from {I5,I6,I7,I12}, the C-family, and {T1}. Widening {R1}
   later is permitted; narrowing or splitting is not. Other 2026-09-17 scan arms (liquidity sweep,
   Wedge Pop, …) remain **unregistered candidates**: a future arm may enter {R1} as slot 2 and
   inherits the scan's multiplicity debt.
2. **Hypothesis ID: HYP-PM-0012, skipping 0011.** ID 0011 appears once in the registry (2026-09-17
   supersession note) as the *conditional* "conservative reading" that was explicitly NOT taken;
   reusing it for a different mechanism would make that note ambiguous forever. 0011 is hereby
   reserved-retired, never assigned; this is recorded in D-052 and the registry note.
3. **Endpoint as frozen** (protocol §3, unchanged): primary = h=20 per-signal excess, BOTH benchmarks
   must clear independently; 12-month PROMOTE track t < −2.5 both; 18-month final t < −3.0 both;
   REJECT if cumulative excess turns positive on either benchmark or <100 distinct signal-dates by
   month 12; decay haircut: forward weaker than −0.5% vs IHSG at month 12 = decayed, not deferred.
4. **First eligible entry: 2026-09-22** (first full IDX session after the act; signals fill at
   next-session open, so nothing is lost by excluding act-day).
5. **Explicit non-wiring:** nothing in this act touches FWD-PM-REGIME-002's entries, exits, or
   ledger. Any overlay built on this signal requires FWD-PM-FADE-001 to clear a §3 checkpoint first.

## 4. Exact implementation texts (apply verbatim on approval)

### 4a. `docs/roadmap/DECISION_LOG.md` — append D-052

```markdown
### D-052 · Price-Reversal {R1} family opened; HYP-PM-0012 (failed-breakdown anti-edge) registered; FWD-PM-FADE-001 opened
**Status:** RECORDED · **Date:** 2026-09-21 · **Type:** Family open + registration act (D-028/PG-3) ·
**Approval authority:** Owner instruction 2026-09-21 (approving Option A of
`P-M/forward_fade/OWNER_DECISION_PACKAGE_R1_OPEN_2026-09-21.md`)

**What was registered.** HYP-PM-0012 — the failed-breakdown anti-edge: low(t) < lo20(t) AND
close(t) > lo20(t) (lo20 = prior-20-session rolling low, shifted 1) on the per-row liquid threshold
universe (`adv20 >= Rp 1e9`, close >= Rp 50, >= 18/20 sessions traded), next-open fill, fixed
h ∈ {5,10,20} holding periods, 0.60% RT, dual benchmark (IHSG + equal-weight liquid book, both
required), one-way entry-date-clustered SE. Registered claim: forward excess is NEGATIVE; the
tradeable form is an avoidance/exit overlay candidate, never a short and never a standalone entry.

**In-sample basis (no confirmatory weight).** Three independent builds agree: h=20 −1.46% (t −5.64,
IHSG) / −1.47% (t −8.20, EW-book); ex-2025 −1.88% (t −6.80, IHSG); 12,131 signals, 757 tickers, top
name 0.6%. Discovery debt: 2026-09-17 ~12-arm pattern scan (+6 strictness variants); Bonferroni-18
bar (z ≈ 2.99) cleared by every reported horizon.

**Endpoint (frozen, protocol §3).** 12-month PROMOTE track t < −2.5 on BOTH benchmarks; 18-month
final t < −3.0 both; REJECT if cumulative excess >= 0 on either benchmark or <100 distinct
signal-dates by month 12; decay haircut −0.5% vs IHSG at month 12.

**Family.** P-M · Price-Reversal {R1} opened at this registration, member 1 of the family, scope:
OHLCV-only short-horizon reversal anti-edges, separately denominated from all existing families.
Widening permitted; narrowing/splitting not.

**ID numbering ruling.** HYP-PM-0011 is reserved-retired (referenced only as the untaken
"conservative reading" in the 2026-09-17 FWD-PM-REGIME-001→002 supersession note); this registration
takes HYP-PM-0012.

**Non-wiring clause.** FWD-PM-REGIME-002 is untouched. Any overlay use requires FADE-001 to clear a
§3 checkpoint first (BOOK_OVERLAY_POLICY §4 two-stage rule).

**Receipts:** `P-M/forward_fade/PROTOCOL.md` (registration sha256 `<SHA_AT_OPEN>`) ·
`P-M/forward_fade/ledger.json` (opened empty; first eligible entry 2026-09-22) ·
`P-M/HYP-PM-0012_REGISTERED.md` · `scripts/fade_failed_breakdown.py` (SHA256SUMS verified 2026-09-21).
```

### 4b. `docs/research_programs/P-M/HYP-PM-0012_REGISTERED.md` (new)

```markdown
# HYP-PM-0012 — REGISTERED

**Registered:** <ACT_UTC> · **Program:** P-M · **Family:** Price-Reversal {R1} (member 1)
**Spec id:** FWD-PM-FADE-001 · **Status:** REGISTERED → IN_TESTING
**Frozen protocol:** `P-M/forward_fade/PROTOCOL.md` · sha256 `<SHA_AT_OPEN>`
**Ledger:** `P-M/forward_fade/ledger.json` (opened empty; no back-fill permitted)

## Mechanism

Failed-breakdown anti-edge. A liquid IDX name sweeps intraday below its trailing 20-session low,
then closes back above it — the widely-taught bullish "stop-hunt/spring/shakeout" reversal. The
registered claim inverts the retail reading: uninformed buying attracted by the popular pattern
underperforms net of cost, so forward excess after the signal is NEGATIVE. Signal: low(t) <
lo20(t) and close(t) > lo20(t), lo20 = prior-20-session rolling low shifted 1; per-row liquid
threshold universe; next-session-open fill; fixed 5/10/20-session holds; 0.60% RT. No entry is
proposed: the eventual tradeable form is an avoidance/exit overlay (BOOK_OVERLAY_POLICY two-stage
rule), never a short.

## Frozen endpoint and decision rule

Primary endpoint: per-signal h=20 excess vs BOTH benchmarks (IHSG; equal-weight liquid book),
one-way entry-date-clustered SE. Both must clear independently.

- 12 months: PROMOTE track requires t < −2.5 on both AND cumulative excess negative on both.
- 18 months (final): PROMOTE requires t < −3.0 on both.
- REJECT at any checkpoint: cumulative excess turns >= 0 on either benchmark, or < 100 distinct
  signal-dates by month 12 (dead-signal guard).
- Decay haircut (pre-declared): forward h=20 vs IHSG weaker than −0.5% at month 12 = decayed
  in-sample estimate, not a deferred confirmation.

## Backtest reference (in-sample discovery, no confirmatory weight)

12,131 signals / 1,151 dates / 757 tickers, 2021-07-05 → 2026-07-29. h=20: −1.46% vs IHSG
(t −5.64), −1.47% vs EW-book (t −8.20); ex-2025 −1.88% (t −6.80, IHSG). Three independent builds
(original scan, its self-audit next-open correction, this spec's from-scratch rebuild) agree within
0.1–0.3pp. Bonferroni-18 (full discovery scan) cleared at every horizon.

## Family declaration (binding, append-only)

**P-M · Price-Reversal {R1}** — short-horizon reversal / failed-breakout patterns derived from
OHLCV only (no flow instrument, no trend features), measured as negative forward excess, liquid IDX
universe. Opened at this registration per D-028/PG-3, Owner ruling D-052. Widening {R1} later is
permitted; narrowing or splitting it is not. Other 2026-09-17 scan arms remain unregistered
candidates; any arm later registered into {R1} inherits the scan's multiplicity.

## Disclosed prior search

Arm P3a of `P-M/pattern_scan/PATTERN_SCAN_2026-09-17.md` (~12 arms + 6 strictness variants on one
corpus). Mechanism argument is post-hoc plausibility for a search-discovered effect, carried
honestly in PROTOCOL §0/§8. The close-fill bias the scan found in itself (§7 there) is designed
out here from the start (next-open fill).

## Carried limitations

No dedicated split-continuity audit for this universe (±35% contamination guard only, §8.3);
fixed-horizon event study, no claim about optimal holding; overlay application (entries vs exits)
deliberately unscoped until a checkpoint clears; ADV20 threshold proxy, not real IDX80 history
(re-derive before operational use); costs are the repo authority, not broker-quoted.

**ID note:** 0011 reserved-retired (untaken conditional reading, 2026-09-17 supersession note);
D-052 assigns 0012.
```

### 4c. `HYPOTHESIS_REGISTRY.md` — three edits + header bump

Main table (after the HYP-PM-0010 row):
```
| **HYP-PM-0012** | P-M · **Price-Reversal {R1}** (NEW family) | failed-breakdown anti-edge: sweep below the trailing 20-session low then close back above → **negative** forward excess (avoidance/anti-edge; no entry, never a short) | **REGISTERED → IN_TESTING** 2026-09-21 · forward test **FWD-PM-FADE-001 OPEN**, ledger empty (0 signals), first eligible entry 2026-09-22 | [[HYP-PM-0012_REGISTERED]] · `P-M/forward_fade/PROTOCOL.md` — registration sha256 `<SHA_AT_OPEN>` · spec frozen 2026-09-20 v1 (`scripts/fade_failed_breakdown.py`, SHA256SUMS) | **Price-Reversal {R1} opened** (1st member) |
```

Family-slot ledger (new row after Price-Trend):
```
| **P-M · Price-Reversal** | {R1} | **1** — HYP-PM-0012 (REGISTERED, in forward test) | family opened at this registration (D-028, PG-3), owner decision 2026-09-21 (**D-052**). Scope: OHLCV-only short-horizon reversal anti-edges (negative forward excess), liquid IDX. Separately denominated from {I5,I6,I7,I12}, the C-family, and {T1}. Discovered in the 2026-09-17 ~12-arm pattern scan; the scan's multiplicity is carried by this registration (Bonferroni-18 cleared in-sample) and inherited by any future arm registered from it. Widening {R1} permitted; narrowing or splitting not. HYP-PM-0011 reserved-retired, never assigned (D-052). |
```

Notes section (new paragraph, after the pattern-scan note):
```
- **HYP-PM-0012 (Price-Reversal {R1}, opened 2026-09-21)** — registered under **D-052** per Owner
  instruction (decision package `P-M/forward_fade/OWNER_DECISION_PACKAGE_R1_OPEN_2026-09-21.md`,
  Option A). Failed-breakdown anti-edge: sweep below the trailing 20-session low, close back above
  → forward excess NEGATIVE vs both benchmarks, net of 0.60% RT. In-sample: h=20 −1.46%/t −5.64
  (IHSG), −1.47%/t −8.20 (EW-book), ex-2025 −1.88%/t −6.80; 12,131 signals, 757 tickers, top name
  0.6%; three independent builds agree within 0.3pp; Bonferroni-18 cleared. Endpoint: 12-month
  t < −2.5 BOTH benchmarks, 18-month t < −3.0 both; REJECT if cumulative excess >= 0 on either or
  <100 signal-dates by month 12; decay haircut −0.5% at month 12. Anti-edge only — no entry, never
  a short; any overlay use requires a §3 checkpoint first (BOOK_OVERLAY_POLICY §4) and FWD-PM-
  REGIME-002 is untouched. HYP-PM-0011 reserved-retired, never assigned (D-052).
```

Header: `**Last updated:** 2026-09-21`.

### 4d. `forward_fade/ledger.json` (new, opened empty — schema drafted now, timestamps at execution)

Same conventions as `forward_regime/ledger.json`: append-only, one object per signal written when
its h=20 window closes (or is censored at data end), no back-fill before `opened_utc`. Per-signal
fields: `ticker`, `signal_date` (t), `entry_date` (t+1), `entry_open`, and per-horizon results for
h ∈ {5,10,20}: `exit_date`, `exit_close`, `gross_return`, `net_return`, `ihsg_return`, `excess_ihsg`,
`ewbook_return`, `excess_ewbook`, plus `censored` flag and `generated_utc`. `trades: []`,
`hypothesis_id: "HYP-PM-0012"`, `spec_id: "FWD-PM-FADE-001"`, `first_eligible_entry: "2026-09-22"`,
`protocol_sha256` = `<SHA_AT_OPEN>`.

### 4e. `forward_fade/PROTOCOL_DRAFT.md` → `PROTOCOL.md` (rename + status act)

`git mv`, then two line-level changes only: title `DRAFT, PRE-REGISTERED SPEC, NOT REGISTERED` →
`REGISTERED 2026-09-21 (HYP-PM-0012, D-052) — FWD-PM-FADE-001`, and Status line → `REGISTERED →
IN_TESTING. Family: P-M · Price-Reversal {R1} (member 1).` plus a dated one-line registration note
at the top of the amendment area: sections 1–9 unchanged. `<SHA_AT_OPEN>` is computed AFTER this
edit and pinned in 4a–4d.

## 5. What this act deliberately does NOT do

No overlay wiring into FWD-PM-REGIME-002; no other pattern-scan arm registered; no change to the
TREND drafts or the vol overlay; no short-side reading of the signal; no parameter tuned (spec is
the 2026-09-20 v1 freeze, hash-verified today).

## 6. Execution on approval

One commit, message: `docs(P-M): open Price-Reversal {R1} -- register HYP-PM-0012 (failed-breakdown
anti-edge), open FWD-PM-FADE-001 (D-052)` — containing 4a–4e and this package. Order: rename+status
edit → compute sha → ledger → REGISTERED doc → DECISION_LOG → registry → commit.
