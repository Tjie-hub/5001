"""Production WSGI entry point (audit P-5).

Run via gunicorn — configuration and the scheduler lifecycle live in
gunicorn.conf.py (post_worker_init starts the scheduler inside the single
worker; worker_exit shuts it down gracefully):

    venv/bin/python -m gunicorn -c gunicorn.conf.py wsgi:app

Dev fallback remains `python app.py` (Flask server, same init path).
"""
from app import app  # noqa: F401
