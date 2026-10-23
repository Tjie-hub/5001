# ZCODE BRIEF — jurnal26: a labelled P/L basis for holdings, and tape recording for names checked by hand

**Issued:** 2026-10-21, by Claude (planner role). Owner: "next task", "delegate to zcode".
**Repo:** `~/jurnal26` (branch `main`). The 5001 repo is touched only to read the decision log.

## 0. What Claude found

**J1, cost basis.**
- `ledger.positions()` mirrors `index.html` `calc()`: sort by (date, id), clamp sells to the shares held, apply fees,
  and reduce the remaining cost by each sell's net proceeds (**net-cost average**). The cycle resets at 0 shares.
- So `cost / qty` is **net cash still at risk per share**, not an average buy price. On 2026-10-21 the read showed:

  | Name | Last price | cost / qty |
  |---|---|---|
  | BMTR | 56 | 457 |
  | ARNA | 500 | 778 |
  | TOWR | 402 | 524 |
  | INDR | 2,800 | 7,211 |

- The figures above are what the review used. They are **not wrong by construction**, but they are unlabeled, so no
  report can quote profit or loss from them. The INDR figure, net cost per share 2.6× the price, deserves a direct
  check: is it a mis-entered transaction, or real realised losses?

**J2, tape for names checked by hand.**
- `bigplayer_watch.py MAPI --check` (ad hoc) records that day's tape for MAPI only while it runs.
- MAPI on 10-20 had tape only to 09:00 until Claude ran it at 14:03. Names not on the watch list or in holdings get
  no full-session tape.

## Rules
- **D-098/D-099/D-103/D-108 freeze.** `bigplayer_watch.py`, `tape.py` and `limit_watch.py` are frozen forward-record
  instruments. **Do not edit them.** J2 is built in a **new** module or script that imports `tape` and
  `bigplayer_watch` read-only. Ad hoc names must **never** write to `bigplayer_events.jsonl` or `limit_watch_events.jsonl`,
  or enter the watch/holdings universe the D-098 record is defined on (protocol §4: watch list plus holdings).
- **The journal is the owner's book.** Never write to `state` / `txns` / `plans` / `watch`. Read only.
  `index.html` `calc()` stays the authority: any new number must reproduce it exactly where they overlap.
- **Stockbit:** read `.stockbit_token` only, never log in, keep request budgets small, and stop on 401/403/429. Do not
  run anything heavy 21:05–06:30, when the nightly tape backfill shares the token.
- Tests are hermetic (`pytest -q` in `~/jurnal26`, currently 203 passed). Commit locally; **do not push**.
- **Restarts:** server changes need a jurnal26 restart. Do one only after 16:15, and say how you restarted.

---

## J1. A labelled P/L basis next to net cost

1. **INDR check:** list its `txns` (date, type, qty, price) and say whether 7,211 per share is real (realised losses
   carried into net cost) or a data-entry error (e.g. a price in rupiah thousands, or qty in lots). **Report only.**
   If it is an entry error, describe the fix for the owner to make in the UI; do not edit it.
2. Add `ledger.basis(st)` returning, per open position:
   - `qty`;
   - `net_cost`, which is today's `cost`;
   - `avg_buy`: the average buy price of the shares still held in the current cycle, including buy fees, with sells
     removing shares at the running average;
   - `realised`: realised P/L in the current cycle, net of fees.

   Invariant to test: `net_cost == avg_buy * qty - realised`, to the rupiah after rounding rules are fixed.
3. **Tests:**
   - one buy;
   - two buys then a partial sell (gain, then loss);
   - a sell that over-sells, clamped;
   - a full exit, then re-entry, resetting the cycle;
   - fees from `cfg` and the defaults;
   - and the invariant on the live book shape, using a synthetic copy and not the real DB.
4. **Where it shows.** Use it in the scripts' text (`position_alerts`, `review`, and `bigplayer_watch`'s "Held position"
   line is frozen, so **not** there). Label the numbers explicitly, e.g. `avg buy 61 · unrealised -8.2% · realised
   -Rp3.1M · net cost/share 457`. Before showing it anywhere in `index.html`, ask the owner in the report; do not add
   it unasked.

## J2. Record the day's tape for names checked by hand

1. New script `adhoc_tape.py`:
   - `adhoc_tape.py add MAPI [--until YYYY-MM-DD]` writes a separate list, `data/adhoc_tape.json`, with today as the
     default end date;
   - `list` and `drop` subcommands.
2. **Recording.**
   - On a schedule (systemd user timer or cron, every 5 minutes during 09:00–16:15 on weekdays), record each ad hoc
     name's tape into the existing `tape` table with `bigplayer_watch.record()` and its paging budget.
   - Before 09:00:30 coverage exists, the first run backfills toward the open, as the watch recorder already does.
   - No events, no alerts, no state file, no event-log lines.
3. **Universe guard.** Any name already on the watch list or in holdings is skipped, since the D-098 recorder owns
   those. Test that an ad hoc name never reaches `bigplayer_events.jsonl`.
4. **Labelling.** Ad hoc names' tape is stored in the same `tape` table. Write a side table or a jsonl
   (`adhoc_tape_log.jsonl`: date, ticker, rows added) so a later study can tell ad hoc coverage from the D-098
   universe. **No outcome reads.**
5. **`--check` view.** `adhoc_tape.py read MAPI` prints the same descriptive session read that `bigplayer_watch`
   prints: `tape.session()`, `divergence()` and `tempo()`, plus `book_depth` on a fresh book. It is print-only.
6. Add the timer unit, or the cron line, to the repo's deploy files the way the existing jurnal26 timers are kept.
   Install it only after tests pass, outside market hours.

## Deliverable

`docs/ZCODE_PNL_BASIS_ADHOC_TAPE_2026-10-21.md` in `~/jurnal26` (or wherever jurnal26 keeps reports), covering:
- the J1 INDR finding, the basis numbers for the four holdings, and the test lines;
- the J2 install log, plus one recorded name end to end (rows per half-hour);
- each item as DONE, BLOCKED (why) or NOT RUN (why), and the commit hashes.

Not pushed.
