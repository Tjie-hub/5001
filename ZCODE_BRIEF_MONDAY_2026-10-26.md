# ZCODE BRIEF — Monday 2026-10-26: auction live check, PEAD G0 power run, {FQ} PIT follow-ups, index rebalance prep

**Issued:** 2026-10-26 08:50 WIB, by Claude (planner role). Owner: "delegate all task for zcode".
**Repos:** `~/10 Projects/idx-walkforward-5001` (`ops/hardening-2026-07-10`) and `~/jurnal26` (`main`).
**Push: HOLD** in both repos until the owner says "push" (fast-forward only). Commit locally.
**Scheduling:** systemd one-shot timers (`systemd-run --user`) only; never ZCode's own automations.

## State at issue (verified 08:49)
- 5001 is in sync with origin (last `9fcd90d`). jurnal26 `main` is **3 commits ahead** of origin (HOLD unchanged).
- Weekend brief `ZCODE_BRIEF_WEEKEND_2026-10-24.md`: G1 DONE; **G2 and G3 NOT RUN** (carried below as H2 and H1).
- Sunday Y2 full pull is closed (`9372efb`): fin.db 957 tickers, 0 parse failures, archive verified 2,873/2,873.
- {FQ} PIT v2 (`11_FQ_PIT_RULE_DRAFT_V2_2026-10-25.md`): owner approved **D1–D8 as recommended, record only**
  (§10, `9fcd90d`). **D9 (freeze / v3) NOT approved.**
- Auction timers 08:50 / 08:59 / 09:02 armed for their first live fire today.

## Rules
- Stockbit: read `.stockbit_token` only, never log in, stop on 401/403/429. Nothing heavy 21:05–06:30.
- Frozen: jurnal26 `bigplayer_watch.py`, `tape.py`, `limit_watch.py`; `P-M/pead/` at `e7e68db`. No outcome reads on
  any frozen forward record.
- Production DB: writes only via `data.db.connect()`. Research code never imports execution modules.
- D-numbers, PEAD registration, the {FQ} freeze and any v3 belong to the owner: propose text, do not file.
- Restart 5001 only via `scripts/safe_restart.sh`, never a bare `systemctl restart`.

## H1. Auction monitor — first live day (jurnal26) — today after ~09:35
This is F3.2 of `ZCODE_BRIEF_IHSG_FALLBACK_AND_FOREIGN_FIELDS_2026-10-23.md` plus the unchecked part of weekend G3.
1. `journalctl --user -u jurnal26-auction-iep -u jurnal26-auction-match -u jurnal26-auction-post --since today`:
   each fired once, exit 0. If any failed, report the error line; fix only a clear bug, with a test.
2. `data/auction_reports/2026-10-26*` exists and reads sensibly: prev close from the 5001 DB, IEP/gap, match print,
   first minutes. Compare a few names against the backfilled 10-16..10-22 reports for format.
3. `GET /api/auction?date=2026-10-26` with the read token (`~/.config/autoclaw-idx-monitor/read_token`, never the
   owner token) returns today's report.
4. Telegram: the auction output must respect the important-only allowlist. Report what, if anything, was sent.

## H2. PEAD G0 power run (5001) — today after 16:00 (it refuses during market hours)
Carried from weekend G2 unchanged. Run `docs/research_programs/P-M/pead/g0_pead_power.py` per
`G0_FREEZE_PEAD_2026-10-23.md` (~1–2 GB RAM). Power check only, **not** an outcome read: no post-event return may be
looked at. The pre-run arithmetic expects power ~2–8% against the 20% minimum, so the stop rule probably fires.
Report the numbers, whether it fired, and a **proposed** D-entry text (WITHDRAWN uncounted if it fired, like the
10-16 sector arm and {LC} D-110). Do not file it.

## H3. {FQ} PIT — prep work for the approved D4 and D8 (5001, data only)
The owner approved D1–D8 (record only). Do **not** write a v3, do not freeze, do not file a D-entry.
1. **D4 late-filer list:** from the reachable news sources already cited in v2 §3 and the Sources list, build
   `P-M/data_acquisition/12_FQ_LATE_FILERS_2026-10-26.csv` (ticker, period, sanction tier, source URL, [P]/[S] tag)
   for every period those articles name. Count repeat names. No join to prices, no returns.
2. **Unfiled at day 30:** the count v2 §9 lists as "not built". Use only data that exists without an outcome read;
   if the data cannot answer it, say why.
3. **D8 primary texts:** retry reachability of (i) Kep-36/PM/2003, (ii) Kep-00087/BEI/12-2025 and the pre-2025 I-E
   article, and the COVID-era IDX decisions (Kep-00027/BEI/03-2020, Kep-00089/BEI/10-2020) from this machine. Record
   exactly what was reachable. Anything blocked goes on an owner-browser list with its URL.
4. Write `12_FQ_PIT_FOLLOWUPS_2026-10-26.md`: results of 1–3, plus which D-items are now unblocked for a v3 if the
   owner later asks for one.

## H4. Index rebalance 2026-11-02 — prep only
The IDX30/LQ45/IDX80 lists are hand-kept in `fetcher.py` + the `idx_tickers` flags + the jurnal26 backfill (last
update `91cc4bb`, Aug–Oct 2026).
1. Find the IDX announcement of the constituents effective 2026-11-02 (reachable news/secondary if idx.co.id is
   blocked; tag the source).
2. If found, prepare the change as a commit that is **not applied to `idx_tickers` before 2026-11-02**, plus a dated
   one-shot timer or written instructions for the switch. Report adds/removes per index.
3. If not yet announced, say so and stop.

## Deliverable
`docs/reports/ZCODE_MONDAY_2026-10-26.md` (5001): each of H1–H4 as DONE / BLOCKED (why) / NOT RUN (why), the PEAD G0
numbers with the proposed D-entry text, the files written, and the commit hashes of both repos.
