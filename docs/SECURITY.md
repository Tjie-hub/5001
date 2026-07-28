# Security Guide

Security hardening phase (2026-07-11). Closes institutional-audit §7-1 /
§13: route authentication + authorization, secret hygiene, audit trail.
Backward compatible: with `AUTH_MODE` unset (or `off`) the HTTP surface
behaves exactly as before.

## Authentication

Static API tokens, configured only via environment variables (never in
source). A request may present its token three ways:

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:5001/api/signals/today
curl -H "X-API-Key: $TOKEN"            http://localhost:5001/api/signals/today
curl "http://localhost:5001/api/signals/today?api_key=$TOKEN"
```

Browser/UI use (no frontend changes needed): log in once per session —

```bash
curl -c cookies.txt -X POST http://localhost:5001/auth/login \
     -H 'Content-Type: application/json' -d "{\"token\": \"$TOKEN\"}"
```

or from the browser devtools console:
`fetch('/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({token:'...'})})`.
The session cookie then authenticates page and API requests.
`POST /auth/logout` clears it; `GET /auth/whoami` reports mode + role.

### Modes (`AUTH_MODE`)

| Mode | Behavior |
|---|---|
| `off` (default) | No checks. Legacy behavior. |
| `shadow` | Credentials evaluated; would-be denials logged + audited; nothing blocked. |
| `enforce` | Missing credential → 401; insufficient role → 403. Fail closed. |

Unknown `AUTH_MODE` values fail closed to `enforce` at request time and are
rejected by startup validation.

### Migration path

1. Generate tokens: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Add `AUTH_TOKEN_*` values to `.env`, set `AUTH_MODE=shadow`, restart.
3. Watch `logs/app.log` for `shadow-auth` warnings and `audit_events` for
   `shadow_allowed` rows; fix any client that would be denied (give the
   scheduler/cron scripts the scheduler token, dashboards a viewer token).
4. Set `AUTH_MODE=enforce`, restart. Startup validation refuses `enforce`
   with no tokens configured (lockout guard).

## Authorization (roles)

Comma-separated token lists per role:

| Env var | Role | Rank | May access |
|---|---|---|---|
| `AUTH_TOKEN_VIEWER` | viewer | 1 | read-only APIs, UI pages, /metrics |
| `AUTH_TOKEN_OPERATOR` | operator | 2 | viewer + manual scans, backtests, paper open/close, scheduler run |
| `AUTH_TOKEN_SCHEDULER` | scheduler (internal) | 2 | same rank as operator — for cron/internal callers |
| `AUTH_TOKEN_ADMIN` | admin | 3 | everything: config changes, agent/provider controls, telegram controls, clear-history |

Every registered route is classified in `security/route_policy.py`
(public/viewer/operator/admin). Unclassified routes require admin (fail
closed) and `tests/security/test_route_policy.py` fails CI if a new route is
left unclassified. Public routes: `/health`, `/static/*`, `/auth/*`, and
`/telegram/updates` (protected by its own `TELEGRAM_WEBHOOK_SECRET` HMAC).

## Audit trail

`audit_events` table in the main DB (deliberately separate from
`provider_events`). Recorded: auth failures (enforce and shadow), successful
operator/admin mutations (`operational_action`, `config_change`,
`admin_action`), provider availability switches (`provider_switch`). Writes
are best-effort and never break the request path.

```sql
SELECT ts, action, actor_role, actor_fingerprint, resource, outcome
FROM audit_events ORDER BY ts DESC LIMIT 20;
```

Actors are identified by a sha256[:12] token fingerprint — raw tokens never
touch the DB or logs.

## Secret management checklist

- Secrets live only in `.env` (mode 600, gitignored) and `.stockbit_token`
  (600). Startup validation **aborts** if either is group/world accessible.
- No credentials in source: `tests/security/test_secret_hygiene.py` scans
  every production `.py` for hardcoded secret-shaped literals and asserts
  `.env`/`.stockbit_token` are untracked.
- Log redaction: `SecretRedactionFilter` (utils/logging_config.py) masks the
  values of all known secret env vars (`TELEGRAM_TOKEN`, `ZAI_API_KEY`,
  `AUTH_TOKEN_*`, …) if they ever reach a log line.
- HTTP 500 responses carry only `{"error", "request_id"}` — stack traces go
  to the JSON log, never across the HTTP boundary.
- Rotation: edit `.env`, restart the service. (Tokens are static bearer
  secrets; expiry/rotation automation is a known remaining risk — see the
  hardening report.)

## Remaining risks (acknowledged)

- No TLS termination in the app — front with a TLS reverse proxy before any
  non-LAN exposure; bearer tokens over plain HTTP are sniffable.
- Static tokens: no expiry, no per-user identity, no rate limiting.
- The Flask session cookie key falls back to `os.urandom` per boot when
  `FLASK_SECRET_KEY` is unset (sessions drop on restart; set it in `.env`).
