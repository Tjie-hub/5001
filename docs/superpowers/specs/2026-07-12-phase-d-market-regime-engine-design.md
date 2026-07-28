# Phase D — Market Regime Engine (Design)

**Status:** design approved 2026-07-12 · **Track:** Research Master Plan v2, Phase D
**Prereq:** Phase C Statistical Gatekeeper (committed `7338a29`, `f796bfe` on `ops/hardening-2026-07-10`)
**Deliverable of this session:** spec → implementation plan → **full TDD build**, engine populated/validated on **NR7 as the golden reference**; the other 13 roster strategies are a documented follow-up run.

---

## 1. Objective

Determine **under which market regimes an edge exists**, and attach a required
**regime profile to every strategy**. Phase D *produces* the regime taxonomy and
per-strategy profiles that Phase C *consumes*; it makes **no promotion decisions**
and **changes no production regime usage** (both explicit non-goals).

## 2. Decisions locked in brainstorming

| # | Decision | Choice |
|---|---|---|
| 1 | Deliverable scope | Spec → plan → full TDD build |
| 2 | Taxonomy structure | **Hierarchical** — primary axis = 3-class regime (unchanged multiplicity family); vol & liquidity are **secondary conditioners** that enter a strategy's family **only when its edge is shown to depend on them** |
| 3 | Regime granularity | **Per-ticker** entry regime for edge cells (consistent with Phase C and the validated NR7_BULL cell) + a **market-wide (IHSG) transition detector** layered on top as context/overlay |
| 4 | Build population | Engine fully built + **NR7 golden reference** populated/validated live; batch-populate the other 13 as a follow-up |

## 3. Motivating finding — the current family is a flat placeholder

`research/gatekeeper/gate_config.yaml` (v1) pre-registers the multiplicity family as:

```yaml
family:
  regimes: [BULL, BEAR, SIDEWAYS, HIGH_VOL, LOW_VOL, HIGH_LIQ, LOW_LIQ]
```

This is **7 flat siblings** feeding the DSR `n_trials` denominator. But:

- A trade is exactly **one** of BULL/BEAR/SIDEWAYS (mutually exclusive), yet is
  *simultaneously* one vol-tier and one liq-tier — the four vol/liq labels are
  **orthogonal to** regime, not siblings of it.
- No conditioner tags trades with `HIGH_VOL`/`LOW_VOL`/`HIGH_LIQ`/`LOW_LIQ` today, so
  those four cells are **always empty**. In `stage_multiplicity` they enter
  `family_pvalues` as `p=1.0`, making Bonferroni/BH divide by **7 tests instead of 3**
  — a stricter denominator **carrying no edge**, a pure artifact. (Note: DSR's `n_trials`
  is *separately* derived from the non-empty scan cells — `len(scan_sharpes)`, already 3 —
  so DSR is unaffected by this list; only the Stage-3 multiplicity denominator is.)

Phase D replaces this flat list with the hierarchical structure (§5) and implements
the conditioners that were only ever named as placeholders. See §7 for the exact,
pre-registered effect this has on NR7's committed Phase C decision.

## 4. Architecture — `research/regime/` package

New package, read-only w.r.t. production, mirroring the `research/gatekeeper/` layout.

| Module | Responsibility | Depends on |
|---|---|---|
| `taxonomy.py` | Canonical cell definitions: the 3 **primary** regimes + the 2 **declarable** conditioning axes (vol, liq). Single source of truth for "what cells exist" and which axis is primary vs declarable. Carries `TAXONOMY_VERSION`. | — |
| `conditioners.py` | Pure functions tagging a trade/bar with **vol-tier** (HIGH/LOW) and **liq-tier** (HIGH/LOW) from pre-registered cut-points. | `engine/regime_filter`, `engine/liquidity` |
| `transitions.py` | Market-wide (IHSG) regime-transition detector: labels each date `STEADY`/`TRANSITION` + direction. | `engine/regime_filter.detect_regime` |
| `profile.py` | Builds a **per-strategy regime profile**: per primary regime cell a verdict `PRESENT/ABSENT/REVERSED` + evidence, plus a secondary conditioning check that may mark an axis `DECLARED` for a (strategy, regime). | `research/nr7_study`, `research/statistics` |
| `storage.py` | Append-only `regime_profiles` + `regime_profile_cells` tables; fingerprinted like `gate_decisions`. | `data.db` |
| `config.py` | Loads pre-registered thresholds/cut-points from `regime_config.yaml`. | — |
| `cli.py` | Populate/query entrypoint. | all above |

**Package invariant:** the hierarchy is enforced at the module boundary. `taxonomy.py`
marks regime as *always* in the family and vol/liq as *declarable*; only `profile.py`
can promote an axis to `DECLARED`, and only past the pre-registered evidence bar. No
other module can widen a family.

## 5. Taxonomy (`taxonomy.py`)

- **Primary partition** (mutually exclusive, always in the multiplicity family):
  `BULL`, `BEAR`, `SIDEWAYS` — from `engine/regime_filter.detect_regime` at the
  trade's per-ticker entry bar (identical to `research/studies/regime_edge_scan._regime_at`).
- **Declarable axes** (orthogonal sub-partitions **within** a regime cell):
  - `vol` → tiers `HIGH_VOL` / `LOW_VOL`
  - `liq` → tiers `HIGH_LIQ` / `LOW_LIQ`
- A cell key is `(regime[, vol_tier][, liq_tier])`. The **default** family is regimes
  only (`{BULL, BEAR, SIDEWAYS}`). An axis appears in a strategy's family **only** when
  `profile.py` marks it `DECLARED` for that (strategy, regime).
- `TAXONOMY_VERSION` is stamped on every profile so a taxonomy change starts a new
  lineage (same discipline as `config_hash`).

## 6. Conditioner cut-points (`conditioners.py`, pre-registered in `regime_config.yaml`)

Pure, deterministic, no look-ahead — all computed from data **available at the entry bar**.

- **Vol-tier** (per-ticker, market-context-free by default): realized volatility (or ATR%)
  over a trailing window, compared to that ticker's own trailing-history **median**.
  `HIGH_VOL` if ≥ median at entry, else `LOW_VOL`. The window and the median-lookback are
  pre-registered constants. (Median split chosen over a global percentile so the tier is
  self-relative and robust to universe composition.)
- **Liq-tier** (per-ticker): 30-day ADV value (`engine/liquidity.get_adv_value_30d`) vs a
  pre-registered ADV threshold, tiered relative to the eligible universe. Liquidity remains
  an **eligibility filter** in production (`VALUE_LIQ_MIN_IDR`); here it is only a
  *descriptive conditioning tier*, never a new eligibility gate.

Cut-points live in `regime_config.yaml` with a `version`; bumping the version starts a new
profile lineage.

## 7. Data flows

### Flow A — build a strategy's regime profile (`profile.py`)

```
collect OOS trades (reuse gatekeeper collector / regime_edge_scan machinery)
  → tag each trade: primary regime (per-ticker, at entry) + vol-tier + liq-tier
  → group into primary regime cells (BULL / BEAR / SIDEWAYS)
  → per cell, verdict via research.statistics bootstrap CI (N checked FIRST):
       if N < min_n_cell            → ABSENT, flagged `insufficient=true` (CI not trusted)
       elif CI lower bound > 0      → PRESENT   (edge present)
       elif CI upper bound < 0      → REVERSED  (edge is negative here)
       else                         → ABSENT    (CI straddles 0 → no edge)
  → secondary conditioning check per PRESENT cell:
       split that cell's trades by vol-tier (then liq-tier);
       if |expectancy(HIGH) − expectancy(LOW)| clears the pre-registered
       conditioning bar with non-overlapping CIs → mark that axis DECLARED
       for this (strategy, regime)
  → write profile + cells (append-only, fingerprinted)
```

Verdict thresholds (`min_n_cell`, CI level/boot) default to the Phase C /
`nr7_study.THRESHOLDS` constants so Phase D starts consistent with today's discipline.
The conditioning bar is a **new** pre-registered constant in `regime_config.yaml`.

### Flow B — market-wide transition detection (`transitions.py`)

```
IHSG daily series → detect_regime per bar (rolling)
  → STEADY vs TRANSITION (regime changed within the last K bars)
  → direction (e.g. BULL→SIDEWAYS)
```

Descriptive/context only. It **does not re-key edge cells**. `profile.py` may attach a
"transition-sensitivity" note to a cell's `evidence_json` (e.g. trades entered in
`TRANSITION` windows underperform), but that is evidence on the existing per-ticker cell,
not a new cell dimension. K is pre-registered.

**Boundary:** Flow A owns **edge attribution** (per-ticker). Flow B owns **market context**
(IHSG). They meet only inside `profile.py`.

## 8. Storage (`storage.py`) — append-only, fingerprinted

**`regime_profiles`** — one row per (strategy, run):
`profile_id` (PK), `strategy_fn`, `config_hash`, `taxonomy_version`,
`corpus_fingerprint`, `created_at`.

**`regime_profile_cells`** — one row per (profile, regime cell):
`cell_id` (PK), `profile_id` (FK), `regime`, `verdict` (PRESENT/ABSENT/REVERSED),
`n_trades`, `mean_net`, `ci_low`, `ci_high`,
`vol_axis_declared` (bool), `liq_axis_declared` (bool),
`evidence_json` (conditioning splits + transition-sensitivity note).

Both tables: `CREATE TABLE IF NOT EXISTS` by readers allowed; **never UPDATE/DELETE** —
a re-run inserts a new `profile_id` (full lineage preserved), exactly like `gate_decisions`.

## 9. Phase C integration — the "widen-only-on-declared-evidence" contract

Completion criterion: *"the taxonomy is the canonical input to C's multiplicity correction."*

1. **`taxonomy.py` is the single source** of the primary regime list. `gate_config.yaml`
   is bumped to **v2**: its `family.regimes` becomes `[BULL, BEAR, SIDEWAYS]` (the flat
   vol/liq placeholders removed — §3). Because the config file *is* the pre-registration
   (its literal values feed `config_hash`), it stays a frozen literal rather than importing
   the taxonomy at load time; a consistency test
   (`test_gate_config_family_is_the_taxonomy_primary_regimes`) asserts the frozen literal
   equals `taxonomy.PRIMARY_REGIMES`, so any drift between the two fails CI. Likewise
   `regime_config.taxonomy_version` is pinned to `taxonomy.TAXONOMY_VERSION` by test.
2. **Per-candidate widening.** When Phase C builds a candidate for strategy *S* with
   governing regime *R*, it queries *S*'s latest `regime_profile`. If `vol` (or `liq`) is
   `DECLARED` for cell *R*, Phase C widens **that strategy's** family to include the
   corresponding sub-cells for the DSR `n_trials` + p-value set. If nothing is declared
   (the expected default), the family stays regime-only — **identical to today minus the
   empty placeholders**.
3. **Direction guarantee:** Phase D can only ever *widen* a family on positive conditioning
   evidence; it can **never silently loosen** the gate.

**Effect on NR7's committed Phase C decision (pre-registered, honest):**
NR7 → BULL cell `PRESENT`. NR7's final verdict is **REJECT at `walk_forward`** (BULL
consistency 46.8% < 50%), and walk-forward consistency is independent of the multiplicity
family — so **the REJECT verdict is unchanged**. The only intermediate change:
`stage_multiplicity`'s denominator drops from **7 tests to 3** (the empty vol/liq
placeholders removed), which makes Bonferroni/BH *less* strict — and NR7 already **PASSED**
multiplicity at 7, so it still passes at 3. **DSR is unaffected** (its `n_trials` already
derives from the 3 non-empty scan cells, not from this list). This family change is enacted
via a `gate_config.yaml` **version bump** (new `config_hash`, new decision lineage) — the
exact discipline the config's own comments require. The golden regression (§10) pins:
verdict stays REJECT-at-walk_forward; multiplicity stays PASS.

> **Prediction corrected by the live run (2026-07-12).** The design originally predicted
> NR7 would declare **no** conditioning axis. The live build (§10) falsified that: NR7's
> BULL cell **declares the liquidity axis** (its edge is liquidity-conditional). This does
> **not** change the committed Phase C decision, because the live `build_candidate →
> profile lookup → sub-cell population` path is deferred (see §10 note + §12); the widening
> hook is wired and unit-tested but not fed by a live profile this session. When that
> wiring lands, NR7's BULL family would widen to `BULL::HIGH_LIQ` / `BULL::LOW_LIQ` —
> making multiplicity **stricter**, never looser (the direction guarantee holds).

## 10. Testing (TDD)

Suite under `tests/regime/`, mirroring `tests/gatekeeper/`.

**Unit (synthetic, deterministic):**
- `taxonomy.py` — cell enumeration; primary-vs-declarable classification; `TAXONOMY_VERSION` stability.
- `conditioners.py` — vol-tier & liq-tier on hand-built series; boundary cases at the median/threshold cut; no-look-ahead (tier at bar *t* uses only ≤ *t* data).
- `transitions.py` — a synthetic IHSG series crossing BULL→SIDEWAYS→BEAR; assert STEADY/TRANSITION labels + direction land on the correct bars incl. the K-bar window edges.
- `profile.py` — deterministic trade sets producing a PRESENT cell (CI>0), an ABSENT cell (CI straddles 0), a REVERSED cell (CI<0); assert verdicts. Engineered high-vs-low-vol gap → axis DECLARED; no gap → NOT declared. Reuses Phase C's exact-sample-statistics fixture helper.
- `storage.py` — write/read round-trip; append-only (re-write ⇒ new row, never mutate); fingerprint determinism.

**Integration:**
- **Golden regression (linchpin):** on the Phase C v2 family `[BULL,BEAR,SIDEWAYS]`,
  `stage_multiplicity` with NR7's BULL-significant p-values stays **PASS** (family dropped
  from 7 labels to 3; DSR `n_trials` already 3, unchanged) — so NR7's verdict remains
  **REJECT at `walk_forward`**. (This test drives the stage directly and does not depend on
  NR7's live axis declarations.)
- Phase C candidate build reads a **synthetic** profile with a DECLARED vol axis → its
  multiplicity family widens to include the vol sub-cells.
- Write-fence: add `regime_profiles`, `regime_profile_cells` to `RESEARCH_TABLES` in
  `tests/test_research_data_fence.py`; assert no production scope writes them.

**Live validation (NR7 golden reference — run once, recorded here on build):**
- Real profile build on NR7 over the liquid universe; record BULL/BEAR/SIDEWAYS verdicts +
  any declared axes into this spec as the reference result.
- Assert full `pytest` green and **no production code path changed** (Phase C held the same
  bar: 1433 passed, prod untouched).

**Recorded live NR7 golden reference (2026-07-12, `DB_PATH` = copy of prod `walkforward.db`,
as_of 2026-07-10, canonical 187-ticker `liquid_universe`, 1108 trades):**

| Regime | Verdict | n | CI (net %/trade) | mean | vol axis | liq axis |
|---|---|---|---|---|---|---|
| BULL | **PRESENT** | 333 | [+0.324, +2.056] | +1.197 | — | **DECLARED** |
| BEAR | ABSENT | 156 | [−1.066, +2.051] | +0.432 | — | — |
| SIDEWAYS | REVERSED | 619 | [−1.352, −0.447] | −0.905 | — | — |

- **Fidelity check PASSED:** the BULL cell (n=333, CI [+0.324, +2.056], +1.197%) reproduces
  Phase C's committed live run **exactly** — the collector uses the same canonical corpus.
- **Finding — NR7's BULL edge is liquidity-conditional (pre-registered declaration):**
  splitting the BULL cell by liq-tier gives **LOW_LIQ** (ADV Rp 5–10bn) n=201 **+2.29%** vs
  **HIGH_LIQ** (ADV ≥ Rp 10bn) n=132 **−0.47%**; gap 2.76%, **disjoint CIs**. The edge lives
  in smaller liquidity-floor-passing names and *reverses* on mega-caps — pooling both tiers
  dilutes a real +2.29% edge to +1.20%. This is a genuine Phase D discovery, not an
  artifact; the design's original "no axis declared" prediction is corrected (§9). The
  conditioning bar (`min_gap_pct=0.50`, disjoint-CI) was pre-registered *before* this run —
  it was **not** tuned to this result. Follow-up in §12.
- **A collector fidelity bug was found and fixed during this validation:** the default
  universe must be the 187-ticker `liquid_universe` (Phase B/C corpus), **not** the full
  958-ticker `ohlcv` set. An unfiltered universe inflated the corpus to 6107 trades and
  corrupted the regime cells; regression test
  `test_collect_defaults_to_liquid_universe_not_all_tickers` locks the correct universe.
- Full suite **1464 passed** (Phase C baseline 1433 + 31 new regime tests); no production
  code path changed.

> **Live-wiring scope note:** the golden regression tests `stage_multiplicity` on the v2
> 3-regime family directly; it does **not** depend on NR7 declaring zero axes. The live
> `build_candidate → profile lookup → sub-cell population` path that would feed the declared
> liq axis into Phase C is **deferred** (§12) — so the recorded declaration does not alter
> the committed NR7 REJECT this session.

## 11. Non-goals

- No promotion decisions (Phase C owns those).
- No change to production regime usage (`detect_regime`, macro overlay, scanner gates stay as-is).
- No new eligibility gate from liquidity tiers (production keeps `VALUE_LIQ_MIN_IDR`).
- No batch population of the other 13 roster strategies in this session (documented follow-up).

## 12. Open follow-ups (post-build)

- **NR7 BULL `LOW_LIQ` refinement (from the live finding, §10):** evaluate whether the
  `BULL::LOW_LIQ` sub-cell (+2.29%, n=201) clears the full Phase C gate on its own
  (CI / PSR / DSR / WF / OOS) — i.e. whether the *real* NR7 edge should be re-specified as
  BULL ∧ LOW_LIQ rather than pooled BULL. Pre-register the sub-cell as a hypothesis before
  running (it was discovered post-hoc, so it needs its own out-of-sample confirmation).
- **Wire the live Phase C consumption of profiles:** `build_candidate` looks up a strategy's
  latest `regime_profile` and populates `meta["declared_labels"]` + splits the governing
  regime cell into `regime::tier` sub-cells, so the declared-axis widening (already hooked +
  unit-tested) actually fires in the live gate.
- Batch-populate regime profiles for the full 14-strategy roster (the literal Phase D
  completion criterion) via a `cli.py` scan run.
- Feed transition-sensitivity into Phase C as an optional evidence stage (deferred; Phase D
  only attaches the note).
