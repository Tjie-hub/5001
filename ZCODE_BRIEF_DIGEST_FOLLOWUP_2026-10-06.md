# ZCode brief — evening digest follow-up (2026-10-06)

**Branch:** continue on `fix/telegram-curation` (on top of `33681ec`). New commit(s); do not amend `33681ec`.
**Category:** Production / Infrastructure. **Owner-requested.**
**Context:** follow-up to `ZCODE_BRIEF_TELEGRAM_CURATION_2026-10-06.md` and your report
`ZCODE_REPORT_TELEGRAM_CURATION_2026-10-06.md`. Review of `utils/notify_policy.py::flush_digest`
found the defects in §1; the owner's answers to your flagged items are in §4.

## Hard constraints (unchanged)

- `logs/TELEGRAM_OFF` stays in place. Do not remove it. Do not send any real Telegram message.
- Do not restart `idx-walkforward` (or any service). Production runs from the working tree; the owner
  restarts.
- Tests stay hermetic: no network, no writes to the real `logs/`.
- Never print tokens or secrets.

## 1. Defects in `flush_digest()` (fix all)

**D1 — Items appended during a flush are lost.** It reads every `*.jsonl`, sends, then renames every
`*.jsonl` to `.sent`. An item that a cron process appends between the read and the rename is archived
without being sent.
*Fix:* claim first, then read: atomically rename each `<day>.jsonl` → `<day>.jsonl.sending` before
reading. New appends then go to a fresh `<day>.jsonl`. On a successful send, rename `.sending` →
`.sent`. On a failed or suppressed send, merge the items back (prepend them to the live file, or keep
the `.sending` file and pick it up on the next flush). Never drop them silently.

**D2 — The digest is always rejected as HTML.** The message uses `parse_mode=HTML` but embeds
`<{event}>` (e.g. `<market.ihsg_technical>`) and the raw item text. Telegram returns 400 (unsupported
tag), so every digest goes out through the plain-text fallback, with a literal `<b>` in the title. Any
`<`, `>` or `&` in item text causes the same failure.
*Fix:* `html.escape()` the item text, and drop the `<event>` token. Use a readable section label
instead (see §3: group by section, with a header line per section). Add a test asserting that the
built message contains no unescaped `<` outside the tags you emit on purpose.

**D3 — A second flush on the same day is impossible.** The flush send is
`event=report.evening_digest` with `once_per_day`, so the late flush in §2 would be suppressed.
*Fix:* register a separate event `report.late_digest` (TIER_SEND, once_per_day). Alternatively, give
the flush a `subject` of `main` / `late`. Either is fine; say which you chose.

**D4 — The backlog after the blackout.** While `TELEGRAM_OFF` exists, every flush is suppressed and
the buffer grows. On the first flush after the owner removes the file, weeks of items would come out
as one truncated message.
*Fix:* at flush time, items older than **2 calendar days** are not sent. Archive them to `.stale` and
end the message with one line: "N older items skipped (see logs/digest_buffer)". Add a test for this.

## 2. Late flush at 20:45 WIB

Add a second scheduler job, `notify_late_digest`, at 20:45 WIB every day, calling the same flush with
the late event from D3. When the buffer is empty it must send **nothing** (no "empty digest" message).
Purpose: items buffered after 17:45 (forward-test cycle 18:30, broker flow 20:15) then arrive the same
evening instead of the next day. The 17:45 main flush stays as it is.

## 3. Shared buffer for external writers (jurnal26)

The owner's personal journal app (`~/jurnal26`, a separate repo with a separate venv, not importable
from here) will write its tier-2 items into **this** buffer, so the owner gets one digest instead of
two. Your side:

- **Document the line contract** in the `notify_policy.py` module docstring: one JSON object per line,
  appended with a single `write()` call:
  `{"event": str, "ts": float (epoch seconds), "text": str, "source": str (optional), "section": str (optional)}`.
  The file is `logs/digest_buffer/<YYYY-MM-DD WIB>.jsonl`.
- **The flush must accept lines with `source` set** (e.g. `"jurnal26"`) and events that are not in
  the registry, as long as they are in the digest buffer. The registry/classification gate applies to
  sends from this codebase, not to lines already in the buffer. A malformed line is skipped and
  logged, never fatal.
- **Group the message by section:** use `section` when present, else a section derived from the
  event prefix (`market.*` → Market, `report.*` → Reports, …). One header per section; jurnal items
  appear under their own sections (Positions, Patterns, Screener, Corporate actions, Weekly).
- **Split at Telegram's limit instead of truncating.** If the digest exceeds ~3,800 chars, send it as
  consecutive parts (part 1/2, 2/2) under the same gated event. The `.sent` archive happens only after
  all parts went out.
- I (Claude, the jurnal26 side) will point jurnal's `notify.digest()` at this file and retire its own
  17:45/19:50 timers once your commit lands. **Do not touch `~/jurnal26`.**

## 4. Owner decisions on your flagged items

1. 08:45 market-health briefing → **log-only** (keep as you have it).
2. "No strategy is admissible" sentinel → **log-only** (keep).
3. WF re-validation advisory → **log-only** (keep).
4. OHLCV reconciliation (21:00) → **tier 1, once_per_day** (keep). Add one comment at its registry line:
   "review after 1 week live; demote to digest if it fires most days".
5. Forward-test summary → stays **digest**; the 20:45 late flush (§2) gives same-evening delivery.

## 5. Tests and done-criteria

- Unit tests for D1–D4, the late flush (silent when empty), external-source lines, section grouping,
  multi-part split, and stale skip. All tests hermetic, using a tmp `DIGEST_DIR` and state file.
- Run `tests/` for the notify policy + telegram suites + `test_cron_contract.py` +
  `security/test_route_policy.py` (if any route changes), then the full suite in the background.
  Report the exact pass/fail counts.
- `python -m py_compile` on every touched file.
- Commit with a Conventional-Commits subject (`fix(ops): …` / `feat(ops): …`), push to
  `fix/telegram-curation`.
- Short report `ZCODE_REPORT_DIGEST_FOLLOWUP_2026-10-06.md`:
  - what changed, per item
  - the D3 choice
  - a sample of the rendered digest built from a fixture buffer with both 5001 and jurnal26 lines,
    as text; not sent
  - test counts
  - anything you could not do
