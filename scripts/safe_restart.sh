#!/usr/bin/env bash
# Restart idx-walkforward only if the working tree boots (scripts/preflight_boot.py). 2026-10-15: a commit that
# could not boot was restarted straight into a 2.5-minute outage. The running service is untouched on failure.
set -euo pipefail
cd "$(dirname "$0")/.."
if ! venv/bin/python scripts/preflight_boot.py; then
  echo "safe_restart: preflight failed -- NOT restarting; the running service keeps serving" >&2
  exit 1
fi
systemctl --user restart idx-walkforward
systemctl --user is-active idx-walkforward
