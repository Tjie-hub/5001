#!/bin/bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
export SECTORS_APP_MODE="${SECTORS_APP_MODE:-shadow}"
exec venv/bin/python3 app.py
