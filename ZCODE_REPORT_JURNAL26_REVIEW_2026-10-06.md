# ZCode report — adversarial review of jurnal26 (2026-10-06)

Review of `/home/tjiesar/jurnal26` at HEAD `36abec3` (branch `main`, clean tree). Read-only on the
target; every dynamic test ran against a `sqlite3.backup()` copy of `data/jurnal.db` served on port
5099 with a test-only token and a dead `JURNAL_PROD_URL` (nothing touched 5001). Queries against
`data/walkforward.db` used `mode=ro`. **The 5099 instance and the DB copy were deleted afterwards**
(killed PID 284329, `rm -rf /tmp/jurnal26-review-5099`, port verified dead); `~/jurnal26` git tree is
still clean, both live services stayed active, no Telegram was sent, no token was printed (tokens were
compared by truncated SHA-256 only).

Verdict up front: no Critical finding. The server-side sync engine held up under everything I threw at
it. The damage concentrates in the client money math and its disagreement with `review.py` once data
arrives from anywhere other than the validated UI forms — plus one stored-XSS class and an isolation
model that is safe only by accident of which timers exist.

---

## High

### H1. `review.build()` and `calc()` disagree on the same transactions after an over-sell: the Research tab shows phantom money — CONFIRMED

- `review.py:107-115` (no sell clamping) vs `index.html:217` (`var q=Math.min(t.qty,p.qty)`).
- Scenario: `BUY 1000@100`, `SELL 1200@120`, `BUY 500@110` — the over-sell is blocked by the trade
  form (`index.html:622`) but **passes unvalidated through `importData()` (`index.html:1108-1116`) and
  any force-push from a device with drifted local state**. `importData` accepts any JSON with a `txns`
  array; no per-txn validation exists anywhere client- or server-side.
- Result: Stocks tab (calc, clamped): position **500 sh @ avg 110.17**. Research tab (review.build,
  unclamped): position **300 sh @ avg 38.64, cost 11,592.50, P/L +1,840,907.50** — a fantasy number
  derived from a negative cost basis. `position_alerts.journal()` (`position_alerts.py:32-38`) uses the
  same unclamped arithmetic, so alerts key off the phantom 300-share view too.
- Evidence (both run on the real code):
  - Node harness executing the actual `calc()` from `index.html`:
    `D UI calc -> AAA qty 500 avg 110.17 | closed cycles: 1`
  - `review.build()` on the 5099 copy with the same three txns (prod stubbed):
    `{"qty": 300, "avg": 38.6416..., "cost": 11592.5, "mv": 1852500.0, "pl": 1840907.5, ...}`
- Fix: clamp sells in `review.build()` and `journal()` exactly as `calc()` does
  (`q = min(t.qty, p["qty"])`, skip when `q <= 0`, reset the cycle at 0), and reject over-sells at the
  import boundary (`importData`: for each ticker, running qty must never go negative).

### H2. A same-day SELL can be silently swallowed when ids are not chronological — CONFIRMED

- `index.html:202` sorts by `(date, id)`; `index.html:217-220` drops a SELL whose clamp is 0 with no
  warning (`if(q<=0)return`).
- Scenario: a device (or an imported backup) holds `SELL 100 (id 1)` and `BUY 1000 (id 2)` with the
  same date. The SELL is processed first against an empty position, clamps to 0, and vanishes: its
  proceeds never reduce cost, no journal entry is created, `fillMissing()` can't see it. The txn still
  lists in History, so the books *look* complete.
- Evidence (real `calc()`, Node harness):
  `H -> sell-before-buy same date: AAA qty 1000` — the 100-share sale had no effect at all.
- Ids are only guaranteed chronological per device (`nextId`); `importData`/cross-device merges mix
  id spaces, so the precondition is realistic.
- Fix: when a SELL clamps to zero (or is short), surface it — a badge like the `missing` journal
  entries ("N sales could not be applied") — and validate on import that per ticker, in (date,id)
  order, sells never exceed held shares.

### H3. Stored XSS: ticker is interpolated unescaped into inline handlers and headings — CONFIRMED

- `index.html:439,441,443,446` (`onclick="editPx('`+x.ticker+`')"` etc.), `index.html:957`
  (`openRv` path), and unescaped HTML at `index.html:913` / `931` (`row(r)`/`rvDetail` inject
  `r.ticker` raw — this one comes from review.json, i.e. from the synced state).
- The trade form does not validate ticker format (`saveTrade` has no regex; only the sniper form does,
  `index.html:810`), and the server accepts anything (`PUT /api/state` checks only that `txns` is a
  list).
- Evidence: on the 5099 copy I stored ticker `X');alert(1)//` via `PUT /api/state` (accepted, echoed
  back by `GET /api/state`); `renderEq` then produces `onclick="editPx('X');alert(1)//')"` which
  executes. Vectors: typing it, importing a crafted backup JSON, or syncing from a device whose state
  was tampered with.
- Escalation: the sync token lives in localStorage (`inv_cfg`, `index.html:1083`), so injected JS can
  read it — the token guards both journal instances' full read/write API.
- Fix: validate tickers at every entry point (form, import, and server-side `PUT`:
  `/^[A-Z0-9]{2,6}$/` like `saveWatch`), and `esc()` tickers in the onclick builders / rv rows (or
  attach handlers via `addEventListener` with data attributes).

### H4. Fees are user-configurable in the UI but hardcoded in review.py — CONFIRMED

- `index.html:141` defaults `bf:0.0015, sf:0.0025` but Settings edits them (`saveCfg`,
  `index.html:1091`); `review.py:24` hardcodes `BF, SF = 0.0015, 0.0025`.
- Evidence (real `calc()` with `CFG.bf=0.001, CFG.sf=0.003`): UI avg **100.10** on a 1000@100 buy;
  `review.build()` reports **100.15**. The Research tab's qty/avg/P/L/weight silently disagree with
  the Stocks tab for every position whenever the owner tunes fees.
- Fix: store the fee pair in the synced state (e.g. `state.cfg`) and have `review.build()` read it, or
  freeze fees and remove the Settings fields.

---

## Medium

### M1. Net-cost accounting displays nonsense after a large profitable partial sell — CONFIRMED

- `index.html:214-244`: sells reduce `p.cost` by net proceeds, so a deep-ITM partial sell drives cost,
  avg and BEP negative, and `unrPct` is zeroed by its `cb>0` guard.
- Evidence (real `calc()`; buy 1000@100, sell 990@500, price 500):
  `qty 10 | avg -39361.25 | cb -393612.50 | unrPct 0.00 | be -39459` — the card shows
  "Avg −39,361", "BEP −39,459", "+398,600 (0.00%)". Totals stay right and the realized P/L at full
  close is exact (verified by hand: 13,024.25 in test G), so this is a display defect, not a books
  defect.
- Fix: once `cb <= 0`, switch the card to "proceeds already recovered + remaining 10 sh" wording
  instead of an average; at minimum suppress negative avg/BEP.

### M2. 5003/5004 isolation is safe only because no timer ever runs against 5003 — CONFIRMED

- Verified safe today: separate DBs, separate tokens (SHA-256 prefixes `e9e234…` vs `d0856b…`), per-DB
  `-review.json`/`-review-reads.json`/`candidates`, `jurnal26-review.service` pins
  `JURNAL_DB=jurnal.db`, and *none* of the other alert/screener units set `JURNAL_DB`, so they all
  default to `data/jurnal.db` (`server.py:19`). No file, spool line or message from user B reaches
  user A today.
- But the shared, not-per-DB state means one env var flips it into a leak:
  `digest_spool.jsonl` (`notify.py:20`), `position_alert_state.json` (`position_alerts.py:21`),
  `watch_alert_state.json` (`watch_alert.py:18`), `bank_alert_state.json`, `three_push_state.json`,
  `climax_alert_state.json` — all keyed by bare file. Run any alert script with
  `JURNAL_DB=jurnal-5003.db` and (a) user B's tier-2 items land in the **owner's** digest, (b) B's
  `stop:BBCA:2026-10-06` dedup key suppresses the owner's BBCA stop alert (or vice versa) — a missed
  act-now alert.
- The flip side already bites: **5003's user has no stop/target/zone/suspension/insider alerts at all
  and no review timer** — if they enter positions with stops, nothing watches them, silently.
- Fix: derive state files per DB stem (as review.py does), and either give 5003 its own timers or state
  explicitly in the README that alerts cover 5004 only.

### M3. The digest-merge plan (brief §8 / `ZCODE_BRIEF_DIGEST_FOLLOWUP_2026-10-06.md` §3) — challenge: the contract cannot keep instances or outages apart

- **No per-instance field.** The line contract is `{event, ts, text, source?, section?}` with
  `source: "jurnal26"`. There is one buffer for the whole host. The moment anything ever runs against
  the 5003 DB (M2), user B's positions enter the owner's digest with no way to filter them. Add an
  instance/user field to the contract now, while it's cheap.
- **The 2-day stale skip deletes jurnal items on a 5001 outage.** D4 archives `>2 calendar days` old
  items to `.stale`, never sent. jurnal26's own sender today has no such drop. If 5001's flush is down
  (service stopped, TELEGRAM_OFF left on over a weekend — the current kill file has been in place since
  Oct 5) while jurnal's timers keep appending, day-3+ items are permanently undelivered. jurnal tier-1
  items are unaffected (they go direct), but every tier-2 alert would silently evaporate.
- **Section collision.** jurnal's `market_label` change writes section `"Market"`, which merges under
  5001's Market header; the owner can't tell a journal heuristic line from a 5001 line. Give jurnal
  sections a `jurnal26: ` prefix or their own top grouping.
- **ts format**: contract wants epoch seconds; `notify.digest()` writes ISO strings today — must be
  converted when repointed, or the flush's stale math misparses.
- **Cutover orphans**: retiring jurnal's 17:45/19:50 timers leaves anything still sitting in
  `digest_spool.jsonl` unsent forever; migrate it at cutover.
- Timezone is *not* a problem: the host clock is Asia/Jakarta (verified `timedatectl`), same as the
  buffer's `<date>` naming. File permissions are also fine (same UID, umask 0077 on the writers).

### M4. No backups of `data/jurnal*.db`, no restore test — CONFIRMED

- `backup/` holds exactly two files from 2026-10-05 (the pre-migration export). The DB is the only
  complete store (client localStorage is per-device and wiped by a pull); daily snapshots live *inside*
  the same file that would be lost. Nothing WAL-safe runs automatically; `manage.py restore` exists but
  has never been exercised against a backup of the live file.
- Fix: a daily user timer doing `sqlite3.connect(src, mode=ro).backup()` (or `VACUUM INTO`) to
  `backup/jurnal-YYYYMMDD.db` + 30-day retention, and one documented restore drill.

### M5. Every watchlist cache miss is a ~13 s full-universe scan of the production DB — CONFIRMED (measured)

- `watchlist.screen` (`watchlist.py:39-79`) pivots ~500 days × all tickers; measured on this host:
  `screen seconds: 13.34 | date 2026-10-05 | picks 31`. It runs in up to three separate processes
  around the EOD window (`three_push` 17:05/19:05, `screener` 17:20/19:20) plus on every
  `/api/watchlist` cache miss in each server process. A 13 s read transaction on `walkforward.db` holds
  back WAL checkpoints of the production writer for its duration (all jurnal26 opens are `mode=ro` —
  verified at every call site — so this is deferral, not corruption).
- Also: the mtime cache key (`server.py:331`) uses main-db and `-wal` mtimes; every 5001 checkpoint
  truncates/regresses the key and forces a needless rescan.
- Fix: cache the screen result in a small per-DB JSON (like review.json) written by one timer, and have
  both servers and `three_push`/`screener` read it; or key the cache on `max(final date)` instead of
  mtimes.

### M6. Resolving a 409 with "Pull from server" destroys this device's edits irreversibly — PLAUSIBLE

- `pullState(true)` (`index.html:1054-1067`) overwrites every `S.*` array from the server; the local
  arrays are gone from memory *and* localStorage (`saveLocal()` follows). The server keeps daily
  snapshots, but the device that lost the race has no local undo and no export prompt. A phone edited
  offline whose push then 409s (desktop edited meanwhile) loses one side's entries by design — the UI
  offers no merge and no pre-discard export.
- Fix: before a destructive pull, stash current local state to `inv_pre_pull_<date>` (or auto-download
  the export JSON) and mention it in the confirm dialog.

### M7. Both instances bind 0.0.0.0 on the Werkzeug dev server with no rate limiting — CONFIRMED

- `server.py:343` (`app.run(host="0.0.0.0")`), no throttle on `/api/*`: a LAN/Twingate peer can
  brute-force `X-Token` unthrottled. Token entropy looks adequate (≥32 chars), auth is fail-closed and
  constant-time (`server.py:50-59`), and there are no CORS headers, so browser cross-origin writes are
  blocked — the exposure is raw TCP guessing plus Werkzeug's dev-server robustness.
- Fix: `waitress`/`gunicorn` on 127.0.0.1 with the reverse side (Twinget/pack) doing the exposure, or
  at least add a simple failed-attempt backoff.

### M8. A malformed `*-review-reads.json` kills the whole review build; the timer failure is silent — PLAUSIBLE

- `review.py:125` (`json.loads(READS.read_text())`) and `:167` (`date.fromisoformat(w["date"])`) are
  uncaught; a bad hand/Claude edit to the reads file makes every refresh fail. In the server the tab
  shows `refresh_error` (good), but the 17:25/19:25 timer is a oneshot whose traceback goes only to the
  journal — the Research tab then serves a stale build indefinitely with nothing flagged to the owner.
- Fix: wrap reads per-ticker (skip bad entries), and make `review.py` failure emit a tier-2 digest line
  (the same trick as the `stale:` watchdog in `position_alerts.py:202-205`).

### M9. bank_alert's self-description is now stale vs HYP-PM-0014, and its exit date ignores IDX holidays — CONFIRMED

- `bank_alert.py:5-6` says "Not registered/forward-tested in the idx-walkforward governance corpus";
  the alert text says "Not forward-tested" — but since 2026-10-05 the exact same rule **is** registered
  (HYP-PM-0014) and **is** in forward test (`docs/research_programs/P-M/forward_bank/PROTOCOL.md`,
  recorder cron 09:40). The honest label is "forward test in progress, not yet validated". The code
  comment at `bank_alert.py:130` ("the only validated edge") overstates it the same way (protocol §5:
  "the forward test is what decides").
- `add_trading_days` (`bank_alert.py:61-67`) counts Mon–Fri only, so the "sell around {date}" line can
  name a day before the actual 10th session when Indonesian holidays fall in the window; the protocol
  counts sessions from `trading_calendar`.
- The per-bank evidence strings match the protocol's frozen numbers exactly (BBCA n56 +1.64%, BBRI
  +2.02% t 3.04, BMRI +0.24%, BBNI −0.50%) — those held up.

### M10. Thread-pool starvation can take down prices and analysis together — PLAUSIBLE

- One shared 8-worker pool (`server.py:123`) serves `/api/prices` and `/api/analysis`; `yfinance`
  calls have no internal timeout (`_fetch_price`), so 8 hung Yahoo requests freeze both endpoints
  (`wait(..., timeout=...)` returns, but workers stay busy and later requests queue). Recovery requires
  the sockets to eventually error out.
- Fix: give the pool a separate small pool for prices vs analysis, or set `socket.setdefaulttimeout`.

### M11. `notify.send_digest` has the same crash-window item loss 5001's D1 fixed — CONFIRMED (code trace)

- `notify.py:48-60`: `SPOOL.replace(work)` → read → send → `work.unlink()`. A crash between the rename
  and the unlink strands every item in `digest_spool.jsonl.sending` forever: the next run sees no
  SPOOL and prints "digest empty". Also `emit()` appends to the spool *before* `sent[key]` is saved, so
  a crash between them re-emits (duplicate digest item) on the rerun — benign by comparison.
- Fix: on startup of `send_digest`, merge any leftover `*.sending` back into the spool before
  proceeding (the same claim-then-read ordering 5001 now uses). Note this whole path is slated for
  retirement by the merge (M3), but until that lands it is the live sender.

---

## Low

- **L1** `review.py:128` — the `mode=ro` prod connection in `build()` is never closed (leaks one
  handle per build inside the server's refresh thread).
- **L2** `screener.py:140-153` — `cur` is read in a transaction that is immediately rolled back, then
  `_write` re-begins and writes that (now possibly stale) snapshot; a phone edit landing in the window
  is clobbered for keys other than `watch`. The comment claims the opposite of what the code does.
- **L3** No dependency pinning at all (no requirements.txt; venv shows yfinance 1.7.0, pandas 3.0.6,
  Flask 3.1.3) — a yfinance API change breaks quotes/prices silently (they already fail soft).
- **L4** `index.html:293` — "Fees & costs" in Metrics is gross-minus-net where gross uses rounded
  per-cycle average prices; it's an approximation labelled as an exact number.
- **L5** `/api/prices` lacks the `isalnum()` filter `/api/analysis` has (`server.py:260` vs `:137`);
  junk tickers go straight to yfinance.
- **L6** `importData` accepts any shape (root of H1/H2); even a `txns: [{}}]`-style typo can corrupt
  state that then syncs everywhere.
- **L7** Deleting a swing BUY silently converts its closing SELL into a core sale and drops the
  "closed swings" P/L line (`swingOf`, verified in test F: closedPL 14,842.50 → 0.00). Books stay
  consistent; the swing history just disappears.

---

## Challenged and held up

- **Optimistic concurrency (§2):** on the 5099 copy — stale `baseVersion` → 409; missing `baseVersion`
  → 409; emptying `txns` against non-empty old → 400; `force=1` empties and *keeps* unsent keys
  (shallow merge); four concurrent valid PUTs → exactly one 200, three 409; exactly one snapshot per
  day (pre-first-change state); `BEGIN IMMEDIATE` serializes correctly.
- **Auth (§4):** every `/api/*` route (state GET/PUT, prices, analysis, review GET/POST refresh,
  candidates, watchlist) returns 401 with no or a wrong token — tested individually; fail-closed unset
  token; `compare_digest`; token in a header, never the URL; no CORS headers, so cross-origin browser
  writes can't carry the custom header (CSRF blocked by construction).
- **Swing / reverse-swing bookkeeping (§1):** partial closes, over-closes (clamped identically in core
  and lot accounting), cycle resets clearing lots, `rsKept`, buy-back netting — verified against the
  real code with hand-computed expectations; realized P/L at full close is exact to the rupiah
  (13,024.25 on a 4-txn reverse-swing scenario); `pa.swing_open`/`reverse_open` mirror `swingOf`
  faithfully.
- **Alert hygiene (§5):** `is_final=1` on every bar query; provisional bars excluded; `watch_alert`
  requires a bar dated *today* (no pre-open false fires); suspension check tolerates a provisional
  bar; the `stale:` EOD watchdog threshold is sane (825 finals on a normal session vs the <500
  trigger) and correctly stayed silent on 2026-10-06 (not a calendar session — verified in the DB);
  intraday dedup keys are per ticker+day; 10-session cool-lists match the studies. Holiday behaviour
  verified live: today's 11:00 timer runs were no-ops.
- **Honesty labels (§6), mostly:** three-push and non-bank climax alerts carry their null results
  inline; volume-climax/ARB/MA-break/insider texts state "no edge/information only"; the bank
  per-name evidence strings match the frozen protocol numbers; the screener footer and AUTO-sniper
  `why` say "unvalidated sources". Residual overstatements are M9 (bank alert framing) and the sniper
  card's ready-to-execute "Limit orders: N lot @ X" line, which reads like a recommendation even
  though the source disclaimer exists (worth a "not a signal" tag on AUTO cards).
- **SQL/path safety (§4):** parameterized SQL everywhere including the dynamic IN-list
  (`position_alerts.py:324`); ticker path injection into 5001 URLs blocked by the `isalnum` filter on
  `/api/analysis`; every `walkforward.db` open across all seven call sites uses `mode=ro`.
- **Ops (§9):** all `OnCalendar` specs parse as intended (`systemd-analyze calendar` normalized forms
  checked, including `09..15:00/15`); timers and host clock are both Asia/Jakarta; linger is on and
  both services/timers are enabled (reboot-safe); `Persistent=true` reruns are harmless because
  `bank_alert` re-checks the bar date and the EOD dedup keys hold; journal usage is trivial (506 lines
  for the main service); `data/` and `backup/` are git-ignored.

## Cleanup statement (required by the brief)

The 5099 server was killed (PID 284329, port re-checked dead), `/tmp/jurnal26-review-5099` including
the DB copy, test token, harnesses and logs was deleted. No browser was used against 5099, so no
localStorage to clear. `~/jurnal26` was not modified: `git status` clean at start and end; live
services `jurnal26.service` and `jurnal26-5003.service` untouched and active throughout.
