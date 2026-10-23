# ZCODE BRIEF — Consolidated 2026-10-22: {FQ} pilot → Sunday, market-risk fix, opening-auction monitor + daily analysis

**Issued:** 2026-10-22 ~09:30 WIB, by Claude (planner role). Owner: "next task for zcode — update all including
auction monitoring and analyzing".
**Supersedes for scheduling:** `ZCODE_BRIEF_UPDATE_2026-10-22.md` (its U1–U3 are folded in here as A1–A3).
**Still in force:** every rule of `ZCODE_BRIEF_FQ_FULL_PULL_AND_PIT_REVISION_2026-10-21.md` and
`ZCODE_BRIEF_TOKEN_REFRESH_HARDENING_2026-10-21.md` (token file read-only, no login, never touch the saved login at
`~/.local/state/idx-walkforward/playwright_state`, `safe_restart.sh` only, no outcome reads on fundamentals).

## Standing rules for this brief
- **Never use ZCode's own automation/scheduler.** It binds the chat (one automation per session), and it dies on a
  Z.ai 429 (10-21 19:05). Anything that must run at a time is a **systemd user timer** (`systemd-run --user` for
  one-offs, unit files in the repo for recurring jobs). A model turn only checks results afterwards.
- **Push: HOLD.** Origin is 8 commits behind, and the 6 token-hardening commits (`d904430..6deaaf0`) sit **under**
  the {FQ} commits, so any push publishes them. Commit locally. Push only after the owner writes "push" (Claude
  reviewed the token commits on 10-22 and found nothing blocking; the decision is the owner's). jurnal26 (3 J1/J2
  commits + new work) is on the same HOLD.
- **jurnal26 frozen files** (D-098/099/103/108): `bigplayer_watch.py`, `tape.py`, `limit_watch.py`. Do not edit.
  Import them read-only.
- **Telegram is important-only** (`logs/TELEGRAM_OFF` stays). Do not add a new always-on message. Anything new that
  sends must go through the existing policy (5001 `utils/notify_policy`, jurnal26 `notify`), and needs a stated reason
  to be `BLACKOUT_EXEMPT`.
- **Research boundary.** The auction monitor (C) is **descriptive context**, like `macro_watch`. Daily per-name
  reports are fine. **Pooled statistics across days** ("does an IEP gap predict the 09:15 move?", hit rates,
  averages, t-stats) are a hypothesis test: they need a mechanism D-entry and a frozen G0 first (D-070 §1, D-086).
  Do not compute or print them. Store the raw records so a later registered study can use them.
- Each item ends DONE, BLOCKED (why) or NOT RUN (why) in the deliverable.

---

## A. {FQ} financials (carried over)

**A1 — Validate tonight's pilot.** The systemd timer `fq-pilot-20261022` fires at **19:05 WIB** (check:
`systemctl --user list-timers fq-pilot-20261022.timer`). It runs the token check, the 10-name fetch and `parse`, and
logs to `logs/fin_pilot_20261022.log`.
- Do **not** run a second pilot while it's pending. If there's no `START` in the log by 19:15, run the same three
  commands yourself before 21:50.
- After ~19:45 (or Friday morning), score the five pass criteria:
  1. all 3 statements × 10 names;
  2. BTEL and TRAM history present;
  3. bank layouts (BBCA, PNBS) parsed;
  4. no 401, 403 or 429;
  5. parse failures 0, or each one explained.
- Fill the pilot table and the extrapolation in both reports. Commit (push HOLD).

**A2 — Arm Sunday, only if A1 passes.** Wrapper `scripts/fin_full_pull_20261025.sh` (`4a56236`) as two one-off
timers via `systemd-run --user`, at **Sun 2026-10-25 09:05** (tag `s1`) and **13:00** (tag `s2`, resume).
- Before arming, fix the small issues Claude found in review:
  - `pgrep -f tape_backfill` matches any process whose command line contains that text (an editor, a grep). Match
    the real process precisely, e.g. `pgrep -f 'jurnal26/.venv/bin/python .*tape_backfill.py'`, or check the systemd
    unit state (`systemctl --user is-active jurnal26-tape-backfill.service`).
  - Make `s2` refuse if an `s1` fetch is still running: a lock file, or `pgrep` on the fetch command.
- Confirm `crontab -l` still has `40 21 * * 6,0` (the Saturday token). Record the unit names in the report.

**A3 — After Sunday's data exists** (Sun afternoon or Mon, fresh chat):
- run `parse`, write the sha256 manifest and the coverage table;
- copy to `/mnt/storage2tb/idx-archive/stockbit_fin/`, verified on both sides;
- write the PIT v2 draft (propose only), per `ZCODE_BRIEF_FQ_FULL_PULL_AND_PIT_REVISION_2026-10-21.md` Y2.4–Y3.

## B. Market-risk score: stop a lagging trend reading from setting today's tier (5001, production)

**Finding (Claude review, 10-22).** On 2026-10-21 the score read **97.5 CRITICAL (09:05) → 74.5 → 96.0 → 96.0 →
94.0** while IHSG was **+0.36%**. The 09:05 `risk.market_critical` alert was sent (BLACKOUT_EXEMPT). The cause is the
10-16 rule in `engine/risk_score.compute_market_risk_score`: a missing sensor is dropped and the others are rescaled.
With VPIN `n/a` and accdist empty, `technicals` (BEARISH_TREND since the MSCI drop, a slow MA/structure read) carries
most of the weight, so a lagging trend state is presented as today's market risk.

1. **Reproduce.** Run a hermetic test with the 10-21 09:05 / 11:05 component values (pull them from the logs or
   recompute them read-only from the DB for that date). Show the 97.5 and the 96.0.
2. **Fix proposal: pick one and justify it in the report.**
   - (a) **Coverage gate.** CRITICAL and RED need at least 2 live *flow/breadth* sensors (vpin, accdist, breadth,
     foreign_flow). With fewer, cap the tier at ORANGE and label it "partial sensors: n of 5".
   - (b) **Weight cap.** Cap `technicals`' rescaled weight (e.g. at 0.35) so one slow sensor can't exceed 1/3.
   - In both cases the **IHSG shock floor stays exactly as is**: −8% on the day's own bar is CRITICAL whatever the
     sensors say. Tests: the 10-16 live event (−8.01% open → CRITICAL) must still pass, unchanged.
3. **No new tuned constants beyond the one in your choice.** State that it was set by reasoning, not fitted. Record it
   as a production change in `docs/OPERATIONS.md`, or wherever the 10-16 change was recorded. It is not a research
   result, so no D-entry is needed unless you find the 10-16 change was itself a D-entry. Check, and supersede that
   entry if so.
4. **Deploy:** run `scripts/safe_restart.sh` **after 16:15** (never during market hours). Then verify the next
   scan's log line.
5. Also fix the small `--preopen-check` issues from the review:
   - on a second same-day run, a deduped alert makes it exit 1, which triggers cron_wrap's generic alert as a
     duplicate. Treat "deduped" as delivered;
   - the weekend wording says "before the 08:50 OHLCV fetch". Make it day-aware.

## C. Opening-auction monitor + daily analysis (jurnal26, new)

**Why (owner, 10-22):** "8.58 is the auction time. need to see what happened and after 9.00." Today the only
pre-open read was `macro_watch`'s single **08:56:27** snapshot of 20 big caps' indicative open. It took no read at the
match, no comparison with the actual open, and no read after 09:00. Claude's manual read today (09:09) showed:
- the auction matched about −1.5% (median, 20 big caps) against −1.4% indicated;
- in the first 9 minutes, buyers took BBCA −2.8% → −1.4%, BMRI/BREN/GOTO back to flat, PGAS −3.7% → −1.5%;
- TPIA, ASII and ICBP stayed at or below the open;
- SMIL (a watch name) opened 444, fell to **420, below its planned stop of 436**, and was back to 438 by 09:09.

**C1. Verify the session timetable first.** From the Stockbit feed itself, and IDX's trading rules if reachable,
establish the exact pre-opening phases now in force:
- order entry, the non-cancellation period if any, the match time (trades stamped **08:58:00** in the running trade),
  and the continuous-session start (09:00);
- whether the Friday schedule differs.

The order-book reply has `iepiev` (a dict: indicative equilibrium price/volume), `open`, `high`, `low`,
`lastprice`, `previous`, `volume`, `value`, `frequency`, and market-wide `up/down/unchanged`.
- Document each field's meaning by observation.
- **Do not use `fbuy/fsell/fnet`** without checking them: BBCA's `fnet` read Rp448bn at 09:09 against Rp163bn traded
  today, so it isn't today's session.

**C2. New module `auction_watch.py`** (jurnal26; it imports `bigplayer_watch` only for the token, book and page
helpers).
- **Universe:** the `macro_watch` 20 big caps, plus holdings, watch list and `adhoc_tape` names. Dedupe it.
- **Reads per weekday:**

  | Time (WIB) | Read |
  |---|---|
  | 08:50, 08:55, 08:57:30 | IEP and IEV from `iepiev`: the indicative open and its volume |
  | ~08:59 | the match: `open` and the 08:58:00 auction trades from the running trade (matched volume and value) |
  | 09:02, 09:05, 09:15, 09:30 | `lastprice`, `high`, `low`, `volume`, plus the 5-level book share via `tape.book_read` |

- **Budget:** ~30 names × 8 reads ≈ 240 GETs/day at ≥0.3 s spacing. Stop on 401/403, back off on 429. Run nothing
  21:05–06:30.
- **Storage:** append-only `data/auction_events.jsonl`, one line per name per read, each with `date`, `phase`,
  `ticker`, the fields, `prev_close`, the `bands` ARA/ARB floor in force, and a `version` (the module's git hash).
  Never rewrite it.
- **Timers:** recurring systemd user units in the repo's deploy files, the same pattern as
  `jurnal26-macro-preopen.timer`, with `Persistent=false` (a missed auction read is gone, not caught up). Install
  outside market hours.

**C3. Daily analysis: descriptive, per day.** Add `auction_watch.py report [DATE]`, written to
`data/auction_reports/<date>.md`. Also show it on the jurnal26 card/API only if the Brokers/Research tab pattern makes
that cheap; otherwise the file alone. The report covers:
- **Market:** the median IEP move at 08:50/08:55/08:57:30 → the matched open → 09:15 → 09:30, and the breadth counts.
- **Per name:** prev close, IEP path, auction open (% vs prev and vs the last IEP), auction volume as % of the 09:30
  volume, and the 09:15/09:30 last.
  - Mark "**reversed**" when the 09:30 move from the open has the opposite sign and is at least 1%; "**extended**"
    when the same sign and at least 1%.
  - These two words describe the day. **They are not a signal**; say so in the report's footer.
- **Your names first:** holdings and watch, each against its plan's stop/target/zone. Flag any name that traded
  through its stop or zone between 08:58 and 09:30 (SMIL today), and any at or near the ARB/ARA at the match.

**C4. Alerts** (owner policy: important only). One Telegram message per day at most, sent ~09:01 and **only** when
a **holding** matched at or within 1% of the ARB, or opened ≥5% below its previous close.
- It uses the existing jurnal26 `notify` positions path. Make it `BLACKOUT_EXEMPT` only if that path already is.
- Everything else goes to the report file only.

**C5. Backfill a few days for the report format.** Running-trade history serves past sessions (`date=`, 12 months),
so build reports for **10-16 (the MSCI shock), 10-19, 10-20, 10-21 and 10-22**:
- use the 08:58:00 auction trades and the trades to 09:30;
- the IEP path is not recoverable for past days. Mark it "n/a (not recorded)".

These five reports are for the owner to read. **Do not pool them into statistics** (see the research boundary).

**C6. Tests (hermetic):**
- universe build and dedupe;
- phase scheduling and the budget guard;
- 401/429 stop;
- report rendering from fixture lines, including the reversed/extended labels and the stop-breach flag;
- the alert rule fires only for holdings under its two conditions;
- frozen-file hashes unchanged.

## Order of work
1. **B** (code + tests now; restart after 16:15 today).
2. **C1 → C2 → C6** (code today), with timers installed after 16:15 so they start Friday 08:50. **C5** backfill
   after 19:00, outside the token-heavy windows.
3. **A1** after ~19:45 tonight.
4. **A2** once A1 passes.
5. **A3** Sunday/Monday.

## Deliverable
`docs/reports/ZCODE_CONSOLIDATED_2026-10-22.md` (5001) for A and B, and
`~/jurnal26/docs/ZCODE_AUCTION_WATCH_2026-10-22.md` for C. Include:
- test result lines, the restart log line, and the timer list (`systemctl --user list-timers` excerpt);
- the C5 report paths;
- every item's status;
- all commit hashes (not pushed: push HOLD until the owner says "push").
