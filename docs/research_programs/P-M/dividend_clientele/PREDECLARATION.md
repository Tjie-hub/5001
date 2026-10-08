# PREDECLARATION — dividend clientele D1/D2 (HYP-PM-0017 draft), G0 freeze

**Status:** frozen before any outcome is read · **Date:** 2026-10-08 ·
**Authority:** **D-073** (mechanism accepted, owner 2026-10-08: "D first", "2%"), brief
`ZCODE_BRIEF_DIVIDEND_CLIENTELE_G0_2026-10-08.md` (0279035) as CORRECTED by the owner's task order
(2026-10-08: census **N = 603, bar 3.2950** — the brief's "601 / 3.2940" is stale per the D-075
census note). Where brief and D-entry disagree, D-073 wins; conflicts are listed in HANDOFF_G0.md.
**Branch:** `research/dividend-clientele-2026-10` from hardening `8664856`, new worktree.
**Family:** new family **{SE} Structural-event forced flow**, opened at this registration
(D-028, PG-3). Two gates: **G0 = this freeze + a counts-only census + PIT tests**, then STOP;
**G1 = one run** after owner approval (machine-gated on `DIVIDEND_G1_APPROVED=1`), then
RESULT/VERDICT/HANDOFF, STOP. Any fix after G1 is a new, disclosed, re-frozen run.
**The sha256 sidecar (`PREDECLARATION.sha256`) covers THIS file, `dividend_clientele.py`,
`outcomes.py`, `g0_census.py`, `g1_run.py`, `synthetic.py` and
`test_pit_dividend_clientele.py`.**

## 1. Question

A cash dividend is a scheduled event whose right is fixed at the cum date. Two flows follow
(D-073): (i) **D1 pre-cum demand** — yield and capture buyers push the price up into the cum date;
(ii) **D2 ex-day tax clientele** — the marginal holder values a rupiah of dividend at less than a
rupiah of price (dividends taxed 10–20%, gains at 0.1%), so the ex-date drop should be smaller than
the dividend and the cum-close → ex-open gap should pay. Honest prior (D-073): D1 is likely null
(underpowered); D2 is the real test but a positive gap can sit inside the 0.60% cost. A NULL closes
dividends as a source of flow edge.

## 2. Data and population (frozen)

- **Snapshot.** Read-only `data/walkforward.db` via the pinned snapshot
  `/home/tjiesar/scratch/g0_snapshots_2026-10-08/walkforward_snapshot_2026-10-08.db`
  (sha256 `a2d7e675e5c66387446b888287ebbe7cef563b278c48f1518a88c797bc4bbc47`, dataset
  fingerprint `9c26e0df2fdd4e4b…`, max date 2026-10-07 — full values in `CENSUS_G0.json`).
  G1 verifies BOTH before reading any outcome and SystemExit's on drift.
- **Source tables:** `ohlcv` (raw bars, `COALESCE(is_final,1)=1`) and
  `corporate_action_events` (`action_type='dividend'`). Sessions = the DISTINCT `ohlcv` dates.
- **Events.** `dividend_currency='CURRENCY_IDR'`, `dividend_value > 0`, parsed
  `dividend_cumdate` + `dividend_exdate`, deduped by `dividend_id`; several dividends on one
  (ticker, cum date) are summed into one event. Every removal is counted by reason.
- **Session mapping.** cum = the trading session on `dividend_cumdate`; a cumdate that is not a
  session is excluded (the effective panel starts 2021-07-05 — the walkforward corpus has no
  earlier bars — so the D-073 "2009 →" half runs 2021-07..2023-12; say so). ex = the FIRST session
  after cum; it must equal `dividend_exdate` — a mismatch is excluded, not repaired.
- **Liquidity.** ADV20 = mean(close × volume) over the 20 most recent of the ticker's last 21 bars
  STRICTLY before cum (the frozen feasibility convention, `structural_events_census.py`);
  < 21 pre-bars or ADV20 < Rp 10bn → not liquid.
- **Exclusions (event level, both arms):** a split, bonus, reverse-split or rights ex-date inside
  [cum − 10 sessions, ex + 1 session]; missing ticker bar at cum or ex; FORU from 2026-09-14
  (D-063). D1 additionally requires a bar at its entry session.

## 3. Arms (exactly two; directions fixed by D-073)

### D1: pre-cum run-up

- **Anchor** (the date the dividend is public) = the EARLIER of:
  - **(a)** the latest `rups_date` for the ticker 1–90 calendar days before cum;
  - **(b)** `dividend_created`, when it is before cum AND passes the artefact test.
- **Artefact test (frozen before any outcome):** `dividend_created` is an artefact if it is
  ≥ `dividend_exdate`, or if its exact date is shared by more than 50 dividend rows (a bulk load).
  The test is computable and separates the known bulk loads cleanly, so **D1 uses the earlier of
  (a) and (b)** — the two-clause rule applies, not the (a)-only fallback. The distribution and
  tallies are in `CENSUS_G0.json`.
- **Entry:** the close of the LATER of cum − 10 sessions and the first session strictly after the
  anchor. **Exit:** the cum close. **Window:** 3–10 sessions; shorter windows are dropped from D1.
  No anchor → dropped from D1, kept in D2.
- **Outcome (G1):** stock close_entry → close_cum minus the total-return EW liquid book over the
  same sessions, minus the 0.60% round trip. The stock collects no dividend inside the window.

### D2: ex-day capture

- **Population:** yield = dividend / close at the session immediately before cum (the ticker's bar
  on that exact session; missing → yield undefined, counted), yield ≥ **2%**.
- **Outcome (G1):** (open_ex + 0.9 × dividend − close_cum)/close_cum − 0.60%, minus the book's
  return from the cum close to the ex open (ex-morning book members add their dividends back).
  The 0.9 is the 10% resident final tax.
- **Report only, not tested:** the gross-of-tax row (×1.0); the ex-close exit row; the drop ratio
  (close_cum − open_ex)/dividend as median and IQR.

## 4. Benchmark and controls (frozen)

- **Book:** equal-weight portfolio of every name with ADV20 ≥ Rp 10bn recomputed point-in-time
  (ADV through t−1, bar at t and t−1). **Total return:** on a member's IDR dividend ex-date its
  dividend is added back into that day's return, from the same `corporate_action_events` rows
  (gross; the benchmark is total return). A member with a split, bonus, reverse-split or rights
  ex-date that day is dropped from the book that day. The book is unadjusted for splits. The event
  stock is excluded from its own book.
- **Volatility control (pass condition 3):** the same arithmetic against the equal-weight book of
  liquid names in the event stock's Parkinson-60 decile at the reference date (park60 =
  sqrt(mean_60 ln(H/L)² / (4 ln 2)) over the 60 sessions before the date, deciles across the
  liquid universe that day), instead of the plain EW book. Events without a defined decile are
  counted and excluded from that control's mean. This guards the VOLEX {V} overlap (D-062).

## 5. PIT tests (frozen; all must pass at G0)

- **(a)** The anchor date precedes the entry session for every D1 event; an AGM at cum − 3
  sessions gives a 2-session window and is dropped.
- **(b)** Yield, ADV20 and Parkinson-60 use only bars before the reference date — identical values
  when the panel is truncated at it.
- **(c)** Book membership on day t uses only ADV computed on earlier days — identical membership
  when every bar after t is deleted.
- **(d)** The total-return add-back uses an EX date, never a cum date.
- **(e)** Synthetic D2: cum close 1000, dividend 50, ex open 960, flat book →
  (960 + 45 − 1000)/1000 − 0.006 = **−0.001** — the driver reproduces this EXACTLY.
- **(f)** The G0 census path never computes a return after entry: AST proof that `g0_census.py`
  and `dividend_clientele.py` import neither `outcomes` nor any outcome function, plus a
  forbidden-token grep (`pct_change`, `shift`).

## 6. Inference and pass bar (frozen; per arm, on its own)

- **Primary t** = the smaller of (i) the t of calendar-month means (events grouped by the cum
  date's month) and (ii) the two-way cluster-robust t by cum month × ticker
  (Cameron-Gelbach-Miller, G/(G−1) small-sample factors).
- **An arm passes only if ALL hold:**
  1. **Strength:** pooled mean > 0 **and** primary t ≥ **3.2950** — frozen at G0 as
     `bar_v2.e_max_abs_z(603)` = 3.294959 (exact), N = 603 = census ledger 601 (D-075 census note:
     D-071's ratified 595 + the two exploratory arms run 2026-10-08) + this G0's two arms (D1, D2).
  2. **Both halves positive:** cum ≤ 2023-12-31 and cum ≥ 2024-01-01 (the split is frozen; the
     first half is in effect 2021-07..2023-12 — no liquid event is earlier; say so).
  3. **Volatility control positive** (§4 decile book).
  4. **D2 only:** it must pass at the 0.9 tax factor (the tested statistic), not only gross; and
     it must NOT be positive only in the top yield tercile — if the lower two terciles together
     have mean ≤ 0, D2 fails as economically unusable (D-073). Tercile edges are frozen from the
     G0 census (`CENSUS_G0.json: d2.yield_tercile_edges`), pre-event data only.
- **Both arms are reported whichever passes.** No "best of", no horizon grid, no yield grid.
- **Also report:** n per arm and half; win rate; mean and median; the year table; AGM season
  May–Jul vs rest; yield terciles; the D1 window-length distribution; the foreign-ownership proxy
  split — **none PIT; not reported** (no point-in-time ownership history exists; D-073).

## 7. Power (HANDOFF_G0; pre-event σ only)

- **D1:** MDE = t_bar · σ_d · √h / √n at the actual anchored n and actual median window, with
  σ_d = the median across D1 events of the daily-return SD over the 60 sessions before entry;
  the month-clustered variant uses √n_months.
- **D2:** MDE = t_bar · σ_overnight / √n with σ_overnight = the median across D2 events of the
  overnight (open vs prior close) return SD over the 60 sessions before cum.
- Recomputed values are in `HANDOFF_G0.md` and `CENSUS_G0.json` (counts and pre-event σ only).

## 8. G1 protocol (frozen)

One run, from the frozen tree, `DIVIDEND_G1_APPROVED=1` required. The snapshot sha256 and dataset
fingerprint are verified against `CENSUS_G0.json` BEFORE any outcome; drift stops the run.
`g1_run.py --synthetic` may be run at any time (fixture market only). RESULT `<utc>.json`,
`VERDICT.md`, `HANDOFF_G1.md`, then STOP. **Forward test (record only, nothing built):** if an arm
passes, the forward test is on new liquid dividends after the G1 date with the same frozen rules,
recorded at cum and ex; the natural host is the D-064 ex-date monitor's table
(`check_issuance_windows.py` lineage), detection-only, owner-gated.

## 9. G0 rule

No return after any event's entry/cum close is computed, printed or stored before G0 approval
(D-070 rule 1; a breach voids the study). Pre-entry prices (ADV, yield, volatility deciles,
pre-event σ) are allowed. The census path is physically separated from the outcome module
(`outcomes.py`) and AST-tested (§5f).

**Falsification (D-073, unchanged):** the D1 or D2 pooled mean ≤ 0, below the frozen bar, or a
sign flip across the halves; D2 positive only gross of the 10% tax or only in the top yield
tercile.

**Governance (draft, do not file):** registration HYP-PM-0017 = D1 + D2, 2 arms, family {SE}
slot 1; census 603, bar 3.2950; draft D-entry text in `REGISTRATION_DRAFT.md` under the next free
number at filing (expected **D-076** — the brief's "expected D-075" is stale, D-075 is taken).
HYPOTHESIS_REGISTRY.md, FAILURE_REGISTRY.md and DECISION_LOG.md are NOT edited by this branch.
The D-064 ex-date monitor continues unchanged.
