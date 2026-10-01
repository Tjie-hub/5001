# IDX Walkforward — TODO

_Last updated: 2026-09-22 — closed P0-1 (security work was committed `817f732` on 2026-08-20),
verified 2/3 of P0-3's collection errors are now clean, and closed P0-6 (Stockbit auto-token
corruption incident + fix). Base plan is still the 2026-08-19 full-stack machine audit below; all
Sprint 8–19 work is shipped and archived further down._

**Execution-environment rule (2026-08-19):** all compute-heavy work runs on the **WSL Ubuntu box on
the Windows PC (`tjiejet`)**, not the XPS-13 (`tjiesar`) — that box OOMs and drops the session under
load. The XPS-13 is production-only: it runs the live service and holds the live DB.

**Critical environment fact:** `.stignore` excludes `*.db` — **databases do NOT sync between the two
machines.** Code syncs; data does not. So:
- `D:\IDX\data\walkforward.db` (3.3 GB, repaired 2026-08-15) is a **local copy**, ~4 days stale on
  OHLCV. Fine for research verdicts on a 5-year corpus; not the production DB.
- Any DB migration must be run **twice** — once locally (WSL), once on production (XPS-13).
- Code edits made in WSL propagate to production via Syncthing. **Deploy is still a deliberate act**
  (`scripts/release.sh` + `systemctl --user restart`).

Reference: `Audit/` corpus + `docs/RESEARCH_MASTER_PLAN.md` v3. Full audit findings and evidence
trail: the 2026-08-19 machine audit (workflow map, joint failures, test-cache analysis).

---

# 🔥 ACTIVE — Post-Audit Execution Plan (2026-08-19)

**Sequencing is load-bearing.** P1 must complete before any gatekeeper run, or the append-only
evidence ledger forks silently. P3 must complete before any forward-test number is meaningful.

---

## 🔴 P0 — Preserve & Establish Ground Truth

_Hours, not days. No research judgement required. Do this first._

- [x] **P0-1. Commit the uncommitted security work** — DONE. `security/middleware.py` +
      `security/route_policy.py` committed `817f732` (2026-08-20, "fix(security): gate ADMIN routes
      unconditionally; escalate 10 side-effect routes"). Verified 2026-09-22.

- [ ] **P0-2. Run the real test suite and record it** — the on-disk cache
      (`.pytest_cache/v/cache/lastfailed`, 72 entries) is *cumulative across partial runs*, not a
      current failure count, and is likely polluted by Windows-side runs where POSIX-only tests
      (chmod, symlinks, /tmp) fail environmentally. There is currently **no trustworthy number**.
      _Where:_ WSL (Python 3.12 venv, matching CI) · _Cmd:_
      `python -m pytest -q 2>&1 | tee logs/pytest_full_20260819.log` ·
      _Accept:_ a real pass/fail/error tally committed to the log · _Est:_ ~6 min runtime.
      **2026-10-01, XPS-13 tally (venv Python 3.12.3, same major as CI):** `python -m pytest -q` →
      **3450 passed, 3 skipped, 0 failed**, 0 collection errors, 609s — `logs/pytest_full_20261001.log`.
      First trustworthy tally on the production box (old 72-entry cache was stale; current cache
      held 11). Item stays open only for the **WSL re-run before P1-1** — the P0/P1 brief wants the
      known-good baseline on the box the migration runs on.

- [x] **P0-3. Resolve the 3 collection errors** — re-verified 2026-09-22: `tests/test_auto_token.py`
      and `tests/test_stockbit_fetcher_ensure_valid_token.py` now **collect clean** (42 tests,
      confirmed while fixing the 2026-09-22 auto-token incident below). `tests/agent_firm/test_client.py`
      **no longer exists on disk** — needs a fresh check for what replaced it (renamed under
      `tests/agent_firm/` during a reorg, or genuinely dropped) before this item can close.
      _Where:_ WSL · _Depends:_ P0-2 · _Accept:_ confirm `test_client.py`'s fate, then close.
      **CLOSED 2026-10-01 (XPS-13):** fate confirmed — deleted intentionally 2026-07-08 in
      `85cab31` ("chore(firm): delete DeepSeekClient — replaced by ZAIProvider"); the replacement
      provider has its own suite (`tests/agent_firm/providers/test_zai_provider.py`). The two
      auto-token files re-collected clean in the 2026-10-01 full run.

- [ ] **P0-4. Track or delete the 5 untracked test files** — 283 test files on disk, **278 tracked**.
      CI checks out only tracked files, so these have **never run in CI**:
      `tests/test_news_filter.py` (2 of the cached failures), `tests/test_filter_exploration.py`,
      `tests/agent_firm/providers/test_quota_{hydration_edge_cases,scenarios,state_persistence}.py`.
      They currently do the worst of both: run locally, pollute the failure cache, prove nothing in
      CI. Decide per-file: real coverage → commit; scratch → delete.
      _Where:_ WSL · _Depends:_ P0-2 · _Accept:_ `git ls-files 'tests/**test_*.py' | wc -l` equals
      the on-disk count.
      **CLOSED 2026-10-01 (XPS-13):** 359 tracked = 359 on disk, 0 untracked test files. All five
      landed as real coverage: `test_news_filter.py` → `cf18e43`, `test_filter_exploration.py` →
      `e83e3d6`, the provider quota trio → `1933233` (owner-verified 52 passed / 0 failed 2026-09-21).

- [x] **P0-6. Stockbit auto-token corruption incident (2026-09-22)** — DONE, commit `04e4fdd`.
      `.stockbit_token` held the literal 9-byte string `undefined` (not a JWT) since 2026-09-21
      17:05, so every downstream job sending `Bearer $(cat .stockbit_token)` got 401s. Root cause:
      `_capture_from_page()`'s `on_request` listener accepted the *first* `Authorization: Bearer
      <value>` header seen on any `exodus.stockbit.com` request with no shape check — Stockbit's SPA
      fires an early request literally reading `Bearer undefined` before its client-side auth state
      hydrates (guaranteed right after `credential_login()`'s `localStorage.clear()`), and
      `verify_token()` only checks HTTP status, not token shape, so it wrote straight through. Fixed
      with `_is_jwt_shaped()` gating both capture points; 4 new regression tests in
      `tests/test_auto_token.py::TestJwtShapeGuardAtCapture` pin the exact scenario. Live token
      re-established via `auto_token.py --login` (valid 2026-09-22 09:13, 24h TTL). Also:
      `backups/` (8.5GB untracked migration DB snapshot) added to `.gitignore` (`2154f15`) — it
      wasn't covered by the existing `*.backup*` rule and a stray `git add -A` would have tried to
      commit a 9GB file.

- [ ] **P0-5. Triage the 64-file untracked pile** — long-standing open thread, now enumerated:
      `docs/audit/STOCKBIT_FLOW_*` (11 files), 10 `docs/superpowers/plans/*.md`,
      `Audit/R5_TIER1_DB_SPLIT_CLOSURE_REPORT.md`, `docs/data/`, `docs/infra/`, `images/`,
      `scripts/probe_*.py`. Commit what is real work-product; `.gitignore` the rest.
      _Where:_ WSL · _Accept:_ `git status --porcelain | grep -c '^??'` → 0.
      **Re-triaged 2026-10-01 (XPS-13):** the enumerated 64-file pile is fully resolved — 0 of the
      enumerated paths remain untracked. The CURRENT pile is new material, now smaller:
      `data/.fuse_hidden*` (12 FUSE mount artefacts) and `data/ajaib_raw/` (raw TOWR snapshot
      scrapes) → both gitignored 2026-10-01, raw data stays out of git. Two dirs remain as
      **Owner decisions** (real work-product both, but not session work): `atr_plan/` (14 files —
      standalone ATR-exit study the Owner unzipped from ~/Downloads 2026-09-24, has null-test
      methodology + results_2026-09-24 + verdict.csv + its own unit tests; recommend commit) and
      `Claude outputs/` (22 files — Owner's claude.ai download folder: session briefs/playbooks/
      pine+py scratchpads; the BRPT playbook itself marks the scripts "session scratchpad, not
      saved to the repo"; recommend committing the .md briefs/playbooks and ignoring/deleting the
      scratch). Item stays open on those two decisions only.

---

## 🔴 P1 — Activate the Research Fence (blocks all research work)

_`data/research.db` **does not exist**. The R-5 physical fence is committed code (`5e9b9b4`) with a
cutover runbook (`9bb2fd7`) that was never `--apply`-ed. All 8 Tier-1 tables still live in
`walkforward.db`._

> ⚠️ **Do not run the gatekeeper before this completes.** `connect_research()` *creates*
> `research.db` on first call and `ensure_gate_tables()` creates empty tables in it — so the next
> gate run writes its decision to a fresh empty DB while every historical `gate_decisions` row stays
> in `walkforward.db`. The append-only ledger forks in two, silently, with no error.
>
> **2026-10-01, cross-box note (from an XPS-13 session):** P1-1/P1-2 are WSL-side and **cannot be
> executed from XPS-13** — the DBs deliberately do not sync. XPS-13's `data/walkforward.db` is the
> LIVE production DB (service active during market hours), so running the migration here would be
> P1-3 out of order — its own dependency is P1-2 "prove it locally first" on WSL — and P1-3 means a
> service stop: do it outside 09:00–15:30 WIB as a deliberate, Owner-coordinated action.

- [ ] **P1-1. Cutover — LOCAL (WSL)** — `python scripts/migrate_r5_tier1.py` (dry-run default) →
      review output → `--apply`. Migrates: `research_runs`, `gate_decisions`, `gate_evidence`,
      `regime_profiles`, `regime_profile_cells`, `hypotheses`, `hypothesis_links`,
      `failure_registry`.
      _Where:_ WSL · _Accept:_ `data/research.db` exists; row counts match pre-migration.

- [ ] **P1-2. Verify no orphans (LOCAL)** — confirm every Tier-1 table landed intact and nothing
      remains stranded in `walkforward.db`. Back up first (`scripts/db_backup.py`).
      _Where:_ WSL · _Depends:_ P1-1 · _Accept:_ per-table row-count diff = 0.

- [ ] **P1-3. Cutover — PRODUCTION (XPS-13)** — same script, on the live DB. **Separate action
      because DBs do not sync.** Low memory cost (8 metadata tables, not the 3.3 GB OHLCV/ticks), so
      OOM risk is low — but stop the service first.
      _Where:_ XPS-13 · _Depends:_ P1-2 (prove it locally first) · _Accept:_ service restarts clean,
      `/health` green.

- [ ] **P1-4. Verify production + confirm `RESEARCH_DB_PATH`** — check `.env` / systemd unit so both
      hosts resolve the same intended path.
      _Where:_ XPS-13 · _Depends:_ P1-3.

- [ ] **P1-5. Define a safe refresh path for the WSL research corpus** — data is excluded from sync
      **deliberately**: Syncthing writing a live WAL-mode SQLite file while the app holds it open
      produces `database is locked`, failed writes, and ultimately the 2026-07-29 corruption. That
      exclusion is correct and must stay. But it leaves the WSL research copy with **no defined way
      to be refreshed**, so it silently rots as research keeps running against an ageing corpus.
      **Never fix this by raw-copying the live DB** — a file copy of an open WAL database is the same
      failure class as syncing it (torn read, no checkpoint, inconsistent).
      **Use the existing, correct tool:** `scripts/db_backup.py` already takes the snapshot via the
      sqlite3 **online-backup API** (`src.backup(dst, pages=4096)`) — WAL-safe and consistent even
      while the app is writing — then runs `PRAGMA integrity_check` + per-table row counts, and only
      then compresses to `.zst`. It already runs nightly on production via systemd --user timers
      (`b70a17b`).
      _Proposed:_ add a **second Syncthing folder for `~/backups/idx-walkforward-5001/` only**. Those
      are compressed, verified, inert archives that no process ever holds open — they sync with zero
      lock risk, unlike the live DB. WSL then decompresses the newest snapshot on demand to refresh
      its research corpus. Alternative if a second sync folder is unwanted: scp the newest `.zst`
      over Twingate as a manual step before each research batch.
      _Where:_ both · _Accept:_ a documented one-command refresh, and a note in `docs/OPERATIONS.md`
      stating why the live DB is never copied directly.

---

## 🟠 P2 — Resolve the NR7 Grandfather (needs P1)

_`registry/edge_registry.yaml` has `NR7_BULL` v1 **APPROVED**. `engine/registry_loader.py:40-47`
carries an explicit debt entry stating the conflict: "APPROVED 2026-07-04 under the pre-Phase-C
generalization bar; Phase C gate=REJECT and shadow N=0. Governs on legacy grounds" — deadline
**2027-01-08**. This is a documented, deliberate risk acceptance, **not** a bookkeeping error. The
problem is that the evidence it rests on has since eroded (see P4) and nobody has revisited it._

- [ ] **P2-1. Re-run the gatekeeper on NR7 against current data** —
      `python -m research.gatekeeper.cli evaluate --strategy "NR7 Breakout" --report out/nr7_gate_20260819.md`
      Gets a *current* decision instead of July's. Memory-heavy (186 tickers × 5y OHLCV → pandas).
      _Where:_ **WSL only** · _Depends:_ P1-2 · _Accept:_ a new `gate_decisions` row in
      `research.db` + the report file.

- [ ] **P2-2. Query the live forward test** — the manifest still reads
      `shadow: {trades: 0, verdict: pending}` from 2026-07-04, six weeks ago. Has shadow N moved off
      zero? Run `research/studies/phase5_tracker.py` against **production** data.
      _Where:_ XPS-13 (production data) · _Accept:_ a real N and expectancy, or a confirmed zero.

- [x] **P2-3. 🔑 OWNER DECISION — revoke or re-affirm** — SUPERSEDED by D-029 (4f3098f): NR7 already moved to SHADOW; the revoke/re-affirm choice is moot. (2026-09-30) — with P2-1/P2-2 in hand:
      **(a)** revoke to `SHADOW` (stops live selection immediately, keeps collecting forward data), or
      **(b)** re-affirm APPROVED in writing, explicitly acknowledging the P4 erosion.
      Drifting to the 2027-01-08 deadline by default is the one option that is not a decision.
      _Depends:_ P2-1, P2-2 · _Accept:_ a dated entry in the registry changelog + manifest.

- [ ] **P2-4. Make runtime evidence-validation enforcing, not advisory** —
      `registry_loader.py:147`'s `entries.append(e)` sits **outside** the `if reasons:` block, so an
      entry failing `validate_evidence()` is still loaded and still governs. R-10 is enforced in CI,
      not at runtime. Gate loading on the receipt (keep `_LIFECYCLE_DEBT` as the explicit,
      shrink-only exception).
      _Where:_ WSL · _Depends:_ P2-3 (don't change enforcement while the NR7 status is unresolved).

---

## 🔴 P3 — Fix the Live/Backtest Execution-Model Mismatch

_**The correctness bug.** Backtest and research use `is_final=1` completed bars with a 1-bar delay
(`engine/strategies.py:203-256`, Donchian `.shift(1)` at `:2065`, trailing stop lagged in
`engine/exits/evaluator.py:46-56` — all verified genuinely clean of look-ahead). Live scans read
`is_final=0` **still-forming** bars (`data/loaders.py:68-93` says so in its own docstring;
`scheduler/__init__.py:258-262`, 5×/day), and `scheduler/scanner.py:1673` → `paper_trade.py:439`
inserts that price with **no re-fetch and no delay**._

> **Consequence:** paper-trading P&L is not evidence for the backtested edge — it is evidence for a
> different, never-validated execution model. This also means P2-2's forward-test number is
> measuring the wrong system.

- [ ] **P3-1. Decide the approach** — **(a)** delay live fills to next-bar-open to match what was
      validated (cheaper; preserves the entire existing evidence base), or **(b)** re-validate every
      strategy against a partial-bar execution model (expensive; invalidates prior WF results).
      Recommendation: **(a)**.

- [ ] **P3-2. Implement** — align the live path with the chosen model; add a regression test that
      pins live entry-price semantics to the backtest's.
      _Where:_ WSL · _Depends:_ P3-1.

- [ ] **P3-3. Reset the forward-test clock** — any forward-test evidence collected under the old
      mismatched model is not evidence for the new one. Restart the shadow/forward window from the
      deploy date.
      _Depends:_ P3-2.

---

## 🟠 P4 — Make the Evidence Honest

_Each item independently undermines the 2026-07-04 approval that P2's grandfather rests on._

- [ ] **P4-1. `liquid_universe()` point-in-time fix** —
      `research/studies/nr7_generalization_study.py:77-90` filters the whole 5-year study by
      **today's** ADV, not per-trade-date. A ticker illiquid today is excluded from its entire
      history. Survivorship-style contamination **in the flagship strategy's own evidence base**.
      _Where:_ WSL · _Accept:_ ADV computed as-of each trade's entry date; study re-run.

- [ ] **P4-2. Model ARB/ARA fillability in backtest + walk-forward** — price-limit bands exist only
      in the live path (`paper_trade.py:211-228`, single call site `:372`), never in backtest/WF. So
      every historical expectancy — including NR7's +1.64%/trade — assumes every computed SL/TP was
      always fillable. Structurally inflates the breakout/momentum family (NR7, ORB, Inside Bar,
      TFB), which trades exactly the volatility spikes most likely to hit a limit freeze.
      _Where:_ WSL · _Note:_ likely the single largest correction to OOS expectancy.

- [ ] **P4-3. Wire V3-1 (family scoping + effective-N) into `gate_config`** — DSR's trial count
      (`research/gatekeeper/stages.py:87` ← `candidate.py:169-180`) counts **regime cells (3–6)**,
      not the ~14 strategies × hundreds of tickers × optimizer grids actually searched. Undercounted
      by 2–3 orders of magnitude. **This is already designed** in `RESEARCH_MASTER_PLAN.md` §3.1
      (scope by `(dataset epoch, feature_space_hash)`, Kish-style `N_eff`) and has sat unwired for
      over a month. Per §3.1(c) it is a major config version bump, non-retroactive.
      _Where:_ WSL · _Depends:_ P1 (config change → new decision lineage).

- [ ] **P4-4. Gate the ML regime classifier on its own honesty check** — `scanner.py:476-478` trains
      a fresh model per ticker per day and calls `.predict()` **without ever checking**
      `holdout_accuracy` / `beats_baseline`. The model can fail to beat a majority-class baseline and
      still gate live signals; the module's own honesty metric is orphaned data.
      _Where:_ WSL.

- [ ] **P4-5. Remove the unreachable `UNCERTAIN` branch** — `scanner.py:492` filters on a regime value
      `detect_regime()` can no longer return since the 3-class refactor folded it into `SIDEWAYS`
      (`regime_filter.py:106`). Dead branch contradicting its own comment. Also: delete the dead
      `strategy_regime_adaptive` body (`regime_filter.py:304`, removed from dispatch for whole-window
      look-ahead, audit ref C-7; only a defunct migration script references it).

- [ ] **P4-6. Liquidity-scaled slippage** — `engine/exits/costs.py:9-11,28-31` applies a **flat
      0.10%** per leg with no volume/participation scaling, on a roster the repo's own docs describe
      as mostly illiquid. Commission (0.15%/0.25%) and lot size (100, correctly enforced in both
      paths) are fine.

- [ ] **P4-7. Reconcile the live scan universe against the research corpus** —
      `data/fetcher.py:10-36` is a **static, hardcoded current-membership** IDX30/LQ45/IDX80 snapshot
      ("preserved for backward compat"), not reconstructed per historical date, and **not the ticker
      set the strategies were backtested against**. Also: only 14/959 tickers are flagged inactive in
      `idx_tickers` — implausibly low for 5 years of IDX history, and `data/ticker_discovery.py` can
      only discover tickers yfinance still serves, so pre-discovery delistings are an unverifiable
      blind spot.

- [ ] **P4-8. Fix the "AI-powered market regime detection" docstring** — overstates what is live.
      Reality: rule-based ADX/MA-slope (`detect_regime()`) drives every live call site, with an
      under-gated ML overlay. Claims-vs-code contradiction.

- [ ] **P4-9. Score the never-tested strategies before they can fire** — strategies with no
      walk-forward evidence should not reach live dispatch. Note `_COUNTER_TREND_BOOK`
      (`scanner.py:732`: Crash Recovery, Panic Rebound) **deliberately bypasses the wf consistency
      gate** — that exemption needs an explicit re-decision, not silent inheritance.

---

## 🟢 P5 — Generate New Evidence

- [ ] **P5-1. Write `run_exp_pa_0001.py`** — the confirmatory script for **HYP-PA-0001** (index
      reconstitution / closing-auction dislocation), REGISTERED 2026-07-19 and never executed. Fully
      specified in `docs/research_programs/P-A/HYP-PA-0001_HARNESS_SPEC.md`; data curated
      (`WP-D/reconstitution_events.csv`, 210 sourced ticker-events, 105 ADD / 105 DELETE, 13 review
      clusters, 2022-08→2026-05). Estimator: event-study CAR vs IHSG, 230-td estimation window
      ending ~20 td before announcement, reversal window t+1..t+5, cluster-robust (CR1) SEs by review
      date, α=0.05. Test 2: DELETE-only net-of-cost (N=105) using the **imported** 0.60% round-trip
      constant from `engine/exits/costs.py` — not re-derived. Dedup key `(ticker, effective_date,
      event_type)`. Follow `run_exp_pm_0001.py`'s packaging discipline (read-only DB, JSON results +
      execution log, frozen MANIFEST) — **not** its estimator.
      _Where:_ **WSL only** (memory-heavy) · _Depends:_ P1-2.

- [ ] **P5-2. Execute under custody + close out** — run once, apply the frozen decision rule
      verbatim, produce `results.json`, `execution.log`, `EVIDENCE_PACKAGE.md`, and either an
      Accepted-Knowledge or Failure-Library entry. **No re-runs, no k-tuning** (X1/R15).
      _Depends:_ P5-1.

- [ ] **P5-3. Update `HYPOTHESIS_REGISTRY.md` + `FAILURE_REGISTRY.md`** with the outcome.

---

## 🧊 Standing Rule

**No new governance documents until P4 lands.** Three overlapping governance tracks already exist —
`docs/research_os/` (L1–L8 institutional architecture, 22 files), `docs/RESEARCH_MASTER_PLAN.md` v3
(phases A–H), and `docs/research_programs/` (P-M / P-A) — reconciled by a fourth document. The
binding constraint on this system is **execution, not specification**.

**The pattern the audit found:** five separate completed designs that were never activated — the DB
fence built but not cut over, V3-1 designed but not wired, HYP-PA-0001 specified but not run, the
security fix deployed but not committed, the NR7 grandfather time-boxed but not revisited. Not a
competence problem; a finishing problem.

---
---

# 📦 ARCHIVE — Shipped Sprints (2026-05 → 2026-06)

_All items below are complete. Retained for provenance; superseded as an active work list by the
plan above and by the `Audit/` corpus._

## ✅ Sprint 11 — Agent-Firm Mode Toggle (SHIPPED 2026-05-27)

- [x] `engine/agent_firm/config.py` — `_runtime`, `set_mode()`, `get_enforce()`, `is_active()` runtime override
- [x] `POST /api/agent/config` — off/shadow/enforce toggle, runtime state persisted in memory
- [x] `GET /api/agent/status` — returns `get_enforce()` (runtime-aware, not static env var)
- [x] `scheduler.py` — uses `get_enforce()` to respect runtime mode
- [x] Topbar pill (OFF/SHADOW/ENFORCE) in `backtest_multi.html` with confirm modal on ENFORCE

---

## ✅ Infrastructure — Sibling Services (RESOLVED 2026-05-27)

- [x] **`idx-walkforward.service`** — was old duplicate of `idx-walkforward-5001.service`, causing port 5001 conflict. Disabled.
- [x] **`idx-monitor.service`** — pointed to `/home/tjiesar/idx-monitor/` (non-existent, never built). Disabled after 411+ crash loops.
- [x] **`idx-walkforward-5001.service`** confirmed sole authoritative service, active and healthy.

---

## ✅ Sprint 8 — News Volume Spike Detector (SHIPPED + VALIDATED 2026-05-27)

- [x] News source: **Google News RSS** (`<ticker> saham`, `hl=id`)
- [x] Schema: `news_mentions(ticker, date, count, headlines_json, updated_at)`
- [x] Daily fetch all tickers @ **17:00 WIB** (`run_news_fetch`)
- [x] Spike rule: `today_count ≥ 3× 30d_avg AND today_count ≥ 3`
- [x] Surface ⚡ tag + section in `flow_broker_report` Telegram
- [x] Cold-start window passed
- [x] **Coverage verified**: 2026-04-26 → 2026-05-26, 17 trading days, 972 tickers, 15,558 rows, 411 spike events
- [x] **Spike → entry filter REJECTED**: back-tested 344 events — win rate 35.5%, avg next-day return -0.58%. News spikes lag price (news chases moves). ⚡ Telegram tag stays as informational only.

---

## ✅ Sprint 10 — Regime 3-Class Redesign (SHIPPED 2026-05-27)

- [x] **`detect_regime()`** — ADX-14 EWM + MA20 5-bar slope → BULL / BEAR / SIDEWAYS (was TRENDING/SIDEWAYS/UNCERTAIN)
- [x] **`RegimeClassifier`** — upgraded to multinomial LogisticRegression (3 classes)
- [x] **Bear dip-scout watchlist** (`engine/watchlist.py`) — adds oversold BEAR names (RSI<35, quality gate), promotes on BULL flip
- [x] **Quality gate** — `backtest_cache` win_rate ≥ 50% + return ≥ 5% (replaced `wf_scores.weighted_score` which was per-ticker normalized, useless as absolute filter)
- [x] **Expiry bumped 30 → 60 days** — backed by hitting-time study: median BEAR→BULL = 59 cal days; 30d window captures only 20% promotions vs 43% at 60d
- [x] **Scheduler bear lane** wired into `scheduled_multi_strategy_scan()` — iterates full `ohlcv_map`, uses real OHLCV for ADX
- [x] **`app.py`** — all UNCERTAIN → SIDEWAYS; regime gate blocks BEAR; 3-class emoji (📈/🐻/➡️)
- [x] **`templates/dive.html`** — regime badge CSS for BULL/BEAR/SIDEWAYS
- [x] **Agent-firm** — `analytics.py`, `smoke.py`, `regime_v1.md` prompt updated; 6 test files migrated TRENDING → BULL
- [x] **Markov regime rejected** — per-ticker too sparse (93% zero BEAR→BULL transitions); signal = echoes current regime label only. Not worth building. (see memory)
- [x] Merged to master (d8a4a51), pushed to origin

---

## ✅ Sprint 10b — IDX Holiday Calendar (SHIPPED 2026-05-27)

- [x] `IDX_MARKET_HOLIDAYS_2026` (21 dates) added to `engine/calendar_filter.py`
- [x] `is_trading_day()` — returns False on weekends + IDX public holidays
- [x] Backtest windows exclude non-trading days
- [x] Suspension gap detector uses trading-day counter

---

## ✅ Sprint 12 — Audit Response: Tier 1 Quick Wins (SHIPPED 2026-05-30)

- [x] **R1. Execute `PLAN.md` — Frontend Strategy Registry** — Server-side implementation: `/api/strategy/list` + `/api/strategy/markers/<key>/<ticker>` using canonical engine strategies. Dropdown auto-populated, markers cached per key, daily-only gate, color-coded per strategy. 10 strategies live. SHIPPED (verified 2026-05-30).
- [x] **R2. Consolidate `DB_PATH` and config** — `config.py` at project root: `load_dotenv()` once, exports `DB_PATH` + Telegram vars. Updated 9 files: `routes_backtest_multi.py`, `monitor.py` (4 inline getenv → 1 module-level), `engine/sector_rotation.py`, `engine/sectors_app_filter.py`, `engine/suspension_detector.py`, `screener/fundamental.py`, `screener/db.py`, `flow_filter.py`. 166 tests pass. SHIPPED 2026-05-30.
- [x] **R3. Extract `send_telegram()` to shared utility** — `utils/telegram.py` with rate limiting (1s interval) and retry (2 retries, exp backoff). Replaced in `scheduler.py` and `monitor.py`. 8 unit tests. SHIPPED 2026-05-29.
- [x] **R4. Add `/health` endpoint** — Flask route returning `{"status", "db", "last_scan", "open_trades"}`. 7 unit tests. SHIPPED 2026-05-29.

---

## ✅ Stockbit Screener Integration (SHIPPED 2026-05-30)

- [x] `screener/stockbit_screener.py` — JWT capture from DS browser session, token validation, `fetch_template_tickers(id)`, `run_screener(id)`, `GURU_TEMPLATES` (id 63 high_volume_breakout, id 77 foreign_flow_uptrend)
- [x] `screener/fundamental.py` — `run_query()` gains `ticker_filter` param; safe IN-clause injection
- [x] `screener/routes.py` — `GET /screener/fundamental` accepts `stockbit_template`; `GET /screener/stockbit/templates`; `GET /screener/stockbit/run`
- [x] `templates/screener.html` — Stockbit Filter sidebar with template dropdown and badge indicator
- [x] **ohlcv chart fix** — `/api/ticker/<ticker>/full` now returns 250-bar OHLCV array; dive chart was showing "Chart data loading…" placeholder because `d.ohlcv` was missing from response

### ✅ Follow-up bugs (found + fixed during verification 2026-05-30)

- [x] **SB-1. Silent Stockbit filter failure** — `screener/routes.py` now propagates `stockbit_error` (exception message) and always sets `stockbit_template` in response on failure. `renderResults` in `screener.html` shows ⚠️ in amber in `sbStatus` div. 6 unit tests. SHIPPED 2026-05-30.
- [x] **SB-2. Dead `/api/screener/stockbit/templates` endpoint** — `loadStockbitTemplates()` added to `screener.html`; fetches on `init()`, populates `<select>` dynamically (saved templates preferred, builtin as fallback). Hardcoded options removed. SHIPPED 2026-05-30.

---

## ✅ Sprint 13 — Audit Response: Tier 2 Medium Improvements (SHIPPED 2026-05-30)

- [x] **R5a. Split `scheduler.py`** — `scheduler/` package: `state.py` (caches), `utils.py` (shared helpers), `jobs.py` (10 job fns), `scanner.py` (11 scan fns), `reports.py` (4 report fns), `__init__.py` (start_scheduler + re-exports). Old 1887-line `scheduler.py` deleted. SHIPPED 2026-05-30.
- [x] **R5b. Split `app.py`** — `routes/` package: `backtest.py` (backtest/paper/signals/agent), `flow.py` (flow/broker), `screener.py` (ticker/dive/strategy/fastmover/premover/sector/calendar), `telegram.py` (webhook/polling). app.py reduced to 77 lines. 97 tests pass. SHIPPED 2026-05-30.
- [x] **R6. Portfolio-level backtesting** — `engine/portfolio_backtest.py` equal-weight 10-stock portfolio. 8 unit tests. SHIPPED 2026-05-30.
- [x] **R7. Paper trade expiry + auto-close** — `check_expired_trades()` in `paper_trade.py`: closes trades held >30 days at market. 6 unit tests. SHIPPED 2026-05-30.
- [x] **R8. Sector rotation filter** — `engine/sector_rotation.py`: ranks sectors by momentum, flags top 3. 9 unit tests. SHIPPED 2026-05-30.

---

## ✅ Sprint 14 — Architecture Cleanup (SHIPPED 2026-05-30)

- [x] **R9. Merge `idx_screener` into main project** — `screener/` package migrated, `screener_clone.py` deleted. 22 unit tests.
- [x] **R10. Data layer consolidation** — `data/` package: `db.py`, `fetcher.py`, `ticker_discovery.py`. Single source of truth for DB schema.
- [x] **R11. Delete dead code** — `_archive/` created with 24 files, 2,880 lines archived. `scheduler.py.manual_backup` created. SHIPPED 2026-05-30.

---

## ✅ Sprint 16 — Indicator Lag Audit Fixes (SHIPPED 2026-05-30)

### ✅ Critical — Simplified ATR (missing True Range gap components) — FIXED

- [x] **I1. Fix `strategy_inside_bar_breakout()` line 753** — Replaced `(high-low).rolling(14).mean()` → `calc_atr(df, 14)` (full True Range). Affects TP (swing_hi_20 or entry+2×ATR) and position sizing.
- [x] **I2. Fix `strategy_nr7_breakout()` line 836** — Replaced `ranges.rolling(14).mean()` → `calc_atr(df, 14)`. `ranges` kept for NR7 detection. Affects TP (entry+2×ATR) and position sizing.
- [x] **I3. Fix `strategy_orb()` line 945** — Replaced `(high-low).rolling(14).mean()` → `calc_atr(df, 14)`. Affects OR range proxy (open±ATR×0.5), TP (swing_hi_20 or ATR×2), and SL.

### ⚠️ Medium — Inconsistent ATR/ADX smoothing across modules

- [x] **I4. Audit ATR methodology** — Decision: document, don't standardize. SMA used in `strategies.py` + `premover_detector.py` (position sizing, simpler, less lag). Wilder's EWM in `regime_filter.py` is required by ADX/DMI spec. Comments added to all 3 files. SHIPPED 2026-05-30.

### ⚠️ Low — Volume ratio self-inclusion

- [x] **I5. Document VR behavior** — Added comment to `calc_vol_ratio()`: rolling mean includes current bar (dampens spikes ~10%), intentional conservatism. SHIPPED 2026-05-30.

### Revalidation

- [x] **I6. Re-run walkforward** — 857/972 tickers refreshed 2026-05-30. Post-fix gains: Inside Bar +3.8pp consistency / +17% score, NR7 +4.3pp / +17%, ORB +5.7pp / +7%. Full True Range ATR measurably improves all three strategies. SHIPPED 2026-05-30.

---

## ✅ Sprint 17 — BRPT Deep-Dive Gap Analysis (FULLY SHIPPED 2026-06-05)

_Source: BRPT.md live analysis — BRPT crash -35% May 2026 exposed critical gaps._

### ✅ Critical — Extreme Event Handling

- [x] **G1. Backtest auto-rolling pipeline** — `engine/backtest_roller.py`: 4,216 records in `out/meta_dataset_backtest.json`, `backtest_windows` DB table (4,216 rows). Scheduler: monthly 1st Sunday 10:00 WIB. BRPT window 5 (2026-04-16→2026-06-04) visible. 8 unit tests. SHIPPED 2026-06-04.
- [x] **G2. Trading suspension / data gap detector** — `engine/suspension_detector.py` with three-layer API, `suspension_events` table (1,477 rows), calendar-aware trading-day counter. Detected BRPT/DEWA/BULL May-2026 cluster. 15 unit tests. SHIPPED 2026-05-28.
- [x] **G3. Crash recovery strategy pattern** — `strategy_crash_recovery()` in `engine/strategies.py`: gap ≥5 cal-days + ≥20% gap-down, VR>2x entry within 3 bars, SL=resume bar low, TP=50% gap retracement. BRPT validation: +22.4%. 7 unit tests. SHIPPED 2026-06-05.
- [x] **G4. VR spike context classifier** — `classify_volume_context(df)` in `engine/indicators.py`: crash_absorption/exhaustion_distribution/breakout_accumulation/normal. Added to `score_ticker_reversal()`. REVERSAL_BREAKOUT alerts show context tags. 6 unit tests. SHIPPED 2026-06-05.

### ✅ High Value — Detection-Action Gap

- [x] **G5. Fundamental data auto-refresh on price shock** — `check_keystats_freshness()` in `scheduler/scanner.py`: blocks stale+shock signals, allows stale-but-quiet through, attempts inline re-fetch. 17 unit tests. SHIPPED 2026-05-29.
- [x] **G6. Premover → paper trade auto-execution** — `get/set_premover_mode()`, `evaluate_premover_trade()` (DD, max_open, duplicate, regime gates), `run_premover_eod()` in `scheduler/jobs.py`. `GET/POST /api/paper/premover_mode`. Telegram shadow summary. 8 unit tests. SHIPPED 2026-06-05.
- [x] **G7. Adaptive strategy switching by regime** — `adaptive_strategy_selector(ticker, df, min_consistency)` in `scheduler/scanner.py`: regime+ADX sub-band → strategy candidates via `_REGIME_STRATEGY_MAP`, consistency gate, fallback to `get_ticker_best_strategies()`. BEAR always returns []. Wired into `scheduled_multi_strategy_scan()`. 5 unit tests. SHIPPED 2026-06-05.
- [x] **G8. Post-suspension alert pipeline** — `send_suspension_resume_alerts()` in `scheduler/__init__.py`: queries `suspension_events WHERE resume_date=today`, fires Telegram alert with duration, gap%, CAUTION warning. 9 unit tests. SHIPPED 2026-05-30.

### ✅ High Value — dive.html UI Gaps

- [x] **G9. Suspension gap marker on chart** — Red ▼ SUSP Nd X% marker at resume bar. SHIPPED 2026-06-04.
- [x] **G10. Regime → strategy recommendation badge** — Tooltip on regime badge: "Recommended: [strategy]". SHIPPED 2026-06-04.
- [x] **G11. Crash context annotation on chart** — Client-side scan for >20% drop in 10-bar window; red ▼ CRASH X% markers. SHIPPED 2026-06-04.
- [x] **G12. Fundamental red flag badge** — Red ⚠️ badge: NPM<0, DER>3, earn_growth<-100. SHIPPED 2026-06-04.

### ✅ Documentation

- [x] **G13. BRPT case study in docs/** — `docs/BRPT_CASE_STUDY.md`: full timeline, ATR inflation, VR miscontextualization, strategy failure table (10 strategies), crash recovery validation, 5 design lessons. SHIPPED 2026-06-05.

---

---

## ✅ (Archived) June 2026 "Outstanding" list — all items shipped

_Superseded by the ACTIVE plan at the top of this file. Every checkbox below is `[x]`; retained for provenance only._

---

## 🔴 #1 — Sprint 18: Crash Early Warning System

_Source: macro_idx.md crash analysis (IHSG -34.84%, 9,135 → 5,952). Three broken sensors, five detection gaps, one composite score._

**⚠️ URGENT: IHSG crashing -2%+ today (June 5), approaching 5,600 from 5,839 close. System generated 67 BULLISH signals on May 1, 48 BULLISH on May 14 — mid-crash. System is blind to bear markets.**

### 🔴 Critical — Fix Broken Sensors (ship first)

- [x] **C1. Fix scheduled_signals BEARISH/SELL path** — Added `scan_distribution_signals()`: queries `stockbit_flow` for score≤-3 BEARISH tickers, filters by regime (skip BULL) + declining price, saves to `scheduled_signals` with `signal_direction='SELL'`. Extracted `_ensure_scheduled_signals_table()` + `_save_signals_to_db()` helpers; added `signal_direction` column (migration-safe). API returns `signal_direction` field. 11 unit tests. SHIPPED 2026-06-05.
- [x] **C2. Fix bandar_detector accdist calculation** — Root cause: `broker_accdist` stores text labels ('Acc'/'Dist'); `CAST(text AS REAL)` = 0.0 in SQLite, making every query that treated it as numeric return 100% accumulation bias. Added `accdist_label_to_score()` (7-level map: Big Acc→+3 … Big Dist→-3), `get_market_accdist_summary(date)` (dist_pct, acc_pct, avg_numeric_score, label). Wired into scanner daily log and `/api/market/accdist` endpoint (with `?series=1` for 30-day time series). 19 unit tests. SHIPPED 2026-06-05.
- [x] **C3. VPIN market toxicity sensor** — `get_market_vpin_summary(conn, date)` in `engine/vpin.py`: aggregates daily_screen vpin column into avg_vpin + pct_above_08 + pct_above_095 + label (GREEN/YELLOW/ORANGE/RED/CRITICAL). Thresholds: CRITICAL when pct_above_095≥75% or avg≥0.95 (matches Apr 28 crash: avg=0.973, 85% >0.95). Wired into scanner with Telegram alert on CRITICAL/RED. `/api/market/vpin` endpoint with `?series=1`. 12 unit tests. SHIPPED 2026-06-05.
- [x] **C4. Market breadth sensor** — `engine/breadth.py`: `get_market_breadth(conn, date)` computes advancers/decliners (vs prev trading day close), adv_dec_ratio, pct_advancing, pct_above_ma20 (20-day rolling), label (BULL_MARKET/NEUTRAL/WEAK/BEAR_MARKET). Wired into scanner daily log. `/api/market/breadth` endpoint with `?series=1`. 11 unit tests. SHIPPED 2026-06-05.
- [x] **C5. Technical death cross / lower high detector** — `engine/technicals.py`: `detect_ihsg_technicals(conn, date)` detects MA5/MA20 death cross (MA5 < MA20), lower high sequence (3-segment peak comparison), support breaks at 6,200/6,000/5,500. Label: BEARISH_TREND/DOWNTREND/NEUTRAL/UPTREND. Wired into scanner with Telegram alert on BEARISH_TREND+death_cross. `/api/market/technicals` endpoint. 12 unit tests. SHIPPED 2026-06-05.
- [x] **C6. Multi-sensor composite risk score** — `engine/risk_score.py`: `compute_market_risk_score()` weighted ensemble: VPIN 30% + accdist 20% + breadth 20% + technicals 15% + foreign flow 15% → 0-100 score, GREEN/YELLOW/ORANGE/RED/CRITICAL tiers. Wired into scanner pre-scan log. `/api/market/risk` endpoint (full sensor breakdown + sensors dict). 8 unit tests. SHIPPED 2026-06-05.

### 🟠 High — Alert & Response Infrastructure

- [x] **C7. Telegram alert routing by risk tier** — `engine/risk_alert.py`: `route_risk_alert()` CRITICAL→immediate Telegram, RED/ORANGE→market_risk_log (sent=0), GREEN→silent. `get_pending_risk_alerts()`, `mark_alerts_sent()`, `build_risk_summary_message()`. Scheduler: hourly RED bundle at :30, EOD ORANGE/YELLOW summary at 16:00. Wired into scanner post-risk-score computation. 10 unit tests. SHIPPED 2026-06-05.
- [x] **C8. Scheduled market health report** — `engine/health_report.py`: `build_market_health_report()` formats risk score, VPIN, breadth, accdist, foreign flow, IHSG technicals (death cross flags, support breaks) as Telegram message. Scheduler: 08:45 WIB Mon-Fri via `run_market_health_report()`. 8 unit tests. SHIPPED 2026-06-05.
- [x] **C9. Auto circuit breaker** — `engine/circuit_breaker.py`: `CircuitBreakerState` enum (OPEN/CLOSED), `check_circuit_breaker(risk)` → OPEN only on CRITICAL tier (fail-open for all others). `get_market_risk_for_circuit_breaker()` helper assembles live sensor data. `run_premover_eod()` gates on breaker state: OPEN → log + Telegram alert + return early. 9 unit tests. SHIPPED 2026-06-05.
- [x] **C10. VPIN batch compute for all tickers** — `run_vpin_daily_batch(date_str)` in `scheduler/jobs.py`: runs `calc_vpin()` for all tickers, persists to `vpin_scores` table (ticker, date, vpin, vpin_label, bucket_count, error) and updates `daily_screen.vpin`. Scheduler: Mon-Fri 18:00 WIB. `ensure_vpin_scores_table()` helper. 7 unit tests. SHIPPED 2026-06-05.
- [x] **C11. Backfill VPIN history** — `run_vpin_backfill(days=90)` in `scheduler/jobs.py`: iterates daily_screen dates for last 90 days, skips tickers already in vpin_scores, computes and saves gaps. Fail-open per ticker. SHIPPED 2026-06-05.

**Total Sprint 18:** ~26 hours, 11 tasks.

---

## 🟠 #2 — Sprint 19: IDX Watchlist Dashboard

_Source: macro_idx.md ticker scan + Sprint 18 market risk score concept. Single-page dashboard: "What is the market doing, and which tickers should I watch?"_

### 🎯 Goal

Replace scattered monitoring (Telegram + DB queries + macro_idx.md reports) with a single auto-refreshing dashboard — answered in <5 seconds.

### 🔴 Core — Backend Data Layer

- [x] **D1. `/api/dashboard/risk` endpoint** — Aggregates market risk: `risk_score` + tier, `ihsg` (OHLCV, MA5, MA20, death_cross, YTD), `breadth` (advancers/decliners, pct_up, trend), `foreign_flow` (today, 5d, 20d, trend), `vpin` (avg, % >0.8, % >0.95), `sectors` (top 3 accumulate/distribute). Read-only from walkforward.db. ~2 hr.
- [x] **D2. `/api/dashboard/watchlist` endpoint** — BUY WATCH / AVOID / WAIT lists: hammer (>3% intraday bounce) + foreign BUY >Rp 5B + volume >50M for buy_watch; foreign SELL >Rp 100B in 3d + YTD drop >20% for avoid; hammer + foreign SELL for wait. 10 unit tests. SHIPPED 2026-06-05.
- [x] **D3. `/api/dashboard/signals` endpoint** — Last 20 agent_decisions + today's scheduled_signals count by verdict. 8 unit tests. SHIPPED 2026-06-05.

### 🟠 Core — Frontend Dashboard (`templates/watchlist.html`)

- [x] **D4. Market Risk Gauge (sticky header)** — Large risk score (0-100) color-coded, tier label (SAFE/CAUTION/WARNING/DANGER/CRITICAL), mini 7-day sparkline, auto-refresh badge. ~3 hr.
- [x] **D5. IHSG Panel** — Current level, day chg%, intraday range, YTD, mini OHLC bars (10d), key support/resistance (5,500/5,000/6,200/6,500), MA status line. ~2 hr.
- [x] **D6. Breadth & Flow Panel** — Side-by-side gauges: adv/dec ratio, % above MA20, foreign net flow bar chart (10d). ~2 hr.
- [x] **D7. BUY WATCH Table** — Sortable columns: ticker, close, chg%, bounce%, foreign_net_3d, volume, entry_trigger, stop_loss. Color rows by conviction. ~3 hr.
- [x] **D8. AVOID Table** — Tickers to avoid: foreign distribution + YTD laggards. Red-tinted rows. ~1.5 hr.
- [x] **D9. WAIT List** — Distribution-into-bounce tickers. Amber rows. ~1 hr.
- [x] **D10. Sector Heatmap** — Grid: sectors as rows, columns for momentum/flow/VPIN. Green→red gradient. ~2 hr.

### 🟡 Nice-to-Have

- [x] **D11. Agent-Firm Live Feed** — Scrollable log of agent decisions with verdict badges. ~1.5 hr.
- [x] **D12. Checklist Panel** — Today's auto-checklist: data fetched ✓, signals scanned ✓, trades reviewed ✓. ~1 hr.
- [x] **D13. VPIN Toxicity Panel** — Gauge + % tickers above threshold + 30-day trend sparkline. ~1.5 hr.
- [x] **D14. Telegram `/dashboard` command** — Compact summary: risk tier + IHSG + top 3 BUY WATCH. ~1 hr.
- [x] **D15. Mobile-responsive** — Stack panels vertical, tables → cards, touch-friendly. ~1.5 hr.

### 📋 Dependencies

```
C1-C6 (Sprint 18) ────→ D1 (risk endpoint) ──→ D4-D6 (panels)
broker_flow (existing) ──→ D2 (watchlist) ────→ D7-D10 (tables)
agent_decisions ─────────→ D3 (signals) ──────→ D11 (live) + D12 (checklist)
```

**Prerequisites:** C1-C6 should ship before D1. D2-D3 can ship independently.

**Total Sprint 19:** ~26 hours, 15 tasks.

---

## 🟡 #3 — Sprint 15: Big-Liquidity Value Signal Filter

_Source: user request (2026-05-27). Pre-entry signal gate: restrict trades to high-liquidity stocks ranked by value metrics._

- [x] **L1. Define liquidity criteria** — ADV (avg daily volume ≥ threshold), market cap (≥ IDX30/LQ45 minimum), bid-ask spread (≤ 2%). Source: daily OHLCV volume + fundamental data.
- [x] **L2. Build value composite score** — Fundamental ratios: P/E (trailing), P/B, PEG, dividend yield, EV/EBITDA. Normalize and weight into `value_score` per ticker.
- [x] **L3. Integrate as pre-entry gate** — Insert liquidity + value filter into signal pipeline (`check_current_entry_signal()` or `scan_momentum_signals()`), before regime/quality gates. Reject signals below liquidity threshold or bottom value quartile.
- [x] **L4. Back-test filter impact** — Compare win rate, Sharpe, and max drawdown with vs. without filter.
- [x] **L5. Surface in dive.html** — Add `ADV`, `MktCap`, `value_score` columns to screener table. Color-code liquidity tier and value rank.

**Total Sprint 15:** ~10 hours, 5 tasks.

---

## 🔵 #4 — Backlog: Tier 4 Nice-to-Have

- [x] R13. Structured logging (JSON, correlation IDs, log rotation)
- [x] R14. Prometheus metrics endpoint (scan duration, signals generated, open trades)
- [x] R15. Multi-timeframe support (hourly/daily/weekly bar aggregation — like QC TradeBarConsolidator)
- [x] R16. Strategy warmup caching (avoid recomputing indicators every scan; cache per ticker per day)

---

## ✅ Sprint 14 — R12: GitHub Actions CI (SHIPPED 2026-06-22)

- [x] **R12. GitHub Actions CI + pytest for core engine** — `.github/workflows/test.yml`: runs full pytest suite on every push to `master` + all PRs, Python 3.12, pip cache, concurrency-cancel. Made the suite CI-safe in the process:
  - Restored orphaned `screener/brpt_filter.py` (committed import on `feat/chart-viewer` referenced a module that lived only on `fix/news-fetch-premarket-overnight`) — was blocking all test collection.
  - Fixed time-bomb in `tests/agent_firm/test_news_lookup.py` (hardcoded May dates vs relative `-30 days` window → anchored fixture to `date.today()`).
  - Fixed `tests/test_bear_watchlist_ranking.py`: `create=True` on `patch.object`, updated to log-only contract (Telegram send was intentionally removed in lean-notification audit `89baa33`), and isolated DB via temp `agent_decisions` table (was depending on ambient gitignored live DB). Updated stale docstring on `rank_bear_watchlist_and_notify`.
  - Verified: **597 tests pass with `data/walkforward.db` removed** (true CI condition).
