# D1/D2 Production Semantic Defect Audit — 2026-09-10

**Type:** Read-only audit. **PRODUCTION CHANGES = NONE.**
**Author:** Claude (Sonnet 5), read-only session, 2026-09-10.
**Scope:** Legacy production consumers of `broker_flow` (`investor_type`, `lot`, `lot_value`,
`value`, `value_total`), vs. Dataset A, Dataset B, and P-M research code.

---

## A. Environment / commit / git status

- Repo: `/home/tjiesar/10 Projects/idx-walkforward-5001`
- Branch: `ops/hardening-2026-07-10`
- HEAD: `9b6e3800c3dbdd0e717b00da91f0eccfda0f7226`
- DB: `data/walkforward.db`, accessed throughout via `sqlite3.connect(...)` +
  `conn.execute('PRAGMA query_only=ON')`. No `INSERT`/`UPDATE`/`DELETE`/`ALTER`/`VACUUM`/`CREATE`
  statements were issued against it at any point in this audit.
- **Pre-existing working-tree state** (not caused by this audit — recorded before any inspection
  began): `git status --porcelain=v1` showed 452 entries (187 untracked `??`, 63 modified `M`,
  202 renamed `R`) — a large in-progress `docs/` reorganization (Agent Firm ADRs and Audit reports
  moved under `docs/archive/`) plus modifications to `.gitignore`, `app.py`, `data/db.py`,
  `data/loaders.py`, `deploy/crontab`, and others. **None of this was touched, created, or modified
  by this audit.** The only file this audit created is this report.
- This audit ran no tests, no gatekeeper, no G1, no return/alpha computation, and made no edits to
  `broker_flow`, Dataset A, Dataset B, hypotheses, fetchers, or schemas.

---

## B. D1 findings — `investor_type` misinterpreted as end-investor class

### Ground truth (verified independently, see §I for queries)

`broker_flow.investor_type` takes exactly 3 values: `Asing`, `Lokal`, `Pemerintah`. Cross-checked
against `docs/research_programs/P-M/dataset_b/fingerprint.py`'s `SEMANTIC_REGISTER` (built earlier
today by prior P-M research work in this same session/day, independent of this audit), which
states the verified meaning:

> `"meaning": "Ownership category of the BROKERAGE HOUSE: foreign-owned / local /
> government-state-owned brokerage"` … `"research_use": "say 'foreign-owned brokerage flow'.
> NEVER 'foreign investor flow', 'retail investor flow' or 'institutional investor flow'."`

Evidence backing that classification (from the same register, and independently confirmed by this
audit's own read-only queries): all 95 broker codes carry exactly one `investor_type` each,
invariant across the full history (2025-01-02 → 2026-09-09, 3,026,786 rows); the `Pemerintah`
class has exactly 4 constant members (`CC`, `NI`, `OD`, `DX`).

**No production code was found that labels `investor_type` as "retail investor" or "institutional
investor"** — a targeted search (`grep -rn "retail\|institutional"` cross-referenced against
`investor_type`/`Asing`/`Lokal`/`Pemerintah`/`broker_flow`) returned zero matches outside the LLM
prompt finding in B.1 below. The defect that *is* pervasive is the narrower one: `investor_type='Asing'`
is uniformly relabeled **"foreign"** — and in one place, **"institutional and/or foreign"** — as if
it denoted the class of end-investors placing the order, rather than the brokerage's own ownership
category.

### B.1 — HIGHEST SEVERITY: LLM Agent Firm prompt, live trade-signal review

- **File:** `engine/agent_firm/prompts/flow_v1.md`
- **Lines:** 4, 6–9, 12–13, 21
- **Current interpretation:** The system prompt fed to the "Flow Specialist" LLM agent literally
  instructs it to "decide whether **institutional and/or foreign money** is genuinely accumulating
  or distributing this stock" (line 12–13), based on a field named `net_foreign_14d` described as
  "net foreign lots over the last 14 days" (line 7).
- **Why incorrect:** `net_foreign_14d` is built entirely from `broker_flow WHERE investor_type='Asing'`
  (see B.2/C.4 below) — a filter on brokerage ownership, not on the end-investor placing the order.
  The prompt asks the LLM to reason about "institutional and/or foreign money" — **both** of the
  interpretations the known defect explicitly prohibits — using data that cannot support either
  claim.
- **Downstream impact:** This is not a report label — it is a live input to the multi-provider LLM
  review (`engine/agent_firm/`) that gates real paper-trade execution (per CLAUDE.md: "An optional
  multi-provider LLM 'agent firm' … reviews signals before they trigger trades"). The LLM's
  `flow_verdict` / `smart_money_signal` / `reasoning` output, generated under this false premise, is
  one of the Tier-1 context objects assembled for every `SignalCandidate` at all five live
  construction sites (per CLAUDE.md's ADR-AF-002 closure note: `scheduler/scanner.py` x2,
  `scheduler/jobs.py` x2, `monitor.py` x1).
- **Affects Dataset A/B or legacy production consumer:** Legacy production consumer only (live
  Agent Firm runtime). Dataset A/B are unaffected — see §E/§F.

### B.2 — `engine/agent_firm_context.py::build_flow_context()`

- **Lines:** 151–152 (comment), 165–177, 204
- **Current interpretation:** Computes `net_foreign_14d` from `investor_type='Asing'` rows and
  attaches it to `FlowContext` under that name; the module comment at line 15 calls it
  "`net_foreign_14d`'s SUM."
- **Why incorrect:** Same brokerage-ownership-as-end-investor conflation as B.1; this is the
  function that produces the value B.1's prompt reasons over.
- **Downstream:** `engine/agent_firm/schemas.py` (`FlowContext.net_foreign_14d`, lines 57–58;
  `SignalCandidate.foreign_score`, line 144) → `engine/agent_firm/agents/flow.py` (`foreign_score`
  passed to the LLM at line 32; docstring lines 6–7 repeat "foreign_score" language) → B.1's prompt.
- **Affects:** Legacy production (Agent Firm runtime). Not Dataset A/B.

### B.3 — `engine/risk_score.py::compute_market_risk_score()` / `_foreign_flow_risk()`

- **Lines:** 76 (`_foreign_flow_risk` function name), 108, 117 (docstring: "`foreign_net_5d`: 5-day
  net foreign flow in IDR (negative = outflow)")
- **Current interpretation:** Treats the `investor_type='Asing'`-derived net as "foreign flow" with
  a directional "outflow" reading, feeding 15% weight (`c_foreign * 0.15`) into the composite
  0–100 market risk score.
- **Why incorrect:** Same conflation; "outflow" implies a specific class of market participant is
  net-selling and withdrawing capital, which the underlying data (brokerage ownership, not investor
  class) cannot establish.
- **Downstream:** The composite `score`/`tier` this produces routes real Telegram alerts (see B.5)
  and is exposed via `/api/dashboard/risk` (routes/flow.py) and `/api/v1/market/...`
  (`routes/v1/market.py`, lines 7, 32 — comment-level only, passthrough).
- **Affects:** Legacy production only.

### B.4 — `flow_filter.py::get_foreign_accumulation()` / `get_top_foreign_accumulation()`

- **Lines:** 293–345, 348–374 (docstrings at 294, 298; dict key `foreign_net_lots` at 336;
  ticker-selection query at 360)
- **Current interpretation:** "Net foreign (Asing) flow score" — same "Asing = foreign" labeling.
- **Why incorrect:** Same conflation as above. (Note: this function's *arithmetic* — `SUM(lot)` at
  lines 316–320 — is D2-correct; see §D. The defect here is purely the D1 label, not the math.)
- **Downstream:** Consumed by `scheduler/jobs.py::run_foreign_snapshot()` (B.5) and
  `engine/ticker_detail.py` (lines 300–312, key `foreign_net_lots`, key `foreign_accumulation`).
- **Affects:** Legacy production only.

### B.5 — `scheduler/jobs.py::run_foreign_snapshot()` — live Telegram alert

- **Lines:** 539–577 (docstring 540–542; message text 564, 566, 571, 573: `"🟢 No significant
  foreign buying"`, `"🔴 No significant foreign selling"`)
- **Current interpretation:** A **user-facing Telegram alert**, sent daily at 14:30 WIB, framed as
  "foreign buying"/"foreign selling."
- **Why incorrect:** Same conflation, now reaching an external human reader (the operator) as a
  market-structure claim about foreign investors, not brokerage ownership.
- **Downstream:** Direct Telegram send (`scheduler/CLAUDE.md`'s reporting infrastructure).
- **Affects:** Legacy production only.

### B.6 — `engine/health_report.py` and `engine/risk_alert.py` — Telegram-facing labels

- **Files/lines:** `engine/health_report.py:33,82` (`"Foreign 5d: {…} IDR"`);
  `engine/risk_alert.py:78` (`f"Foreign: {components.get('foreign_flow', '?'):.1f}\n\n"`)
- **Current interpretation:** Both render the B.3 composite-risk "foreign" component directly into
  Telegram messages (the EOD health report and the risk-tier alert).
- **Affects:** Legacy production only.

### B.7 — `engine/premarket_revision.py` — Premarket Briefing

- **Lines:** 145 (`_overnight_foreign_net`), 189, 260–269 (message text: `"settled overnight
  foreign net {…} on …"`)
- **Current interpretation:** Frames overnight brokerage-ownership flow as "foreign" sentiment that
  can revise the frozen EOD trade plan into the 08:45 WIB Premarket Briefing (per CLAUDE.md: "EOD is
  the frozen base plan, Premarket revises it").
- **Downstream:** Directly influences which tickers get carried forward/dropped in the Premarket
  revision, and the accompanying Telegram narrative.
- **Affects:** Legacy production only. (Also a D2 site — see C.5.)

### B.8 — `engine/dashboard.py` — dashboard-facing watchlist ranking

- **Lines:** 77–100 (`_get_foreign_flow`, docstring line 78: "Compute Asing net flow"), 265–286
  (inline duplicate inside `get_watchlist()`), 316–317 (`foreign_net_today`, `foreign_net_3d`
  dict keys), 346–347 (`buy_watch`/`avoid` lists sorted by these fields)
- **Current interpretation:** Ranks the dashboard's "buy watch" and "avoid" ticker lists by
  `foreign_net_today`/`foreign_net_3d`, i.e., presents brokerage-ownership flow as an actionable
  "smart money" signal to the operator.
- **Affects:** Legacy production only (also a D2 site — see C.3).

### B.9 — `engine/premover_detector.py` — pre-market scoring heuristic

- **Lines:** 14, 217 (comment: "positive foreign/smart-money net flow (stockbit)", contributing
  5 of the detector's points)
- **Affects:** Legacy production only.

### B.10 — Naming-convention-only occurrences (low risk, no misinterpretation found)

- `tools/foreign_flow_idx80_gap.py`, `tools/backfill_foreign_flow_idx80.py`,
  `tools/agent_backfill_foreign_flow_idx80.py` — these use "foreign_flow" purely as a *variable/
  module-name shorthand* for "the `investor_type='Asing'` slice of `broker_flow`." The module
  docstring of `tools/foreign_flow_idx80_gap.py` (lines 1–20) is in fact self-aware and precise:
  "'Foreign flow' is the `investor_type='Asing'` slice of that same table." These are gap-detection/
  backfill orchestration tools; they do not make an end-investor claim anywhere, and do not feed a
  report or a trading decision. Flagged as a **naming nit**, not a semantic-correctness defect —
  included in the remediation map (§G) for consistency, not urgency.
- `routes/telegram.py:159,188` — passthrough of already-computed `risk['foreign_flow']`/
  `foreign_net_today` (B.3/B.8's output) into Telegram text; not an independent defect site, just a
  consumer of the upstream label.

### Quantified scope (D1)

- **17 production files** reference `investor_type`/`foreign` in a way that treats
  `investor_type='Asing'` as an end-investor signal (B.1–B.9), of which **9 are primary
  computation/labeling sites** (B.1–B.9 above) and **3 are naming-only** (B.10).
- **Reports/surfaces affected:** EOD/Premarket/Forward-Testing Telegram reports (via
  `engine/health_report.py`, `engine/premarket_revision.py`, `scheduler/jobs.py`), the live
  Agent Firm LLM review (B.1/B.2, gates real paper trades), `/api/dashboard/risk`,
  `/api/dashboard/watchlist`, `/api/v1/market/*`, and the ticker-detail API.
- No occurrence of "retail investor" or "institutional investor" labeling was found tied to
  `investor_type`, **except** the LLM prompt in B.1, which explicitly says "institutional and/or
  foreign" — the single instance where *both* prohibited interpretations co-occur.

---

## C. D2 findings — `BUY_lot_value − SELL_lot_value` used where a signed column already exists

### Ground truth (reproduced independently, see §I)

Confirmed via `PRAGMA table_info(broker_flow)` and direct row inspection:

| Column | Sign convention (verified) |
|---|---|
| `lot` | **Signed** — BUY rows positive, SELL rows negative (e.g. sample SELL row: `lot=-587306`). Matches the known defect's premise exactly: "Stockbit lot is already signed." |
| `value` | **Signed** — BUY rows positive, SELL rows negative (e.g. same row: `value=-384768032500`). `value ≈ lot × 100 × avg_price`. |
| `lot_value` (vendor `blotv`/`slotv`) | **NOT signed** — always non-negative on both sides (`MIN(lot_value)=99` for both BUY and SELL across the whole table). Per `dataset_b/fingerprint.py`'s `SEMANTIC_REGISTER`: *"GROSS shares transacted on the broker's dominant side; non-negative."* It is **not** a per-side Rupiah value comparable in scale to `value`; ratios of `lot_value` to `lot` vary from ~100 to ~714 across sampled rows, confirming it is not simply `lot × price`. |
| `value_total` | Also non-negative both sides — gross exposure, per the same register. |

**Correct research/production net construction:** `SUM(lot)` for a share-count net, or `SUM(value)`
for a signed Rupiah net — **no `BUY − SELL` subtraction needed**, and no `side` filter needed,
because the sign is already carried per-row.

**Incorrect construction found in production (5 sites, all copy-pasted variants of the same
anti-pattern):** `SUM(lot_value) WHERE side='BUY' ...` minus `SUM(lot_value) WHERE side='SELL' ...`.
Because `lot_value` is unsigned on both sides, this subtracts two positive gross-dominant-side
magnitudes — a different (and, per `fingerprint.py`, only "partially verified") quantity from the
signed net that `SUM(lot)`/`SUM(value)` would give directly.

### C.1 — `scheduler/jobs.py`

- **Function:** inline in the job that builds the market health report (around
  `build_market_health_report` call)
- **Lines:** 786–788
  ```
  fb = SUM(lot_value) WHERE investor_type='Asing' AND side='BUY'  AND trade_date in [-7d, today]
  fs = SUM(lot_value) WHERE investor_type='Asing' AND side='SELL' AND trade_date in [-7d, today]
  foreign_net = fb - fs
  ```
- **Correct construction:** `SUM(lot)` (share net) or `SUM(value)` (Rupiah net) over the same
  window and filter, no side split, no subtraction.
- **Downstream:** `compute_market_risk_score()` (B.3) → EOD health report Telegram send
  (`build_market_health_report`, line 792).

### C.2 — `scheduler/scanner.py`

- **Lines:** 1469–1471 — byte-identical pattern to C.1, variable names `_fb`/`_fs`/`_rs_foreign`.
- **Downstream:** Feeds the **live, intraday** market risk score computed on every scan cycle
  (`_compute_risk` at line 1474), which routes into `engine/risk_alert.route_risk_alert()` —
  i.e. this defect can trigger real-time risk-tier Telegram alerts during market hours.

### C.3 — `engine/dashboard.py`

- **Function:** `_get_foreign_flow()` (lines 77–100, two inline copies of the pattern: the nested
  `_net()` helper at 80–89 and the duplicate `today_net` query at 91–99), and again inside
  `get_watchlist()` (lines 265–286, per-ticker `foreign_today`/`foreign_3d` dicts).
- **Downstream:** `get_risk_dashboard()` and `get_watchlist()` — `/api/dashboard/risk` and
  `/api/dashboard/watchlist` API responses, and the `buy_watch`/`avoid` ranking (B.8).

### C.4 — `engine/agent_firm_context.py::build_flow_context()`

- **Lines:** 165–177 (`net_buy`/`net_sell`/`net_foreign_14d = int(net_buy - net_sell)`)
- **Downstream:** The single highest-severity site — this is the exact number the LLM Flow
  Specialist prompt (B.1) reasons over, for every live signal candidate.

### C.5 — `engine/premarket_revision.py::_overnight_foreign_net()`

- **Lines:** 145–160
- **Downstream:** Feeds the 08:45 WIB Premarket Briefing revision logic (B.7) — `foreign["net_lot_value"]
  < 0` / `> 0` branches at lines 260, 266 directly gate revision narrative text.

### C.6 — `routes/flow.py` (`/api/dashboard/risk`)

- **Lines:** 292–299 (`foreign_buy`/`foreign_sell`/`foreign_net = foreign_buy - foreign_sell`)
- Byte-identical pattern to C.1/C.2, independently duplicated for the API route rather than shared
  with `scheduler/jobs.py` or `scheduler/scanner.py`.

### Secondary, smaller-magnitude compounding defect (all 6 sites above)

All six sites filter with `WHERE side='BUY'`/`WHERE side='SELL'` string equality rather than
`sign(lot)`/`sign(value)`. Per `dataset_b/fingerprint.py`'s `SEMANTIC_REGISTER`
(`broker_flow.side`, "VERIFIED WITH DEFECT"): `side` and the sign of `lot`/`value` occasionally
disagree (a vendor rounding artifact). This audit independently reproduced the disagreement count
on the **full, unfiltered `broker_flow` table** (not the Dataset A PIT window that
`fingerprint.py` scoped its own 757/1,822 figures to): **3,585 BUY rows with `lot<0`** and **7,349
SELL rows with `lot>0`**, out of 3,026,786 total rows (≈0.36%). This is a much smaller effect than
the `lot_value`-vs-`lot` unit mismatch above, but it means the six `side`-filtered queries are not
even internally self-consistent with the `lot`/`value` sign convention on every row.

### Quantified example — reproduced independently

Using the exact query from `scheduler/jobs.py:786-788` (market-wide, `investor_type='Asing'`,
7-day trailing window ending `2026-09-09`, the most recent date in the table):

| Quantity | Value (reproduced 2026-09-10) | Previously documented (this session, earlier today) |
|---|---|---|
| `fb` (`SUM(lot_value)`, BUY) | 28,003,292,858 | — |
| `fs` (`SUM(lot_value)`, SELL) | 28,200,203,080 | — |
| **Production `fb - fs`** | **−196,910,222** | **≈ −196.9M** ✅ matches exactly |
| **Correct `SUM(lot)`** (share-lots) | −14,831,553 | — |
| **Correct `SUM(lot) × 100`** (shares) | **−1,483,155,300** | **≈ −1.483B** ✅ matches exactly |
| Correct `SUM(value)` (signed Rupiah, for reference — a third, differently-scaled quantity) | −218,155,569,300 | — |

Both previously-documented consistency-check numbers were **reproduced exactly** from the live
database on 2026-09-10 using only the production code's own query, confirming they were not
mis-transcribed. Note `SUM(value)` gives yet a third number: `lot_value` is not simply a rescaling
of `lot`, and is not the right column to reach for a Rupiah-denominated net either — the only
correct signed-Rupiah-net column is `value` itself, summed directly (no subtraction).

**Sign-agreement rate** (production `fb - fs` formula vs. the correct `SUM(lot)`, per ticker-day,
`investor_type='Asing'`, **full table**, no PIT/date filtering): out of **102,587** ticker-day
observations, **11,235 disagree in sign (10.95%)**. A previously-documented figure from earlier
today cited "11.34% (10,971/96,739)" over a **differently-scoped** (Dataset A PIT-window-filtered,
96,739-observation) population — the two figures are close but were **not reproduced from identical
populations**; both point to the same qualitative finding (roughly 1 in 9 ticker-days flips sign
under the wrong formula), but this audit's own number (10.95% over the full 102,587-row population)
should be treated as this report's reproduced figure, not the earlier 11.34%.

**Magnitude/scope:** `investor_type='Asing'` rows: 1,057,862 of 3,026,786 total broker_flow rows
(872 distinct tickers, 102,587 distinct ticker-dates, 2025-01-02 → 2026-09-09). All five D2 sites
(C.1–C.5) query this population with the defective formula; all are live in the current production
runtime (none behind a shadow flag).

---

## D. Consumers NOT affected (explicitly verified correct)

- **`flow_filter.py::get_foreign_accumulation()`/`get_top_foreign_accumulation()`** (lines
  293–374) — D2-clean: uses `SUM(lot)` directly (lines 316–320), no `BUY − SELL` subtraction. (Its
  *label* is still D1-affected — see B.4.)
- **`stockbit_broker_period.py::_merge_broker_rows()`** (lines 90–129) — a *different* table
  (`stockbit_broker_period`, not `broker_flow`). Explicitly documents "the API returns sell fields
  negative" (docstring, line 93) and computes `sell_value = abs(sval)`, then
  `net_value = buy_value - sell_value`. Algebraically this equals `buy_value + sval` (since
  `sval` is negative) — i.e. it recovers the correctly-signed net. This is a **correct, deliberate,
  self-documented implementation** of the same underlying accounting the D2 sites get wrong — a
  useful positive reference for remediation (§G).
- **`routes/flow.py::api_flow_monitor()`** (`/api/flow/monitor`, lines 18–49) and
  **`engine/trade_flow.py`** (lines 13, 25, 127–195) — both consume `buy_lot`/`sell_lot` from
  `stockbit_flow`/`stockbit_flow_bars`, which are **cumulative, unsigned, intraday bar counters
  from a different vendor concept** (not `broker_flow.lot`, and not `investor_type`-scoped at all).
  Subtracting/differencing them is the correct operation for that data shape; this is not the D2
  defect.
- **`routes/flow.py::api_broker_flow()`** (raw per-ticker/date broker detail, lines 115–144) —
  exposes all 9 raw `broker_flow` columns (including `investor_type`) unmodified, with no relabeling
  and no `BUY − SELL` computation. A correct raw-data passthrough.
- **`stockbit_ownership.py`** — an entirely separate, genuinely end-investor-category dataset
  (share composition by holder type, e.g. "Mutual Funds," "Pension Funds," named entities), fetched
  from a different vendor endpoint (`insider/shareholding/composition`). It does not use
  `investor_type` and is never conflated with `broker_flow` in code.
- **`docs/research_programs/P-M/dataset_b/fingerprint.py`** — the `SEMANTIC_REGISTER` correctly
  documents both defects as ground truth (quoted throughout this report) and is itself the source
  this audit cross-checked against.
- **`tools/backfill_broker_flow*.py`, `tools/backfill_foreign_flow_idx80.py`,
  `tools/agent_backfill_*.py`** — pure ingestion/backfill orchestration; store raw vendor fields,
  compute no net/BUY-SELL aggregate themselves.
- **`research/` package** (`research/statistics.py`, `research/gatekeeper/`, `research/regime/`,
  `research/knowledge/`) — no reference to `investor_type`, `broker_flow`, or foreign-flow
  terminology was found anywhere in this package.

---

## E. Dataset A impact

**NO.**

Evidence: `docs/research_programs/P-M/dataset_b/fingerprint.py`'s module docstring (lines 4–10)
states Dataset A's own F-1 fingerprint pinned "ticker, row count, date range, `SUM(lot)` and
`SUM(lot_value)`" — i.e. Dataset A's own construction already used the D2-correct `SUM(lot)`
aggregation, not `BUY_lot − SELL_lot`. No Dataset A build/fingerprint script was found anywhere
that performs the incorrect subtraction. Dataset A's underlying storage is a frozen snapshot of raw
`broker_flow` rows (including the raw `investor_type` column) — the raw data itself is untouched
by either defect; D1/D2 are defects in downstream *interpretation*, not in the stored data.

## F. Dataset B impact

**NO.**

Evidence: `docs/research_programs/P-M/dataset_b/fingerprint.py`'s `SEMANTIC_REGISTER` (quoted
throughout §B/§C) is the authoritative, already-correct documentation of both defects — it
explicitly warns future research code against `BUY_lot − SELL_lot` and against calling
`investor_type='Asing'` "foreign investor flow." A search of every `.py` file under
`docs/research_programs/P-M/dataset_b/` for the `BUY − SELL` pattern found **only** the
`SEMANTIC_REGISTER`'s own warning string — no actual occurrence of the defect in Dataset B
construction code (`build_calendar_and_roster.py`, `backfill_broker_flow.py`, `gap_classifier.py`,
`validate.py`, `foundation.py`).

---

## G. Proposed future remediation map (NO CODE CHANGES MADE)

Ordered by severity/blast-radius, for a separately-authorized remediation pass:

1. **`engine/agent_firm/prompts/flow_v1.md`** (B.1) + **`engine/agent_firm_context.py::build_flow_context()`**
   (B.2/C.4) — highest priority: this pair both mislabels (D1) and miscomputes (D2) the one number
   that a live LLM uses to gate real paper-trade signals. Fix the SQL to `SUM(lot)`/`SUM(value)`
   (no side split), rename `net_foreign_14d` to something ownership-accurate (e.g.
   `net_foreign_owned_brokerage_lots_14d`), and rewrite the prompt to drop "institutional and/or
   foreign money" language.
2. **`scheduler/scanner.py`** (C.2) — same SQL defect, live on every intraday scan cycle, feeds
   real-time risk-tier Telegram alerts.
3. **`scheduler/jobs.py::run_foreign_snapshot()` / market health report path** (B.5, C.1) — daily
   14:30 WIB and EOD Telegram sends.
4. **`engine/premarket_revision.py`** (B.7, C.5) — feeds the 08:45 WIB Premarket Briefing's
   trade-plan revision logic, not just a label.
5. **`routes/flow.py`** (B.hidden via C.3 duplication, C.6) — `/api/dashboard/risk` API route;
   consider consolidating this and items 1–4 onto one shared helper (candidate:
   `flow_filter.get_foreign_accumulation()`'s already-correct `SUM(lot)` pattern) instead of five
   independently copy-pasted inline SQL blocks.
6. **`engine/dashboard.py`** (B.8, C.3) — `/api/dashboard/watchlist`'s `buy_watch`/`avoid` ranking.
7. **`engine/risk_score.py`** (B.3) — rename `_foreign_flow_risk`/`foreign_net_5d` and its
   docstring once the upstream callers (2–6) are fixed; this function's own arithmetic (a linear
   scale function) is not itself defective, only its naming and its input's correctness.
8. **`engine/health_report.py`, `engine/risk_alert.py`, `routes/telegram.py`** (B.6) — cosmetic
   label fixes once the upstream values are correct; low individual risk but user-visible.
9. **`engine/ticker_detail.py`, `engine/premover_detector.py`** (B.4, B.9) — label fixes.
10. **`tools/foreign_flow_idx80_gap.py` and siblings** (B.10) — naming-convention cleanup only, no
    urgency; already technically self-documenting.
11. Add a `RESEARCH_TABLES`-style guard or lint rule (analogous to the existing
    `test_research_data_fence.py` pattern) that fails CI if a production `.py` file computes
    `SUM(lot_value) ... WHERE side='BUY'` minus the same `WHERE side='SELL'` — to prevent the
    anti-pattern from being reintroduced at a sixth site.

None of the above was executed. This is a map for a separately-authorized change, per the task's
explicit instruction.

---

## H. Risk assessment

| Consumer | Defect(s) | Risk |
|---|---|---|
| `engine/agent_firm/prompts/flow_v1.md` + `agent_firm_context.py` (B.1/B.2/C.4) | D1 + D2 | **HIGH** — gates live paper-trade signal review with a doubly-wrong number and an explicitly wrong LLM instruction |
| `scheduler/scanner.py` intraday risk score (C.2) | D2 | **HIGH** — real-time, feeds automated risk-tier alert routing during market hours |
| `scheduler/jobs.py::run_foreign_snapshot` (B.5) + market health report (C.1) | D1 + D2 | **MEDIUM-HIGH** — daily Telegram sends read directly by the operator as market-structure fact |
| `engine/premarket_revision.py` (B.7/C.5) | D1 + D2 | **MEDIUM-HIGH** — can change which tickers survive into the Premarket Briefing |
| `routes/flow.py` `/api/dashboard/risk` (C.6) | D2 | **MEDIUM** — API consumer-facing, same defect as C.1/C.2 |
| `engine/dashboard.py` watchlist ranking (B.8/C.3) | D1 + D2 | **MEDIUM** — influences an operator-facing "buy watch"/"avoid" ranking |
| `engine/risk_score.py` labeling (B.3) | D1 (label only) | **LOW-MEDIUM** — arithmetic itself is fine; only the semantic frame is wrong |
| `engine/health_report.py`, `engine/risk_alert.py`, `routes/telegram.py` (B.6) | D1 (label only, passthrough) | **LOW** — cosmetic, no independent computation |
| `engine/ticker_detail.py`, `engine/premover_detector.py` (B.4/B.9) | D1 (label only) | **LOW** |
| `tools/*foreign_flow*.py` (B.10) | D1 (naming only) | **LOW** — self-documenting, no misinterpretation |
| `flow_filter.get_foreign_accumulation`, `stockbit_broker_period._merge_broker_rows`, `stockbit_ownership.py`, Dataset A, Dataset B | — | **NONE** — verified correct or out of scope |

---

## I. Reproduction commands/queries

All run with `sqlite3.connect('data/walkforward.db')` + `conn.execute('PRAGMA query_only=ON')`.

```python
# Schema
conn.execute("PRAGMA table_info(broker_flow)").fetchall()

# investor_type / side domain
conn.execute("SELECT DISTINCT investor_type FROM broker_flow").fetchall()
conn.execute("SELECT DISTINCT side FROM broker_flow").fetchall()

# Sign convention check (lot / value signed; lot_value / value_total unsigned)
conn.execute("SELECT side, MIN(lot), MAX(lot) FROM broker_flow GROUP BY side").fetchall()
conn.execute("SELECT side, MIN(value), MAX(value) FROM broker_flow GROUP BY side").fetchall()
conn.execute("SELECT side, MIN(lot_value), MAX(lot_value) FROM broker_flow GROUP BY side").fetchall()

# Reproduce scheduler/jobs.py:786-788 production formula (7d window ending 2026-09-09)
date_str = '2026-09-09'
fb = conn.execute("SELECT SUM(lot_value) FROM broker_flow WHERE investor_type='Asing' AND side='BUY'  AND trade_date<=? AND trade_date>=date(?,'-7 days')", (date_str, date_str)).fetchone()[0]
fs = conn.execute("SELECT SUM(lot_value) FROM broker_flow WHERE investor_type='Asing' AND side='SELL' AND trade_date<=? AND trade_date>=date(?,'-7 days')", (date_str, date_str)).fetchone()[0]
production_foreign_net = fb - fs                      # -196,910,222

# Correct construction
correct_net_lot = conn.execute("SELECT SUM(lot) FROM broker_flow WHERE investor_type='Asing' AND trade_date<=? AND trade_date>=date(?,'-7 days')", (date_str, date_str)).fetchone()[0]
correct_net_shares = correct_net_lot * 100            # -1,483,155,300
correct_net_value = conn.execute("SELECT SUM(value) FROM broker_flow WHERE investor_type='Asing' AND trade_date<=? AND trade_date>=date(?,'-7 days')", (date_str, date_str)).fetchone()[0]  # -218,155,569,300

# Sign-disagreement rate (full table, per ticker-day)
rows = conn.execute("""
    SELECT ticker, trade_date,
        SUM(CASE WHEN side='BUY' THEN lot_value ELSE 0 END) -
        SUM(CASE WHEN side='SELL' THEN lot_value ELSE 0 END) AS prod_formula,
        SUM(lot) AS correct_net
    FROM broker_flow WHERE investor_type='Asing' GROUP BY ticker, trade_date
""").fetchall()
disagree = sum(1 for (_,_,p,c) in rows if (p>0)!=(c>0) and p!=0 and c!=0)
# len(rows)=102587, disagree=11235 (10.95%)

# side vs sign(lot) mismatch, full table
conn.execute("SELECT side, COUNT(*) FROM broker_flow WHERE (side='BUY' AND lot<0) OR (side='SELL' AND lot>0) GROUP BY side").fetchall()
# [('BUY', 3585), ('SELL', 7349)]

# Scope counts
conn.execute("SELECT COUNT(*) FROM broker_flow").fetchone()                                          # 3,026,786
conn.execute("SELECT COUNT(*) FROM broker_flow WHERE investor_type='Asing'").fetchone()               # 1,057,862
conn.execute("SELECT COUNT(DISTINCT ticker) FROM broker_flow WHERE investor_type='Asing'").fetchone() # 872
```

Code searches used (representative, not exhaustive — run from repo root):
```bash
grep -rn "investor_type" --include="*.py" .
grep -rln "[Aa]sing" --include="*.py" .
grep -rln "foreign" -i --include="*.py" .
grep -rn "buy_lot\|sell_lot\|lot_value\|net_lot\|net_foreign\|foreign_net\|SUM(lot" <file>
```

---

## J. Final status

D1 AUDIT = COMPLETE

D2 AUDIT = COMPLETE

PRODUCTION CHANGES = NONE
