#!/usr/bin/env bash
# Launch the multi-pane chart viewer on http://localhost:5050
set -e
cd "$(dirname "$0")"

if [ ! -d venv ]; then
  echo "Creating virtualenv…"
  python3 -m venv venv
fi

./venv/bin/pip install -q --disable-pip-version-check -r requirements.txt
exec ./venv/bin/python app.py
