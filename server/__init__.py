"""Seshat HTTP layer — a thin FastAPI API over :mod:`core`.

The backend holds the decrypted database connection in server memory only
(keyed by an opaque session cookie) and serves the prebuilt React frontend as
static files, so the whole app runs as a single localhost process.
"""
