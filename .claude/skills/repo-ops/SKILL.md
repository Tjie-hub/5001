---
name: repo-ops
description: Manual data-fetch operations (flow/keystats/token refresh) and release/deploy/rollback commands for this repo. Use when asked to fetch flow or keystats data by hand, refresh the Stockbit token, deploy a release, restart the service, or roll back.
---

Migrated from root `CLAUDE.md` (2026-08-27, /doctor lazy-loading migration) — content unchanged,
only relocated so these commands load only when actually needed instead of every session.

**Manual data operations:**
```bash
python3 flow_filter.py                     # fetch flow for all tickers, save to DB
python3 flow_filter.py BBCA BRPT TLKM       # quick test for specific tickers (no DB write)
python3 stockbit_fetcher.py                 # fetch keystats for IDX80
python3 stockbit_fetcher.py flow            # flow fetch for IDX80
python3 auto_token.py --check               # check if Stockbit JWT is still valid
python3 auto_token.py                       # headless token refresh via Playwright
```

**Release / deploy** (see `docs/OPERATIONS.md` for the full runbook):
```bash
scripts/release.sh                         # build immutable release from git archive HEAD, flip `current` symlink
systemctl --user restart idx-walkforward
scripts/wait_for_health.sh
scripts/rollback.sh --list | scripts/rollback.sh [<version>]
```
