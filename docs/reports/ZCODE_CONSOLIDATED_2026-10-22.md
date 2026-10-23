# ZCODE — Consolidated brief 2026-10-22 (A: {FQ} pilot→Sunday · B: market-risk coverage gate)

**Executed:** 2026-10-22 09:40–19:30 + 2026-10-23 08:15–08:45 WIB. Branch `ops/hardening-2026-07-10`.
**Push: HOLD** (per the brief — the 6 token-hardening commits sit under everything and publish
with any push; awaiting the owner's "push"). Item C's report lives in jurnal26:
`~/jurnal26/docs/ZCODE_AUCTION_WATCH_2026-10-22.md`.

## A. {FQ} financials

### A1. Pilot validated — **DONE, 5/5 PASS**

The 10-21 19:05 ZCode-automation attempt died one second in on a Z.ai 429 (quota; zero GETs).
The pilot ran as the systemd one-shot `fq-pilot-20261022` on **10-22 19:05** (log
`logs/fin_pilot_20261022.log`): preopen-check OK → fetch 30/30 HTTP 200 (no 401/403/429) →
parse 125,192 rows, 0 failures, END 19:05:52. Claude validated 5/5; the numbers were re-verified
read-only from `manifest.jsonl` + `fin.db` and recorded in BOTH reports
(`docs/reports/ZCODE_FQ_FULL_PULL_2026-10-21.md` §Y1 with per-name quarter ranges, and the
companion `ZCODE_FQ_BACKFILL_LC_FILING_2026-10-21.md` pilot table + extrapolation):

1. 10 names × 3 statements — PASS (30/30 files, zero `n_values=0`);
2. BTEL → **Q3-2025**, TRAM → **Q3-2019** — PASS;
3. bank layout — PASS on parsing, with a caveat recorded: **BBCA** shows the bank layout
   (Interest Income/Expense rows); **PNBS parses fully but its stored rows are the generic
   (non-bank) template** — the Sunday coverage table's bank split must key on Interest-Income
   presence, not issuer type;
4. no 401/403/429 — PASS; 5. parse failures 0 — PASS.

Extrapolation: 1.63 s/GET → the remaining **2,847 GETs ≈ 77 min**, inside the 170-min cap;
≈ **12.0M rows** expected.

### A2. Sunday armed — **DONE**

`scripts/fin_full_pull_20261025.sh` (`4a56236` + review fixes in `f664cd8`):
- the backfill guard now checks **service state** (`systemctl --user is-active --quiet
  jurnal26-tape-backfill.service`) — the old `pgrep -f tape_backfill` matched any command line
  carrying that text;
- **flock** on `~/idx_external/stockbit_fin/.pull.lock`: the 13:00 s2 resume refuses while s1
  still runs; no stale locks (released at process exit).
- Tests: 6 (incl. the new lock-refusal case) + backfill 27 = **33 passed**.

**Timers armed and verified** (`systemctl --user list-timers`):
`fq-fullpull-20261025-s1.timer` — **Sun 2026-10-25 09:05 WIB**; `fq-fullpull-20261025-s2.timer`
— **Sun 13:00 WIB** (resume/no-op safety net). `crontab -l` confirmed `40 21 * * 6,0` → the
Saturday-21:40 token is valid to Sunday ~21:40, covering both sessions; all clear of jurnal26's
21:05 backfill. Stop conditions live inside the fetcher (401/403; a second 429; >5% parse
failures).

### A3. After the data exists — NOT RUN (by design)

Sunday afternoon / Monday, **fresh chat**: `parse`, sha256 manifest, coverage table (bank split
by Interest-Income presence — see the PNBS caveat), off-SSD verified copy, Y3 PIT v2
(propose only). Runbook in `ZCODE_FQ_FULL_PULL_2026-10-21.md`.

## B. Market-risk score: coverage gate on the top tiers — **DONE (deployed 10-22 16:20)**

**Reproduced exactly** (`tests/test_risk_live_event.py`, from the logged 10-21 components):
09:05 = 97.5 with vpin/accdist/breadth all missing — technicals (100, slow BEARISH_TREND)
rescaled to half the weight beside the 5-day foreign flow (95) — read CRITICAL while IHSG sat
+0.36%; 11:05 = 96.0 with breadth at its unrounded 93.75.

**Fix chosen: (a) coverage gate** over (b) weight cap. CRITICAL/RED now require **≥2 live
flow/breadth sensors** (`vpin`, `accdist`, `breadth`, `foreign_flow`); with fewer the tier caps
at ORANGE and the result carries `coverage: "partial sensors: n/4 flow-breadth live"`. Why not
(b): capping technicals at 0.35 still leaves ≈97 when it is the only high sensor — it trims the
number, not the claim. One new constant (`2`), **reasoning-set, not fitted**: a top tier claims
today's market is in trouble, which needs corroboration from at least two independent live
readings. The **IHSG shock floor overrides the gate** (the 10-16 −8.01% event still reads
CRITICAL — that test is unchanged). Honest scope: 10:05 (2 live) still reads RED and 11:05
still CRITICAL — the sensors themselves read high there; that is not a coverage failure.

**D-entry check:** the 10-16 change was hotfix `f56cdeb` with **no D-entry** (DECISION_LOG hits
that week are the halt-arb recorder and mechanism drafts) → no D-entry here either; both rules
are recorded in `docs/OPERATIONS.md`'s new "Market-risk score" section.

**Deploy:** `scripts/safe_restart.sh` ran via the one-shot `risk-gate-restart-20261022` at
**16:20:37 on 10-22** (journalctl: gunicorn restarted, listening on 5001) — outside market
hours. **Scan verification:** the first scans under the new code are this morning's; a one-shot
(`risk-gate-verify-20261023`, 09:07) captures them via `scripts/risk_gate_check.py` to
`logs/risk_gate_check_20261023.txt` — expect the 09:05 partial-coverage read ORANGE-labelled
where it used to say CRITICAL (10-21 09:05 sent a BLACKOUT_EXEMPT alert; today's must not).

**B.5 `--preopen-check` fixes** (same commit): a deduped alert now counts as delivered
(`send_telegram` returns the suppression reason — truthy — so a second same-day run exits 0
instead of tripping cron_wrap's duplicate generic alert), and the fix deadline is day-aware
(weekdays: before the 08:50 OHLCV fetch; weekends: the 21:40 refresh may repair). 3 tests.

## Test lines (5001 side)

```
tests/test_risk_live_event.py:      20 passed   (15 prior + 5 gate/reproduction)
tests/test_auto_token.py:           60 passed   (57 prior + 3 B.5)
tests/test_fq_full_pull_script.py:   6 passed   (+ backfill 27 in the same run: 33)
push-gate suites re-run with A2:    33 passed
```

## Commits (all LOCAL — push HOLD)

| commit | item |
|---|---|
| `b89e47b` | B: coverage gate + 5 tests + OPERATIONS record + B.5 preopen fixes |
| `4a56236` | U3/A2 prep: full-pull wrapper + guard tests (10-22) |
| `cb04355` | 10-22 scheduling note in the FQ report |
| `f664cd8` | A1 recorded 5/5 + A2 review fixes + Sunday timers armed |

jurnal26 (same HOLD): `b50fcaf` (item C) on top of `7a41d04`/`5a7795e`/`5c1e3e4`.
Mimosa pre-commit scans were inconclusive (`scanner_enobufs`) throughout; compatibility policy,
no safety claim.

## Status

| item | status |
|---|---|
| A1 validate pilot | **DONE — 5/5 PASS** (recorded in both reports) |
| A2 arm Sunday | **DONE** — s1 Sun 09:05, s2 Sun 13:00, flock + service-state guards, token schedule confirmed |
| A3 after-data turn | **NOT RUN** — Sunday/Monday fresh chat, by design |
| B coverage gate | **DONE — deployed 10-22 16:20**; scan-line capture pending (`logs/risk_gate_check_20261023.txt` after 09:07) |
| B.5 preopen fixes | **DONE** |
| C auction monitor | **DONE/ARMED** — see `~/jurnal26/docs/ZCODE_AUCTION_WATCH_2026-10-22.md` (first fire Mon 08:50; C5 backfill tonight 19:00) |
