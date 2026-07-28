# Production Engine — Owner Decision Package

**Date:** 2026-07-28
**Purpose:** Every item below requires a decision only the system owner can make — this review does
not silently change behavior on any of them. Each decision is prepared with evidence, options, and a
recommendation; none has been acted on unilaterally.

---

## Decision 1 (Mandatory) — Telegram Webhook Security Policy

### The question
Should `TELEGRAM_WEBHOOK_SECRET` be made a hard startup requirement (fail-closed by design), or is
the current "secure if configured, silently insecure if not" pattern acceptable given operational
context?

### Evidence gathered this pass
Direct SSH access to the live production host (`tjiesar@192.168.31.214`) confirmed, by reading the
actual file the running `idx-walkforward.service` loads (not the Windows-side copy, not an
inference):

```
/home/tjiesar/idx-walkforward-current/.env -> /home/tjiesar/10 Projects/idx-walkforward-5001/.env
TELEGRAM_WEBHOOK_SECRET: SET, non-empty
Service state: idx-walkforward.service — loaded, active, running
/health: HTTP 200
```

**The webhook is currently operating fail-closed in practice.** The code's fail-open *design* remains
(nothing prevents a future environment from omitting this variable), but there is no active exposure
today.

### Options

**Option A — Leave as-is.** The webhook is correctly secured today; add nothing. Risk: a future
redeploy to a new environment, or an operator error clearing `.env`, could silently regress to
unauthenticated — with zero signal that this happened, since nothing currently checks for it.

**Option B — Harden `validate_config()` to require `TELEGRAM_WEBHOOK_SECRET` (recommended).** Add the
same enforcement pattern already used for `TELEGRAM_TOKEN`/`TELEGRAM_CHAT_ID` — fail startup if
missing. Given production already has this set (confirmed above), this change is safe to make and
would not affect the currently-running system's next restart. Also add it to `.env.example` so future
environments are provisioned correctly from the start.

**Option C — Add a runtime warning instead of a hard failure.** Log/alert (not block boot) if unset.
Weaker than B, but avoids ever blocking a boot on this specific variable if there's a reason not to
(e.g., a test/staging environment intentionally running without Telegram wired up at all).

### Recommendation
**Option B.** Confirmed safe against the actual live configuration; closes the design gap for every
future deploy without any current-system risk. Add to `.env.example` regardless of which option is
chosen, since that gap is unconditionally worth closing.

### If approved
This is a small, isolated `config.py` + `.env.example` change, in the same spirit as the six fixes
already made this certification — not implemented here because it's the owner's call to make, per
this task's explicit instruction to prepare rather than silently change behavior on a mandatory item.

---

## Decision 2 — `validate_config()` Requiring `DB_PATH` to Pre-Exist

### The question
Should a genuinely fresh/disaster-recovery deployment be allowed to boot with no DB file at all
(matching the "fresh DB allowed" comment already in the code), or should provisioning tooling be
responsible for creating an empty placeholder first?

### Evidence
`config.py`'s `validate_config()` fails startup with `"DB_PATH does not exist"` if the file is
genuinely absent — but two lines later, a separate comment says "a brand-new DB (no tables) is
allowed." These two statements are in tension: an *empty* file is fine; a *missing* file is not,
and nothing in `scripts/release.sh`, the systemd unit, or `scripts/wait_for_health.sh` creates that
placeholder automatically.

**Does not affect the current live system** — its DB has existed since long before this check was
added.

### Options
**Option A** — relax `validate_config()` to also allow a genuinely-missing file, treating it the
same as an empty one (bootstrap it in `init_runtime()`).
**Option B** — leave the check as-is, and instead have `scripts/release.sh` or a deploy runbook step
`touch` the DB file before first boot on a new environment.

### Recommendation
**Option A** is slightly more robust (self-contained, no manual step to forget), but either closes
the gap. Not urgent — no current deploy is affected — recommend resolving before the *next* fresh
environment setup or DR drill is actually attempted, not before this release.

---

## Decision 3 — Restore-Drill Cron Gap

### The question
Why did the weekly restore-drill cron entry stop firing after 2026-07-19, while the daily backup
cron entry (which had the same ~36h gap around 07-25/26) recovered on its own?

### Evidence
Confirmed live on the production host:
- `logs/cron_db_backup.log`: entries resumed cleanly 07-26 and 07-27, both `rc=0`.
- `logs/cron_db_restore_drill.log`: last entry is 2026-07-19 — the most recent scheduled Sunday
  (2026-07-26) drill did not run, and this log file's own gap has not self-resolved the way the
  backup log's did.

This is a live, currently-open data-safety-verification gap (not a data-loss risk — backups
themselves are current and verified) as of this writing.

### Options
**Option A** — investigate directly (check `crontab -l` on the host for whether the entry still
exists, check `/var/log/syslog`/`journalctl -u cron` for the relevant window, confirm the wrapped
script itself still exists and is executable).
**Option B** — run one manual restore drill immediately as a stopgap, then investigate the cron gap
separately without urgency.

### Recommendation
**Both.** Run a manual drill this week regardless of root cause (cheap, immediately closes the
verification gap for now); separately investigate why this specific entry didn't resume like its
sibling did — could be a stale `crontab` entry, a permissions issue on that specific script, or
something removed accidentally during the same event that caused the 07-25/26 gap.

---

## Decision 4 — Land the Deferred Token-Write Hardening

### The question
Should the already-written `_write_token_atomic()` hardening for `auto_token.py`/`stockbit_fetcher.py`
(currently sitting uncommitted, deliberately excluded from RC1 per
`Audit/RC1_RELEASE_PACKAGING_2026-07-28.md` §2c) be reviewed and committed now, or deferred further?

### Evidence
This work already exists, was written for a real 2026-07-27 incident (a different one — the
`ensure_valid_token()` fallback bug, not this certification's findings), and the Security Review
independently flagged its absence from committed HEAD as a real gap (non-atomic writes, no explicit
chmod). It was excluded from RC1 purely for release-scope hygiene reasons, not because it's unready.

### Recommendation
Land it as the very next commit after this release ships — it's ready, tested (per the RC1 packaging
report's own notes), and closes a real, already-identified gap. Not a condition of this release
(RC1's own scope never included it), but shouldn't sit deferred indefinitely either.

---

## Decision Log Summary

| Decision | Blocks this release? | Recommended action | Owner sign-off needed on |
|---|---|---|---|
| 1. Webhook hardening | No (verified safe today) | Option B, as a fast-follow | Whether to harden now or defer |
| 2. DB_PATH bootstrap | No | Option A, before next fresh deploy | Which option |
| 3. Restore-drill gap | No (backups current) | Manual drill + investigate | None — just execute |
| 4. Token-write hardening | No | Land as next commit | Timing only |
