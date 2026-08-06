# Task 2B-3 — Read-Only Configuration API

**Status:** Approved 2026-08-06 (Production Engine Phase 2, Workstream 2B, Task 3 of 4).
Builds on the frozen v1 foundation and 2B-1/2B-2; no framework changes.

## Configuration sources audited

- `config.py` — the central `.env` reader. Holds `DB_PATH`, `EDGE_SCORE_MODE` (+ `edge_mode()`
  getter), and several fields that are secrets by definition (`TELEGRAM_TOKEN`,
  `TELEGRAM_WEBHOOK_SECRET`, `FLASK_SECRET_KEY`) — none of the latter are exposed.
- `security/auth.py::auth_mode()` — existing getter for `AUTH_MODE`.
- `engine/agent_firm/config.py` — the agent firm's own config module, already exposing
  `FIRM_ENABLED`, `FIRM_ENFORCE`, `GOVERNOR_ENABLED` as plain module constants (computed once
  at import, same lifecycle as every other agent-firm setting) — no secrets among these three.
- `utils/release.py::release_info()` — already the source for `/health`'s version field; safe,
  already-established reuse (`version`, `source`, and — only for a built release — `git_sha`,
  `built_at`).
- `utils/logging_config.py::_SECRET_VARS` — the pre-existing, security-hardening-vetted list of
  env vars this repo already classifies as secret (`TELEGRAM_TOKEN`, `ZAI_API_KEY`,
  `DEEPSEEK_API_KEY`, `TAVILY_API_KEY`, `FLASK_SECRET_KEY`, `STOCKBIT_PASS`,
  `AUTH_TOKEN_ADMIN/OPERATOR/VIEWER/SCHEDULER`, `TELEGRAM_WEBHOOK_SECRET`). Used here as
  confirmation of what NOT to expose, not as a mechanism (see "approach" below).
- `scheduler.WIB` — the existing `Asia/Jakarta` tz constant, already used everywhere else for
  scheduling.
- `logging.getLogger().getEffectiveLevel()` — live introspection of the actual configured
  level; no separate `LOG_LEVEL` env var exists in this repo (`setup_logging()` hardcodes
  `INFO`), so this reads Python's own logging state rather than inventing a config field.

## Approach: explicit allowlist, not a redacted dump

Two ways to build a "safe config" endpoint: (a) enumerate every env var and redact/mask
anything matching a secret pattern, or (b) hand-pick a small, fixed set of known-safe fields
and expose only those. **(b) is used.** A blocklist/redaction approach is one missed pattern
away from a leak the next time a var is added; an allowlist can only ever under-expose, which
is exactly the posture this task asks for ("when uncertain, omit... prefer too little than too
much"). `utils/logging_config._SECRET_VARS` was cross-checked against the allowlist below to
confirm no overlap, not used as the exposure mechanism itself.

## New service module

`engine/config_info.py` — `get_config_summary()` / `get_runtime_config()`, pure aggregation
over the sources above (no new env reads of its own except one gap below). Keeps
`routes/v1/config.py` a thin call-and-wrap, matching the required
Route → Configuration service → Existing configuration module layering.

**One gap found:** `SECTORS_APP_MODE` has no existing reusable getter — it's read inline in
`scheduler/scanner.py` (`os.getenv("SECTORS_APP_MODE", "off")`, line ~215), not exposed as a
function. Per this task's own explicit instruction ("if a reusable service/helper is needed,
place it in the service layer"), a `sectors_app_mode()` getter is added to `config.py`,
mirroring `edge_mode()`'s existing style exactly (same shape, same file, same pattern already
proven for `EDGE_SCORE_MODE`). `scheduler/scanner.py`'s own inline read is untouched — this
adds a second, independent reader for API-exposure purposes only; zero behavior change.

## Endpoints (kept as suggested — no reorganization needed)

- `GET /api/v1/config` — build/static facts: `{version, release_source, git_sha?, built_at?,
  database_backend: "sqlite", timezone: "Asia/Jakarta", logging_level}`. `git_sha`/`built_at`
  only present for a built release (`release_info()`'s own conditional shape — not normalized
  away, passed through as-is).
- `GET /api/v1/config/runtime` — mode/feature-flag surface: `{auth_mode, edge_score_mode,
  sectors_app_mode, agent_firm_enabled, agent_firm_enforce, agent_firm_governor_enabled}`.
- Both: `VIEWER`. Nothing here rises to a more sensitive tier than the mode flags already
  exposed at `AUTH_MODE`-adjacent VIEWER routes elsewhere in this repo.

## Fields explicitly excluded (and why)

- `DB_PATH` (raw value) — a private filesystem path; only `database_backend: "sqlite"` is
  exposed, not the path itself ("never expose private file paths unless already considered
  operationally safe" — this one isn't already exposed anywhere, so it's excluded).
- `TELEGRAM_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_CHAT_ID`, `WEBHOOK_URL` — secret or
  identifies a private chat; `TELEGRAM_CHAT_ID`/`WEBHOOK_URL` aren't credentials but are
  low-value operationally and not worth the judgment call.
- `FLASK_SECRET_KEY`, every `AUTH_TOKEN_*`, `ZAI_API_KEY`, `DEEPSEEK_API_KEY`, `TAVILY_API_KEY`,
  `STOCKBIT_USER`/`STOCKBIT_PASS` — credentials or PII (`STOCKBIT_USER` is an email).
- Agent-firm numeric tuning (spend caps, timeouts, governor rate constants, circuit-breaker
  thresholds, provider order) — not secrets, but far more detail than "operational visibility"
  needs and drifts fast; only the three on/off flags already called out as acceptable
  (`agent_firm_enabled`, `agent_firm_enforce`, `agent_firm_governor_enabled`) are exposed.
- "Scheduler enabled" — no such distinct config flag exists (the scheduler always starts in
  `init_runtime()`); live scheduler state is already `/api/v1/scheduler`'s job, not duplicated
  here.
