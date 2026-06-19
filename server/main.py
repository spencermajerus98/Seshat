"""FastAPI application: the API under ``/api`` plus the prebuilt React SPA.

Everything runs in one localhost process — no Node.js at runtime. Start with::

    python -m uvicorn server.main:app --host 127.0.0.1 --port 8501
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .routers import (
    auth,
    exp_meta,
    experiments,
    files,
    notebook,
    protocols,
    settings,
    summary,
    sync,
)

# Interactive docs stay off by default; this is a single-user local tool, not a
# public API. Flip SESHAT_DOCS=1 locally if you want /docs while developing.
_DOCS = os.environ.get("SESHAT_DOCS") == "1"

app = FastAPI(
    title="Seshat",
    version="3.0",
    docs_url="/api/docs" if _DOCS else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if _DOCS else None,
)

for r in (
    auth.router,
    notebook.router,
    experiments.router,
    exp_meta.router,
    protocols.router,
    files.router,
    summary.router,
    sync.router,
    settings.router,
):
    app.include_router(r)


# ── Static SPA ────────────────────────────────────────────────────────────────
_DIST = config.FRONTEND_DIST
_ASSETS = os.path.join(_DIST, "assets")
if os.path.isdir(_ASSETS):
    app.mount("/assets", StaticFiles(directory=_ASSETS), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    """Serve real static files; fall back to index.html for client routes."""
    if full_path.startswith("api/"):
        raise HTTPException(404, "Not found")

    candidate = os.path.normpath(os.path.join(_DIST, full_path))
    if full_path and candidate.startswith(_DIST) and os.path.isfile(candidate):
        return FileResponse(candidate)

    index = os.path.join(_DIST, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return HTMLResponse(
        "<h1>Seshat</h1><p>Frontend not built yet. Run "
        "<code>npm install &amp;&amp; npm run build</code> in <code>frontend/</code>.</p>",
        status_code=200,
    )
