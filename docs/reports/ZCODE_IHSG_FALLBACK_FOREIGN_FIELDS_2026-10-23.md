# ZCODE — IHSG settled-bar fallback + order-book foreign fields (brief 2026-10-23)

**Deliverable for `ZCODE_BRIEF_IHSG_FALLBACK_AND_FOREIGN_FIELDS_2026-10-23.md` (F1, F2, F3).**
Executed 2026-10-23 15:25–16:05 WIB. Push HOLD (the brief's §Push: the earlier owner approval
covered only the push through `3fb2a73` / jurnal26 `5054fb6`).

| Item | Status |
|---|---|
| F1 Stockbit IHSG fallback in `repair_provisional_bars.py` | **DONE** (`21f9cec`) |
| F1.4 10-22 root cause + small fix in `finalise_index_bars` | **DONE — small, clear bug fixed** (report-only output; same commit) |
| F2 foreign-field semantics (jurnal26) | **DONE** (jurnal26 `a001496`), incl. the optional report context (cheap variant, deviation disclosed below) |
| F2.3 cross-repo reader audit | **DONE — no reader treats the book's f-fields as today's** (table below) |
| F3.1 PNBS bank-layout: parser check + runbook rule | **DONE — parser NOT at fault; rule written into the A3 runbook** (docs commit below) |
| F3.2 auction monitor first live day | **NOT RUN — by design: Monday 2026-10-26 after ~09:35** (checklist restated below) |

Test lines: 5001 `52 passed` (`test_repair_provisional_bars`, new
`test_repair_ihsg_stockbit_fallback`, `test_db_centralization`, `test_cron_contract`,
`security/test_secret_hygiene`, `test_fetcher_policy`); jurnal26 `249 passed` (full suite).
Live DB untouched by the repair work (dry run: "No stranded provisional bars on any past
session. Nothing to do."); all repair tests run on fixture DBs with yfinance/Stockbit mocked.

---

## F1 — `repair_provisional_bars.py`: Stockbit fallback for a stranded IHSG session

**Diff summary** (`scripts/repair_provisional_bars.py`, module docstring section "THE IHSG
FALLBACK (2026-10-23)"):

- **Trigger:** yfinance returns no bar for a stranded `(IHSG, date)` — the 10-21 case, where
  `^JKSE` jumps 10-20 → 10-22 while every stock carried a final 10-21 bar. Stocks keep the
  yfinance path untouched (their split basis is yfinance-derived; **no Stockbit price is ever
  written for a stock here** — pinned by test).
- **One GET per stranded IHSG session**: `GET {BASE}/company-price-feed/historical/summary/IHSG
  ?period=HS_PERIOD_DAILY&start_date=…&end_date=…&limit=30&page=1`, window ±12 calendar days
  (`FB_WINDOW_DAYS = REF_SPAN*2`, the same span the yfinance window covers, so the agreement
  check always sees both feeds over one window). Token read from `.stockbit_token` only; never
  a login. Live shape verified 15:31 WIB (HTTP 200) and pinned as
  `tests/fixtures/stockbit_ihsg_summary_window.json`; the 10-21 row equals the owner's
  hand-written fix exactly (open 5,310.848 / high 5,328.36 / low 5,185.36 / close 5,328.36 /
  volume 299,973,450).
- **Agreement gate before writing** (`FB_AGREEMENT = 0.05%`, set by reasoning from the one
  measured pair, not fitted): Stockbit's close must match yfinance's on the **nearest session
  both feeds serve** (the stranded date excluded). 10-22 measured: 5,387.905 vs 5,387.90 =
  0.0004%. Disagreement **or no common session** → skipped with the exact new reason
  `stockbit fallback disagrees with yfinance` (plus a `[fallback]` detail line naming the
  session and both closes), bar left provisional.
- **Stops:** 401/403/429/5xx/network → `StockbitUnavailable` → one `[stop]` line, **all further
  Stockbit GETs disabled for the run** (one token: they would fail the same way), script still
  exits 0 — the bar stays provisional and the 09:00 dead-man's check re-flags it next day.
- **Everything downstream unchanged:** IHSG is `NO_REBASE` (factor 1.0), `plausible_move` and
  the material-delta report still run, and the write is the script's existing
  `UPDATE … WHERE COALESCE(is_final,1)<>1` through `data.db.connect()` — no new write path.
- **Labelling:** each repaired date prints
  `1 via the Stockbit fallback (source: stockbit): IHSG 2026-10-21`. `ohlcv` has **no source
  column** (verified: id, ticker, date, open, high, low, close, volume, is_final), so the line
  also says "(ohlcv has no source column — provenance kept in this output only)" — none was
  added. If a `source` column ever exists, apply-mode sets it to `stockbit` for fallback rows
  (branch tested).
- **Edge guard:** a fully-empty yfinance window no longer swallows IHSG in the whole-date
  "no settled data returned" skip — the fallback must run and fail its agreement check loudly.

**Tests** (`tests/test_repair_ihsg_stockbit_fallback.py`, 8 new; incident values as fixtures):
yfinance-gap+agreement → repaired `is_final=1` with the owner's exact values and
`source: stockbit` labelling · disagreement (3.5% off on the common session) → new reason, bar
untouched · no common session (empty yfinance window) → new reason, whole-date skip bypassed ·
401 → rc 0, exactly ONE GET for two stranded dates (no retry, no second date), both bars
provisional · stocks never call the Stockbit path · source-column branch · live-response parse
(URL window ±12 d, Bearer header, row fields).

## F1.4 — why the 10-22 bar was provisional and unreported at 10-23 09:00

Journal-evidenced timeline (`journalctl --user -u idx-walkforward`, `logs/app.log`,
`logs/cron_provisional_bars_check.log`):

1. **10-21 intraday:** `_save_df` writes the 10-21 IHSG bar provisional (the ~11:05 snapshot,
   close 5,297.77, volume 0 — the value every scan carried that day).
2. **10-21 09:31:** `IHSG: finalised 1 provisional past session(s)` — that settled **10-20**,
   correctly; 10-21 is "today" and excluded (yfinance `end` is exclusive). The 16:15 EOD
   scraper settles tradebook tickers **only, never the index** (stated in
   `finalise_index_bars`' own docstring) — so nothing settles an index bar on its own day.
3. **10-22 09:31:** incremental fetch ran, **no "finalised" line at all**:
   `finalise_index_bars` had pending={10-21}; `yf.download(^JKSE, start=10-21, end=10-22)`
   contained no 10-21 row, so the update loop never visited the date → n=0 → the print is
   conditional on n → **silent**. No `IHSG finalisation failed` warning exists either (grep of
   app.log: zero hits) — the function returned normally.
4. **10-23 09:00:** `check_provisional_bars` flagged 10-21 (`GRACE_DAYS = 2` crossed, rc=1).
   The 10-22 bar — close 5,219.4 vs settled 5,387.9, −3.13% — was **one day old, inside the
   grace window, so not flagged** ("not flagged as stranded yet" is by design, not an
   additional failure). The repair `--apply` then settled 10-22 via the normal yfinance path
   before the 09:10 staged-fill fetch (which is why no "finalised" line appears on 10-23
   either — nothing was left pending).

**Direct answer:** yes — the finalisation step **skips a pending IHSG date silently when
yfinance lacks the day**: it iterates yfinance's rows only, so a pending date absent from the
download is never visited, counted, or reported, and n=0 produces no log line.

**Fix applied** (small and clear, `data/fetcher.py`): `finalise_index_bars` now reports the
unresolvable remainder by name — `IHSG: N provisional past session(s) still unsettled
(yfinance returned no bar): <dates>` — printed (→ service journal, like the existing
"finalised" line) **and** `logging.warning` (→ app.log), covering the empty-download path too.
No change to what gets *written* — the data repair for that case is the fallback above, which
keeps the token dependency out of the always-running fetcher. Test added
(`test_finalise_index_bars_names_sessions_yfinance_lacks`); the three existing finalise tests
pass unchanged.

## F2 — order-book `fbuy/fsell/fnet` are the previous session's foreign flow

**F2.1 — corrected explanations.**
`auction_watch.py`'s C1 field comment and `docs/ZCODE_AUCTION_WATCH_2026-10-22.md` C1 both
said "not used … not this session's number". Replaced with the verified semantics: **the
previous session's foreign buy/sell/net** — BBCA's `fnet` read Rp448.09bn at 09:09 on 10-22,
exactly the 10-21 `net_foreign` of the dated historical summary (brief §0). The doc note also
records that the original wording was a guess and this is the corrected, source-matched
statement.

**F2.2 — optional report context: DONE, cheap variant, one disclosed deviation.**
`parse_snapshot` now stores `prior_fnet` from the **already-fetched** book reply (zero extra
GETs) and the daily report renders it per name as `prior-session foreign net ±RpX.Xbn`
(earliest read of the day wins — the pre-open read is unambiguously prior-session). It feeds
no alert, threshold, or statistic, and is never presented as today's flow; backfilled past-day
reports (built from dated trade pages, no book reads) simply omit it.
**Deviation:** the brief prefers the historical summary's dated `net_foreign` as the source;
using it would add ~30 GETs/day on a second endpoint, which is not "cheap" against the C2
budget (~240 GETs/day) — so the book field is used, with the equality of the two sources
verified on the BBCA datapoint and the semantics stated everywhere the value appears.
Switching the source later is a three-line change if the planner disagrees.

**F2.3 — reader audit (both repos; grep `fbuy|fsell|fnet|net_foreign|foreign_buy|foreign_sell`
+ `orderbook`):**

| Reader | What it reads | Treated as today's? | Change |
|---|---|---|---|
| jurnal26 `auction_watch.py` (comment + new `prior_fnet`) | book `fnet` | no — labelled prior-session | comment corrected; context field added (F2.2) |
| jurnal26 frozen `bigplayer_watch.py` / `tape.py` / `limit_watch.py` | **zero reads** of the f-fields (grep) | n/a | none (D-098/D-108; untouched, hashes pinned by tests) |
| jurnal26 `index.html` (5004 cards) | `net_5d` / `foreign_net_5d` / flow5 — broker-flow 5-day aggregates, dated by construction | no | none |
| 5001 `engine/agent_firm_context.py`, `engine/agent_firm/schemas.py`, `agents/flow.py` | `net_foreign_owned_brokerage_lots_14d` from `broker_flow` (investor_type='Asing' lots) | no — 14-day aggregate, not the book | none |
| 5001 `_archive/idx_fetcher.py` | writer of the **historical summary's** per-date foreign columns (each row dated) | no | none (archived) |
| 5001 `tools/ajaib_fetcher.py` | Ajaib vendor debug tool; its "orderbook" is a different API | n/a | none |

**Conclusion:** nothing anywhere reads the book's f-fields as today's flow; the only display
fixes needed were the two documentation corrections in F2.1.

## F3.1 — PNBS bank-layout caveat: parser verdict + runbook rule

Parser check on the pilot's raw files (offline; `~/idx_external/stockbit_fin/raw/`):

- **BBCA** income statement carries `Interest Income` / `Interest Expense` (`account_en`) and
  `Pendapatan Bunga` / `Beban Bunga` (`account_id`) — the bank layout, parsed correctly by the
  same generic extractor.
- **PNBS** carries **neither, in either language** (both `account_en` and `account_id`
  grepped) — its statement rows are the generic template, the same shape as TLKM's
  (Total Revenue / Others / Total Pendapatan / Total COGS / Gross Profit / …).

**Verdict: the parser is NOT mis-mapping — the feed itself serves PNBS through the generic
template.** `parse_report` is a faithful row extractor (it stores whatever `acc-name` rows the
HTML carries, with both language names); no fix is needed and none was made.

**Runbook updated** (`docs/reports/ZCODE_FQ_FULL_PULL_2026-10-21.md`, Y2/A3 step 6): the
Sunday coverage table's bank-vs-non-bank split keys on **Interest-Income presence —
`Interest Income` in `account_en` OR `Pendapatan Bunga` in `account_id`, both languages
checked** — never on issuer type/SIC. Banks that file under the generic template (PNBS is the
first known) go on a footnote list inside the coverage table itself, so the Sunday turn needs
no rediscovery.

## F3.2 — NOT RUN (Monday 2026-10-26, after ~09:35; fresh check)

1. `jurnal26-auction-iep/match/post` fired (enable one-shot ran 16:20 today, 10-23);
2. `data/auction_events.jsonl` has lines for every phase;
3. `data/auction_reports/2026-10-26.md` rendered;
4. no request errors;
5. `GET /api/auction?date=2026-10-26` with the **read** token
   (`~/.config/autoclaw-idx-monitor/read_token` — never the owner token);
6. confirm the C5 backfill ran tonight 19:00 (log `data/auction_backfill_20261023.log`,
   reports for 10-16/19/20/21/22) — armed from the consolidated brief, not this one.

## Timer state at close of this turn (15:54 WIB, 10-23)

`enable-auction-timers-20261023` 16:20 today (pending) · `auction-backfill-20261023` 19:00
today · `fq-fullpull-20261025-s1` Sun 09:05 · `-s2` Sun 13:00 · the three auction timers
themselves still `disabled`, exactly as designed until 16:20. Nothing was scheduled through
ZCode's own automation.

## Commits (all local; push HOLD)

- 5001 `21f9cec` — F1 fallback + F1.4 loud remainder + tests (this report's evidence).
- 5001 docs commit (this one) — F3.1 runbook rule + this report.
- jurnal26 `a001496` — F2 corrections, `prior_fnet` context, 3 tests (suite 249 passed).
