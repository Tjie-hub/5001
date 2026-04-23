#!/bin/bash
# Start IDX Strategy Suite on port 5001
cd "$(dirname "$0")"
exec ./venv/bin/python app.py "$@"
