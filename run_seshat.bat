@echo off
REM ============================================================
REM  Seshat launcher (Windows)
REM  - Creates a local virtual environment on first run
REM  - Installs/repairs dependencies if anything is missing
REM  - Serves the app at http://127.0.0.1:8501 (localhost only)
REM
REM  The web UI is a prebuilt static bundle (frontend\dist), so
REM  Node.js is NOT required to run Seshat — only Python 3.11+.
REM ============================================================
setlocal
cd /d "%~dp0"

REM --- Ensure a virtual environment exists -------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo [Seshat] First run: creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [Seshat] ERROR: could not create venv. Is Python installed and on PATH?
        pause
        exit /b 1
    )
)
call ".venv\Scripts\activate.bat"

REM --- Ensure dependencies are actually installed ------------------------
REM Don't trust that the venv folder exists; verify the web stack imports.
REM This self-heals a venv left half-installed by an earlier failed install.
python -c "import fastapi, uvicorn, pypdf" >NUL 2>&1
if errorlevel 1 (
    echo [Seshat] Installing dependencies ^(this can take a few minutes^)...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [Seshat] ERROR: dependency installation failed. See the messages above.
        echo          Check your internet connection and that Python 3.11+ is installed.
        pause
        exit /b 1
    )
)

REM --- Final sanity check ------------------------------------------------
python -c "import fastapi, uvicorn, pypdf" >NUL 2>&1
if errorlevel 1 (
    echo [Seshat] ERROR: the web stack still isn't installed after setup. Cannot start.
    pause
    exit /b 1
)

echo [Seshat] Starting at http://127.0.0.1:8501  (open it in your browser)
start "" "http://127.0.0.1:8501"
python -m uvicorn server.main:app --host 127.0.0.1 --port 8501

pause
endlocal
