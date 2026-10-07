# ZCODE REPORT — evening digest follow-up (2026-10-06)

**Branch:** `fix/telegram-curation` · **Commit:** after `33681ec` (not amended) ·
**Brief:** `ZCODE_BRIEF_DIGEST_FOLLOWUP_2026-10-06.md` (f85911e)
**Constraints honored:** `logs/TELEGRAM_OFF` untouched and still in place; no Telegram
message sent (all verification with capturing fakes / tmp dirs); no service restarted;
`~/jurnal26` untouched.

## 1. What changed, per item

**D1 — items appended during a flush were lost.** `flush_digest` now claims first, then
reads: every live `<day>.jsonl` is atomically renamed (`os.replace`) to `<day>.jsonl.sending`
before reading, so an item a cron process appends during the flush lands in a fresh
`<day>.jsonl` and can never be archived unsent. On a successful send `.sending` → `.sent`;
on a failed or suppressed send the `.sending` files stay and are picked up by the next flush
(leftover `.sending` files are claimed again at the start of every flush). Never dropped.
Test: `test_d1_item_appended_during_flush_is_not_lost` (a fake sender appends mid-flush;
the late arrival survives to the next flush's message).

**D2 — digest always rejected as HTML.** Item text is now `html.escape()`d, the raw
`<{event}>` token is gone, and items are grouped under readable `<b>Section</b>` headers.
The only unescaped `<`/`>` left in the message are the tags the flush emits on purpose
(`<b>`, `</b>`, `<i>`, `</i>`); a test asserts that after stripping those, no `<` or `>`
remains (`test_d2_digest_message_is_html_safe`, plus a dedicated `&`, `<`, `>` offender test).
The old silent degradation to plain-text-with-literal-`<b>` cannot recur.

**D3 — second flush on the same day was impossible.** Choice: **a separate event
`report.late_digest` (TIER_SEND, once_per_day)**, registered in EVENTS; `flush_digest` takes
an `event` parameter (default `report.evening_digest`) and the late flush is a one-line
wrapper `flush_late_digest()`. I chose the distinct event over a `main`/`late` subject
because it reads clearly in the registry and in the dedup-state file. Every part of a
flush shares the event and is distinguished by `subject="partN"` so multi-part digests
are not swallowed by once_per_day either.

**D4 — backlog after the blackout.** At flush time, items from buffer files older than
**2 calendar days** (file-name day, WIB) are archived to `<day>.jsonl.stale` and never
sent; when any were skipped the message ends with one line:
`… N older items skipped (see logs/digest_buffer)`. Unparsable file-day names are treated
as fresh (never silently dropped). Tests: `test_d4_items_older_than_two_days_are_stale_skipped`
(includes the exactly-2-days-old boundary item being kept) and
`test_d4_only_stale_items_no_send`. One deliberate semantic choice to make D4's model
accurate: the gate now buffers tier-2 items **even while `TELEGRAM_OFF` exists** (dedup
still applies), so the buffer does grow during a blackout and the first flush after it is
lifted delivers ≤2-day items; tier-1 sends remain fully blocked by OFF.

**§2 Late flush at 20:45 WIB.** New scheduler job `notify_late_digest` (daily 20:45 WIB,
same `_add_job` guarded registration) calling `flush_late_digest()`. Empty buffer →
returns `None` and sends nothing (covered by `test_late_flush_silent_when_buffer_empty`).
The 17:45 main flush is unchanged; the CI test
`test_digest_flush_jobs_registered` now asserts both jobs and their times.

**§3 Shared buffer for jurnal26.** The line contract is documented in the
`notify_policy.py` module docstring: one JSON object per line, single `write()` call,
file `logs/digest_buffer/<YYYY-MM-DD WIB>.jsonl`,
`{"event": str, "ts": float, "text": str, "source": str (optional), "section": str (optional)}`.
The flush accepts lines with `source` and unregistered events — the classification gate
applies to sends from this codebase, not to lines already in the buffer. Malformed lines
(not JSON, not an object, missing/empty `text`) are skipped, counted, and logged as one
WARNING per flush — never fatal (`test_malformed_buffer_line_skipped_never_fatal`).
Grouping: explicit `section` wins, else event-prefix mapping (market.* → Market,
report.* → Reports, screener.* → Screener, data.*, risk.*, trade.*, llm.*, bot.*,
system.* → matching labels, else Other). External items render with a small
`<i>(jurnal26)</i>` suffix. When the digest exceeds ~3,800 chars it is sent as
consecutive parts (`(1/2)`, `(2/2)`) under the same gated event; the `.sent` archive
happens only after ALL parts went out — a part-2 failure keeps the claimed `.sending`
files for the next flush (`test_multi_part_split_when_over_limit`,
`test_multi_part_failure_keeps_everything`).

**§4 Owner decisions** — all applied as ruled: 1–3 kept log-only; 4 kept tier 1 with the
requested comment added at the `data.ohlcv_reconcile` registry line ("review after 1 week
live; demote to digest if it fires most days"); 5 forward-test summary stays digest and
now gets same-evening delivery via the 20:45 late flush (it runs at 18:30, before 20:45).

## 2. D3 choice

Separate event `report.late_digest` (TIER_SEND, once_per_day) + `flush_digest(event=…)`
parameter; the 20:45 job registers the `flush_late_digest` wrapper. Multi-part sends
additionally use `subject="partN"` so a single once_per_day key can never suppress a
later part or a later flush's first part.

## 3. Sample rendered digest (fixture buffer with 5001 + jurnal26 lines — NOT sent)

Built by a throwaway script against a tmp `DIGEST_DIR` with a capturing sender; the
jurnal "Screener" line deliberately contains `<textarea>`, `&` and `>` to show escaping.

```
📋 <b>Evening Digest</b> — 2026-10-06

<b>Reports</b>
• EOD Trade Plan 05/10 — 3 BUY candidates: BBRI 4.780 (SL 4.690), TLKM 3.120 (SL 3.060), ASII 5.150 (SL 5.020)
<b>Market</b>
• IHSG label change: RECOVERY → DOWNTREND (death cross, broke 6200)
<b>Screener</b>
• EOD retry: 7 tickers finalised, now 822/958 final
• 2 hits: &lt;textarea&gt; injection test &amp; 100% &gt; 90% escaped ok <i>(jurnal26)</i>
<b>Positions</b>
• BBCA closed +2.1% at 8.850; open exposure now Rp 12.4M <i>(jurnal26)</i>
<b>Patterns</b>
• BUMI stair-case bottom forming, watch 5.20 breakout <i>(jurnal26)</i>
<b>Corporate actions</b>
• TLKM cum-date tomorrow (dividend Rp 129/share) <i>(jurnal26)</i>
<b>Weekly</b>
• W40 review: 4 trades, 3 green <i>(jurnal26)</i>
```

Sent as `event=report.evening_digest subject=part1`; buffer dir afterwards:
`['2026-10-06.jsonl.sent']`.

## 4. Tests

- New/updated in `tests/test_notify_policy.py`: D1 claim-then-read, D2 HTML-safety (×2),
  D3 late-flush-not-blocked + late-flush-silent-when-empty, D4 stale skip + only-stale
  no-send, external-source lines + section grouping + prefix fallback, multi-part split +
  multi-part failure keeps `.sending`, malformed lines skipped, tier-2 buffering during OFF
  with dedup applied. Classification gate now asserts the 20:45 job too.
- Targeted run (notify policy + classification + telegram util + both redaction suites +
  auto_token + EOD finalisation token + cron contract + security route policy + scheduler
  wiring): **139 passed**.
- Full suite (background): **3506 passed, 0 failed, 3 skipped** in 19m12s, with the
  production `logs/TELEGRAM_OFF` kill file present throughout.
- `python -m py_compile` clean on every touched file (`utils/notify_policy.py`,
  `scheduler/__init__.py`, `tests/test_notify_policy.py`,
  `tests/test_notify_policy_classification.py`).

## 5. Not done / notes

- `~/jurnal26` untouched, per the brief — the jurnal side points its `notify.digest()` at
  this buffer and retires its own timers after this commit lands.
- No service restart; production still runs the blackout build until the owner deploys.
- `logs/TELEGRAM_OFF` still in place; with this branch deployed, tier-2 items will buffer
  while it exists (deduped) and the first post-lift flush sends ≤2-day items only.
