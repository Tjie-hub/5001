# Production Engine — Security Review Report

**Date:** 2026-07-28
**Scope:** Phase 5 of the final release certification — secrets never committed, environment
validation, database safety, destructive-command protection, backup/restore integrity, token
handling, logging redaction.
**Method:** One dedicated adversarial fork plus this reviewer's own follow-up fixes. The
secret-in-git-history check (below) is the single highest-value check in this entire certification —
verified directly against full repository history, not current HEAD alone.

---

## Highest-Value Result: No Secret Has Ever Been Committed, In Any Commit, Ever

`git log --all --full-history -- .env .stockbit_token` returns nothing. A full-history filename scan
for credential-shaped paths across the repository's ~700-commit history found only `auto_token.py`
(legitimate source code, not a secret). Pickaxe searches (`git log --all -p -S/-G`) for real
Telegram bot-token patterns (`bot[0-9]{6,}:[A-Za-z0-9_-]{30,}`) and JWT patterns (`eyJ...\.eyJ`)
across all history returned **zero** real hits — every `TELEGRAM_TOKEN=` value ever committed is a
placeholder (`your_bot_token_here`, `REDACTED_TELEGRAM_TOKEN`). This is a genuinely clean result,
verified with the tools that would actually catch a historical leak, not just a current-state grep.

`.gitignore` correctly covers `.env`, `.stockbit_token`, `*.db`/`*.db-wal`/`*.db-shm`, `logs/`, and
`.playwright_state/` — verified with `git check-ignore -v` on each path, not read-and-assumed.

---

## Findings — Fixed This Session

**P1 — `STOCKBIT_PASSWORD`/`STOCKBIT_PASS` name mismatch silently disabled password redaction.**
`utils/logging_config.py`'s `_SECRET_VARS` list named the wrong env var — the real one
(`STOCKBIT_PASS`, per `auto_token.py:28`) was never in the redaction match set. **Fixed** (commit
`0c35d1b`) — one-word correction, plus the existing test (which asserted the same wrong name and thus
verified nothing about the real password) corrected to match.

**P1 — `paper_trade.py`'s exception-echoing `print()` calls bypassed redaction entirely.** Four call
sites wrote raw exception text to stdout, outside the `SecretRedactionFilter` attached to every
configured logging handler. **Fixed** (commit `21edd4d`) — routed through the module's own logger,
which automatically applies the same redaction filter with no new logic.

**P3 — `.stockbit_token.lock` not gitignored.** Empty file, no real exposure, but a hygiene gap.
**Fixed** (commit `ac2d349`).

---

## Findings — Evidenced, NOT Fixed (Required Follow-Up)

**P0 — `/telegram/updates` webhook fails open when `TELEGRAM_WEBHOOK_SECRET` is unset.**
`routes/telegram.py` skips its own HMAC verification entirely if the var is empty; `config.py`
defaults it to `""`; it's absent from `.env.example`; and `validate_config()` doesn't enforce it the
way it enforces `TELEGRAM_TOKEN`/`TELEGRAM_CHAT_ID`. If a deployment never sets this one specific,
easy-to-miss variable, an unauthenticated actor can POST to this endpoint and dispatch
`/status`/`/signals`/`/flow`/`/dashboard` with an attacker-chosen `chat_id` — redirecting live
trading signals with zero credentials. **Not fixed here**: this reviewer cannot confirm the real
production `.env` already has this set, and unilaterally hardening `validate_config()` to require it
risks refusing to boot an already-live system on its next restart if it doesn't. **Required action:
confirm this secret is actually set in production now; add the same startup enforcement already
used for the other two Telegram vars as an immediate fast-follow once confirmed safe.**

**P1 — `redact_secrets()` structurally cannot redact the live Stockbit bearer JWT.** The token lives
only in the file `.stockbit_token`, never an env var — the redaction mechanism has no way to ever
know or match its value. Any exception text that happens to embed it would leak unredacted.

**P1 — Truncation happens before redaction at 10+ call sites** (`scheduler/jobs.py`,
`scheduler/reports.py`, `scheduler/__init__.py`, `scheduler/utils.py`) — `str(e)[:120..300]` is
applied before the text reaches `send_telegram()`'s internal redaction call. A secret whose full
value straddles the truncation cutoff would leave an unredacted partial fragment. Fixing correctly
touches 10+ call sites — larger than a single-pass minimal fix.

**P1 — Committed token-write path lacks atomic write / explicit permission hardening.**
`auto_token.py`/`stockbit_fetcher.py` at committed HEAD use plain `open(file, "w")` — non-atomic
(a crash mid-write can leave a truncated token), relies entirely on process umask, never explicitly
`chmod`s to 0600. A hardened `_write_token_atomic()` (mkstemp + chmod 0600 + `os.replace`) exists but
only in local, uncommitted working-tree state — deliberately excluded from RC1 per
`Audit/RC1_RELEASE_PACKAGING_2026-07-28.md` §2c (bundled with unrelated 2026-07-27 incident-hardening
work). This finding confirms that exclusion has a real, now-documented security cost.

**P1 — `cron_wrap.sh`'s Telegram crash alert bypasses redaction entirely.** This shell-based alert
path (raw `curl`) was never in scope of the Python-only R-4 redaction fix. A cron-wrapped script
whose crash log embeds a token/URL fragment would ship it unredacted.

**P2 — `redact_secrets()` is exact-configured-value-match only, not pattern-based.** Does not
generically catch a bare JWT, an `Authorization: Bearer` fragment, or any secret-shaped string that
isn't currently the exact value of one of the ~10 tracked env vars.

**P2 — `.playwright_state/`'s live session cookies aren't covered by the secret-permission check.**
Correctly gitignored (no git-exposure risk), but as sensitive as `.stockbit_token` once populated,
and `config.py`'s mode-600 check only covers `.env`/`.stockbit_token`.

---

## Verified Clean

- **No destructive command found unprotected.** `scripts/release.sh`/`rollback.sh` never delete
  anything (symlink-swap only). `scripts/db_backup.py::prune()` is narrowly regex-scoped to its own
  backup directory with an explicit keep-set computed before any `unlink()`. `scripts/db_restore.py`
  defaults to verify-only; `--apply` moves the live DB aside with a timestamp suffix rather than
  deleting it. No unscoped `rm -rf`/`DROP TABLE`/`TRUNCATE`/`os.remove` found anywhere in
  `scripts/`, `scheduler/`, `engine/`, `data/`.
- **Raw token value is never logged in full** — `auto_token.py` explicitly logs `len(captured)`, not
  the token itself.
- **Backup integrity:** genuine SQLite online-backup API use (not `cp`), `PRAGMA integrity_check` +
  full row-count verification before compression, fail-loud on any verification failure.
- **Restore integrity:** verify-only by default; `--apply` is reversible (old DB moved aside, never
  deleted); confirmed actually run weekly with real passing logs (2026-07-12, 2026-07-19).

---

## Recommendation

No P0/P1 fixed-vs-unfixed item here changes the certification's overall GO-with-conditions posture
(see `Audit/PRODUCTION_ENGINE_RELEASE_CERTIFICATION.md`), but the `TELEGRAM_WEBHOOK_SECRET`
confirmation is the single most urgent item in this review and should be verified against the real
production environment before or immediately after this release ships.
