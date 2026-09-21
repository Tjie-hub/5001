# ADR-005 — Frontend Deployment Strategy

| Item | Value |
|---|---|
| ADR ID | FRONTEND-ADR-005 |
| Title | Frontend deployment strategy — build automation and serving-layer topology |
| Status | **PROPOSED — decision not made.** This document lays out options and a recommendation; it does not select one. |
| Date | 2026-08-19 |
| Depends On | Interacts with ADR-006 (legacy UI disposition) on the serving-layer question — see §7. Not a hard prerequisite of it. |
| Authority | `frontend/README.md` blocker U-8 · `ADR-001` §7 ("Follow-up ADRs required" names ADR-005) · `.github/workflows/frontend.yml` `TODO(ADR-005)` block |
| Closes | Blocker **U-8** (blocks CI deploy stage, release) — closes only once an option is chosen and implemented |
| Freeze effect | None yet. On approval of an option, that option's serving-layer topology becomes FROZEN; changing it again requires a superseding ADR. |

**Naming note:** this is `FRONTEND-ADR-005`. A separate, unrelated `ADR-005` already exists inline inside
`docs/infra/CROSS_MACHINE_RESEARCH_ARCHITECTURE_v1.0.md` ("Consume the R-5 physical DB split; preserve the CI
write-fence") — a local numbering sequence for cross-machine research infrastructure, in a different namespace.
The two are not related; don't conflate them.

---

# 1. Context

## 1.1 What exists today

Production serves the frontend through a **stop-gap** added directly to `app.py` (lines ~236-266), preceded by
its own comment explaining exactly what it is and isn't:

> "Stop-gap SPA serving for frontend/ (Phase 9 React app) — `frontend/README.md` lists production deployment
> strategy as U-8/ADR-005, still undecided. This is deliberately minimal: it serves `npm run build`'s
> `frontend/dist` output for any GET path that isn't already an explicit Flask route or under `/api`... It does
> NOT touch the pre-existing Flask-template pages above (`/`, `/portfolio`, etc.) ... disposing of the legacy UI
> is ADR-006/U-9's decision, not this route's."

Concretely: a `/assets/<path:filename>` route, a `/favicon.svg` route, and a `/<path:path>` catch-all that
serves `frontend/dist/index.html` for any path not already claimed by an explicit Flask route or `/api/*`.
`security/route_policy.py` independently classifies these same three routes with the identical framing —
`# --- frontend/ SPA stop-gap serving (ADR-005/U-8 still undecided) ---`.

**This route is explicitly not ADR-005.** It is the bridge that unblocked the SPA in production while ADR-005
remains open (also documented as a stop-gap in `Audit/PRODUCTION_ENGINE_BACKLOG.md`). The question this ADR
answers is what happens *around* that bridge: whether it becomes the permanent answer, gets replaced, or gets
formalized into the release pipeline.

## 1.2 What the codebase already assumes

`frontend/vite.config.ts`'s dev-server proxy config carries its own comment stating a design intent that
predates this ADR:

> "Dev-only: the `src/api` client fetches relative `/api/v1/*` paths so the same code works unproxied once
> frontend and Flask share an origin in production (deployment strategy still undecided — README's U-8/ADR-005)."

In other words, the frontend's API client already assumes **same-origin** production serving — relative paths,
no CORS wiring on the backend. That assumption is baked into working code today, not merely a preference stated
in a doc.

## 1.3 Existing infrastructure reality

- **No TLS or reverse proxy exists anywhere in the repo today.** `gunicorn.conf.py` binds `0.0.0.0:5001`
  directly; the systemd unit (`deploy/idx-walkforward.service`) runs gunicorn as the only process; there is no
  nginx config, Dockerfile, `docker-compose.yml`, or Caddy config anywhere in the tree (`find` confirms zero
  hits). Production is bare gunicorn/systemd.
- `gunicorn.conf.py` enforces **exactly one worker** — the process embeds APScheduler and owns the SQLite
  writer (see CLAUDE.md "Never raise gunicorn `workers` above 1..."). This constraint is orthogonal to the
  deployment-strategy decision but bounds what any option can assume about the backend process model.
- `scripts/release.sh` builds an immutable release from a git archive of `HEAD`, flips a `current` symlink, and
  restarts systemd. It has **no frontend build step today** — grep for npm/vite/dist/build returns nothing.
- CI (`.github/workflows/frontend.yml`) already runs a full quality-gate pipeline (`npm ci`, lint, typecheck,
  test, build, format:check) and produces a `dist/` artifact — but stops there. The workflow file itself carries
  a verbatim TODO naming this exact gap:

  > "TODO(ADR-005): no deployment stage until the deployment and environment strategy exists. Phase 7 v1.0's
  > outline sections 57-58 (Environment Strategy, Deployment Pipeline) were dropped rather than answered in
  > v1.1, so there is no build target, hosting model, environment configuration, or decision on how this relates
  > to the existing gunicorn/systemd release pipeline. Tracked as blocker U-8."

So the CI gates already exist and already pass; the only missing piece is what happens to their output.

---

# 2. Decision Drivers

| # | Driver |
|---|---|
| C-1 | **Solo operator.** No dedicated ops/infra function — ongoing maintenance burden matters at least as much as architectural cleanliness. |
| C-2 | Existing release model is immutable-symlink + systemd (`scripts/release.sh` / `rollback.sh`); any option should fit that model rather than replace it. |
| C-3 | No TLS/reverse-proxy layer exists today for *any* part of the app — this decision is not being made against an existing proxy, it would be introducing the first one if it introduces one at all. |
| C-4 | The frontend API client already assumes same-origin relative paths in production (§1.2) — a cross-origin option would be reopening a decision the frontend code has already made, not a neutral choice among equals. |
| C-5 | CI already produces a validated `dist/` build (4 required gates); the gap is purely "what consumes it," not "how do we build it." |
| C-6 | No nginx/Docker/CDN config exists anywhere in the repo — nothing has been technically pre-committed toward a serving-layer direction. |
| C-7 | Whatever is chosen must also be able to serve the legacy Flask/Jinja routes (`/`, `/portfolio`) for as long as ADR-006 keeps them alive — the two ADRs share this surface even though they answer different questions. |

---

# 3. Options Considered

## Option 1 — Formalize the stop-gap

Keep the `app.py` catch-all (§1.1) as the permanent serving mechanism. Add a frontend build step
(`npm ci && npm run build`) into `scripts/release.sh` ahead of the existing Python/DB release packaging, so
`frontend/dist` ships inside the same immutable release directory as the backend code — no more manual
`npm run build` before a deploy. Wire the frontend.yml quality gates into the release/CI path as an actual gate
(a release can't proceed if the frontend build fails), closing the TODO comment instead of just narrating it.

| | |
|---|---|
| **What changes** | `scripts/release.sh` gains a build step; `.github/workflows/frontend.yml`'s TODO block is resolved; no new runtime component. |
| **Cost to build** | **Small.** One script addition, a manifest/version-stamp update so a release records its frontend build provenance the same way it already does for the Python side, removal of the now-stale TODO comment. |
| **Cost to maintain (solo)** | **Low.** One deployment unit (systemd + gunicorn), one health check, one log stream, one process to restart. Directly consistent with the single-process/single-worker discipline already enforced elsewhere in this repo (`gunicorn.conf.py`'s `workers=1` guard, the "production stability over feature velocity" posture CLAUDE.md documents repo-wide). Static asset serving via Flask's `send_from_directory` has no gzip/brotli negotiation tuning, no HTTP/2, no edge caching — acceptable at personal-dashboard traffic levels, not built for real external load. |
| **What breaks / needs revisiting if wrong** | If traffic, concurrent viewers, or asset payload size ever grow meaningfully, static-serving performance and cache-header control become a real limitation. Moving to Option 2 later is **additive**, not a rewrite — nginx can be dropped in front of the existing Flask app without touching its routes. This option doesn't foreclose Option 2, it just doesn't build it preemptively. |

## Option 2 — Reverse proxy separation

Introduce nginx (or Caddy) as the actual internet-facing process. It serves `frontend/dist/` static files
directly — real `Cache-Control` headers, gzip/brotli, HTTP/2 — and reverse-proxies `/api/*` (and, for however
long ADR-006 keeps them, the legacy Jinja routes) to gunicorn on `127.0.0.1:5001`. gunicorn stops binding
`0.0.0.0`.

| | |
|---|---|
| **What changes** | New proxy config file, new systemd unit for the proxy, a decision on TLS (this would also be the first time TLS exists anywhere in this stack — see C-3), `scripts/release.sh` needs to refresh whatever directory/symlink the proxy serves from, and every existing Flask route (blueprints, legacy templates, `/api/*`) needs explicit proxy rules verified against regressions. |
| **Cost to build** | **Medium.** Vite already content-hashes build output filenames, so cache-busting is close to free; the proxy-rule surface is the real work, especially getting the legacy-route passthrough right so ADR-006's interim state (whatever it lands on) keeps working unchanged. |
| **Cost to maintain (solo)** | **Medium-High.** A second service with its own security-update cadence, a second config surface that has to stay in sync with every backend route change, a second log stream to check, a second thing that can independently be down while the other is up (health-check ambiguity: is the site down because gunicorn crashed, or because nginx did?). This is the textbook "more moving parts, cleaner separation" tradeoff the task brief names explicitly. |
| **What breaks / needs revisiting if wrong** | For a solo operator, this is the classic failure mode of maintaining infrastructure sized for a team rather than the actual load. Reversal cost is real too, and grows once TLS/cert renewal lives on the proxy — unwinding it later is more disruptive than never adding it. |

## Option 3 — Split-origin static hosting

Deploy `frontend/dist/` to a separate static host (CDN, S3-equivalent, Cloudflare Pages, etc.) on a different
origin than the Flask API; the browser makes cross-origin calls to the Flask API.

| | |
|---|---|
| **Why it's the weakest fit here** | It contradicts a decision the frontend codebase has already made (C-4, §1.2) — same-origin relative-path serving is assumed in working code, not just documented as a preference. Adopting this option means reworking the API client's path assumptions, adding CORS handling to Flask (not present anywhere today — no CORS middleware exists in `security/` or `app.py`), and introducing a third-party hosting account/dependency with no supporting evidence anywhere in the repo that this was ever the intended direction (no CDN config, no Docker, nothing). |
| **Cost to build/maintain** | Not scoped in detail — including it only so the option space is complete. Choosing this effectively reopens the `vite.config.ts` same-origin assumption too, not just ADR-005 in isolation, so it's a larger decision than its label suggests. |

---

# 4. What Doesn't Change Under Any Option

- The core release model — build → immutable release directory → symlink flip → systemd restart
  (`scripts/release.sh`) — is compatible with all three options; only *what* gets built and *where it ends up*
  varies.
- The `gunicorn.conf.py` `workers = 1` constraint (APScheduler + SQLite writer ownership) is untouched by this
  decision either way — none of the three options ask gunicorn to run more than one worker.

---

# 5. Recommendation

**Recommend Option 1 — formalize the stop-gap.**

Reasoning:

1. **Lowest build and maintenance cost** for a solo operator (C-1), and the smallest change surface to close
   U-8 — a script addition and a CI-gate wire-up, not a new service.
2. **Matches the assumption already encoded in working code** (C-4) — `vite.config.ts`'s same-origin proxy
   comment already predicts exactly this outcome.
3. **Matches the existing operational philosophy** documented repeatedly across this repo: single-worker
   gunicorn, immutable-release + systemd, "production stability over feature velocity" as a consistent pattern
   rather than a one-off choice.
4. **Doesn't foreclose Option 2.** If a real reason to add a reverse proxy shows up later — genuine TLS
   requirement, genuine static-serving load — that migration is additive on top of Option 1, not a redo.

Suggested triggers for revisiting Option 2 specifically: (a) a real TLS / public-internet-exposure requirement
appears — note that would *also* motivate solving TLS for the entire app, not just the frontend, since no TLS
exists anywhere today (C-3); or (b) static asset volume/concurrent traffic genuinely stresses Werkzeug's static
serving in practice, not hypothetically.

**This is a recommendation only. Tjie decides. No implementation shall begin against any option — including
Option 1 — until one is explicitly selected.**

---

# 6. Open Questions

| # | Question |
|---|---|
| Q-1 | Is there a TLS / public-internet-exposure requirement on any near-term horizon? This changes whether Option 2's TLS argument is live now or hypothetical, and whether it should be evaluated together with a repo-wide TLS decision rather than a frontend-only one. |
| Q-2 | Once an option is picked, should the CI build gate (`frontend.yml`) actually **block** `scripts/release.sh` from proceeding on failure, or stay advisory? Not resolved here — an implementation detail downstream of picking an option. |
| Q-3 | See §7 — this ADR and ADR-006 share the "what serves the legacy Jinja routes" surface. Whichever option is chosen here needs to keep serving those routes unchanged for as long as ADR-006 keeps them alive. |

---

# 7. Relationship to ADR-006

ADR-006 (legacy UI disposition) decides *whether and when* `/` and `/portfolio` retire. This ADR decides *how
the frontend gets built and served*, independent of that timeline. The two intersect only at one point: whatever
serving layer this ADR selects must continue serving the legacy Flask routes correctly for however long ADR-006
keeps them around.

- Under **Option 1** (recommended here), this is already true today — the Flask app serves both the legacy
  routes and the SPA catch-all side by side, and nothing about formalizing the stop-gap changes that.
- Under **Option 2**, the reverse-proxy rules would need explicit passthrough for the legacy routes, not just
  `/api/*` and `dist/` — an extra piece of proxy configuration to get right and keep right as ADR-006 executes.
- Under **Option 3**, the legacy routes stay served by Flask directly (same-origin with the API, unlike the
  SPA) — meaning the app would straddle two different origin models simultaneously, one more reason Option 3 is
  the weakest fit while any legacy route is still live.

Neither ADR blocks the other from being decided first.

---

**Status:** **PROPOSED — awaiting owner decision.** No option is approved. No implementation shall begin.

# End of ADR
