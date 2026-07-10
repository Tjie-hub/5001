#!/bin/bash
# Start IDX Strategy Suite on port 5001.
#
# Production is normally managed by systemd (deploy/idx-walkforward.service):
#   systemctl --user start idx-walkforward
# Running this script by hand launches the SAME gunicorn runtime in the
# foreground. `./start.sh dev` falls back to the Flask dev server.
cd "$(dirname "$0")"

# sectors.app overlay — observability only (logs disagreements, does not block trades).
export SECTORS_APP_MODE="${SECTORS_APP_MODE:-shadow}"

if [ "$1" = "dev" ]; then
    exec ./venv/bin/python app.py
fi
exec ./venv/bin/python -m gunicorn -c gunicorn.conf.py wsgi:app
