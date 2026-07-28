# Security & Release Hardening — Completion Report (2026-07-11)

Phase scope: route authentication, authorization, secret management,
release-based deployment, startup validation, audit trail, security tests,
documentation. Constraints honored: no trading logic, no strategies, no
provider architecture, no LangGraph, no DB redesign, no frontend work;
backward compatibility mandatory (with no new env vars set, every request
behaves exactly as before).

Closes the two remaining High-risk institutional-audit findings (2026-07-10):
**§7-1/§13 unauthenticated HTTP surface** and **§14 working-tree deployment /
untested rollback**.

## 1. Files modified / created

**New `security/` package**
- `security/auth.py` — token→role resolution (constant-time compare), 4 roles
  (viewer=1, scheduler=2, operator=2, admin=3), `AUTH_MODE` off/shadow/enforce
  (default `off`; unknown values fail closed to enforce).
- `security/route_policy.py` — all 97 registered routes classified
  public/viewer/operator/admin (method-split where GET/POST differ);
  unclassified routes require admin (fail closed).
- `security/middleware.py` — one `before_request` enforcement hook + one
  `after_request` audit hook, wired in `app.py` after blueprint registration.
- `security/routes.py` — `POST /auth/login` (session cookie so the UI works
  under enforce with zero frontend changes), `POST /auth/logout`,
  `GET /auth/whoami`.
- `security/audit_trail.py` — `audit_events` table (separate from
  `provider_events`), self-creating schema, best-effort/never-raises writes.

**Modified**
- `app.py` — auth blueprint + middleware wiring; generic JSON 500 handler (no
  tracebacks across HTTP); `/health` reports the running release version;
  boot log includes version+source.
- `config.py` — `validate_config()` extended (abort-on-failure kept):
  AUTH_MODE sanity, enforce-requires-tokens lockout guard, 16-char token
  floor, non-empty-DB core-table check, claude-CLI-on-PATH when routed,
  `.env`/`.stockbit_token` must be mode 600, `release.json` schema check.
- `utils/logging_config.py` — `SecretRedactionFilter` on both handlers (masks
  values of all known secret env vars if they ever reach a log line).
- `utils/release.py` (new) — release manifest reader with working-tree
  git-SHA fallback.
- `scripts/release.sh`, `scripts/rollback.sh` (new) — release build + atomic
  switch + rollback (details in §4 below).
- `deploy/idx-walkforward.service` — targets `~/idx-walkforward-current`;
  cutover steps in the header. **File updated only — NOT installed.**
- `engine/agent_firm/providers/alerts.py` — provider_switch audit hook
  (guarded, additive). **Left uncommitted deliberately**: the file belongs to
  the pending provider-resilience changeset awaiting operator activation.
- `.env.example`, `docs/SECURITY.md` (new), `docs/OPERATIONS.md`.

## 2. Tests added (49 new; suite 1284 → 1333)

- `tests/security/test_auth.py` (6) — mode parsing incl. unknown-fails-closed,
  token resolution (multi-token lists, empty/None), rank matrix, fingerprint.
- `tests/security/test_route_policy.py` (3) — **guard tests**: every
  registered route classified, no stale entries, method-split + fail-closed
  default verified.
- `tests/security/test_middleware.py` (10) — end-to-end through the real app:
  off=open; enforce blocks anonymous (401) / wrong role (403) / bad token
  (401); viewer read-vs-operate split; admin/viewer config split; all three
  credential carriers (Bearer, X-API-Key, query param); shadow never blocks;
  session login/logout lifecycle; whoami.
- `tests/security/test_audit_trail.py` (7) — table self-creation, never-raise
  contract, separation from provider_events, middleware records operational
  actions and auth failures, provider held/restored switches recorded.
- `tests/security/test_secret_hygiene.py` (5) — `.env`/`.stockbit_token`
  untracked, source scan for hardcoded secret literals, redaction filter
  behavior + installation, 500 response carries no traceback/exception text.
- `tests/security/test_release_scripts.py` (6) — release dir is versioned +
  read-only + manifest-complete; atomic switch; parameterless rollback returns
  to previous; named rollback; `--list` marks current; rollback with nothing
  older fails nonzero; shared paths symlinked not copied.
- `tests/security/test_release_info.py` (4) — manifest wins, working-tree
  fallback, `/health` version field.
- `tests/test_config_validation.py` (+9) — enforce-without-tokens aborts,
  short token aborts, unknown AUTH_MODE aborts, good tokens pass, foreign DB
  (wrong tables) aborts, empty DB allowed for first boot, claude-CLI check,
  invalid/valid release manifest.

“Expired credentials” (spec Phase 7): static tokens have no expiry by design;
the invalid/revoked-credential rejection path is what the tests cover, and
the absence of expiry is listed as a remaining risk below.

## 3. Test results

```
1333 passed in 419.88s   (full suite, 2026-07-11 03:15 WIB)
```

Zero failures, zero regressions (pre-phase baseline: 1284 passed). Backward
compat verified explicitly: with `AUTH_MODE` unset, existing route tests pass
untouched and `test_mode_off_everything_open` pins the legacy behavior.

## 4. Release-based deployment (implemented, cutover pending)

`scripts/release.sh`: `git archive HEAD` → `~/releases/idx-walkforward/
<YYYYmmdd-HHMMSS>-<shortsha>/`; writes `release.json` (version, git_sha,
branch, built_at, built_by); symlinks shared mutable state (`.env`, `venv`,
`logs`, root DBs, `.stockbit_token`); chmods the code read-only; flips
`~/idx-walkforward-current` atomically (`ln -sfn` + `mv -T`). Smoke-built for
real: release `20260711-030213-cb040a0` exists on disk with a correct
manifest. `scripts/rollback.sh` flips to the previous or a named version and
supports `--list`.

**The running service was NOT touched.** The installed systemd unit still
points at the legacy working-tree symlink; the updated unit file + cutover
runbook (release → cp unit → daemon-reload → restart) are ready. This is
deliberate: the working tree also carries the uncommitted provider-resilience
changeset awaiting operator activation — one restart will activate both, and
that restart is the operator's call.

## 5. Remaining security risks

1. **No TLS** — the app serves plain HTTP on 0.0.0.0:5001; bearer tokens are
   sniffable off-LAN. Front with a TLS reverse proxy before any real API
   exposure. (Unchanged from audit; out of this phase's scope.)
2. **Static tokens** — no expiry, no rotation automation, no per-user
   identity, no rate limiting/lockout on failed auth. Rotation = edit `.env`
   + restart. Failed attempts are at least audited now.
3. **AUTH_MODE=off is still the default** — the surface stays open until the
   operator runs the shadow→enforce migration (docs/SECURITY.md runbook).
4. `FLASK_SECRET_KEY` unset → per-boot random session key (login sessions
   drop on restart). Set it in `.env` before relying on session login.
5. Claude CLI subscription auth remains a privilege-boundary smell (audit
   §13, unchanged — provider architecture was out of scope).

## 6. Remaining operational risks

1. **Cutover not executed** — release-based systemd unit not installed; prod
   still runs (old code) from the working-tree path. Until cutover, §14's
   "mutable working tree" finding is closed in tooling but not in production.
2. **Uncommitted work on the branch** — the provider-resilience changeset
   (incl. `alerts.py` with the new audit hook) is uncommitted; a release
   built today would exclude it (`git archive HEAD`). Commit + release +
   restart should happen together.
3. Branch `ops/hardening-2026-07-10` (now 18 commits) is unmerged/unpushed.
4. Release GC: no pruning of old releases yet (disk growth is slow — code
   only, DBs excluded — but unbounded).
5. Audit trail lives in the same SQLite file as business data (same-disk,
   same-backup failure domain).

## 7. Production readiness score

| Dimension | 2026-07-10 audit | Now | Why |
|---|---|---|---|
| Security | Critical/High findings open | **7/10** | Full-surface RBAC implemented + guard-tested, fail-closed defaults, secret hygiene fenced, audit trail live — but not yet *enforced* in prod (mode off) and no TLS. |
| Deployment & rollback | ~2/10 (working tree, untested rollback) | **7/10** | Immutable versioned releases, atomic switch, tested rollback, startup validation, version in /health — pending the one-time cutover. |
| Overall institutional | 5/10 | **6.5/10** | Top-6 audit conditions now all have closed tooling; remaining gap is activation (enforce mode + unit cutover) and the structural Medium items (migrations framework, worker separation, DB-connect guard breadth). |

Score becomes ~7.5/10 the day the operator (a) commits the provider work,
(b) runs `scripts/release.sh` + installs the unit, and (c) walks
shadow→enforce. All three are runbook'd, reversible, and test-covered.
