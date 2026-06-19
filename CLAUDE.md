# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running the app

```bash
# Windows (recommended — handles venv creation and dependency install automatically)
run_seshat.bat

# Manual start (any OS)
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
python -m uvicorn server.main:app --host 127.0.0.1 --port 8501
```

The app opens at **http://127.0.0.1:8501**. Enable interactive API docs by setting `SESHAT_DOCS=1` in the environment before starting (`/api/docs`).

### Running tests

```bash
pytest -q                        # full suite
pytest tests/test_notebook.py    # single file
pytest -k "test_add_entry"       # single test by name
```

All tests use an in-memory temporary database via `tests/conftest.py`'s `conn` fixture — no app startup required.

### Frontend development

```bash
cd frontend
npm install
npm run build      # rebuild frontend/dist (committed to repo; required by backend)
npm run dev        # hot-reload dev server at :5173, proxies /api → :8501
```

The prebuilt `frontend/dist` is committed and served directly by FastAPI at runtime. Node.js is not needed to run the app — only to rebuild after changes to `frontend/src`.

## Architecture

Seshat is a single localhost process: a FastAPI backend (`server/`) exposes a JSON API under `/api` and serves the prebuilt React SPA (`frontend/dist`). There is no cloud connectivity.

### Layer map

```
core/        Pure Python business logic — db, crypto, notebook, experiments,
             exp_types, vocab, files, importers, sync, summary, models.
             No FastAPI imports; fully unit-tested.

server/      Thin FastAPI wrappers over core/. One file per domain router
             (routers/). Shared concerns: config.py (paths), security.py
             (session registry), deps.py (FastAPI dependencies), schemas.py.

frontend/    React 18 + Vite + TypeScript + Mantine 7 + TanStack Query 5.
             src/api.ts is the single fetch wrapper (all requests go to /api).
             src/auth.tsx manages lock/unlock state globally.

tests/       pytest against core/ and FastAPI (via TestClient).
```

### Session and authentication model

There is no user account system. The user supplies a passphrase at the lock screen, which becomes the SQLCipher encryption key. `server/security.py` keeps a process-local dict (`_sessions`) mapping random opaque tokens → open database connections. The token is sent to the browser as an httponly same-site cookie (`seshat_session`). Every authenticated API request resolves its connection through `server/deps.py:current_session` → `server/deps.py:db` (a context manager that holds `sess.lock` to serialise concurrent access to the shared connection). Sessions auto-expire after 1 hour of idle.

### Database

`core/db.py` handles backend selection: **SQLCipher** (`sqlcipher3-wheels`) when available, falling back silently to standard `sqlite3` (no encryption). `db.connect()` opens or creates the database, runs the schema, runs additive migrations (`_run_migrations`), and seeds default vocab + experiment types on first use. All schema lives in `core/db.SCHEMA` plus `_EXPERIMENT_COLUMNS_V2` (columns added in v2 upgrade).

Data files written by the app are under `data/` (database, config JSON); Syncthing inbox is `inbox/`. Both are gitignored.

### Frontend ↔ backend contract

All API calls go through `src/api.ts`. The SPA is a same-origin app in production (FastAPI serves `dist/`); during `npm run dev`, Vite proxies `/api` to port 8501. There are no external API calls — the frontend is completely offline-capable once built.
